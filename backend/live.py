# -*- coding: utf-8 -*-
"""Persisted, opt-in process demonstration. Not a calibrated physical model."""
import json,random,threading,traceback
from datetime import datetime,timedelta
from .db import connect,one,rows,now,audit
from .telemetry import device_freshness

LABEL='动态演示产线（模拟）'
DEFENSE_LABEL='答辩演示产线（模拟）'
DEFENSE_FACTORY=1
DEFENSE_DEVICE=3
INTERVAL=3
PROFILES={
 1:dict(name='精密外壳成型',temperature=72.,pressure=5.2,vibration=.72,cycle=6.8,usage=.04,risk=.018),
 2:dict(name='厚壁壳体成型',temperature=76.,pressure=5.8,vibration=.90,cycle=9.2,usage=.055,risk=.028),
 3:dict(name='轻量支架成型',temperature=69.,pressure=4.8,vibration=.62,cycle=8.1,usage=.03,risk=.022),
}
PHASES={'warming':'预热稳态','producing':'稳定生产','short_stop':'短暂停机','changeover':'换料确认',
 'fault':'温控故障','cooling':'降温观察','awaiting_resume':'等待复产确认','paused':'工单暂停','shortage':'缺料等待','stopped':'演示已停止'}

def initial_state(run,stamp):
    return dict(phase='warming',phase_elapsed=0.,cycle_elapsed=0.,cycle_target=PROFILES[run['factory_id']]['cycle'],
      stable=0.,resume_required=False,last_step=stamp,batch=1,batch_shift=0.,batch_n=0,batch_bad=0,
      pending_n=0,pending_bad=0,produced=0,next_stop=14+run['factory_id']*2,stops=0,settling=0,load=0.,temperature_drift=0.)

def state_of(run):
    s=initial_state(run,run['updated_at']);s.update(json.loads(run.get('state') or '{}'));return s

def describe(record):
    if not record:return None
    result={k:v for k,v in record.items() if k not in ('user_id','state')};s=state_of(record)
    result.update(phase=s['phase'],phase_label=PHASES[s['phase']],profile=PROFILES[record['factory_id']],
       phase_seconds=round(s['phase_elapsed']),cycle_seconds=round(s['cycle_target'],1),
       batch=s['batch'],pending_samples=s['pending_n'],resume_required=s['resume_required'],
       batch_samples=s['batch_n'],batch_defects=s['batch_bad'],
       batch_rate=1-s['batch_bad']/s['batch_n'] if s['batch_n'] else None)
    defense=s.get('defense')
    if defense:
        result.update(mode='defense',staffing=defense['staffing'],reused_device=defense['reused_device'])
    return result

def annotate(c,entity,records):
    if entity in ('devices','orders','materials','quality'):
        sources={r['record_id']:r for r in rows(c,'SELECT record_id,label FROM source_records WHERE entity=?',(entity,))}
        for record in records:
            src=sources.get(record['id'])
            record['archived']=bool(src);record['source']=src['label'] if src else '平台业务数据'
    column={'devices':'device_id','orders':'order_id','materials':'material_id','quality':'order_id'}.get(entity)
    runs=rows(c,'SELECT '+column+',running,state FROM demo_runs ORDER BY id') if column else []
    demo={r[column]:r for r in runs}
    for r in records:
        run=demo.get(r['order_id'] if entity=='quality' else r['id'])
        if not run:continue
        defense=json.loads(run['state']).get('defense')
        if entity=='devices' and defense and defense['reused_device'] and not run['running']:
            last=one(c,'SELECT id FROM readings WHERE device_id=? ORDER BY id DESC LIMIT 1',(r['id'],))
            if not last or last['id']!=defense.get('last_reading_id'):continue
        r['source']=DEFENSE_LABEL if defense else LABEL;r['simulated']=True
    return device_freshness(records) if entity=='devices' else records

def current_run(c,factory):
    return one(c,"""SELECT r.* FROM demo_runs r LEFT JOIN (
                       SELECT entity,max(id) last_selection FROM audit
                       WHERE factory_id=? AND action IN ('启动动态演示','停止动态演示','准备答辩演示')
                       GROUP BY entity
                   ) a ON a.entity=CAST(r.id AS CHAR)
                   WHERE r.factory_id=? ORDER BY r.running DESC,a.last_selection DESC,r.id DESC LIMIT 1""",(factory,factory))

def snapshot(c,f,device_id=None):
    run=current_run(c,f)
    device=one(c,'SELECT * FROM devices WHERE factory_id=? AND id=?',(f,device_id or (run or {}).get('device_id',0)))
    if not device:device=one(c,"SELECT * FROM devices WHERE factory_id=? AND temperature IS NOT NULL ORDER BY id LIMIT 1",(f,))
    if device:annotate(c,'devices',[device])
    current=datetime.now();start=(current-timedelta(minutes=15)).isoformat(timespec='seconds')
    defense=state_of(run).get('defense') if run and device and device.get('simulated') and device['id']==run['device_id'] else None
    if defense:
        first=defense.get('first_reading_id',0);last=defense.get('last_reading_id',0)
        history=rows(c,'SELECT * FROM readings WHERE device_id=? AND id BETWEEN ? AND ? ORDER BY id DESC LIMIT 40',(device['id'],first,last))[::-1]
        recent=rows(c,'SELECT * FROM readings WHERE device_id=? AND id BETWEEN ? AND ? AND created_at>=? ORDER BY id DESC LIMIT 320',(device['id'],first,last,start))[::-1]
    else:
        recent=rows(c,'SELECT * FROM readings WHERE device_id=? AND created_at>=? ORDER BY id DESC LIMIT 320',(device['id'],start))[::-1] if device else []
        history=rows(c,'SELECT * FROM readings WHERE device_id=? ORDER BY id DESC LIMIT 40',(device['id'],))[::-1] if device else []
    hours=[(current.replace(minute=0,second=0,microsecond=0)-timedelta(hours=i)).isoformat(timespec='hours') for i in range(7,-1,-1)]
    reports=rows(c,"SELECT substr(p.created_at,1,13) `hour`,sum(p.quantity) quantity FROM production_reports p JOIN orders o ON o.id=p.order_id WHERE o.factory_id=? AND p.created_at>=? GROUP BY `hour`",(f,hours[0]))
    lookup={r['hour']:r['quantity'] for r in reports}
    minutes=[(current.replace(second=0,microsecond=0)-timedelta(minutes=i)).isoformat(timespec='minutes') for i in range(14,-1,-1)]
    production=rows(c,"SELECT substr(p.created_at,1,16) `minute`,sum(p.quantity) quantity FROM production_reports p JOIN orders o ON o.id=p.order_id WHERE o.factory_id=? AND p.created_at>=? GROUP BY `minute`",(f,minutes[0]))
    minute_lookup={r['minute']:r['quantity'] for r in production}
    inspection=rows(c,'SELECT batch,sample_size,defects,created_at FROM quality WHERE order_id=? AND inspector=? ORDER BY id DESC LIMIT 8',(run['order_id'],'演示在线检测'))[::-1] if run else []
    return {'server_time':current.isoformat(timespec='seconds'),'demo':describe(run),'device':device,'readings':history,'recent_readings':recent,
      'window_start':start,'minute_output':[{'time':m,'quantity':minute_lookup.get(m,0),'partial':i==14} for i,m in enumerate(minutes)],
      'inspections':inspection,'hourly':[{'hour':h[11:]+':00','quantity':lookup.get(h,0)} for h in hours],
      'events':rows(c,"SELECT id,action,entity,user_name,created_at FROM audit WHERE factory_id=? AND action NOT IN ('登录','退出登录','修改密码') ORDER BY id DESC LIMIT 12",(f,)),
      'source':DEFENSE_LABEL if defense else LABEL if device and device.get('simulated') else '最近采集记录',
      'stale_after_seconds':device['freshness_limit'] if device else 120}

def actor(run):return {'username':'演示采集器','factory_id':run['factory_id']}

def transition(c,run,s,phase,stamp=None):
    if s['phase']!=phase:
        event_id=audit(c,actor(run),'演示工况 · '+PHASES[phase],str(run['id']),PHASES[s['phase']]+' → '+PHASES[phase],stamp=stamp)
        s['phase']=phase;s['phase_elapsed']=0.;s['cycle_elapsed']=0.;s['stable']=0.
        return event_id

def save(c,run,s,stamp,**values):
    values.update(state=json.dumps(s,ensure_ascii=False),updated_at=stamp)
    c.execute('UPDATE demo_runs SET '+','.join(k+'=?' for k in values)+' WHERE id=?',tuple(values.values())+(run['id'],))

def flush_quality(c,run,s,o,stamp):
    n=s['pending_n'];bad=s['pending_bad']
    if not n:return
    batch=o['code']+'-B%02d'%s['batch']
    quality_id=c.execute('INSERT INTO quality(factory_id,order_id,batch,sample_size,defects,defect_type,inspector,created_at) VALUES(?,?,?,?,?,?,?,?)',
      (run['factory_id'],o['id'],batch,n,bad,'模拟外观检测','演示在线检测',stamp)).lastrowid
    incident=latest_interlock(s)
    if incident and incident.get('resume_at'):
        incident['quality_ids'].append(quality_id)
    s['batch_n']+=n;s['batch_bad']+=bad;s['pending_n']=s['pending_bad']=0
    audit(c,actor(run),'演示检测完成',batch,'%s 件中 %s 件不合格'%(n,bad))
    if bad/n>.05 and not one(c,"SELECT id FROM anomalies WHERE order_id=? AND status!='已关闭'",(o['id'],)):
        c.execute('INSERT INTO anomalies(factory_id,device_id,order_id,title,severity,description,source,created_at) VALUES(?,?,?,?,?,?,?,?)',
          (run['factory_id'],run['device_id'],o['id'],'演示批次外观缺陷率超限','高','%s：检测 %s 件，%s 件不合格；模拟结果需人工处置。'%(batch,n,bad),LABEL,stamp))

def fault_alarm(c,run,stamp):
    if not one(c,"SELECT id FROM anomalies WHERE device_id=? AND order_id IS NULL AND source=? AND status!='已关闭'",(run['device_id'],LABEL)):
        c.execute('INSERT INTO anomalies(factory_id,device_id,title,severity,description,source,created_at) VALUES(?,?,?,?,?,?,?)',
          (run['factory_id'],run['device_id'],'演示线温控故障 · 已阻断自动报工','高','模拟温控故障已联锁停产。观察模具温控回路逐渐升温；恢复后须降温稳定并人工确认复产，异常另行点检闭环。',LABEL,stamp))


def latest_interlock(state):
    incidents=state.get('defense',{}).get('interlocks',[])
    return incidents[-1] if incidents else None


def latch_fault(c,run,state,stamp):
    fault_event_id=transition(c,run,state,'fault',stamp)
    state['resume_required']=True
    defense=state.get('defense')
    if not defense:
        fault_alarm(c,run,stamp)
        return
    incident=latest_interlock(state)
    if incident and not incident.get('resume_at'):return
    order=one(c,'SELECT * FROM orders WHERE id=?',(run['order_id'],))
    # Close the prior sampling interval before moving to the new shutoff interval.
    flush_quality(c,run,state,order,stamp)
    cutoff=len(defense['outputs'])
    if incident:incident['restart_end']=cutoff
    anomaly_id=c.execute('INSERT INTO anomalies(factory_id,device_id,title,severity,description,source,created_at) VALUES(?,?,?,?,?,?,?)',
        (run['factory_id'],run['device_id'],'答辩演示温控联锁', '高',
         '模拟温控故障，已停止自动报工与耗料。降温稳定后人工确认复产，另由现场人员处理并提交设备点检。',DEFENSE_LABEL,stamp)).lastrowid
    defense['interlocks'].append({'anomaly_id':anomaly_id,'fault_at':stamp,'fault_event_id':fault_event_id,
                                  'fault_output_index':cutoff,'quality_ids':[],'reviews':[]})


def reusable_seed_device(c):
    device=one(c,"SELECT * FROM devices WHERE id=? AND factory_id=? AND code='EQ-03' AND name='自动装配单元' AND line='装配三线'",(DEFENSE_DEVICE,DEFENSE_FACTORY))
    if not device or any(device[k] is None for k in ('temperature','pressure','vibration')):return None
    did=device['id']
    if one(c,"SELECT 1 FROM source_records WHERE entity='devices' AND record_id=?",(did,)):return None
    if not one(c,"SELECT 1 FROM orders WHERE device_id=? AND factory_id=1 AND code='MO-202610-003' AND batch='LOT-01-003'",(did,)):return None
    if one(c,"""SELECT 1 FROM orders o LEFT JOIN demo_runs r ON r.order_id=o.id
                 WHERE o.device_id=? AND o.status IN ('生产中','已暂停') AND r.id IS NULL""",(did,)):return None
    if one(c,"SELECT 1 FROM anomalies WHERE device_id=? AND status<>'已关闭' AND coalesce(source,'') NOT IN (?,?)",(did,DEFENSE_LABEL,LABEL)):return None
    if one(c,"SELECT 1 FROM audit WHERE factory_id=? AND action='记录设备采集值' AND entity=?",(DEFENSE_FACTORY,str(did))):return None
    return device


def create_run(c,user,f,stamp,mode=None):
    seq=c.execute('SELECT coalesce(max(id),0)+1 FROM demo_runs').fetchone()[0]
    defense=mode=='defense';p=PROFILES[f]
    code=('SIM-DEF-%02d-%04d' if defense else 'SIM-%02d-%04d')%(f,seq)
    device=reusable_seed_device(c) if defense else None
    reuse=bool(device)
    if not device:
        did=c.execute('INSERT INTO devices(factory_id,code,name,line,status,temperature,pressure,vibration,runtime,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
          (f,code,'答辩演示成型单元' if defense else '演示成型单元','答辩演示线' if defense else '模具温控回路 · '+p['name'],
           '待机',p['temperature']-8,.4,.18,0,stamp)).lastrowid
        device=one(c,'SELECT id,line FROM devices WHERE id=?',(did,))
    did=device['id']
    oid=c.execute('INSERT INTO orders(factory_id,code,product,batch,quantity,status,priority,due_date,device_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
      (f,code,'演示连接器外壳',code+'-B01',120,'生产中','普通',stamp[:10],did,stamp)).lastrowid
    mid=c.execute('INSERT INTO materials(factory_id,code,name,spec,unit,stock,min_stock,location) VALUES(?,?,?,?,?,?,?,?)',
      (f,code,'演示 PA66 原料','%.3f kg / 件'%p['usage'],'kg',round(p['usage']*150,3),round(p['usage']*50,3),'演示线料仓')).lastrowid
    rid=c.execute('INSERT INTO demo_runs(factory_id,device_id,order_id,material_id,user_id,running,started_at,updated_at) VALUES(?,?,?,?,?,1,?,?)',
                   (f,did,oid,mid,user['id'],stamp,stamp)).lastrowid
    run=one(c,'SELECT * FROM demo_runs WHERE id=?',(rid,));state=initial_state(run,stamp)
    if defense:
        from .workforce import prepare_defense_staffing
        staffing=prepare_defense_staffing(c,user,f,device['line'],datetime.fromisoformat(stamp))
        state['defense']={'staffing':staffing,'reused_device':reuse,'prepared_at':stamp,'outputs':[],'interlocks':[]}
    save(c,run,state,stamp,reason='预热至稳定窗口后开始生产')
    return run


def stop_run(c,run,stamp,reason):
    state=state_of(run);order=one(c,'SELECT * FROM orders WHERE id=?',(run['order_id'],))
    flush_quality(c,run,state,order,stamp)
    transition(c,run,state,'stopped',stamp);save(c,run,state,stamp,running=0,reason=reason)
    c.execute("UPDATE devices SET status='待机' WHERE id=?",(run['device_id'],))
    if state.get('defense'):
        c.execute("UPDATE orders SET status='已取消' WHERE id=? AND status IN ('生产中','已暂停')",(run['order_id'],))


def demo_owns_device(c,device_id):
    run=one(c,'SELECT running,state FROM demo_runs WHERE device_id=? ORDER BY id DESC LIMIT 1',(device_id,))
    if not run:return False
    defense=json.loads(run['state']).get('defense')
    return bool(run['running'] or not defense or not defense['reused_device'])


def defense_owns_device(c,device_id,order_id):
    run=one(c,'SELECT state FROM demo_runs WHERE device_id=? AND running=1 AND order_id<>?',(device_id,order_id))
    return bool(run and json.loads(run['state']).get('defense'))


def record_equipment_review(c,anomaly,task_id,event_id,passed):
    for run in rows(c,'SELECT * FROM demo_runs WHERE factory_id=? AND device_id=? ORDER BY id DESC',
                    (anomaly['factory_id'],anomaly['device_id'])):
        state=state_of(run)
        for incident in state.get('defense',{}).get('interlocks',[]):
            if incident['anomaly_id']==anomaly['id']:
                incident['reviews'].append({'task_id':task_id,'event_id':event_id,'passed':passed})
                c.execute('UPDATE demo_runs SET state=? WHERE id=?',(json.dumps(state,ensure_ascii=False),run['id']))
                return


def output_window(links,reports,moves):
    report_ids=[report_id for report_id,_ in links if report_id in reports]
    move_ids=[move_id for _,move_id in links if move_id in moves]
    return {'report_count':len(report_ids),'output_count':sum(reports[i]['quantity'] for i in report_ids),
            'consumed_quantity':round(sum(moves[i]['quantity'] for i in move_ids),6),
            'first_report_id':report_ids[0] if report_ids else None,'last_report_id':report_ids[-1] if report_ids else None,
            'first_move_id':move_ids[0] if move_ids else None,'last_move_id':move_ids[-1] if move_ids else None}


def timeline(c,f,run_id):
    from .api import ApiError
    run=one(c,'SELECT * FROM demo_runs WHERE factory_id=? AND id=?',(f,run_id))
    if not run:raise ApiError('演示记录不存在',404)
    state=state_of(run);defense=state.get('defense',{});links=defense.get('outputs',[])
    device=one(c,'SELECT id,code,name,line FROM devices WHERE factory_id=? AND id=?',(f,run['device_id']))
    order=one(c,'SELECT id,code,batch,completed,quantity,status FROM orders WHERE factory_id=? AND id=? AND device_id=?',(f,run['order_id'],run['device_id']))
    material=one(c,'SELECT id,code,name,unit,stock FROM materials WHERE factory_id=? AND id=?',(f,run['material_id']))
    reports={r['id']:r for r in rows(c,'SELECT id,quantity FROM production_reports WHERE order_id=?',(run['order_id'],))}
    moves={m['id']:m for m in rows(c,"SELECT id,quantity FROM stock_moves WHERE material_id=? AND direction='出库'",(run['material_id'],))}
    checks={q['id']:q for q in rows(c,'SELECT id,batch,sample_size,defects,created_at FROM quality WHERE order_id=? AND factory_id=?',(run['order_id'],f))}
    events=rows(c,"""SELECT id,'process' type,created_at at,action label,user_name actor FROM audit WHERE factory_id=? AND entity=?
                  AND (action LIKE '演示工况 · %' OR action IN ('准备答辩演示','启动动态演示','停止动态演示','模拟温控故障','开始降温观察','确认演示复产','模拟短暂停机','模拟换料','采集间隔中断'))""",(f,str(run_id)))
    interlocks=[]
    for incident in defense.get('interlocks',[]):
        anomaly=one(c,'SELECT id,title,status,source,created_at FROM anomalies WHERE id=? AND factory_id=? AND device_id=? AND order_id IS NULL',(incident['anomaly_id'],f,run['device_id']))
        task=one(c,"""SELECT t.id,t.status,t.assignee,u.name assignee_name FROM tasks t JOIN users u ON t.assignee=u.id AND u.factory_id=t.factory_id
                     WHERE t.factory_id=? AND t.anomaly_id=? ORDER BY t.id DESC LIMIT 1""",(f,anomaly['id'])) if anomaly else None
        inspection={'type':'equipment','status':'pending','event_id':None,'note':None,'reviewer':None,'reviewed_at':None}
        if task:
            task_events=rows(c,"SELECT id,'task' type,created_at at,action label,user_name actor,note FROM task_events WHERE task_id=?",(task['id'],))
            reviews={r['event_id']:r for r in incident['reviews'] if r['task_id']==task['id']}
            for event in sorted(task_events,key=lambda item:item['id']):
                note=event.pop('note');review=reviews.get(event['id'])
                if review:
                    inspection.update(status='passed' if review['passed'] else 'failed',event_id=event['id'],
                                      note=note,reviewer=event['actor'],reviewed_at=event['at'])
                events.append(event)
        fault=incident['fault_output_index'];resume=incident.get('resume_output_index');stop=incident.get('restart_end')
        shutdown=output_window(links[fault:resume],reports,moves)
        completed_before=output_window(links[:fault],reports,moves)['output_count']
        shutdown.update(completed_before=completed_before,completed_after=completed_before+shutdown['output_count'])
        restart=output_window(links[resume:stop] if resume is not None else [],reports,moves)
        restart['quality_records']=[dict(checks[i],source_type='simulation') for i in incident['quality_ids'] if i in checks]
        interlocks.append({'fault_at':incident['fault_at'],'fault_event_id':incident['fault_event_id'],
          'resume_at':incident.get('resume_at'),'resume_event_id':incident.get('resume_event_id'),
          'anomaly':anomaly,'task':task,'inspection':inspection,'shutdown':shutdown,'restart':restart})
    events.sort(key=lambda e:(e['at'],e['type'],e['id']))
    return {'run_id':run_id,'factory_id':f,'source_type':'simulation','source':DEFENSE_LABEL if defense else LABEL,
            'device':device,'order':order,'material':material,'staffing':defense.get('staffing'),
            'phase':state['phase'],'running':bool(run['running']),'interlocks':interlocks,'events':events}

def control(c,user,f,action,moment=None):
    from .api import ApiError,role
    stamp=(moment or datetime.now()).isoformat(timespec='seconds')
    run=current_run(c,f)
    defense=state_of(run).get('defense') if run else None
    if action=='prepare-defense' or (defense and action!='start'):role(user,'engineer')
    if action=='prepare-defense':
        if f!=DEFENSE_FACTORY:raise ApiError('答辩演示在星铸工厂提供',409)
        if run and run['running']:
            if not defense:raise ApiError('请先停止当前动态演示，再准备答辩演示',409)
            incident=latest_interlock({'defense':defense})
            closed=incident and incident.get('resume_at') and incident['quality_ids'] and one(c,"SELECT id FROM anomalies WHERE id=? AND status='已关闭'",(incident['anomaly_id'],))
            if not closed:return describe(run)
            stop_run(c,run,stamp,'本轮答辩演示已经结束，开始新一轮演示')
        run=create_run(c,user,f,stamp,'defense')
    elif action=='start':
        if defense and run['running']:raise ApiError('请先停止当前答辩演示，再启动普通动态演示',409)
        if defense:
            run=one(c,"SELECT * FROM demo_runs WHERE factory_id=? AND JSON_EXTRACT(state,'$.defense') IS NULL ORDER BY id DESC LIMIT 1",(f,))
            defense=None
        order=one(c,'SELECT * FROM orders WHERE id=?',(run['order_id'],)) if run else None
        if not run or order['status'] in ('已完成','已取消'):
            run=create_run(c,user,f,stamp)
        elif not run['running']:
            s=state_of(run);transition(c,run,s,'cooling' if s['resume_required'] else 'warming');s['last_step']=stamp
            save(c,run,s,stamp,running=1,started_at=stamp,user_id=user['id'],reason='恢复采集，检查工况后继续')
    elif run and action=='stop':
        if not defense or run['running']:stop_run(c,run,stamp,'人工停止演示')
    elif run and run['running']:
        s=state_of(run);phase=s['phase']
        if defense and action in ('short-stop','changeover'):raise ApiError('答辩演示使用固定批次，仅支持温控联锁流程',409)
        if action=='fault':
            latch_fault(c,run,s,stamp)
        elif action=='recover' and phase=='fault':transition(c,run,s,'cooling',stamp)
        elif action=='resume' and phase=='awaiting_resume':
            d=one(c,'SELECT * FROM devices WHERE id=?',(run['device_id'],));p=PROFILES[f]
            if not device_freshness([dict(d,simulated=True)],moment)[0]['fresh'] or abs(d['temperature']-p['temperature'])>1.5:
                raise ApiError('采集已过期或温度不在稳定窗口，请继续观察',409)
            s['resume_required']=False;s['settling']=5;transition(c,run,s,'warming',stamp)
            incident=latest_interlock(s)
            if incident:incident.update(resume_at=stamp,resume_output_index=len(s['defense']['outputs']))
        elif action in ('short-stop','changeover') and phase=='producing':
            transition(c,run,s,'short_stop' if action=='short-stop' else 'changeover');s['hold_seconds']=12 if action=='short-stop' else 21
        else:raise ApiError('当前工况不允许此操作；降温稳定后才能确认复产',409)
        s['last_step']=stamp
        if action=='resume' and latest_interlock(s):
            latest_interlock(s)['resume_event_id']=audit(c,user,'确认演示复产',str(run['id']),DEFENSE_LABEL,f,stamp=stamp)
        save(c,run,s,stamp,scenario='overheat' if s['phase']=='fault' else 'normal',reason=PHASES[s['phase']])
        if s['phase']!='producing':c.execute('UPDATE devices SET status=? WHERE id=?',('预警' if s['resume_required'] else '待机',run['device_id']))
    else:raise ApiError('请先启动演示产线')
    titles={'prepare-defense':'准备答辩演示','start':'启动动态演示','stop':'停止动态演示','fault':'模拟温控故障','recover':'开始降温观察','resume':'确认演示复产','short-stop':'模拟短暂停机','changeover':'模拟换料'}
    if action!='resume' or not defense:
        audit(c,user,titles[action],str(run['id']),DEFENSE_LABEL if defense or action=='prepare-defense' else LABEL,f,stamp=stamp)
    return describe(one(c,'SELECT * FROM demo_runs WHERE id=?',(run['id'],)))

def approach(previous,target,speed,dt):return previous+max(-speed*dt,min(speed*dt,target-previous))

def advance(c,run,moment=None):
    if not run['running']:return
    current=moment or datetime.now();stamp=current.isoformat(timespec='seconds');s=state_of(run);p=PROFILES[run['factory_id']]
    elapsed=(current-datetime.fromisoformat(s['last_step'])).total_seconds()
    if elapsed<=0:return
    dt=min(elapsed,INTERVAL*2);s['last_step']=stamp;tick=run['tick']+1
    defense=s.get('defense');sample_window=3 if defense else 10
    r=random.Random((1 if defense else run['id'])*1000003+run['factory_id']*10007+tick*97)
    o=one(c,'SELECT * FROM orders WHERE id=?',(run['order_id'],));m=one(c,'SELECT * FROM materials WHERE id=?',(run['material_id'],));d=one(c,'SELECT * FROM devices WHERE id=?',(run['device_id'],))
    if (current-datetime.fromisoformat(run['started_at'])).total_seconds()>=1200 or o['status'] in ('已完成','已取消'):
        stop_run(c,run,stamp,'工单结束或演示达到20分钟上限')
        return
    if elapsed>INTERVAL*3:
        s['cycle_elapsed']=0;s['stable']=0;dt=INTERVAL
        if s['phase']=='producing':transition(c,run,s,'warming')
        audit(c,actor(run),'采集间隔中断',str(run['id']),'不补算失联期间产量；重新检查稳定状态')
    if s['phase'] not in ('fault','cooling','awaiting_resume'):
        if o['status']!='生产中':transition(c,run,s,'paused')
        elif m['stock']+1e-8<p['usage']:transition(c,run,s,'shortage')
        elif s['phase'] in ('paused','shortage','stopped'):transition(c,run,s,'cooling' if s['resume_required'] else 'warming')
    phase=s['phase'];s['phase_elapsed']+=dt
    s['load']=max(-.16,min(.16,.72*s['load']+r.uniform(-.065,.065)))
    s['temperature_drift']=max(-.5,min(.5,.96*s['temperature_drift']+r.uniform(-.08,.08)))
    target=p['temperature']+s['temperature_drift']+s['batch_shift']
    if phase=='fault':target=97.5+s['load']*3
    elif phase in ('paused','shortage','short_stop','changeover'):target=p['temperature']-4
    temperature=round(approach(d['temperature'],target,.75,dt)+r.uniform(-.09,.09),2)
    busy=phase=='producing'
    pressure_target=p['pressure']*(1+s['load']) if busy else .35 if phase in ('fault','cooling','awaiting_resume') else 1.2
    pressure=round(max(0,approach(d['pressure'],pressure_target,.9,dt)+r.uniform(-.035,.035)),3)
    vibration_target=p['vibration']*(1+s['load']*2) if busy else .18
    vibration=round(max(0,approach(d['vibration'],vibration_target,.3,dt)+r.uniform(-.025,.025)),3)
    # A fresh rehearsal can inherit a hot shared device from a stopped run.
    # Warming already prevents output while that reading returns to the stable window.
    inherited_heat=defense and defense['reused_device'] and phase=='warming' and not s['produced'] and not latest_interlock(s)
    if temperature>90 and not s['resume_required'] and not inherited_heat:
        latch_fault(c,run,s,stamp);busy=False
        phase=s['phase']
    if phase in ('warming','cooling'):
        s['stable']=s['stable']+dt if abs(temperature-p['temperature'])<=1.2 else 0
        if s['stable']>=6:
            transition(c,run,s,'awaiting_resume' if s['resume_required'] else 'producing')
            s['cycle_target']=p['cycle']*r.uniform(.88,1.15)
    elif phase in ('short_stop','changeover') and s['phase_elapsed']>=s.get('hold_seconds',12):
        if phase=='changeover':
            flush_quality(c,run,s,o,stamp);s['batch']+=1;s['batch_n']=s['batch_bad']=0;s['batch_shift']=r.uniform(-.65,.65);s['settling']=5
            c.execute('UPDATE orders SET batch=? WHERE id=?',(o['code']+'-B%02d'%s['batch'],o['id']))
        transition(c,run,s,'warming')
    elif phase=='producing' and s['phase']=='producing':
        s['cycle_elapsed']+=dt
        if s['cycle_elapsed']>=s['cycle_target']:
            s['cycle_elapsed']-=s['cycle_target'];s['cycle_target']=p['cycle']*(1+s['load']*.3)*r.uniform(.86,1.18)
            completed=o['completed']+1;s['produced']+=1
            c.execute('UPDATE orders SET completed=?,status=? WHERE id=?',(completed,'已完成' if completed>=o['quantity'] else '生产中',o['id']))
            report_id=c.execute('INSERT INTO production_reports(order_id,quantity,user_id,created_at) VALUES(?,?,?,?)',(o['id'],1,run['user_id'],stamp)).lastrowid
            c.execute('UPDATE materials SET stock=round(stock-?,6) WHERE id=?',(p['usage'],m['id']))
            move_id=c.execute('INSERT INTO stock_moves(material_id,direction,quantity,note,user_name,created_at) VALUES(?,?,?,?,?,?)',(m['id'],'出库',p['usage'],'模拟耗料 · '+o['code'],'演示采集器',stamp)).lastrowid
            if defense:defense['outputs'].append([report_id,move_id])
            risk=min(.35,p['risk']+abs(temperature-p['temperature'])*.016+abs(s['load'])*.10+(.07 if s['settling'] else 0)+abs(s['batch_shift'])*.02)
            s['pending_n']+=1;s['pending_bad']+=int(r.random()<risk);s['settling']=max(0,s['settling']-1)
            audit(c,actor(run),'演示报工 +1 件',o['code'],'计划模拟节拍 %.1fs；耗料 %.3fkg'%(s['cycle_target'],p['usage']))
            if s['pending_n']>=sample_window or completed>=o['quantity']:flush_quality(c,run,s,o,stamp)
            if completed>=o['quantity']:transition(c,run,s,'stopped')
            elif not defense and s['produced']>=s['next_stop']:
                s['stops']+=1;next_phase='changeover' if s['stops']%2==0 else 'short_stop'
                transition(c,run,s,next_phase);s['hold_seconds']=r.randint(15,24) if next_phase=='changeover' else r.randint(6,12)
                s['next_stop']=s['produced']+r.randint(13,21)
    status='预警' if s['resume_required'] else '运行' if s['phase']=='producing' else '待机'
    c.execute('UPDATE devices SET temperature=?,pressure=?,vibration=?,status=?,runtime=runtime+?,updated_at=? WHERE id=?',(temperature,pressure,vibration,status,dt if busy else 0,stamp,run['device_id']))
    reading_id=c.execute('INSERT INTO readings(device_id,temperature,pressure,vibration,created_at) VALUES(?,?,?,?,?)',(run['device_id'],temperature,pressure,vibration,stamp)).lastrowid
    if defense:
        defense.setdefault('first_reading_id',reading_id);defense['last_reading_id']=reading_id
    if not defense or not defense['reused_device']:
        c.execute('DELETE FROM readings WHERE device_id=? AND id NOT IN (SELECT id FROM (SELECT id FROM readings WHERE device_id=? ORDER BY id DESC LIMIT 2400) AS retained)',(run['device_id'],run['device_id']))
    details={'warming':'温度连续稳定6秒后开始生产','producing':'节拍约 %.1fs · %.3fkg/件 · 每%d件检测'%(s['cycle_target'],p['usage'],sample_window),
      'fault':'温控故障联锁，报工与耗料已阻断','cooling':'温度渐变回落，稳定后等待人工确认','awaiting_resume':'已进入稳定窗口，请确认复产；异常需另行复检',
      'short_stop':'现场短停，暂停产出，参数回落','changeover':'换料期间停止产出，结束后新建生产批次','paused':'工单暂停，等待生产管理恢复','shortage':'库存不足，等待补料','stopped':'本次演示结束'}
    save(c,run,s,stamp,tick=tick,running=int(s['phase']!='stopped'),reason=details[s['phase']])

class LiveRuntime:
    def __init__(self):
        self.stop_event=threading.Event()
        with connect() as c:
            c.begin_write()
            for run in rows(c,'SELECT * FROM demo_runs WHERE running=1'):
                s=state_of(run)
                if s.get('defense'):
                    stop_run(c,run,now(),'服务重启，当前答辩演示已停止')
                else:
                    s['phase']='stopped';s['cycle_elapsed']=0
                    save(c,run,s,now(),running=0,reason='服务重启，请手动继续演示')
                    c.execute("UPDATE devices SET status='待机' WHERE id=?",(run['device_id'],))
        self.thread=threading.Thread(target=self.run,daemon=True,name='demo-telemetry');self.thread.start()
    def run(self):
        while not self.stop_event.wait(INTERVAL):
            try:
                with connect() as c:
                    c.begin_write()
                    for run in rows(c,'SELECT * FROM demo_runs WHERE running=1'):advance(c,run)
            except Exception:traceback.print_exc()
    def close(self):self.stop_event.set();self.thread.join(timeout=5)
