import {renderWorkforce} from './workforce.js';
import {overviewConditions} from './conditions.js';
import {liveBar} from './live-ui.js';
import {esc,fmt,pct,date,icon,badge,btn,empty,notice,table,scene,chartLine,graph} from './ui.js';
import {renderMonitor,renderAssistant,federationVisual} from './experience.js';
export const navItems=[
 ['overview','运营总览','home','WORKSPACE'],['monitor','生产监控大屏','device'],['workshop','车间感知','cube'],['orders','生产管理','order'],['quality','质量管理','quality'],
 ['analysis','因果诊断','cause','INTELLIGENCE'],['assistant','AI 因果问答','cause'],['tasks','协同处置','tasks'],['federation','动态联邦分析','network'],
 ['workforce','人员与排班','user','MANAGEMENT'],['materials','仓储物料','box'],['data','数据中心','data'],['settings','系统与审计','settings']
];
export function pageHead(title,description,actions=''){return '<div class="page-head"><div><div class="eyebrow">ZHIYIN YUNLIAN / WORKSPACE</div><h1>'+title+'</h1><p>'+description+'</p></div><div class="row gap8 wrap">'+actions+'</div></div>'}
const cardHead=(title,sub='',right='')=>'<div class="card-head"><div><h2>'+title+'</h2>'+(sub?'<p>'+sub+'</p>':'')+'</div>'+right+'</div>';
const exportBtn=kind=>btn(icon('download')+'导出记录','export','data-kind="'+kind+'"');
const toolbar=(placeholder,extra='')=>'<div class="toolbar"><div class="search">'+icon('search')+'<input id="search" aria-label="搜索记录" placeholder="'+placeholder+'"></div>'+extra+'</div>';
const progress=(done,total)=>'<div class="progress"><span style="width:'+Math.min(100,done/Math.max(total,1)*100)+'%"></span></div>';
const renderAlerts=(alerts)=>alerts.length?alerts.map(a=>'<div class="alert-item"><div class="alert-symbol '+(a.severity==='高'?'high':'')+'">'+icon('alert')+'</div><div class="alert-content"><h3>'+esc(a.title)+'</h3><p>'+esc(a.description.slice(0,45))+'</p><div class="row between">'+badge(a.status)+btn('查看分析 '+icon('chevron'),'open-analysis','data-id="'+a.id+'"','ghost small')+'</div></div></div>').join(''):empty('当前没有待处理异常');
async function renderPageContent(page,S,api){
 if(page==='workforce')return renderWorkforce(S,api);
 if(page==='monitor')return renderMonitor(S,api);
 if(page==='assistant')return renderAssistant(S,api);
 const query='?factory_id='+S.factory;
 if(page==='overview'){
  const [d,live]=await Promise.all([api('/overview'+query),api('/live'+query)]);S.cache.overview=d;let k=d.kpi;
  const stat=(label,value,unit,foot,ico)=>'<div class="card stat-card"><div class="stat-label">'+label+icon(ico)+'</div><div class="stat-number">'+value+'<small>'+unit+'</small></div><div class="stat-foot"><span class="dot"></span>'+foot+'</div></div>';
  return pageHead('生产运营总览','连接车间现场，让每一次生产决策有据可依。',btn(icon('device')+'监控大屏','go','data-page="monitor"')+btn(icon('refresh')+'刷新数据','refresh')+btn(icon('plus')+'新建工单','new-order','','primary'))+
   '<div class="stat-grid">'+stat('累计完成产量',fmt(k.production),'件','计划总量 '+fmt(k.planned)+' 件','order')+stat('今日质检合格率',pct(k.quality_rate),'','已抽检 '+fmt(k.sample_count)+' 件','quality')+stat('有效采集 · 运行设备',k.running+' <small>/ '+k.device_total+'</small>','台','通信未知 '+k.communication_unknown+' 台 · 历史档案 '+k.archive_devices+' 台','device')+stat('待处理异常',k.active_anomalies,'项','分析与处置全程可追溯','alert')+'</div>'+
   overviewConditions(live)+'<div class="dashboard-grid"><div class="stack"><div class="card hero-card"><div class="eyebrow">FROM INSIGHT TO ACTION</div><h2>看见生产全貌<br>找到问题背后的原因</h2><p>汇聚设备、工艺与质量数据，将分析转化为可执行的现场行动。</p>'+btn('进入因果诊断 '+icon('arrow'),'go','data-page="analysis"','dark')+'<div class="hero-art">'+scene([])+'</div></div>'+
   '<div class="card">'+cardHead('质量变化趋势','近 14 天抽检记录 · 按检测日期汇总','<span class="legend"><span><i></i>合格率</span></span>')+chartLine(d.trend.map(x=>({...x,rate:1-x.defects/x.samples})),['rate'],['#548765'],true)+'</div>'+
   '<div class="card">'+cardHead('生产工单进度','掌握交付节奏与生产状态',btn('全部工单 '+icon('chevron'),'go','data-page="orders"','ghost small'))+
   table(['工单 / 产品','生产进度','交期','状态'],d.orders.slice(0,3).map(o=>'<tr><td><strong>'+esc(o.product)+'</strong><small>'+esc(o.code)+'</small></td><td>'+fmt(o.completed)+' <span class="muted">/ '+fmt(o.quantity)+'</span>'+progress(o.completed,o.quantity)+'</td><td>'+esc(o.due_date)+'</td><td>'+badge(o.status)+'</td></tr>').join(''))+'</div></div>'+
   '<div class="stack"><div class="card">'+cardHead('车间实时映射','设备状态与现场采集记录联动','<span class="chip"><span class="dot"></span>最近采集</span>')+'<div class="scene-wrap">'+scene(d.devices)+'</div><div class="row between mt16"><span class="legend"><span><i></i>运行</span><span><i style="background:#d5ac73"></i>预警</span><span><i style="background:#b9c5ba"></i>待机 / 未知</span></span>'+btn('进入车间 '+icon('chevron'),'go','data-page="workshop"','ghost small')+'</div></div>'+
   '<div class="card">'+cardHead('需要关注','优先处理影响质量与交付的事件','<span class="chip">'+k.active_anomalies+' 项</span>')+renderAlerts(d.alerts.slice(0,3))+'</div>'+
   '<div class="card">'+cardHead('闭环处置进展','诊断 → 派单 → 执行 → 复检')+'<div class="row between">'+['待接单','处理中','待复检','已关闭'].map(s=>'<div><strong style="font-size:22px;font-weight:500">'+(d.tasks.find(t=>t.status===s)?.n||0)+'</strong><div class="muted tiny">'+s+'</div></div>').join('')+'</div></div></div></div>';
 }
 if(page==='workshop'){
  const devices=(await api('/devices'+query)).sort((a,b)=>Number(a.archived)-Number(b.archived)||Number(b.fresh)-Number(a.fresh)||a.id-b.id);S.cache.devices=devices;
  return pageHead('车间感知','从设备状态到运行参数，连接现场的每一个变化。',btn(icon('refresh')+'刷新采集状态','refresh'))+
   '<div class="grid2 mb16"><div class="card">'+cardHead('车间空间视图','轻量化设备示意 · 点击设备查看参数')+'<div class="scene-wrap">'+scene(devices,true)+'</div></div><div class="card">'+cardHead('现场采集与状态监测','支持手动录入采集值，通过接口对接采集程序')+
   '<div class="metric-strip"><div><strong>'+devices.length+'</strong><small>当前工厂设备</small></div><div><strong class="green">'+devices.filter(d=>d.fresh&&d.status==='运行').length+'</strong><small>运行中</small></div><div><strong class="orange">'+devices.filter(d=>d.fresh&&d.status==='预警').length+'</strong><small>参数预警</small></div></div>'+
   notice('设备颜色按有效采集显示，过期为通信未知。演示线15秒、普通采集120秒无更新时不计入在线运行。温度超过 90℃、压力超过 8MPa 或振动超过 3mm/s 时触发预警。这些阈值用于演示场景。')+'<div class="divider"></div><p class="instruction">选择设备可查看历史曲线、记录新的温度和压力等采集值。参数越限会进入异常工作台，支持继续分析与处置。</p></div></div>'+
   '<div class="grid3 device-list">'+devices.map(d=>'<div class="card device-card"><div class="row between"><span class="device-code">'+esc(d.code)+'</span>'+badge(d.display_status||d.status)+'</div><div class="device-glyph">'+scene([d]).replace('viewBox="0 0 620 330"','viewBox="180 60 100 130"')+'</div><h3>'+esc(d.name)+'</h3><small class="muted">'+esc(d.line)+'</small><div class="live-received">'+esc(d.source)+' · '+date(d.updated_at)+' 采集 · '+(d.fresh?'有效':'最后记录')+'</div><div class="device-params"><div><strong>'+(d.temperature??'未采集')+'<small>温度 / ℃</small></strong></div><div><strong>'+(d.pressure??'未采集')+'<small>压力 / MPa</small></strong></div><div><strong>'+(d.vibration??'未采集')+'<small>振动 / mm/s</small></strong></div></div>'+btn('设备详情 '+icon('arrow'),'device-detail','data-id="'+d.id+'"')+'</div>').join('')+'</div>';
 }
 if(page==='orders'){
  const orders=(await api('/orders'+query)).sort((a,b)=>Number(a.archived)-Number(b.archived)||b.id-a.id);S.cache.orders=orders;
  return pageHead('生产管理','从计划排产到现场报工，让生产进度清晰可见。',exportBtn('orders')+btn(icon('plus')+'新建工单','new-order','','primary'))+
   '<div class="card">'+toolbar('搜索工单、产品或批次','<span class="muted tiny">'+orders.length+' 条生产工单</span>')+
   table(['工单 / 产品','批次','数量 / 完成','优先级','交期','状态','操作'],orders.map(o=>'<tr data-search="'+esc([o.code,o.product,o.batch].join(' '))+'"><td><strong>'+esc(o.product)+'</strong><small>'+esc(o.code)+'</small><small>'+esc(o.source)+'</small></td><td class="mono">'+esc(o.batch)+'</td><td>'+fmt(o.completed)+' / '+fmt(o.quantity)+progress(o.completed,o.quantity)+'</td><td>'+badge(o.priority)+'</td><td>'+esc(o.due_date)+'</td><td>'+badge(o.status)+'</td><td><div class="table-actions">'+
   (o.status==='待排产'?btn('开始生产','order-state','data-id="'+o.id+'" data-op="start"','small'):o.status==='生产中'?(o.simulated?'<span class="muted tiny">采集器自动报工</span>':btn('报工','report-production','data-id="'+o.id+'"','small primary'))+btn('暂停','order-state','data-id="'+o.id+'" data-op="pause"','small'):o.status==='已暂停'?btn('恢复','order-state','data-id="'+o.id+'" data-op="resume"','small'):'<span class="muted tiny">已归档</span>')+'</div></td></tr>').join(''))+'</div>';
 }
 if(page==='quality'){
  const [records,alerts]=await Promise.all([api('/quality'+query),api('/anomalies'+query)]);S.cache.quality=records;
  const n=records.reduce((a,r)=>a+r.sample_size,0),bad=records.reduce((a,r)=>a+r.defects,0);
  return pageHead('质量管理','批次检测、异常预警与质量追溯，在一个工作台完成。',exportBtn('quality')+btn(icon('plus')+'录入质检','new-quality','','primary'))+
   '<div class="grid3 mb16"><div class="card"><p class="muted">累计抽检数量</p><div class="stat-number">'+fmt(n)+'<small>件</small></div></div><div class="card"><p class="muted">累计质检合格率</p><div class="stat-number green">'+pct(1-bad/Math.max(n,1))+'</div></div><div class="card"><p class="muted">待跟进异常</p><div class="stat-number orange">'+alerts.filter(a=>a.status!=='已关闭').length+'<small>项</small></div></div></div>'+
   '<div class="card">'+toolbar('搜索批次、缺陷类型或检验员')+table(['批次 / 工单','抽检数量','不合格数量','合格率','缺陷类型','检验员','检验时间'],records.map(r=>'<tr data-search="'+esc(r.batch+' '+r.defect_type+' '+r.inspector)+'"><td class="mono">'+esc(r.batch)+'<small>'+(r.order_id?'工单 #'+r.order_id:'未关联工单')+' · '+esc(r.source)+'</small></td><td>'+r.sample_size+'</td><td>'+r.defects+'</td><td><span class="'+(r.defects/r.sample_size>.05?'red':'green')+'">'+pct(1-r.defects/r.sample_size)+'</span></td><td>'+esc(r.defect_type)+'</td><td>'+esc(r.inspector)+'</td><td class="muted">'+date(r.created_at)+'</td></tr>').join(''))+'</div>';
 }
 if(page==='analysis'){
  const [alerts,analyses,samples]=await Promise.all([api('/anomalies'+query),api('/analyses'+query),api('/samples'+query)]);S.cache.anomalies=alerts;S.cache.analyses=analyses;
  if(!alerts.some(a=>a.id===S.anomaly))S.anomaly=alerts.find(a=>a.status!=='已关闭'&&a.order_id)?.id||alerts[0]?.id;
  const active=alerts.find(a=>a.id===S.anomaly);const record=active?.order_id?analyses.find(a=>a.anomaly_id===S.anomaly):null;S.cache.analysis=record;
  return pageHead('因果诊断','从异常现象走向证据，理解工艺因素如何影响质量。',btn(icon('cause')+'询问 AI 建议','go','data-page="assistant"')+btn(icon('history')+'刷新分析记录','refresh'))+
   '<div class="analysis-grid"><div><div class="card-head"><h2>选择异常事件</h2><span class="chip">'+alerts.length+' 项</span></div><div class="analysis-choices">'+alerts.map(a=>'<button class="anomaly-choice '+(a.id===S.anomaly?'selected':'')+'" data-action="select-anomaly" data-id="'+a.id+'"><div class="row between">'+badge(a.severity)+badge(a.status)+'</div><h3>'+esc(a.title)+'</h3><p>'+date(a.created_at)+'</p></button>').join('')+'</div></div><div class="stack">'+
   '<div class="card"><label class="field"><span>分析样本来源</span><select id="analysis-source">'+samples.sources.map(x=>'<option value="'+esc(x.source)+'">'+esc(x.source)+' · '+x.n+' 条</option>').join('')+'</select></label><p class="muted tiny mt16">每次分析只使用所选来源，演示样本与导入样本分别计算。</p></div>'+
   (active?'<div class="card">'+cardHead(esc(active.title),esc(active.description),active.order_id?btn(icon('cause')+'运行分析','run-analysis','data-id="'+active.id+'"','primary'):btn(icon('tasks')+'安排现场检查','inspection-task','data-id="'+active.id+'"','primary'))+'<div class="row wrap"><span class="chip">异常 #'+active.id+'</span><span class="muted tiny">数据来源：'+esc(active.source)+'</span></div></div>':empty('暂无异常'))+
   (record?analysisResult(record):'<div class="card">'+graph()+'<div class="mt24">'+notice('选择异常并运行分析，系统将使用本厂工艺样本，计算调整原料等级和产品规格后的风险差。样本不足时会明确提示。')+'</div></div>')+'</div></div>';
 }
 if(page==='tasks'){
  const tasks=await api('/tasks'+query);S.cache.tasks=tasks;
  return pageHead('协同处置','把分析转化为行动，让每一次现场处理都有回响。',exportBtn('tasks')+btn(icon('plus')+'从异常创建','go','data-page="analysis"','primary'))+
   '<div class="notice mb16">'+icon('phone')+'<p>现场人员可使用手机登录接单、上传照片与提交处置记录；质量人员负责复检，合格后关闭异常。</p></div>'+
   '<div class="task-board">'+['待接单','处理中','待复检','已关闭'].map(status=>'<div class="task-col"><div class="task-col-head">'+status+'<span>'+tasks.filter(t=>t.status===status).length+'</span></div>'+tasks.filter(t=>t.status===status).map(t=>'<button class="task-tile" data-action="task-detail" data-id="'+t.id+'"><div class="row between"><small class="muted">TASK-'+String(t.id).padStart(4,'0')+'</small>'+badge(t.priority)+'</div><h3>'+esc(t.title)+'</h3><p>'+esc(t.action.slice(0,55))+'</p><footer><span class="row gap8"><span class="avatar">'+esc(t.assignee_name[0])+'</span>'+esc(t.assignee_name)+'</span><span>'+date(t.updated_at).slice(5,10)+'</span></footer></button>').join('')+(tasks.some(t=>t.status===status)?'':'<div class="empty tiny">暂无工单</div>')+'</div>').join('')+'</div>';
 }
 if(page==='federation'){
  const d=await api('/federation');S.cache.federation=d;const job=d.jobs[0];let running=job&&['训练中','准备中','已暂停'].includes(job.status);
  return pageHead('跨厂协同','数据留在各厂，模型共同学习；每一次提升都经本厂验证。',btn(icon('refresh')+'刷新结果','refresh')+(S.user.role!=='operator'?btn(icon('quality')+'本厂风险试算','risk-predict'):'')+(S.user.role==='admin'?btn(icon(running?'close':'play')+(running?'取消训练':'发起联合训练'),running?'cancel-training':'start-training','','primary'):'') )+
   federationVisual(d,S)+'<div class="grid3 mb16">'+d.nodes.map(n=>'<div class="card node-card"><span class="node-state">'+badge(n.online?'在线':'离线')+'</span><div class="icon-container">'+icon('network')+'</div><h3>'+esc(n.name)+'</h3><p>独立训练节点 · '+esc(n.city)+'</p><div class="node-stats"><div><strong>'+n.train_n+'</strong><small>训练样本</small></div><div><strong>'+n.validation_n+'</strong><small>验证样本</small></div><div><strong>'+n.test_n+'</strong><small>测试样本</small></div></div>'+(S.user.role==='admin'?'<div class="mt16">'+btn(n.online?'模拟节点离线':'恢复节点','toggle-node','data-id="'+n.id+'" data-enabled="'+(!n.online)+'"','small')+'</div>':'')+'</div>').join('')+'</div>'+
   '<div class="stack">'+(job?'<div class="card">'+cardHead('训练任务 '+esc(job.id),date(job.created_at),badge(job.status))+'<div class="run-status"><span class="muted">轮次 <strong class="green">'+job.round+' / '+job.total_rounds+'</strong></span>'+progress(job.round,job.total_rounds)+'<span class="chip">FedAvg · 逻辑回归</span></div>'+(job.error?'<div class="mt16">'+notice(job.error,true)+'</div>':'')+
   (job.history.length?'<div class="grid2 mt24"><div><h3 class="muted">验证集损失</h3>'+chartLine(job.history,['loss'])+'</div><div><h3 class="muted">验证集 F1</h3>'+chartLine(job.history,['f1'],['#ba9764'],true)+'</div></div>':'<div class="loading">'+(running?'<span class="spinner"></span> 正在本地训练并计算基线':'暂无轮次记录')+'</div>')+'</div>':'<div class="card">'+cardHead('准备开始第一次联合训练','三个节点分别训练，再按各厂样本量聚合模型')+notice('训练指标来自实际计算。系统不会预设联合训练必然优于单厂训练；模型必须通过本厂验证后才会被启用。')+'</div>')+
   (job?.result?.factories?.length?'<div class="card">'+cardHead('各厂效果与模型启用情况','独立测试集结果 · 启用判断仅使用验证集')+table(['工厂','单厂 F1','协同 F1','异常召回率','误报率','模型状态'],job.result.factories.map(f=>'<tr><td>'+esc(f.name)+'</td><td>'+pct(f.local.f1)+'</td><td class="green">'+pct(f.federated.f1)+'</td><td>'+pct(f.federated.recall)+'</td><td>'+pct(f.federated.false_positive_rate)+'</td><td>'+badge(f.deployment.accepted?'已启用':'保留本厂模型')+'<small>'+esc(f.deployment.active_version)+'</small></td></tr>').join(''))+'<div class="mt16">'+notice(job.result.method)+'</div></div>':'')+
   '<div class="card">'+cardHead('协同边界与运行记录')+'<div class="grid2"><div><p class="instruction">'+esc(d.description)+'。训练、验证和测试样本分别生成，平台协调器仅接收模型权重、样本数量和汇总指标。</p><p class="instruction mt16">'+esc(d.privacy)+'</p></div><div>'+d.jobs.slice(0,5).map(j=>'<div class="history-entry row between"><span><strong class="tiny">'+j.id+'</strong><small class="muted" style="display:block">'+date(j.created_at)+' · '+j.round+' 轮</small></span>'+badge(j.status)+'</div>').join('')+'</div></div></div></div>';
 }
 if(page==='materials'){
  const [materials,moves]=await Promise.all([api('/materials'+query),api('/stock-moves'+query)]);materials.sort((a,b)=>Number(a.archived)-Number(b.archived)||Number(b.fresh)-Number(a.fresh)||a.id-b.id);S.cache.materials=materials;
  return pageHead('仓储物料','掌握库存水位，追踪每一笔物料流转。',exportBtn('materials'))+
   '<div class="stack"><div class="card">'+toolbar('搜索物料、编码或库位')+table(['物料 / 编码','规格','库位','当前库存','安全库存','状态','操作'],materials.map(m=>'<tr data-search="'+esc(m.name+' '+m.code+' '+m.location)+'"><td><strong>'+esc(m.name)+'</strong><small>'+esc(m.code)+'</small><small>'+esc(m.source)+'</small></td><td>'+esc(m.spec)+'</td><td>'+esc(m.location)+'</td><td><strong>'+fmt(m.stock)+'</strong> '+esc(m.unit)+'</td><td>'+fmt(m.min_stock)+' '+esc(m.unit)+'</td><td>'+badge(m.archived?'历史余额':m.stock<m.min_stock?'库存偏低':'库存充足')+'</td><td>'+(m.archived?'<span class="muted tiny">存档只读</span>':btn('出入库','stock-move','data-id="'+m.id+'"','small'))+'</td></tr>').join(''))+'</div><div class="card">'+cardHead('出入库流水','每笔操作保存处理人、数量和业务说明')+(moves.length?table(['时间','物料','方向','数量','操作人','说明'],moves.map(m=>'<tr><td>'+date(m.created_at)+'</td><td>'+esc(m.name)+'</td><td>'+badge(m.direction)+'</td><td>'+m.quantity+' '+esc(m.unit)+'</td><td>'+esc(m.user_name)+'</td><td>'+esc(m.note)+'</td></tr>').join('')):empty('尚无出入库操作'))+'</div></div>';
 }
 if(page==='data'){
  const [d,sources]=await Promise.all([api('/samples'+query),api('/sources'+query)]);S.cache.samples=d;
  return pageHead('数据中心','明确来源、统一字段，为可解释分析建立数据基础。',btn(icon('download')+'下载 CSV 模板','download-template')+btn(icon('plus')+'导入工艺样本','import-samples','','primary'))+
   '<div class="grid2 mb16"><div class="card">'+cardHead('工艺分析样本','当前工厂 · 因果分析数据集')+'<div class="stat-number">'+fmt(d.count)+'<small>条</small></div>'+d.sources.map(s=>'<div class="row between mt16"><span class="muted">'+esc(s.source)+'</span><strong>'+fmt(s.n)+'</strong></div>').join('')+'</div><div class="card">'+cardHead('字段与来源约定')+'<p class="instruction">每行代表一个独立检测样本，字段均为 0 / 1：温度偏高、压力偏高、设备磨损、原料等级、产品规格、质检不合格。</p><div class="mt16">'+notice('导入时需注明来源。导入样本追加到本厂分析数据集；跨厂训练使用独立节点的模拟样本，不会自动上传这些记录。')+'</div></div></div>'+
   '<div class="card mb16">'+cardHead('项目业务数据来源','保留源记录编号和文件 SHA-256；设备缺失读数不予补造，历史工单与库存用于追溯')+table(['来源','业务类型','记录数','导入时间'],sources.map(x=>'<tr><td>'+esc(x.label)+'</td><td>'+({devices:'设备档案',orders:'历史工单',quality:'质检存档',materials:'库存存档'}[x.entity]||esc(x.entity))+'</td><td>'+x.n+'</td><td>'+date(x.imported_at)+'</td></tr>').join(''))+'</div>'+
   '<div class="card">'+cardHead('最近样本预览','展示最近 15 条记录')+table(['编号','温度偏高','压力偏高','设备磨损','原料等级','产品规格','不合格','来源'],d.preview.map(r=>'<tr><td>'+r.id+'</td>'+['temp','pressure','wear','material','product','defect'].map(k=>'<td>'+r[k]+'</td>').join('')+'<td>'+esc(r.source)+'</td></tr>').join(''))+'</div>';
 }
 if(page==='settings'){
  const logs=S.user.role==='operator'?[]:await api('/audit'+query);
  return pageHead('系统与审计','管理使用边界，保存每一次关键操作。',btn(icon('settings')+'修改密码','change-password'))+
   '<div class="grid2 mb16"><div class="card">'+cardHead('质因云联','从车间感知到生产决策的智慧工厂平台')+'<dl><div class="kv"><dt>应用版本</dt><dd>1.4.0 · 本地可运行版</dd></div><div class="kv"><dt>当前用户</dt><dd>'+esc(S.user.name)+' / '+esc(S.user.username)+'</dd></div><div class="kv"><dt>数据存储</dt><dd>本地持久化，重启后保留业务记录</dd></div><div class="kv"><dt>平台能力</dt><dd>生产 · 设备 · 质量 · 诊断 · 处置 · 仓储 · 协同</dd></div></dl></div><div class="card">'+cardHead('数据与模型说明')+'<p class="instruction">演示业务与算法样本为模拟数据，接入的项目业务存档单独标明来源。因果分析使用明确假设下的分层效应估计，联邦学习运行真实的本地训练与参数聚合。应用不自动控制真实设备。</p><div class="mt16">'+notice('演示账号具有不同角色权限。正式接入真实数据前，请修改默认密码，并按实际部署环境配置网络保护与数据授权。')+'</div></div></div>'+
   '<div class="card">'+cardHead('操作审计','记录登录、数据变更、分析与协同任务',S.user.role!=='operator'?exportBtn('audit'):'')+(logs.length?table(['时间','用户','操作','对象','详情'],logs.map(l=>'<tr><td>'+date(l.created_at)+'</td><td>'+esc(l.user_name)+'</td><td>'+esc(l.action)+'</td><td>'+esc(l.entity)+'</td><td style="white-space:normal;max-width:400px">'+esc(l.detail)+'</td></tr>').join('')):empty('当前角色无审计访问权限或尚无记录'))+'</div>';
 }
 return empty('页面不存在');
}
function analysisResult(record){
 const r=record.result;
 return '<div class="card">'+cardHead('候选原因与证据','分析 #'+record.id+' · '+fmt(r.sample_count)+' 条样本 · '+date(r.created_at))+
 '<div class="grid3">'+r.factors.map(f=>'<div class="factor"><div class="row between"><h3>'+esc(f.name)+'</h3>'+badge(f.supported?'证据支持':f.sufficient?'尚不明确':'样本不足')+'</div><div class="effect">'+(f.sufficient?(f.effect>=0?'+':'')+(f.effect*100).toFixed(1):'—')+' <small>个百分点</small></div><p>偏高 / 磨损相对正常的风险差</p><p>95% 区间：'+(f.sufficient?(f.ci[0]*100).toFixed(1)+' 至 '+(f.ci[1]*100).toFixed(1):'样本不足，暂不展示')+' 个百分点</p><p>分层覆盖 '+pct(f.coverage)+' · 暴露 '+f.exposed_n+' / 正常 '+f.normal_n+'</p>'+btn('查看处置方案 '+icon('arrow'),'compare-plan','data-key="'+f.key+'"','small')+'</div>').join('')+'</div>'+
 '<div class="mt24">'+graph()+'</div><div class="mt16">'+notice(r.limitations)+'</div></div>'+
 '<div class="card">'+cardHead('分析依据与适用条件',r.method)+'<div class="grid2"><div><h3>分析假设</h3><ul class="evidence-list">'+r.assumptions.map(s=>'<li>'+esc(s)+'</li>').join('')+'</ul></div><div><h3>数据来源</h3><ul class="evidence-list">'+r.sources.map(s=>'<li>'+esc(s)+'</li>').join('')+'</ul><p class="muted tiny">当前分析提供本厂总体工艺因素的候选证据，现场人员仍需核对该批次实际暴露条件。</p></div></div></div>';
}

export async function renderPage(page,S,api){const html=await renderPageContent(page,S,api);return ['monitor','assistant'].includes(page)?html:liveBar()+html}
