import {esc,icon,btn,field,select,notice,table,empty,date,badge} from './ui.js';

const localDate=()=>new Date().toLocaleDateString('sv-SE');
const plusDay=(day,n)=>{const d=new Date(day+'T12:00:00');d.setDate(d.getDate()+n);return d.toLocaleDateString('sv-SE')};
const shortTime=v=>v.slice(11,16);
const timeRange=p=>shortTime(p.start_at)+'—'+(p.end_at.slice(0,10)!==p.start_at.slice(0,10)?'次日 ':'')+shortTime(p.end_at);
const manager=S=>['admin','manager'].includes(S.user.role);
const cardHead=(title,sub='',right='')=>'<div class="card-head"><div><h2>'+title+'</h2><p>'+sub+'</p></div>'+right+'</div>';
const tag=(text,style='')=>'<span class="wf-tag '+style+'">'+esc(text)+'</span>';
const stat=(label,value,sub,style='')=>'<div class="wf-stat '+style+'"><span>'+label+'</span><strong>'+value+'</strong><small>'+sub+'</small></div>';

export async function renderWorkforce(S,api){
 const d=await api('/workforce?factory_id='+S.factory+'&date='+(S.workforceDate||localDate()));S.cache.workforce=d;
 const manage=d.can_manage,personal=d.personal,summary=d.summary;
 const employees=new Map(d.employees.map(e=>[e.id,e]));
 const plans=d.plans.filter(p=>!S.workforceLine||p.line===S.workforceLine);
 const days=Array.from({length:7},(_,i)=>plusDay(d.date,i));
 const getName=id=>employees.get(id)?.name||'员工 #'+id;
 const planCard=p=>'<article class="wf-plan '+(p.phase==='当班'?'current ':'')+(p.status==='已取消'?'cancelled':'')+'"><div class="row between wrap"><strong>'+esc(p.shift_name)+'</strong>'+tag(p.phase,p.phase==='当班'?'green':'')+'</div><span class="wf-time">'+timeRange(p)+'</span><h3>'+esc(p.line)+'</h3><div class="wf-people">'+(p.employee_ids.map(id=>'<span class="'+(p.leave_ids.includes(id)?'absent':'')+'">'+icon('user')+esc(getName(id))+(p.leave_ids.includes(id)?' · 请假':'')+'</span>').join('')||'<span class="muted">尚未安排人员</span>')+'</div><div class="wf-plan-foot">'+(personal?tag(p.required_skill||'综合岗位'):tag('可用 '+p.available_count+' / 需求 '+p.required_count,p.shortage?'amber':'green'))+(p.shortage?tag('缺 '+p.shortage+' 人','amber'):'')+'</div>'+(manage&&p.status==='已发布'&&p.phase!=='已结束'?btn('调整 / 替班','wf-plan','data-id="'+p.id+'"','ghost small'):'')+'</article>';
 const calendar=days.map(day=>'<section class="wf-day '+(day===localDate()?'today':'')+'"><header><span>'+['周日','周一','周二','周三','周四','周五','周六'][new Date(day+'T12:00:00').getDay()]+'</span><strong>'+day.slice(5).replace('-',' / ')+'</strong>'+(day===localDate()?tag('今天','blue'):'')+'</header><div class="wf-day-body">'+(plans.filter(p=>p.work_date===day||(day===days[0]&&p.work_date<day&&p.end_at>day+'T00:00:00')).map(planCard).join('')||'<div class="wf-rest">'+icon('clock')+'<span>暂无排班</span></div>')+'</div></section>').join('');
 const staffTable=table(['员工 / 工号','车间 / 岗位','班组 / 技能','账号 / 状态',...(manage?['操作']:[])],d.employees.map(e=>'<tr><td><strong>'+esc(e.name)+'</strong><small>'+esc(e.code)+'</small></td><td>'+esc(e.workshop)+'<small>'+esc(e.position)+'</small></td><td>'+esc(e.team)+'<small>'+esc(e.skills.join(' / '))+'</small></td><td>'+esc(e.username||'未绑定登录账号')+'<small>'+tag(e.status,e.status==='在职'?'green':'')+(d.on_duty_ids.includes(e.id)?tag('排班当班','blue'):'')+'</small></td>'+(manage?'<td>'+btn('编辑','wf-employee','data-id="'+e.id+'"','ghost small')+'</td>':'')+'</tr>').join(''));
 const leaveList=d.leaves.map(l=>'<article class="wf-leave"><div class="row between wrap"><strong>'+esc(l.employee_name)+'</strong>'+tag(l.status,l.status==='待审批'?'amber':l.status==='已批准'?'green':'')+'</div><p>'+date(l.start_at)+' → '+date(l.end_at)+'</p><div class="wf-reason">'+esc(l.reason)+'</div>'+(l.review_note?'<small class="muted">审批说明：'+esc(l.review_note)+'</small>':'')+'<div class="row gap8 mt16">'+(manage&&l.status==='待审批'?btn('批准','wf-leave-review','data-id="'+l.id+'" data-mode="approve"','primary small')+btn('驳回','wf-leave-review','data-id="'+l.id+'" data-mode="reject"','small'):'')+((manage&&['待审批','已批准'].includes(l.status))||(l.employee_id===d.own_employee_id&&l.status==='待审批')?btn('撤销','wf-leave-review','data-id="'+l.id+'" data-mode="cancel"','ghost small'):'')+'</div></article>').join('');
 return '<div class="page-head"><div><div class="eyebrow">PEOPLE / PRODUCTION / TOGETHER</div><h1>'+(personal?'我的排班':'人员与排班')+'</h1><p>'+(personal?'查看当班安排、提交请假，让每一次交接有据可查。':'把人员、班次与现场任务连接起来，让每条产线有人接手。')+'</p></div><div class="row gap8 wrap">'+btn('请假申请','wf-leave','','')+(manage?btn('班次设置','wf-shifts')+btn(icon('plus')+'发布排班','wf-plan','','primary'):'')+'</div></div>'+
 '<section class="wf-hero"><div class="wf-hero-copy"><div class="eyebrow">RIGHT PEOPLE · RIGHT SHIFT</div><h2>班次有序，协同有据。</h2><p>排班 → 当班识别 → 技能匹配 → 任务派单</p><small>当班状态依据班表与已批准请假计算；实际到岗需现场确认。</small></div><div class="wf-hero-mark" aria-hidden="true">'+icon('user')+icon('clock')+icon('tasks')+'</div></section>'+
 '<div class="wf-stats">'+stat(personal?'我的员工档案':'在职员工',summary.active,personal?'仅展示本人信息':'当前工厂 · 技能档案')+stat(personal?'当前是否当班':'当前排班当班',personal?(summary.on_duty?'是':'否'):summary.on_duty,'实时按班表计算','blue')+stat('所选 7 天班次',summary.plans,'已发布 · 不含已取消','purple')+stat(personal?'待审批请假':'所选 7 天缺员人次',personal?summary.pending:summary.shortage,personal?'等待负责人处理':'同一员工不同班次分别计数','amber')+'</div>'+
 '<section class="card wf-calendar-card">'+cardHead(personal?'我的班表':'生产排班日历',d.date+' 至 '+days[6]+' · 北京时间（UTC+8）',btn('回到今天','wf-today','','ghost small'))+
 '<div class="wf-toolbar"><div class="row gap8">'+btn('上一周','wf-week','data-delta="-7"','small')+'<label class="wf-inline-label">起始日<input id="wf-date" type="date" value="'+d.date+'" aria-label="排班起始日"></label>'+btn('下一周','wf-week','data-delta="7"','small')+'</div><label class="wf-inline-label">产线<select id="wf-line" aria-label="筛选产线"><option value="">全部产线</option>'+d.lines.map(l=>'<option '+(l===S.workforceLine?'selected':'')+' value="'+esc(l)+'">'+esc(l)+'</option>').join('')+'</select></label></div>'+
 (d.warnings.length?'<div class="wf-warning">'+icon('alert')+'<div><strong>有 '+d.warnings.length+' 个班次需要补员</strong><p>'+esc(d.warnings.slice(0,3).map(w=>w.message).join('；'))+(d.warnings.length>3?'；其余见班表':'')+'</p></div></div>':'')+
 '<div class="wf-calendar-scroll"><div class="wf-calendar">'+calendar+'</div></div><div class="wf-calendar-note">跨日班次归属开始日期；请假与班次部分重叠时，保守按整班不可用提示补员。</div></section>'+
 '<div class="wf-bottom"><section class="card">'+cardHead(personal?'我的档案':'员工技能档案','工号 DEMO 开头为初始化演示人员',manage?btn(icon('plus')+'新增员工','wf-employee','','small'):'')+(d.employees.length?staffTable:empty('尚未绑定员工档案，请联系本厂负责人'))+'</section><section class="card">'+cardHead('请假与替班',manage?'审批后班表会提示缺员，请及时安排替班':'本人及负责人可查看详细请假原因',tag(summary.pending+' 待审批',summary.pending?'amber':''))+'<div class="wf-leaves">'+(leaveList||empty('所选时段没有请假记录'))+'</div></section></div>';
}

export function workforceActions({S,api,modal,toast,render}){
 const data=()=>S.cache.workforce;
 const save=async(path,body,message)=>{const r=await api('/workforce/'+path,{factory_id:S.factory,...body});await render();toast(message+(r.warnings?.length?'；'+r.warnings.join('；'):''));return r};
 const skillsFields=selected=>'<fieldset class="wf-options field full"><legend>岗位技能（可多选）</legend>'+data().skills.map(s=>'<label><input type="checkbox" name="skills" value="'+esc(s)+'" '+(selected.includes(s)?'checked':'')+'>'+esc(s)+'</label>').join('')+'</fieldset>';
 function employeeDialog(button){
  const d=data(),old=d.employees.find(e=>e.id===Number(button.dataset.id));
  const accounts=d.accounts.filter(a=>a.id===old?.user_id||!d.employees.some(e=>e.user_id===a.id));
  modal(old?'编辑员工档案':'新增员工档案','<div class="form-grid">'+field('姓名','name','text',old?.name||'','required maxlength="80"')+field('工号','code','text',old?.code||'','required maxlength="40"')+field('所属车间','workshop','text',old?.workshop||'成型车间','required maxlength="80"')+field('岗位','position','text',old?.position||'生产操作员','required maxlength="80"')+field('班组','team','text',old?.team||'','required maxlength="80"')+select('绑定登录账号','user_id',[['','暂不绑定'],...accounts.map(a=>[a.id,a.name+' / '+a.username])],old?.user_id||'')+select('员工状态','status',[['在职','在职'],['停用','停用']],old?.status||'在职')+skillsFields(old?.skills||['生产操作'])+'</div>'+notice('绑定登录账号后，员工可查看自己的班表并接收处置任务。没有账号的员工仍可参与排班。'),{wide:true,onSubmit:async(b,dialog)=>save('employees',{...b,id:old?.id,version:old?.version,skills:[...dialog.querySelectorAll('[name=skills]:checked')].map(i=>i.value)},'员工档案已保存')});
 }
 function planDialog(button){
  const d=data(),old=d.plans.find(p=>p.id===Number(button.dataset.id));
  const employeeOptions=d.employees.filter(e=>e.status==='在职').map(e=>'<label class="wf-person-option"><input type="checkbox" name="employees" value="'+e.id+'" '+(old?.employee_ids.includes(e.id)?'checked':'')+'><span><strong>'+esc(e.name)+'</strong><small>'+esc(e.team+' · '+e.skills.join(' / '))+'</small></span></label>').join('');
  const content='<div class="form-grid">'+field('归属日期','work_date','date',old?.work_date||d.date,'required')+select('生产线','line',d.lines.map(l=>[l,l]),old?.line||S.workforceLine||d.lines[0])+select('班次','shift_id',d.shifts.map(s=>[s.id,s.name+' '+s.start_time+'—'+(s.end_time<=s.start_time?'次日 ':'')+s.end_time]),old?.shift_id||d.shifts[0]?.id)+field('需求人数','required_count','number',old?.required_count||2,'required min="1" max="100" step="1"')+select('岗位所需技能','required_skill',[['','不限制'],...d.skills.map(s=>[s,s])],old?.required_skill||'')+field('排班 / 调班说明','note','textarea',old?.note||'','maxlength="500"')+'<fieldset class="field full wf-options wf-person-options"><legend>安排人员 · 勾选替班人并取消原人员</legend>'+employeeOptions+'</fieldset></div>'+notice('发布时校验跨日重叠、批准请假和技能。不足员额允许保存并提示补员；同一产线同一时段统一维护一个班次。')+(old?'<div class="mt16">'+btn('取消本次排班','wf-cancel-plan','data-id="'+old.id+'"','danger small')+'</div>':'');
  modal(old?'调整排班 / 安排替班':'发布生产排班',content,{wide:true,submit:old?'保存调整':'发布排班',onSubmit:async(b,dialog)=>save('plans',{...b,id:old?.id,version:old?.version,employee_ids:[...dialog.querySelectorAll('[name=employees]:checked')].map(i=>Number(i.value))},old?'排班已调整':'排班已发布')});
 }
 return {
  'wf-today':()=>{S.workforceDate=localDate();return render()},
  'wf-week':e=>{S.workforceDate=plusDay(data().date,Number(e.dataset.delta));return render()},
  'wf-employee':employeeDialog,
  'wf-plan':planDialog,
  'wf-cancel-plan':e=>{const p=data().plans.find(p=>p.id===Number(e.dataset.id));modal('取消排班',field('取消原因','note','textarea','','required maxlength="500"'),{submit:'确认取消',onSubmit:async b=>save('plans',{...b,id:p.id,version:p.version,action:'cancel'},'排班已取消，记录保留')})},
  'wf-shifts':()=>modal('班次设置',notice('结束时间早于或等于开始时间时按次日处理；单班不超过 12 小时。修改模板仅作用于后续新增排班，已有班表保留原时间。')+'<div class="mt16">'+table(['名称','开始','结束','操作'],data().shifts.map(s=>'<tr><td>'+esc(s.name)+'</td><td>'+s.start_time+'</td><td>'+(s.end_time<=s.start_time?'次日 ':'')+s.end_time+'</td><td>'+btn('编辑','wf-shift','data-id="'+s.id+'"','ghost small')+'</td></tr>').join(''))+'</div>',{wide:true,footer:btn(icon('plus')+'新增班次','wf-shift','','primary')+btn('关闭','close-modal')}),
  'wf-shift':e=>{const old=data().shifts.find(s=>s.id===Number(e.dataset.id));modal(old?'编辑班次':'新增班次','<div class="form-grid">'+field('班次名称','name','text',old?.name||'','required maxlength="80"')+field('开始时间','start_time','time',old?.start_time||'08:00','required')+field('结束时间','end_time','time',old?.end_time||'16:00','required')+'</div>',{onSubmit:async b=>save('shifts',{...b,id:old?.id,version:old?.version},'班次模板已保存')})},
  'wf-leave':()=>{
   const d=data(),people=d.employees.filter(e=>e.status==='在职'&&(manager(S)||e.id===d.own_employee_id));
   if(!people.length)throw new Error('请先由本厂负责人绑定你的员工档案');
   modal('请假申请','<div class="form-grid">'+select('请假员工','employee_id',people.map(e=>[e.id,e.name]),d.own_employee_id||people[0]?.id)+field('开始时间（北京时间）','start_at','datetime-local',d.date+'T08:00','required')+field('结束时间（北京时间）','end_at','datetime-local',d.date+'T16:00','required')+field('请假原因','reason','textarea','','required maxlength="500"')+'</div>'+notice('提交后由平台管理员或本厂负责人审批。获批的请假将影响当班识别与派单。'),{onSubmit:async b=>save('leaves',b,'请假申请已提交')});
  },
  'wf-leave-review':e=>{const l=data().leaves.find(l=>l.id===Number(e.dataset.id)),mode=e.dataset.mode;modal(({approve:'批准',reject:'驳回',cancel:'撤销'})[mode]+'请假申请','<p class="mb16">'+esc(l.employee_name)+' · '+date(l.start_at)+' → '+date(l.end_at)+'</p>'+field('处理说明','review_note','textarea','','required maxlength="500"')+(mode==='approve'?notice('批准后与班次重叠的人员将不计整班可用人数，请根据班表缺员提示安排替班。',true):''),{submit:'确认'+({approve:'批准',reject:'驳回',cancel:'撤销'})[mode],onSubmit:async b=>{const r=await save('leaves',{...b,id:l.id,version:l.version,action:mode},'请假记录已更新');if(r.affected_plans?.length)toast('已批准；有 '+r.affected_plans.length+' 个班次需要核对替班人员')}})}
 };
}

export async function dispatchFields(api,anomaly){
 const d=await api('/workforce/candidates?anomaly_id='+anomaly),eligible=d.candidates.filter(u=>u.eligible);
 if(!eligible.length)throw new Error('本厂暂无可派单账号，请先由负责人维护员工账号与请假安排');
 const recommended=eligible.find(u=>u.recommended);
 return '<div class="field full">'+notice('所需技能：'+d.required_skill+'。优先按当班、技能、同产线和待办数量排序；当班状态不等同于实际到岗。')+'</div>'+select('处理人 · 当班与技能推荐','assignee',[['','请选择处理人'],...eligible.map(u=>[u.id,u.name+' ｜ '+u.reason])],recommended?.id||'')+'<input type="hidden" name="required_skill" value="'+esc(d.required_skill)+'">'+field('调度说明（非当班或技能待核验时必填）','dispatch_note','textarea','','maxlength="300" placeholder="例如：已核实临时支援资格并确认到场，或预约下个班次执行。"');
}
export const dispatchBody=b=>({...b,assignee:Number(b.assignee)});
