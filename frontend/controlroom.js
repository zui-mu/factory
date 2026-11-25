import {conditionSummary,processCharts} from './conditions.js';
import {esc,fmt,pct,icon,btn} from './ui.js';
import {morph} from './live-ui.js';
import {renderDefenseRecord} from './defense.js';
const block=(name,title,extra='')=>'<section class="control-panel cp-'+name+'"><div class="cp-head"><h2>'+title+'</h2>'+extra+'</div><div id="monitor-'+name+'" class="cp-body"></div></section>';
const value=(v,digits=1)=>v==null?'—':Number(v).toFixed(digits);
const time=s=>s?s.slice(11,19):'未采集';
const activeDevices=ds=>ds.filter(d=>!d.archived);
const age=d=>d?.updated_at?Math.max(0,(Date.now()-new Date(d.updated_at).getTime())/1000):Infinity;
const stale=d=>!d?.fresh;
const line=(values,color='#43c7ff')=>{
 if(!values.length)return '<span class="cp-empty">等待采集</span>';
 const lo=Math.min(...values)-1,hi=Math.max(...values)+1;
 const points=values.map((v,i)=>[i*300/Math.max(1,values.length-1),70-(v-lo)/(hi-lo)*55]);
 return '<svg class="spark" viewBox="0 0 300 80" preserveAspectRatio="none"><defs><linearGradient id="sensor-fill" x2="0" y2="1"><stop stop-color="'+color+'" stop-opacity=".3"/><stop offset="1" stop-color="'+color+'" stop-opacity="0"/></linearGradient></defs><path d="M0 80 L'+points.map(p=>p.join(' ')).join(' L')+' L300 80 Z" fill="url(#sensor-fill)"/><polyline points="'+points.map(p=>p.join(',')).join(' ')+'" fill="none" stroke="'+color+'" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>';
};
function sensors(l){const d=l.device,old=stale(d);return '<div class="sensor-meta"><strong>'+esc(d?.code||'等待设备')+'</strong><span class="'+(old?'amber':'cyan')+'">'+(old?'通信未知':'采集有效')+'</span></div><div class="sensor-values">'+[[d?.simulated?'模具温度':'温度',d?.temperature,'℃',1],['压力',d?.pressure,'MPa',2],['振动',d?.vibration,'mm/s',2]].map(([name,v,u,n])=>'<div><span>'+name+'</span><strong class="'+(name.includes('温度')&&v>90?'red-value':'')+'">'+value(v,n)+'<small>'+u+'</small></strong></div>').join('')+'</div><div class="sensor-spark">'+line(l.readings.map(r=>r.temperature))+'</div><div class="cp-caption"><span>'+esc(l.source)+'</span><span>'+time(d?.updated_at)+'</span></div>'}
function equipment(ds){const list=activeDevices(ds);return '<div class="equipment-list">'+list.map(d=>'<button data-action="monitor-device" data-id="'+d.id+'"><div><span>'+esc(d.name)+'</span><em class="'+(stale(d)?'muted-value':d.status==='预警'?'amber':'cyan')+'">'+esc(d.display_status||'通信未知')+'</em></div><div class="equipment-bar"><i style="--level:'+Math.min(100,(d.temperature||0)/100*100)+'%;--tone:'+(d.temperature>90?'#eea063':'#687aff')+'"></i></div><small>'+esc(d.code)+' · '+value(d.temperature)+'℃ · '+time(d.updated_at)+'</small></button>').join('')+'</div>'}
function alerts(d){return d.alerts.length?'<div class="alarm-head"><span>异常 / 时间</span><span>处理状态</span></div><div class="alarm-list">'+d.alerts.map(a=>'<button class="alarm-row" data-action="open-analysis" data-id="'+a.id+'"><span><strong><i></i>'+esc(a.title)+'</strong><small>'+time(a.created_at)+' · '+esc(a.severity)+'优先级</small></span><em>'+esc(a.status)+'</em></button>').join('')+'</div>':'<div class="cp-empty">暂无待处理异常</div>'}
function stats(d){const orders=d.orders.filter(o=>o.status!=='已取消'),completed=orders.reduce((n,o)=>n+o.completed,0);return '<div class="count-rings">'+[[orders.length,'生产工单','单'],[completed,'累计报工','件']].map(([n,label,u])=>'<div><div class="count-ring"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="43" fill="none" stroke="#172c64" stroke-width="5"/><circle class="ring-orbit" cx="50" cy="50" r="43" fill="none" stroke="#279ddd" stroke-width="5" stroke-dasharray="2.5 3"/></svg><strong>'+fmt(n)+'<small>'+u+'</small></strong></div><span>'+label+'</span></div>').join('')+'</div><div class="stat-subline"><span>生产中 <b>'+orders.filter(o=>o.status==='生产中').length+'</b></span><span>暂停 <b>'+orders.filter(o=>o.status==='已暂停').length+'</b></span><span>待排产 <b>'+orders.filter(o=>o.status==='待排产').length+'</b></span></div>'}
function gauge(d){const orders=d.orders.filter(o=>o.status!=='已取消'),plan=orders.reduce((n,o)=>n+o.quantity,0),done=orders.reduce((n,o)=>n+o.completed,0),rate=plan?done/plan:0;return '<div class="production-gauge"><svg viewBox="0 0 220 137"><path d="M25 110 A85 85 0 0 1 195 110" fill="none" stroke="#19325b" stroke-width="14"/><path d="M25 110 A85 85 0 0 1 195 110" fill="none" stroke="#34c6d5" stroke-width="14" pathLength="100" stroke-dasharray="'+(rate*100)+' 100"/><path d="M110 108 L43 103 L110 113Z" fill="#8af4ee" transform="rotate('+(rate*180)+' 110 110)"/><circle cx="110" cy="110" r="5" fill="#c7ffff"/><text x="110" y="80" text-anchor="middle" fill="#d5f4ff" font-size="25">'+pct(rate)+'</text><text x="110" y="132" text-anchor="middle" fill="#789ac7" font-size="10">工单累计完成率</text></svg><div><p>计划数量 <strong>'+fmt(plan)+'<small>件</small></strong></p><p>累计完成 <strong>'+fmt(done)+'<small>件</small></strong></p></div></div><div class="quality-strip"><span>今日抽检合格率</span><strong>'+pct(d.kpi.quality_rate)+'</strong><small>'+fmt(d.kpi.sample_count)+' 件</small></div>'}
function orders(d){return '<div class="screen-table-head"><span>工单 / 产品</span><span>完成 / 计划</span></div><div class="screen-orders">'+d.orders.map(o=>'<div class="screen-order"><div><b>'+esc(o.product)+'</b><em class="'+(o.priority==='紧急'?'priority-hot':'')+'">'+esc(o.status)+'</em></div><small>'+esc(o.code)+' · '+esc(o.due_date)+'</small><div class="screen-progress"><i style="width:'+Math.min(100,o.completed/o.quantity*100)+'%"></i></div><p>'+fmt(o.completed)+' / '+fmt(o.quantity)+' 件</p></div>').join('')+'</div>'}
function stock(ms){return ms.filter(m=>!m.archived).map(m=>'<div class="stock-row"><div><span>'+esc(m.name)+'</span><strong class="'+(m.stock<m.min_stock?'amber':'cyan')+'">'+fmt(m.stock)+'<small>'+esc(m.unit)+'</small></strong></div><div class="stock-level"><i style="width:'+Math.min(100,m.stock/Math.max(1,m.min_stock*2)*100)+'%;background:'+(m.stock<m.min_stock?'#e9a75a':'#637beb')+'"></i></div><small>安全库存 '+fmt(m.min_stock)+' '+esc(m.unit)+' · '+(m.stock<m.min_stock?'待补料':'库存正常')+'</small></div>').join('')}
function events(l){return '<div class="event-columns"><span>时间</span><span>现场事件</span><span>来源</span></div><div class="event-rows">'+(l.events.length?l.events.map(e=>'<div><time>'+time(e.created_at)+'</time><span title="'+esc(e.entity)+'">'+esc(e.action)+'</span><small>'+esc(e.user_name)+'</small></div>').join(''):'<p class="cp-empty">等待报工、采集或处置记录</p>')+'</div>'}
function chart(d,l){const hs=l.hourly,max=Math.max(5,...hs.map(h=>h.quantity)),w=620;
 const bar=hs.map((h,i)=>{const x=45+i*70,height=h.quantity/max*100;return '<rect x="'+x+'" y="'+(125-height)+'" width="22" height="'+height+'" rx="2" fill="url(#bar-fill)"/><text x="'+(x+11)+'" y="'+(117-height)+'" text-anchor="middle" fill="#84dbfa" font-size="10">'+h.quantity+'</text><text x="'+(x+11)+'" y="147" text-anchor="middle" fill="#718aad" font-size="10">'+h.hour+'</text>'}).join('');
 const trend=d.trend.slice(-7),points=trend.map((t,i)=>[30+i*270/Math.max(1,trend.length-1),110-(1-t.defects/t.samples)*85]);
 return '<div class="bottom-chart"><div><div class="cp-caption"><span>近8小时报工量（件）</span><span>按报工时间汇总</span></div><svg viewBox="0 0 '+w+' 155" preserveAspectRatio="xMidYMid meet"><defs><linearGradient id="bar-fill" x2="0" y2="1"><stop stop-color="#40d1f0"/><stop offset="1" stop-color="#185ba1"/></linearGradient></defs>'+[25,75,125].map(y=>'<line x1="20" y1="'+y+'" x2="600" y2="'+y+'" stroke="#18315d" stroke-dasharray="3 5"/>').join('')+bar+'</svg></div><div><div class="cp-caption"><span>近7个检测日合格率</span><span>0–100%</span></div><svg viewBox="0 0 330 155" preserveAspectRatio="xMidYMid meet"><line x1="25" y1="110" x2="315" y2="110" stroke="#18315d"/><polyline points="'+points.map(p=>p.join(',')).join(' ')+'" fill="none" stroke="#e4c75d" stroke-width="2"/>'+points.map((p,i)=>'<circle cx="'+p[0]+'" cy="'+p[1]+'" r="3" fill="#eed775"/><text x="'+p[0]+'" y="'+(p[1]-10)+'" text-anchor="middle" fill="#acb9cf" font-size="9">'+pct(1-trend[i].defects/trend[i].samples)+'</text><text x="'+p[0]+'" y="145" text-anchor="middle" fill="#718aad" font-size="9">'+trend[i].date.slice(5)+'</text>').join('')+'</svg></div></div>'}
async function load(S,api,selected){const q='?factory_id='+S.factory;const [d,m,ds,l]=await Promise.all([api('/overview'+q),api('/materials'+q),api('/devices'+q),api('/live'+q+(selected?'&device_id='+selected:''))]);return {d,m,ds,l}}
function regions(data,mode='temperature'){const {d,m,ds,l}=data;return {sensors:sensors(l),equipment:equipment(ds),alerts:alerts(d),stats:stats(d),production:gauge(d),orders:orders(d),stock:stock(m),events:events(l),trend:mode==='history'?chart(d,l):processCharts(l,mode),condition:conditionSummary(l)}}
export async function renderMonitor(S,api){
 const data=await load(S,api);S.cache.controlroom=data;
 const canPrepareDefense=Number(S.factory)===1&&['admin','engineer'].includes(S.user.role);
 const videos=[['factory.mp4','01','工厂全景'],['liushuixian.mp4','02','生产流水线 A'],['liushuixiantwo.mp4','03','生产流水线 B']];
 return '<div class="monitor-board control-room"><header class="control-heading"><div class="control-brand"><img src="/logo.svg" alt=""><span>全景可视化数字工厂<small>SMART FACTORY</small></span></div><div class="control-title"><h1>生产监控大屏</h1><p>从车间感知到生产决策 · '+esc(S.meta.factories.find(f=>f.id===S.factory)?.name||'智慧工厂')+'</p></div><div class="control-clock"><strong id="monitor-clock">--:--:--</strong><small id="monitor-date"></small></div></header>'+
 '<div class="screen-toolbar"><span class="screen-source" id="monitor-source">采集记录</span><span id="monitor-sync">正在连接</span><div class="screen-actions">'+btn('返回工作台','go','data-page="overview"')+(canPrepareDefense?btn('准备答辩场景','demo-prepare-defense'):'')+(S.user.role!=='operator'?btn('处置记录','monitor-defense-record'):'')+btn('暂停数据刷新','monitor-poll')+btn('全屏大屏','monitor-fullscreen')+'</div></div>'+
 '<div id="monitor-condition"></div><div class="control-grid">'+block('sensors','设备传感器','<select id="monitor-device-select" aria-label="选择监测设备">'+data.ds.map(d=>'<option value="'+d.id+'" '+(d.id===data.l.device?.id?'selected':'')+'>'+esc(d.code)+' · '+esc(d.name)+'</option>').join('')+'</select>' )+block('equipment','设备运行状态','<span>最近采集</span>')+block('alerts','异常与处置','<span>点击追溯 →</span>')+block('stats','生产任务统计')+block('production','生产进度','<span>工单口径</span>')+
 '<section class="control-panel cp-cameras"><div class="cp-head"><h2>操作车间展示</h2>'+btn('暂停全部视频','monitor-videos')+'</div><div class="camera-stage">'+videos.map(([src,id,label],i)=>'<article class="monitor-camera '+(i===0?'camera-main':'')+'" data-camera="'+i+'"><video src="/api/media/'+src+'" autoplay muted loop playsinline preload="metadata" aria-label="'+label+'演示视频"></video><button data-action="camera-select" data-camera="'+i+'"><i></i>CAM '+id+' · '+label+'<em>录制演示</em></button><div class="camera-error" hidden>视频加载失败，请重新登录。</div></article>').join('')+'</div><div class="cp-head events-title"><h2>现场事件流水</h2><span>业务操作自动同步</span></div><div id="monitor-events" class="cp-body"></div></section>'+
block('trend','工况与产出趋势','<select id="monitor-trend-mode" aria-label="选择趋势指标"><option value="temperature">温度 · 15分钟</option><option value="pressure">压力 · 15分钟</option><option value="vibration">振动 · 15分钟</option><option value="quality">分组检测</option><option value="history">历史汇总</option></select>')+block('orders','生产订单','<span>交期与进度</span>')+block('stock','物料与补料','<span>按物料单位</span>')+'</div>'+
 '<footer class="control-footer"><span><i></i>录像演示 · 原始视频素材</span><span id="monitor-demo-state">演示产线未启动</span><div>'+(S.user.role!=='operator'?btn('启动演示产线','demo-start')+'<select id="monitor-scenario" aria-label="选择演示工况"><option value="short-stop">短暂停机</option><option value="changeover">换料</option><option value="fault">温控故障</option></select>'+btn('触发工况','demo-scenario')+btn('恢复温控','demo-recover'):'')+btn('退出登录','logout')+'</div></footer>'+
 '<dialog class="defense-dialog" aria-labelledby="defense-title"><div class="defense-dialog-head"><h2 id="defense-title">演示产线处置记录</h2><form method="dialog"><button type="submit" class="btn small">关闭</button></form></div><div class="defense-dialog-body" aria-busy="false"></div><p class="defense-error" role="status" hidden></p></dialog></div>';
}
export function mountMonitor(S,api){
 const board=document.querySelector('.control-room');if(!board)return()=>{};
 let disposed=false,paused=false,demoPending=false,selected=null,timer,clockTimer,scrollTimer,trendMode='temperature',latestData=S.cache.controlroom;const factory=S.factory;
  const recordDialog=board.querySelector('.defense-dialog');
  const recordBody=recordDialog.querySelector('.defense-dialog-body');
  const recordError=recordDialog.querySelector('.defense-error');
  let recordRequest=0;
  const canControlDefense=['admin','engineer'].includes(S.user.role);
  async function refreshRecord(){
   const runId=latestData.l.demo?.id;
   if(!recordDialog.open||!runId)return;
   const request=++recordRequest;
   try{
    const record=await api('/live/timeline?factory_id='+factory+'&run_id='+runId);
    if(disposed||!recordDialog.open||request!==recordRequest)return;
    morph(recordBody,renderDefenseRecord(record));
    recordError.hidden=true;
   }catch(error){
    if(disposed||!recordDialog.open||request!==recordRequest)return;
    recordError.textContent=error.message||'暂时无法读取处置记录';
    recordError.hidden=false;
   }finally{
    if(request===recordRequest)recordBody.setAttribute('aria-busy','false');
   }
  }
  recordDialog.addEventListener('close',()=>{recordRequest++});
 function update(data){
  if(disposed)return;latestData=data;
  for(const [id,html] of Object.entries(regions(data,trendMode)))morph(board.querySelector('#monitor-'+id),html);
  const selector=board.querySelector('#monitor-device-select'),options=data.ds.map(d=>'<option value="'+d.id+'">'+esc(d.code)+' · '+esc(d.name)+'</option>').join('');
  if(selector.dataset.options!==options){selector.innerHTML=options;selector.dataset.options=options}selector.value=String(data.l.device?.id||'');
  const run=data.l.demo,defense=run?.mode==='defense';
  const blocked=demoPending||(defense&&!canControlDefense);
  const prepare=board.querySelector('[data-action="demo-prepare-defense"]');
  if(prepare)prepare.disabled=demoPending;
  const recordButton=board.querySelector('[data-action="monitor-defense-record"]');
  if(recordButton)recordButton.disabled=!run?.id;
  board.querySelector('#monitor-source').textContent=defense?'答辩产线 · 模拟数据':run?.running?'演示产线运行中 · 模拟数据':'业务采集记录 · 演示环境';
  const demoState=board.querySelector('#monitor-demo-state');
  demoState.removeAttribute('role');
  demoState.textContent=run?(run.running?'演示运行 · ':'演示停止 · ')+(run.reason||'等待首条采集'):'演示产线未启动';
  const start=board.querySelector('[data-action="demo-start"],[data-action="demo-stop"]');if(start){start.disabled=demoPending||(defense&&run?.running&&!canControlDefense);start.dataset.action=run?.running?'demo-stop':'demo-start';start.textContent=run?.running?'停止演示':'启动演示产线'}
  const scenario=board.querySelector('[data-action=demo-scenario]'),scenarioSelect=board.querySelector('#monitor-scenario');
  if(scenario){
   scenarioSelect.hidden=defense;
   if(defense)scenarioSelect.value='fault';
   scenario.textContent=defense?'注入温控故障':'触发工况';
   scenario.disabled=blocked||!run?.running||(defense&&run.phase!=='producing');
  }
  const recovery=board.querySelector('[data-action=demo-recover],[data-action=demo-resume]');if(recovery){recovery.dataset.action=run?.phase==='awaiting_resume'?'demo-resume':'demo-recover';recovery.textContent=run?.phase==='awaiting_resume'?'确认复产':run?.phase==='cooling'?'降温观察中':'恢复温控';recovery.disabled=blocked||!run?.running||!['fault','awaiting_resume'].includes(run.phase)}
  board.querySelector('#monitor-sync').textContent='查询 '+time(data.l.server_time)+' · 采集 '+time(data.l.device?.updated_at);
  board.dataset.synced=String(Date.now());board.dataset.connected='true';
 }
 update(S.cache.controlroom);
 const refresh=async()=>{try{const data=await load({factory},api,selected);if(!disposed){update(data);await refreshRecord()}}catch(e){if(!disposed){board.querySelector('#monitor-sync').textContent='连接中断 · 保留最近数据';board.dataset.connected='false'}}};
 const tick=async()=>{if(disposed)return;if(!paused&&!document.hidden)await refresh();if(!disposed)timer=setTimeout(tick,3000)};
 const clock=()=>{const n=new Date();board.querySelector('#monitor-clock').textContent=n.toLocaleTimeString('zh-CN',{hour12:false});board.querySelector('#monitor-date').textContent=n.toLocaleDateString('zh-CN',{year:'numeric',month:'2-digit',day:'2-digit',weekday:'short'})};clock();clockTimer=setInterval(clock,1000);
 board.querySelectorAll('video').forEach(v=>{v.addEventListener('error',()=>v.parentElement.querySelector('.camera-error').hidden=false);v.play().catch(()=>{})});
 const select=async e=>{selected=Number(e.target.value);await refresh()};board.querySelector('#monitor-device-select').addEventListener('change',select);
 board.querySelector('#monitor-trend-mode').addEventListener('change',e=>{trendMode=e.target.value;update(latestData)});
 const click=async e=>{const button=e.target.closest('[data-action]'),action=button?.dataset.action;
  if(action==='monitor-poll'){paused=!paused;button.textContent=paused?'继续数据刷新':'暂停数据刷新';board.dataset.paused=String(paused);if(paused)board.querySelector('#monitor-sync').textContent='数据刷新已暂停，显示最近记录';else await refresh()}
  if(action==='monitor-defense-record'&&!recordDialog.open){
   recordBody.innerHTML='<p class="defense-empty">正在读取处置记录…</p>';
   recordBody.setAttribute('aria-busy','true');
   recordError.hidden=true;
   recordDialog.showModal();
   await refreshRecord();
  }
  if(action==='monitor-videos'){const videos=[...board.querySelectorAll('video')],play=videos.every(v=>v.paused);videos.forEach(v=>play?v.play().catch(()=>{}):v.pause());button.textContent=play?'暂停全部视频':'继续播放视频'}
  if(action==='camera-select')board.querySelectorAll('.monitor-camera').forEach(c=>c.classList.toggle('camera-main',c.dataset.camera===button.dataset.camera));
  if(action==='monitor-device'){selected=Number(button.dataset.id);await refresh()}
  if(action==='monitor-fullscreen'){try{if(document.fullscreenElement)await document.exitFullscreen();else await board.requestFullscreen()}catch{board.querySelector('#monitor-sync').textContent='可使用浏览器 F11 全屏'}}
  if(action?.startsWith('demo-')&&!demoPending){
   demoPending=true;
   const scenario=board.querySelector('#monitor-scenario');
   const requested=action==='demo-scenario'?scenario.value:action.slice(5);
   update(latestData);
   let failure='';
   try{
    await api('/live/demo',{factory_id:factory,action:requested});
    selected=null;
    await refresh();
   }catch(error){failure=error.message}
   finally{
    demoPending=false;
    if(!disposed){
     update(latestData);
     if(failure){
      const status=board.querySelector('#monitor-demo-state');
      status.textContent=failure;
      status.setAttribute('role','alert');
     }
    }
   }
  }
 };
 board.addEventListener('click',click);timer=setTimeout(tick,3000);
 scrollTimer=setInterval(()=>{if(paused||document.hidden||matchMedia('(max-width:760px),(prefers-reduced-motion:reduce)').matches)return;for(const id of ['equipment','alerts','orders','stock','events']){const el=board.querySelector('#monitor-'+id);if(el.matches(':hover')||el.contains(document.activeElement)||el.scrollHeight<=el.clientHeight+2)continue;el.scrollTo({top:el.scrollTop+el.clientHeight>=el.scrollHeight-3?0:el.scrollTop+el.clientHeight*.75,behavior:'smooth'})}},8000);
 return()=>{disposed=true;clearTimeout(timer);clearInterval(clockTimer);clearInterval(scrollTimer);board.removeEventListener('click',click);board.querySelectorAll('video').forEach(v=>{v.pause();v.removeAttribute('src');v.load()});if(document.fullscreenElement===board)document.exitFullscreen().catch(()=>{})};
}
