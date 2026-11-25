"""Factory-scoped staffing, leave approval and explainable dispatch recommendations."""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from .db import rows, one, now, audit

SKILLS = ('生产操作', '设备点检', '工艺调整', '质量检验')


def fail(message, status=400):
    from .api import ApiError
    raise ApiError(message, status)


def text_value(b, key, limit=80, optional=False):
    value = b.get(key, '')
    if not isinstance(value, str) or len(value.strip()) > limit or (not optional and not value.strip()):
        fail('请填写有效的' + {'name':'姓名 / 名称','code':'工号','reason':'请假原因','review_note':'审批说明'}.get(key,key))
    return value.strip()


def integer(value, minimum=1, maximum=1000000):
    if isinstance(value, bool) or not re.fullmatch(r'\d+', str(value)):
        fail('编号或人数必须为整数')
    value = int(value)
    if not minimum <= value <= maximum: fail('编号或人数超出范围')
    return value


def timestamp(value):
    try:
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?', value): raise ValueError()
        return datetime.fromisoformat(value)
    except (ValueError, TypeError): fail('日期时间格式不正确，请使用工厂当地时间')


def day_value(value):
    try:
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value): raise ValueError()
        return datetime.strptime(value, '%Y-%m-%d')
    except (ValueError, TypeError): fail('排班日期不正确')


def shift_times(day, start, end):
    day_value(day)
    if not all(isinstance(t,str) and re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',t) for t in (start,end)):
        fail('班次时间须为 HH:MM')
    first = timestamp(day + 'T' + start)
    last = timestamp(day + 'T' + end)
    if last <= first: last += timedelta(days=1)
    if (last-first).total_seconds() > 12*3600: fail('单班时长不得超过 12 小时，请拆分班次')
    return first.isoformat(timespec='seconds'), last.isoformat(timespec='seconds')


def scoped(c, user, table, record_id):
    from .api import scope
    assert table in ('staff_employees','staff_shifts','staff_plans','staff_leaves')
    item = one(c, 'SELECT * FROM '+table+' WHERE id=?', (integer(record_id),))
    if not item: fail('记录不存在',404)
    scope(user,item['factory_id'])
    return item


def check_version(item,b):
    if integer(b.get('version')) != item['version']: fail('记录已被其他人修改，请刷新后重试',409)


def employee_rows(c,factory):
    items=rows(c,'SELECT e.*,u.username FROM staff_employees e LEFT JOIN users u ON u.id=e.user_id WHERE e.factory_id=? ORDER BY e.code',(factory,))
    for e in items: e['skills']=json.loads(e['skills'])
    return items


def overlap(a,b,start,end):
    return a < end and b > start


def approved_leave(c,employee,start,end):
    return one(c,"SELECT id FROM staff_leaves WHERE employee_id=? AND status='已批准' AND start_at<? AND end_at>?",(employee,end,start))


def plan_rows(c,factory,start,end):
    plans=rows(c,'SELECT p.*,s.name shift_name FROM staff_plans p JOIN staff_shifts s ON s.id=p.shift_id WHERE p.factory_id=? AND p.start_at<? AND p.end_at>? ORDER BY p.start_at,p.line,p.id',(factory,end,start))
    assignments=rows(c,'SELECT a.* FROM staff_assignments a JOIN staff_plans p ON p.id=a.plan_id WHERE p.factory_id=? AND p.start_at<? AND p.end_at>?',(factory,end,start))
    for p in plans: p['employee_ids']=[a['employee_id'] for a in assignments if a['plan_id']==p['id']]
    return plans


def overview(c,user,p):
    from .api import scope
    factory=scope(user,p.get('factory_id')) or 1
    start=day_value(p.get('date') or datetime.now().date().isoformat())
    end=start+timedelta(days=7)
    current=now()
    employees=employee_rows(c,factory)
    own=next((e for e in employees if e['user_id']==user['id']),None)
    manage=user['role'] in ('admin','manager')
    personal=user['role']=='operator'
    if personal: employees=[own] if own else []
    visible={e['id'] for e in employees}
    leaves=rows(c,'SELECT l.*,e.name employee_name FROM staff_leaves l JOIN staff_employees e ON e.id=l.employee_id WHERE l.factory_id=? AND ((l.start_at<? AND l.end_at>?) OR l.status=\'待审批\') ORDER BY l.start_at DESC',(factory,end.isoformat(),start.isoformat()))
    leaves=[l for l in leaves if l['employee_id'] in visible]
    for l in leaves:
        if not manage and (not own or l['employee_id']!=own['id']):
            l['reason']='仅本人及负责人可见'; l['review_note']=''
    plans=plan_rows(c,factory,start.isoformat(),end.isoformat())
    if personal:
        plans=[p for p in plans if own and own['id'] in p['employee_ids']]
        for p in plans: p['employee_ids']=[own['id']]
    warnings=[]
    for plan in plans:
        available=[]
        absent=[]
        for eid in plan['employee_ids']:
            if any(l['employee_id']==eid and l['status']=='已批准' and overlap(l['start_at'],l['end_at'],plan['start_at'],plan['end_at']) for l in leaves): absent.append(eid)
            else: available.append(eid)
        plan['leave_ids']=absent
        plan['available_count']=len(available)
        plan['shortage']=0 if personal or plan['status']=='已取消' else max(0,plan['required_count']-len(available))
        if plan['shortage']:
            warnings.append({'plan_id':plan['id'],'message':f"{plan['work_date']} {plan['line']} · {plan['shift_name']} 缺 {plan['shortage']} 人（请假重叠人员不计整班可用）"})
        plan['phase']='已取消' if plan['status']=='已取消' else '已结束' if current>=plan['end_at'] else '当班' if current>=plan['start_at'] else '待上班'
    # Live duty counts are based on the current time, independent of the week being browsed.
    duty=rows(c,"SELECT DISTINCT a.employee_id FROM staff_assignments a JOIN staff_plans p ON p.id=a.plan_id WHERE p.factory_id=? AND p.status='已发布' AND p.start_at<=? AND p.end_at>?",(factory,current,current))
    on_duty={r['employee_id'] for r in duty if r['employee_id'] in visible and not approved_leave(c,r['employee_id'],current,(datetime.fromisoformat(current)+timedelta(seconds=1)).isoformat())}
    return {'employees':employees,'shifts':rows(c,'SELECT * FROM staff_shifts WHERE factory_id=? ORDER BY start_time',(factory,)),
            'plans':plans,'leaves':leaves,'warnings':warnings,'skills':SKILLS,
            'lines':[r['line'] for r in rows(c,'SELECT DISTINCT line FROM devices WHERE factory_id=? ORDER BY line',(factory,))],
            'accounts':rows(c,'SELECT id,name,username FROM users WHERE factory_id=? AND active=1 ORDER BY id',(factory,)) if manage else [],
            'own_employee_id':own['id'] if own else None,'can_manage':manage,'personal':personal,
            'date':start.date().isoformat(),'updated_at':current,'on_duty_ids':list(on_duty),
            'summary':{'active':sum(e['status']=='在职' for e in employees),'on_duty':len(on_duty),'plans':sum(p['status']=='已发布' for p in plans),'shortage':sum(p['shortage'] for p in plans),'pending':sum(l['status']=='待审批' for l in leaves)}}


def validate_assignments(c,employees,ids,start,end,skill,exclude=None):
    warnings=[]
    for eid in ids:
        e=next((e for e in employees if e['id']==eid),None)
        if not e or e['status']!='在职': fail('排班人员必须是在职的本厂员工')
        if skill and skill not in e['skills']: fail(e['name']+'缺少所需技能：'+skill)
        if approved_leave(c,eid,start,end): fail(e['name']+'在该时段已有批准的请假，请选择替班人员',409)
        other=rows(c,"SELECT p.* FROM staff_plans p JOIN staff_assignments a ON a.plan_id=p.id WHERE a.employee_id=? AND p.status='已发布' AND p.id<>?",(eid,exclude or 0))
        for plan in other:
            if overlap(plan['start_at'],plan['end_at'],start,end): fail(e['name']+'已有重叠排班（含跨日班次）',409)
            gap=min(abs((timestamp(start)-timestamp(plan['end_at'])).total_seconds()),abs((timestamp(end)-timestamp(plan['start_at'])).total_seconds()))
            if gap < 11*3600: warnings.append(e['name']+'相邻班次间隔不足 11 小时，请负责人核对休息安排')
    return sorted(set(warnings))


def save_employee(c,user,b):
    from .api import role,scope
    role(user,'manager')
    old=scoped(c,user,'staff_employees',b['id']) if b.get('id') else None
    factory=old['factory_id'] if old else scope(user,b.get('factory_id')) or 1
    if old: check_version(old,b)
    skills=b.get('skills')
    if not isinstance(skills,list) or not skills or any(s not in SKILLS for s in skills): fail('请选择至少一项有效技能')
    skills=sorted(set(skills))
    status=b.get('status','在职')
    if status not in ('在职','停用'): fail('员工状态无效')
    uid=integer(b['user_id']) if b.get('user_id') else None
    if uid and not one(c,'SELECT id FROM users WHERE id=? AND factory_id=? AND active=1',(uid,factory)): fail('只能绑定本工厂启用的登录账号')
    if uid and one(c,'SELECT id FROM staff_employees WHERE user_id=? AND id<>?',(uid,old['id'] if old else 0)): fail('该账号已绑定其他员工',409)
    if old:
        future=rows(c,"SELECT p.required_skill FROM staff_plans p JOIN staff_assignments a ON a.plan_id=p.id WHERE a.employee_id=? AND p.status='已发布' AND p.end_at>?",(old['id'],now()))
        if future and status!='在职': fail('员工仍有未结束的排班，请先调班或取消安排',409)
        if any(p['required_skill'] and p['required_skill'] not in skills for p in future): fail('所删除的技能仍被未结束的排班使用',409)
    values=(uid,text_value(b,'code',40),text_value(b,'name'),text_value(b,'workshop'),text_value(b,'position'),text_value(b,'team'),json.dumps(skills,ensure_ascii=False),status)
    if old:
        c.execute('UPDATE staff_employees SET user_id=?,code=?,name=?,workshop=?,position=?,team=?,skills=?,status=?,version=version+1 WHERE id=?',values+(old['id'],)); eid=old['id']
    else:
        eid=c.execute('INSERT INTO staff_employees(user_id,code,name,workshop,position,team,skills,status,factory_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',values+(factory,now())).lastrowid
    audit(c,user,'更新员工档案' if old else '新增员工档案',str(eid),'员工 '+values[2],factory)
    return {'id':eid}


def save_shift(c,user,b):
    from .api import role,scope
    role(user,'manager')
    old=scoped(c,user,'staff_shifts',b['id']) if b.get('id') else None
    factory=old['factory_id'] if old else scope(user,b.get('factory_id')) or 1
    if old: check_version(old,b)
    shift_times('2026-01-01',b.get('start_time'),b.get('end_time'))
    values=(text_value(b,'name'),b['start_time'],b['end_time'])
    if old:
        c.execute('UPDATE staff_shifts SET name=?,start_time=?,end_time=?,version=version+1 WHERE id=?',values+(old['id'],)); sid=old['id']
    else:
        sid=c.execute('INSERT INTO staff_shifts(name,start_time,end_time,factory_id) VALUES(?,?,?,?)',values+(factory,)).lastrowid
    audit(c,user,'设置班次',str(sid),' / '.join(values)+'；已有排班保留原时间',factory)
    return {'id':sid}


def save_plan(c,user,b):
    from .api import role,scope
    role(user,'manager')
    old=scoped(c,user,'staff_plans',b['id']) if b.get('id') else None
    factory=old['factory_id'] if old else scope(user,b.get('factory_id')) or 1
    if old:
        check_version(old,b)
        if old['status']=='已取消': fail('已取消的排班不能修改')
        if old['end_at']<=now(): fail('已结束的排班不能修改')
    if old and b.get('action')=='cancel':
        note=text_value(b,'note',500)
        c.execute("UPDATE staff_plans SET status='已取消',note=?,version=version+1 WHERE id=?",(note,old['id']))
        audit(c,user,'取消排班',str(old['id']),note,factory)
        return {'id':old['id'],'warnings':[]}
    shift=scoped(c,user,'staff_shifts',b.get('shift_id'))
    if shift['factory_id']!=factory: fail('班次必须属于本工厂')
    work_date=day_value(b.get('work_date')).date().isoformat()
    start,end=shift_times(work_date,shift['start_time'],shift['end_time'])
    # Staffing-only edits must not silently adopt later changes to the shift template.
    if old and old['shift_id']==shift['id'] and old['work_date']==work_date: start,end=old['start_at'],old['end_at']
    if end<=now(): fail('不能发布已经结束的班次')
    line=text_value(b,'line')
    if not one(c,'SELECT id FROM devices WHERE factory_id=? AND line=?',(factory,line)): fail('请选择本工厂已有产线')
    skill=text_value(b,'required_skill',40,True)
    if skill and skill not in SKILLS: fail('岗位技能无效')
    count=integer(b.get('required_count'),1,100)
    ids=b.get('employee_ids')
    if not isinstance(ids,list) or len(ids)>100: fail('请选择有效的排班人员')
    ids=[integer(i) for i in ids]
    if len(set(ids))!=len(ids): fail('同一员工不能重复排班')
    if len(ids)>count: fail('安排人数超过岗位需求，请先调整需求人数')
    duplicate=one(c,"SELECT id FROM staff_plans WHERE factory_id=? AND line=? AND status='已发布' AND start_at<? AND end_at>? AND id<>?",(factory,line,end,start,old['id'] if old else 0))
    if duplicate: fail('同一产线已有重叠班次，请在原排班中调班',409)
    warnings=validate_assignments(c,employee_rows(c,factory),ids,start,end,skill,old['id'] if old else None)
    if len(ids)<count: warnings.append('该班次缺 '+str(count-len(ids))+' 人，请继续补员')
    note=text_value(b,'note',500,True)
    values=(shift['id'],work_date,line,start,end,count,skill,note)
    before=rows(c,'SELECT employee_id FROM staff_assignments WHERE plan_id=?',(old['id'],)) if old else []
    if old:
        pid=old['id']
        c.execute('UPDATE staff_plans SET shift_id=?,work_date=?,line=?,start_at=?,end_at=?,required_count=?,required_skill=?,note=?,version=version+1 WHERE id=?',values+(pid,))
        c.execute('DELETE FROM staff_assignments WHERE plan_id=?',(pid,))
    else:
        pid=c.execute('INSERT INTO staff_plans(shift_id,work_date,line,start_at,end_at,required_count,required_skill,note,factory_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',values+(factory,now())).lastrowid
    c.executemany('INSERT INTO staff_assignments(plan_id,employee_id) VALUES(?,?)',[(pid,eid) for eid in ids])
    audit(c,user,'调整排班' if old else '发布排班',str(pid),json.dumps({'before':{'start':old['start_at'],'end':old['end_at'],'line':old['line'],'employees':[x['employee_id'] for x in before]} if old else None,'after':{'start':start,'end':end,'line':line,'employees':ids},'note':note,'warnings':warnings},ensure_ascii=False),factory)
    return {'id':pid,'warnings':warnings}


def leave(c,user,b):
    from .api import role
    if b.get('id'):
        item=scoped(c,user,'staff_leaves',b['id']); check_version(item,b)
        employee=scoped(c,user,'staff_employees',item['employee_id'])
        action=b.get('action')
        if action=='cancel':
            if user['role'] not in ('admin','manager'):
                if employee['user_id']!=user['id'] or item['status']!='待审批': fail('仅能撤回自己的待审批请假',403)
            if item['status'] not in ('待审批','已批准'): fail('该请假已处理',409)
            status='已撤销'
        else:
            role(user,'manager')
            if item['status']!='待审批': fail('该请假已处理',409)
            if action not in ('approve','reject'): fail('审批操作无效')
            status='已批准' if action=='approve' else '已驳回'
            if action=='approve' and approved_leave(c,employee['id'],item['start_at'],item['end_at']): fail('已有重叠的批准请假',409)
        note=text_value(b,'review_note',500)
        c.execute('UPDATE staff_leaves SET status=?,review_note=?,reviewer_id=?,version=version+1 WHERE id=?',(status,note,user['id'],item['id']))
        conflicts=rows(c,"SELECT p.id FROM staff_plans p JOIN staff_assignments a ON a.plan_id=p.id WHERE a.employee_id=? AND p.status='已发布' AND p.start_at<? AND p.end_at>?",(employee['id'],item['end_at'],item['start_at']))
        audit(c,user,'请假'+status,str(item['id']),'员工 '+employee['name']+'；受影响排班 '+','.join(str(p['id']) for p in conflicts),item['factory_id'])
        return {'id':item['id'],'affected_plans':[p['id'] for p in conflicts] if status=='已批准' else []}
    employee=scoped(c,user,'staff_employees',b.get('employee_id'))
    if user['role'] not in ('admin','manager') and employee['user_id']!=user['id']: fail('只能为自己申请请假',403)
    if employee['status']!='在职': fail('停用员工不能申请请假')
    start=timestamp(b.get('start_at')); end=timestamp(b.get('end_at'))
    if not timedelta(0)<end-start<=timedelta(days=30): fail('请假结束时间应晚于开始，单次最多 30 天')
    if end<=datetime.now(): fail('不能申请已结束的请假')
    start,end=start.isoformat(timespec='seconds'),end.isoformat(timespec='seconds')
    if one(c,"SELECT id FROM staff_leaves WHERE employee_id=? AND status IN ('待审批','已批准') AND start_at<? AND end_at>?",(employee['id'],end,start)): fail('已有重叠的请假申请',409)
    lid=c.execute('INSERT INTO staff_leaves(factory_id,employee_id,start_at,end_at,reason,created_at) VALUES(?,?,?,?,?,?)',(employee['factory_id'],employee['id'],start,end,text_value(b,'reason',500),now())).lastrowid
    audit(c,user,'申请请假',str(lid),employee['name']+' '+start+' ~ '+end,employee['factory_id'])
    return {'id':lid}


def candidates(c,user,p):
    from .api import role,get_entity
    role(user,'engineer','manager')
    a=get_entity(c,user,'anomalies',integer(p.get('anomaly_id')))
    skill=p.get('skill') or ('工艺调整' if a.get('order_id') else '设备点检')
    if skill not in SKILLS: fail('派单技能无效')
    current=now(); end=(datetime.fromisoformat(current)+timedelta(seconds=1)).isoformat()
    line=(one(c,'SELECT line FROM devices WHERE id=?',(a['device_id'],)) or {}).get('line','')
    employees=employee_rows(c,a['factory_id']); result=[]
    for account in rows(c,'SELECT id,name,role FROM users WHERE factory_id=? AND active=1',(a['factory_id'],)):
        e=next((e for e in employees if e['user_id']==account['id']),None)
        if e and e['status']!='在职': continue
        is_leave=bool(e and approved_leave(c,e['id'],current,end))
        plans=rows(c,"SELECT p.line,p.end_at FROM staff_plans p JOIN staff_assignments s ON s.plan_id=p.id WHERE s.employee_id=? AND p.status='已发布' AND p.start_at<=? AND p.end_at>?",(e['id'],current,current)) if e else []
        matched=bool(e and skill in e['skills']); duty=bool(plans) and not is_leave
        same_line=any(p['line']==line for p in plans) and duty
        workload=c.execute("SELECT COUNT(*) FROM tasks WHERE assignee=? AND status!='已关闭'",(account['id'],)).fetchone()[0]
        reasons=[]
        if not e: reasons.append('未绑定员工档案')
        if is_leave: reasons.append('正在请假，不可派单')
        else: reasons.append('排班当班' if duty else '当前无当班安排')
        reasons.append('技能匹配' if matched else '技能待核验')
        if same_line: reasons.append('同产线')
        reasons.append(str(workload)+' 项待办')
        result.append({**account,'employee_id':e['id'] if e else None,'skills':e['skills'] if e else [],'on_duty':duty,'skill_match':matched,'same_line':same_line,'on_leave':is_leave,'workload':workload,'eligible':not is_leave,'recommended':duty and matched and not is_leave,'reason':' · '.join(reasons)})
    result.sort(key=lambda u:(not u['eligible'],not u['recommended'],not u['on_duty'],not u['skill_match'],not u['same_line'],u['workload'],u['id']))
    return {'candidates':result,'required_skill':skill,'line':line,'at':current}


def dispatch_note(c,user,b,anomaly):
    result=candidates(c,user,{'anomaly_id':anomaly['id'],'skill':b.get('required_skill')})
    candidate=next((u for u in result['candidates'] if u['id']==int(b['assignee'])),None)
    if not candidate or not candidate['eligible']: fail('处理人已停用或正在请假，请重新选择',409)
    note=text_value(b,'dispatch_note',300,True)
    if not candidate['recommended'] and not note: fail('所选人员未当班或技能待核验，请填写调度说明（如预约下班次或已确认临时支援）')
    return '排班派单：'+candidate['reason']+'；要求技能：'+result['required_skill']+('；调度说明：'+note if note else '')


def dispatch(c,method,path,p,b,user):
    if method=='GET' and path=='/api/workforce': return overview(c,user,p)
    if method=='GET' and path=='/api/workforce/candidates': return candidates(c,user,p)
    if method=='POST':
        handlers={'employees':save_employee,'shifts':save_shift,'plans':save_plan,'leaves':leave}
        handler=handlers.get(path.removeprefix('/api/workforce/'))
        if handler: return handler(c,user,b)
    fail('接口不存在',404)


def initialize(c):
    """Run independently of old platform seeds; never overwrite real staffing records."""
    c.executescript((Path(__file__).parent/'sql'/'workforce.sql').read_text(encoding='utf-8'))
    c.begin_write()
    for factory in (1,2,3):
        if one(c,'SELECT id FROM staff_employees WHERE factory_id=? LIMIT 1',(factory,)): continue
        accounts=rows(c,'SELECT id,name FROM users WHERE factory_id=? ORDER BY id',(factory,))
        ids=[]
        for i in range(6):
            account=accounts[i] if i<len(accounts) else None
            skills=[['生产操作','质量检验','工艺调整'],['生产操作','设备点检','工艺调整'],['生产操作','设备点检'],['生产操作','设备点检'],['生产操作','质量检验'],['设备点检','工艺调整']][i]
            position=['质量工艺岗','现场班组长','生产协调岗','设备操作岗','在线检验岗','设备维护岗'][i]
            eid=c.execute('INSERT INTO staff_employees(factory_id,user_id,code,name,workshop,position,team,skills,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(factory,account['id'] if account else None,'DEMO-%d-%02d'%(factory,i+1),account['name'] if account else ['星禾','知夏','清越','云帆','望舒','砺行'][i]+'（演示）','成型车间',position,'晨星班组' if i<3 else '逐光班组',json.dumps(skills,ensure_ascii=False),now())).lastrowid
            ids.append(eid)
        shifts=[]
        for name,start,end in [('早班','08:00','16:00'),('晚班（跨日）','16:00','00:00')]:
            existing=one(c,'SELECT id FROM staff_shifts WHERE factory_id=? AND name=?',(factory,name))
            shifts.append(existing['id'] if existing else c.execute('INSERT INTO staff_shifts(factory_id,name,start_time,end_time) VALUES(?,?,?,?)',(factory,name,start,end)).lastrowid)
        today=datetime.now().date()
        for offset in range(7):
            day=today+timedelta(days=offset)
            if day.weekday()>=5: continue
            for index,(start,end) in enumerate([('08:00','16:00'),('16:00','00:00')]):
                first,last=shift_times(day.isoformat(),start,end)
                pid=c.execute('INSERT INTO staff_plans(factory_id,shift_id,work_date,line,start_at,end_at,required_count,required_skill,note,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(factory,shifts[index],day.isoformat(),'成型一线',first,last,2,'生产操作','初始化演示排班；仅在首次创建，不自动续排。',now())).lastrowid
                c.executemany('INSERT INTO staff_assignments(plan_id,employee_id) VALUES(?,?)',[(pid,eid) for eid in ids[index*3:index*3+2]])
        audit(c,{'username':'system','factory_id':factory},'初始化人员与排班','演示排班','模拟员工和首周班表，后续由负责人维护',factory)
