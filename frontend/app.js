import {workforceActions,dispatchFields,dispatchBody} from './workforce.js';
import {mountLivePage,morph} from './live-ui.js';
import {esc,fmt,pct,date,icon,badge,btn,empty,notice,field,select,scene,chartLine,table} from './ui.js';
import {navItems,renderPage} from './pages.js';
import {mountMonitor,mountAssistant} from './experience.js';
const S={user:null,csrf:'',factory:1,page:'overview',meta:null,cache:{},anomaly:null,render:0,poll:null};
const root=document.getElementById('app');
let toastTimer,disposePage=()=>{};const pendingRequests=new Set();let sessionEpoch=0;
function toast(message,error=false){const el=document.getElementById('toast');el.textContent=message;el.className='visible'+(error?' error':'');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.className='',4500)}
async function api(path,body,options={}){
 const epoch=sessionEpoch,controller=new AbortController();pendingRequests.add(controller);
 let response;
 try{response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',signal:controller.signal,
  headers:{'Content-Type':'application/json','X-CSRF-Token':S.csrf,...(body!==undefined?{'Idempotency-Key':options.key||(crypto.randomUUID?crypto.randomUUID():Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,'0')).join(''))}:{} )},
  ...(body!==undefined?{body:JSON.stringify(body)}:{})});}
 finally{pendingRequests.delete(controller)}
 const data=await response.json();
 if(epoch!==sessionEpoch)throw new Error('登录状态已改变，请重新操作');
 if(!response.ok){
  if(response.status===401&&path!=='/login'){resetSession();showLogin()}
  if(response.status===404&&path.startsWith('/live'))throw new Error('监控服务尚未更新：请在原启动窗口按 Ctrl+C 停止服务，再双击 start.bat 启动，最后刷新页面。只重新打开浏览器不会更新后台服务。');
  throw new Error(data.error||'请求失败，请稍后重试');
 }
 return data;
}
function modal(title,content,{wide=false,onSubmit=null,submit='保存',footer=''}={}){
 document.querySelector('dialog')?.remove();
 const d=document.createElement('dialog');if(wide)d.className='wide';
 d.innerHTML='<form method="dialog"><div class="modal-head"><h2>'+title+'</h2><button type="button" class="icon-btn" data-action="close-modal" aria-label="关闭">'+icon('close')+'</button></div><div class="modal-body">'+content+'<div class="form-error" hidden></div></div>'+
  (onSubmit?'<div class="modal-foot"><button type="button" class="btn" data-action="close-modal">取消</button><button class="btn primary" type="submit">'+submit+'</button></div>':footer?'<div class="modal-foot">'+footer+'</div>':'')+'</form>';
 document.body.append(d);d.showModal();
 d.addEventListener('click',e=>{if(e.target===d)d.close()});d.addEventListener('close',()=>d.remove());
 d.querySelector('form').addEventListener('submit',async e=>{
  e.preventDefault();if(!onSubmit)return;
  const button=d.querySelector('[type=submit]');button.disabled=true;d.querySelector('.form-error').hidden=true;
  try{await onSubmit(Object.fromEntries(new FormData(e.target)),d);if(d.isConnected&&!d.dataset.keepOpen)d.close()}
  catch(err){const el=d.querySelector('.form-error');el.textContent=err.message;el.hidden=false}
  finally{button.disabled=false}
 });
 return d;
}
function resetSession(){
 sessionEpoch++;S.render++;disposePage();disposePage=()=>{};clearTimeout(S.poll);
 pendingRequests.forEach(c=>c.abort());pendingRequests.clear();
 S.workforceDate=null;S.workforceLine='';S.user=null;S.csrf='';S.meta=null;S.cache={};S.anomaly=null;S.factory=1;
 document.querySelectorAll('video').forEach(v=>{v.pause();v.removeAttribute('src');v.load()});
 document.querySelector('dialog')?.close();history.replaceState(null,'','#login');
}
function showLogin(){
 disposePage();disposePage=()=>{};
 root.innerHTML='<main class="login"><section class="login-visual"><div><div class="brand"><img src="/logo.svg" alt=""><div><strong>质因云联</strong><small>ZHIYIN YUNLIAN</small></div></div><h1>从车间感知<br>到生产决策。</h1><p>连接生产现场，洞察质量之因。<br>让数据、分析与现场行动在这里汇合。</p></div><div class="login-scene">'+scene([])+'</div><div class="login-foot">CONNECTED FACTORY · EXPLAINABLE INTELLIGENCE</div></section><section class="login-panel"><form class="login-form" id="login-form"><div class="eyebrow">WELCOME TO YOUR WORKSPACE</div><h2>登录智慧工厂工作台</h2><p>开始今天的生产管理与协同工作。</p>'+field('账号','username','text','admin','required autocomplete="username"')+field('密码','password','password','Zyyl@2026','required autocomplete="current-password"')+'<div class="form-error" hidden></div><button class="btn primary" type="submit">进入工作台 '+icon('arrow')+'</button><div class="demo-accounts"><button type="button" data-action="demo-account" data-user="admin">平台管理</button><button type="button" data-action="demo-account" data-user="engineer">质量工程师</button><button type="button" data-action="demo-account" data-user="operator">现场作业</button></div><p class="login-note">演示密码：Zyyl@2026<br>演示流程使用模拟样本，项目业务存档在数据中心注明来源。</p></form></section></main>';
 document.getElementById('login-form').addEventListener('submit',async e=>{
  e.preventDefault();const b=e.target.querySelector('[type=submit]');b.disabled=true;
  try{const data=await api('/login',Object.fromEntries(new FormData(e.target)));S.user=data;S.csrf=data.csrf;S.factory=data.factory_id||1;await shell()}
  catch(err){const el=e.target.querySelector('.form-error');el.textContent=err.message;el.hidden=false}
  finally{b.disabled=false}
 });
}
async function shell(){
 S.meta=await api('/meta?factory_id='+S.factory);
 const roleLabel={admin:'平台管理员',engineer:'质量工程师',operator:'现场班组长',manager:'生产负责人'};
 root.innerHTML='<aside class="sidebar"><a class="brand" href="#overview"><img src="/logo.svg" alt=""><div><strong>质因云联</strong><small>ZHIYIN YUNLIAN</small></div></a><nav class="nav">'+navItems.map(([id,title,ic,group])=>(group?'<div class="nav-label">'+group+'</div>':'')+'<a href="#'+id+'" data-page="'+id+'">'+icon(ic)+'<span>'+title+'</span></a>').join('')+'</nav><div class="sidebar-bottom"><div class="row"><div class="avatar">'+esc(S.user.name[0])+'</div><div><strong style="font-size:12px">'+esc(S.user.name)+'</strong><small class="muted" style="display:block;font-size:10px">'+roleLabel[S.user.role]+'</small></div><button class="icon-btn" data-action="logout" title="退出登录" aria-label="退出登录" style="margin-left:auto">'+icon('logout')+'</button></div><div class="side-version">智慧工厂平台 <span style="float:right">v1.5.0</span></div></div></aside><div class="shell"><header class="topbar"><div class="breadcrumb"><button class="icon-btn mobile-menu" data-action="menu" aria-label="打开菜单">'+icon('menu')+'</button><span>智慧工厂</span><span>/</span><strong id="crumb">运营总览</strong></div><div class="top-actions"><span class="date muted tiny">'+new Date().toLocaleDateString('zh-CN',{year:'numeric',month:'long',day:'numeric',weekday:'long'})+'</span><span class="chip demo-tag">演示环境 · 数据可追溯</span><select id="factory-select" aria-label="选择工厂">'+S.meta.factories.map(f=>'<option value="'+f.id+'" '+(f.id===S.factory?'selected':'')+'>'+esc(f.name)+'</option>').join('')+'</select><button class="icon-btn" data-action="go" data-page="analysis" title="异常工作台" aria-label="异常工作台">'+icon('bell')+'</button><button class="icon-btn logout-label" data-action="logout" aria-label="退出登录">'+icon('logout')+'<span>退出登录</span></button></div></header><main class="main"><div id="page"></div><footer class="footer"><span>质因云联 · 从车间感知到生产决策</span><span>数据驱动洞察，协同连接行动。</span></footer></main></div><nav class="bottom-nav">'+[['overview','总览','home'],['monitor','监控','device'],['tasks','现场作业','tasks'],['assistant','AI 问答','cause'],['federation','联邦','network']].map(([id,label,ic])=>'<a href="#'+id+'" data-page="'+id+'">'+icon(ic)+label+'</a>').join('')+'</nav>';
 document.getElementById('factory-select').addEventListener('change',async e=>{S.factory=Number(e.target.value);S.workforceLine='';S.cache={};S.anomaly=null;S.meta=await api('/meta?factory_id='+S.factory);await render()});
 const initial=location.hash.slice(1);
 S.page=navItems.some(n=>n[0]===initial)?initial:S.user.role==='operator'?'tasks':'overview';
 if(initial!==S.page)history.replaceState(null,'','#'+S.page);
 await render();
}
async function render(quiet=false){
 if(!S.user)return;
 clearTimeout(S.poll);const current=++S.render;const container=document.getElementById('page');if(!container)return;
 disposePage();disposePage=()=>{};
 document.getElementById('crumb').textContent=navItems.find(n=>n[0]===S.page)?.[1]||'工作台';
 document.querySelectorAll('nav [data-page]').forEach(a=>a.classList.toggle('active',a.dataset.page===S.page));
 document.querySelector('.sidebar')?.classList.remove('open');
 if(!quiet)container.innerHTML='<div class="loading"><span class="spinner"></span> 正在加载工作台</div>';
 try{
  const html=await renderPage(S.page,S,api);
  if(current!==S.render)return;
  container.innerHTML=html;
  if(S.page==='monitor')disposePage=mountMonitor(S,api);
  if(S.page==='assistant')disposePage=mountAssistant(S,api,toast);
  if(S.user.role==='operator')container.querySelectorAll('[data-action="new-order"],[data-action="order-state"],[data-action="run-analysis"],[data-action="inspection-task"],[data-action="import-samples"],[data-action="compare-plan"]').forEach(el=>el.remove());
  document.getElementById('search')?.addEventListener('input',e=>{const v=e.target.value.toLowerCase();container.querySelectorAll('[data-search]').forEach(r=>r.hidden=!r.dataset.search.toLowerCase().includes(v))});
  if(!['monitor','assistant'].includes(S.page))disposePage=mountLivePage(S,api,renderPage,()=>{const search=document.getElementById('search');if(search){const value=search.value.toLowerCase();container.querySelectorAll('[data-search]').forEach(r=>r.hidden=!r.dataset.search.toLowerCase().includes(value))}if(S.user.role==='operator')container.querySelectorAll('[data-action=\"new-order\"],[data-action=\"order-state\"],[data-action=\"run-analysis\"],[data-action=\"inspection-task\"],[data-action=\"import-samples\"],[data-action=\"compare-plan\"]').forEach(el=>el.remove())});

 }catch(err){if(current===S.render&&S.user)container.innerHTML=notice(err.message,true)+'<div class="mt16">'+btn('重新加载','refresh')+'</div>'}
}
function go(page){if(S.page===page)render();else location.hash=page}
window.addEventListener('hashchange',()=>{if(!S.user)return;const p=location.hash.slice(1);S.page=navItems.some(n=>n[0]===p)?p:'overview';render()});
async function taskDetail(id){
 const t=await api('/tasks/'+id);S.cache.task=t;
 const canWork=S.user.role==='admin'||t.assignee===S.user.id,canReview=['admin','engineer','manager'].includes(S.user.role);
 let controls='';
 if(t.status==='待接单'&&canWork)controls+=btn(icon('check')+'接收任务','task-accept','data-id="'+id+'"','primary');
 if(t.status==='处理中'&&canWork)controls+=btn('提交处置记录','task-submit','data-id="'+id+'"','primary');
 if(t.status==='待复检'&&canReview)controls+=btn('录入复检结果','task-review','data-id="'+id+'"','primary');
 if(['待接单','处理中'].includes(t.status)&&canWork)controls+=btn(icon('camera')+'现场照片','task-photo','data-id="'+id+'"');
 modal('处置工单 · TASK-'+String(id).padStart(4,'0'),'<div class="row between mb16"><h3>'+esc(t.title)+'</h3>'+badge(t.status)+'</div><div class="notice">'+icon('tasks')+'<p>'+esc(t.action)+'</p></div>'+
  '<div class="grid2 mt24"><div><h3 class="mb16">处理记录</h3>'+(t.note?'<p class="instruction">'+esc(t.note)+'</p>':empty('待现场反馈'))+
  (t.review_note?'<div class="divider"></div><h3>复检结果</h3><p class="instruction mt16">'+esc(t.review_note)+'</p>'+(t.sample_size?'<p class="green mt16">抽检 '+t.sample_size+' 件，不合格 '+t.defects+' 件，合格率 '+pct(1-t.defects/t.sample_size)+'</p>':''):'')+
  '<div class="preview-photos mt16">'+t.attachments.map(a=>'<a href="/api/photos/'+a.id+'" target="_blank" rel="noopener"><img src="/api/photos/'+a.id+'" alt="'+esc(a.original_name)+'"></a>').join('')+'</div></div><div><h3 class="mb16">工单时间线</h3><div class="timeline">'+t.events.map(e=>'<div class="timeline-item"><strong style="font-size:12px">'+esc(e.action)+' · '+esc(e.user_name)+'</strong><p>'+esc(e.note)+'</p><small>'+date(e.created_at)+'</small></div>').join('')+'</div></div></div>',
  {wide:true,footer:controls+btn('关闭','close-modal')});
}
async function createTask(factor){
 const record=S.cache.analysis;if(!record)throw new Error('请先完成一次分析');
 const staffing=await dispatchFields(api,record.anomaly_id);
 const f=record.result.factors.find(x=>x.key===factor)||record.result.factors[0];
 modal('创建现场处置工单','<div class="mb16">'+notice('请先核对现场条件。工单是待人工执行的检查或处置任务，不会自动修改真实设备参数。')+'</div><div class="form-grid">'+
  staffing+
  field('关联异常','anomaly','text','#'+record.anomaly_id,'disabled')+
  field('处置内容','action','textarea',f.action+'；核对当前批次是否存在该因素，完成后提交现场记录并申请复检。','required maxlength="2000"')+'</div>',
  {submit:'确认并派单',onSubmit:async b=>{await api('/tasks',{...dispatchBody(b),anomaly_id:record.anomaly_id,analysis_id:record.id});toast('处置工单已创建');go('tasks')}});
}
const actions={
 ...workforceActions({S,api,modal,toast,render}),
 'go':e=>{e.closest('dialog')?.close();go(e.dataset.page)},
 'refresh':()=>render(),
 'menu':()=>document.querySelector('.sidebar').classList.toggle('open'),
 'close-modal':()=>document.querySelector('dialog')?.close(),
 'demo-account':e=>{document.querySelector('[name=username]').value=e.dataset.user;document.querySelector('[name=password]').value='Zyyl@2026'},
 'logout':async e=>{
  e.disabled=true;
  try{await api('/logout',{});resetSession();showLogin();document.querySelector('#login-form [name=password]').value='';toast('已退出登录')}
  finally{e.disabled=false}
 },
 'assistant-preset':e=>{
  const form=document.getElementById('assistant-form');form.dataset.scenario=e.dataset.scenario;
  form.querySelector('textarea').value=e.dataset.question;form.querySelector('textarea').focus();
 },
 'assistant-task':e=>{
  const m=S.cache.assistant.messages.find(m=>m.id===Number(e.dataset.id));
  S.cache.analysis=m.response.analysis;return createTask(m.response.factors[0]?.key);
 },
 'export':e=>{location.href='/api/export?kind='+e.dataset.kind+'&factory_id='+S.factory},
 'open-analysis':e=>{S.anomaly=Number(e.dataset.id);go('analysis')},
 'select-anomaly':e=>{S.anomaly=Number(e.dataset.id);render()},
 'run-analysis':async e=>{e.disabled=true;e.innerHTML='<span class="spinner"></span> 正在计算';try{await api('/analyze',{anomaly_id:Number(e.dataset.id),source:document.getElementById('analysis-source')?.value});toast('分析完成，已保存证据记录');await render()}finally{e.disabled=false}},
 'compare-plan':e=>{
  const record=S.cache.analysis,f=record.result.factors.find(x=>x.key===e.dataset.key);
  modal('处置方案 · '+f.name,'<div class="mb16">'+notice(f.supported?'当前样本支持进一步排查该因素。效应为总体风险差，不代表本次处置一定产生相同改善。':'当前证据不足以直接支持调整，建议先补充检测与现场核对。',!f.supported)+'</div>'+
   table(['方案','行动','证据与边界'],'<tr><td>保持现状并观察</td><td>继续采集同类样本</td><td>适合尚未确认现场暴露条件时</td></tr><tr><td>检查并恢复标准条件</td><td style="white-space:normal">'+esc(f.action)+'</td><td style="white-space:normal">暴露相对正常的风险差 '+(f.effect*100).toFixed(1)+' 个百分点；反向干预需假设成立且现场适用</td></tr>')+
   '<div class="mt24"><h3>分层证据</h3>'+table(['原料等级 / 产品规格','正常样本','暴露样本','正常缺陷率','暴露缺陷率'],f.strata.map(s=>'<tr><td>'+s.material+' / '+s.product+'</td><td>'+s.normal+'</td><td>'+s.exposed+'</td><td>'+pct(s.normal_rate)+'</td><td>'+pct(s.exposed_rate)+'</td></tr>').join(''))+'</div>',
   {wide:true,footer:btn('生成检查与处置工单','create-task','data-key="'+f.key+'"','primary')+btn('关闭','close-modal')});
 },
 'create-task':e=>createTask(e.dataset.key),
 'inspection-task':async e=>{
  const a=S.cache.anomalies.find(x=>x.id===Number(e.dataset.id)),staffing=await dispatchFields(api,a.id);
  modal('安排现场检查','<div class="form-grid">'+staffing+field('检查内容','action','textarea',a.description,'required maxlength="2000"')+'</div>',
   {submit:'创建检查工单',onSubmit:async b=>{await api('/tasks',{...dispatchBody(b),anomaly_id:a.id});toast('现场检查工单已创建');go('tasks')}});
 },
 'new-order':async()=>{
  const devices=await api('/devices?factory_id='+S.factory);
  modal('新建生产工单','<div class="form-grid">'+field('产品名称','product','text','','required maxlength="120"')+field('生产批次','batch','text','','required maxlength="120"')+
   field('计划数量','quantity','number',1000,'required min="1" max="1000000" step="1"')+field('计划交期','due_date','date',new Date(Date.now()+86400000).toLocaleDateString('sv-SE'),'required')+
   select('生产设备','device_id',devices.map(d=>[d.id,d.code+' · '+d.name]))+select('优先级','priority',[['普通','普通'],['紧急','紧急']])+'</div>',
   {submit:'创建工单',onSubmit:async b=>{await api('/orders',{...b,factory_id:S.factory});toast('生产工单已创建');await render()}});
 },
 'order-state':async e=>{await api('/orders/'+e.dataset.id,{action:e.dataset.op});toast('工单状态已更新');await render()},
 'report-production':e=>{
  const o=S.cache.orders.find(x=>x.id===Number(e.dataset.id));
  modal('生产报工 · '+esc(o.code),'<p class="instruction mb16">'+esc(o.product)+' · 剩余计划 '+fmt(o.quantity-o.completed)+' 件</p>'+field('本次完成数量','quantity','number',Math.min(100,o.quantity-o.completed),'required min="1" max="'+(o.quantity-o.completed)+'" step="1"'),
   {submit:'确认报工',onSubmit:async b=>{await api('/orders/'+o.id,{...b,action:'report'});toast('报工记录已保存');await render()}});
 },
 'new-quality':async()=>{
  const orders=await api('/orders?factory_id='+S.factory);
  modal('录入质量检测','<div class="form-grid">'+select('关联生产工单','order_id',orders.filter(o=>!o.archived).map(o=>[o.id,o.code+' · '+o.product]))+
   field('缺陷类型 / 检测项目','defect_type','text','尺寸偏差','required')+field('抽检数量','sample_size','number',100,'required min="1" step="1"')+field('不合格数量','defects','number',0,'required min="0" step="1"')+'</div><div class="mt16">'+notice('不合格率超过 5% 会产生关联异常，便于继续分析与处置。')+'</div>',
   {submit:'保存检测结果',onSubmit:async b=>{const r=await api('/quality',b);toast(r.rate>.05?'质检已保存，请关注关联异常':'质检记录已保存');await render()}});
 },
 'device-detail':async e=>{
  const id=e.dataset.id,d=await api('/devices/'+id);S.cache.device=d;
  const details=x=>'<div class="row between mb16"><span class="muted">'+esc(x.line)+' · 最近采集 '+date(x.updated_at)+'</span>'+badge(x.display_status||x.status)+'</div><div class="metric-strip"><div><strong>'+(x.temperature??'未采集')+'℃</strong><small>温度</small></div><div><strong>'+(x.pressure??'未采集')+' MPa</strong><small>压力</small></div><div><strong>'+(x.vibration??'未采集')+' mm/s</strong><small>振动</small></div></div><h3 class="muted mb16">最近 40 条温度记录</h3>'+chartLine(x.readings.map(r=>({...r,date:r.created_at.slice(11,19)})),['temperature']);
  const dialog=modal(esc(d.code)+' · '+esc(d.name),'<div id="device-live-details">'+details(d)+'</div><p class="muted tiny mt16" id="device-live-status">每 3 秒同步采集记录 · 请按设备时间判断新鲜度</p><div class="mt16">'+notice('参数越限会产生异常。当前为演示环境，录入采集值或启动演示产线可验证联动。')+'</div>',
   {wide:true,footer:(d.simulated?btn('大屏工况控制','go','data-page="monitor"'):btn('录入采集值','device-reading','data-id="'+d.id+'"','primary'))+btn('关闭','close-modal')});
  let timer;
  const tick=async()=>{if(!dialog.isConnected||!dialog.open||!S.user)return;try{const latest=await api('/devices/'+id);if(!dialog.isConnected)return;S.cache.device=latest;morph(dialog.querySelector('#device-live-details'),details(latest));dialog.querySelector('#device-live-status').textContent='查询成功 '+new Date().toLocaleTimeString('zh-CN')+' · 采集 '+date(latest.updated_at)}catch{if(dialog.isConnected)dialog.querySelector('#device-live-status').textContent='连接中断，保留最近记录'}if(dialog.isConnected)timer=setTimeout(tick,3000)};
  timer=setTimeout(tick,3000);dialog.addEventListener('close',()=>clearTimeout(timer),{once:true});
 },
 'device-reading':e=>{
  const d=S.cache.device;
  modal('记录设备采集值','<div class="form-grid">'+field('温度 / ℃','temperature','number',d.temperature??'','required min="-50" max="500" step=".1"')+
   field('压力 / MPa','pressure','number',d.pressure??'','required min="0" max="50" step=".01"')+field('振动 / mm/s','vibration','number',d.vibration??'','required min="0" max="100" step=".01"')+'</div>',
   {onSubmit:async b=>{await api('/devices/'+d.id+'/reading',b);toast('采集记录已保存');await render()}});
 },
 'task-detail':e=>taskDetail(Number(e.dataset.id)),
 'task-accept':async()=>{const t=S.cache.task;await api('/tasks/'+t.id,{action:'accept',version:t.version});toast('已接收任务');await render();await taskDetail(t.id)},
 'task-submit':()=>{
  const t=S.cache.task;
  modal('提交现场处置记录','<div class="mb16">'+notice('记录实际检查、调整或维修内容。提交后由质量人员复检。')+'</div>'+field('实际处理过程与结果','note','textarea','','required maxlength="2000"'),
   {submit:'提交复检',onSubmit:async b=>{await api('/tasks/'+t.id,{...b,action:'submit',version:t.version});toast('已提交，等待复检');await render()}});
 },
 'task-review':()=>{
  const t=S.cache.task;
  if(t.review_type==='equipment'){
   modal('确认设备点检结果','<div class="form-grid">'+select('现场检查结论','inspection_pass',[['true','点检通过'],['false','退回继续处理']])+field('复核依据与检查记录','note','textarea','','required maxlength="2000"')+'</div>',
    {submit:'确认点检',onSubmit:async b=>{const r=await api('/tasks/'+t.id,{...b,action:'review',version:t.version});toast(r.status==='已关闭'?'点检通过，事件已关闭':'已退回继续处理');await render()}});return;
  }
  modal('录入复检结果','<div class="form-grid">'+field('复检抽样数量','sample_size','number',100,'required min="1" step="1"')+
   field('不合格数量','defects','number',0,'required min="0" step="1"')+field('复检说明','note','textarea','','required maxlength="2000"')+'</div><div class="mt16">'+notice('不合格率不超过 5% 时关闭工单与异常；超过阈值则退回继续处理。')+'</div>',
   {submit:'确认复检',onSubmit:async b=>{const r=await api('/tasks/'+t.id,{...b,action:'review',version:t.version});toast(r.status==='已关闭'?'复检通过，异常已关闭':'复检未通过，退回继续处理');await render()}});
 },
 'task-photo':()=>{
  const t=S.cache.task;
  modal('上传现场照片',field('JPEG / PNG，不超过 2MB','photo','file','','required accept="image/jpeg,image/png"'),
   {submit:'上传照片',onSubmit:async(b,d)=>{
    const file=d.querySelector('[type=file]').files[0];if(!file)throw new Error('请选择照片');if(file.size>2*1024*1024)throw new Error('图片不得超过2MB');
    const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file)});
    await api('/tasks/'+t.id+'/photo',{name:file.name,data});toast('现场照片已保存');await render();
   }});
 },
 'stock-move':e=>{
  const m=S.cache.materials.find(x=>x.id===Number(e.dataset.id));
  modal('物料出入库 · '+esc(m.name),'<p class="instruction mb16">当前库存 '+fmt(m.stock)+' '+esc(m.unit)+'</p><div class="form-grid">'+select('操作类型','direction',[['入库','入库'],['出库','出库']])+field('数量 / '+esc(m.unit),'quantity','number',10,'required min=".01" step=".01"')+field('业务说明','note','textarea','','required maxlength="1000"')+'</div>',
   {submit:'确认出入库',onSubmit:async b=>{await api('/materials/'+m.id,b);toast('库存与流水已更新');await render()}});
 },
 'risk-predict':()=>{
  modal('本厂质量风险试算','<div class="form-grid">'+[['temp','温度偏高'],['pressure','压力偏高'],['wear','设备磨损'],['material','原料等级'],['product','产品规格']].map(([key,label])=>select(label,key,[['0','0 · 正常 / 类别 0'],['1','1 · 偏高或磨损 / 类别 1']])).join('')+'</div><div class="mt16">'+notice('采用本厂当前模型计算。字段编码须与训练数据一致；预测概率未经真实现场校准。')+'</div>',
   {submit:'计算质量风险',onSubmit:async(b,d)=>{
    const r=await api('/federation/predict',{...b,factory_id:S.factory});d.dataset.keepOpen='true';
    d.querySelector('.modal-body').innerHTML='<div class="stat-number '+(r.flagged?'orange':'green')+'">'+pct(r.risk)+'</div><p class="instruction">模型：'+esc(r.version)+' · 提示阈值 '+pct(r.threshold)+'</p><p class="mt16">'+(r.flagged?'建议增加现场检查，核对温度、压力与磨损。':'当前编码条件未达到模型提示阈值，仍按质检规范执行。')+'</p><div class="mt16">'+notice(r.message)+'</div>';
    d.querySelector('.modal-foot').innerHTML=btn('关闭','close-modal');
   }});
 },
 'start-training':()=>{
  modal('发起跨厂联合训练','<div class="mb16">'+notice('各节点独立读取本地样本，训练逻辑回归模型，并通过 HTTP 交换参数。完成后计算各厂测试集指标。')+'</div><div class="form-grid">'+field('联邦训练轮数','rounds','number',10,'required min="2" max="30" step="1"')+field('每轮本地迭代次数','epochs','number',8,'required min="2" max="15" step="1"')+select('演示节奏','pace',[['1','每轮展示 1 秒'],['0','按计算速度运行'],['2','每轮展示 2 秒']])+'</div>',
   {submit:'开始训练',onSubmit:async b=>{await api('/federation/start',b);toast('训练已启动');await render()}});
 },
 'cancel-training':async()=>{await api('/federation/cancel',{});toast('已请求取消，将在当前轮次结束后停止');setTimeout(()=>render(),700)},
 'pause-training':async()=>{await api('/federation/pause',{paused:true});toast('将在当前轮次结束后暂停');await render(true)},
 'resume-training':async()=>{await api('/federation/pause',{paused:false});toast('训练已继续');await render(true)},
 'toggle-node':async e=>{await api('/federation/nodes/'+e.dataset.id,{enabled:e.dataset.enabled==='true'});toast('节点状态已更新');await render()},
 'import-samples':()=>{
  modal('导入工艺样本','<div class="mb16">'+notice('CSV 包含 temp,pressure,wear,material,product,defect 六列，值为 0 或 1。请确认字段含义与当前工艺一致。')+'</div><div class="form-grid">'+field('CSV 文件','file','file','','required accept=".csv"')+field('数据来源说明','source','text','','required maxlength="120" placeholder="例如：授权实验台采样 / 模拟样本"')+'</div>',
   {submit:'校验并导入',onSubmit:async(b,d)=>{
    const file=d.querySelector('[type=file]').files[0];if(!file)throw new Error('请选择文件');if(file.size>2000000)throw new Error('文件不得超过2MB');
    const result=await api('/samples/import',{csv:await file.text(),source:b.source,factory_id:S.factory});toast('成功导入 '+result.count+' 条样本');await render();
   }});
 },
 'download-template':()=>{
  const csv='\ufefftemp,pressure,wear,material,product,defect\n0,0,0,0,0,0\n1,0,0,1,0,1\n0,1,1,0,1,0\n';
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='工艺样本模板.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 },
 'change-password':()=>{
  modal('修改登录密码','<div class="form-grid">'+field('原密码','old_password','password','','required autocomplete="current-password"')+
   field('新密码','new_password','password','','required minlength="10" autocomplete="new-password"')+'</div><p class="muted tiny mt16">至少 10 位，包含字母和数字。</p>',
   {submit:'更新密码',onSubmit:async b=>{await api('/password',b);toast('密码已更新')}});
 }
};
document.addEventListener('click',async e=>{
 const target=e.target.closest('[data-action]');if(!target||target.disabled)return;
 const handler=actions[target.dataset.action];if(!handler)return;
 e.preventDefault();try{await handler(target)}catch(err){toast(err.message,true)}
});
document.addEventListener('change',e=>{if(e.target.id==='wf-date'){S.workforceDate=e.target.value;render()}if(e.target.id==='wf-line'){S.workforceLine=e.target.value;render()}});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('svg [data-action]')){e.preventDefault();e.target.dispatchEvent(new MouseEvent('click',{bubbles:true}))}});
async function boot(){try{const r=await fetch('/api/me');if(!r.ok)return showLogin();S.user=await r.json();S.csrf=S.user.csrf;S.factory=S.user.factory_id||1;await shell()}catch(err){showLogin();toast('服务连接失败，请确认启动窗口仍在运行',true)}}
boot();
