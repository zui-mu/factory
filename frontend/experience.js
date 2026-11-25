import {esc,fmt,pct,date,icon,badge,btn,chartLine,graph,notice,empty} from './ui.js';
export {renderMonitor,mountMonitor} from './controlroom.js';
export function federationVisual(d,S){
 const job=d.jobs[0],latest=job?.history?.at(-1),running=job&&['训练中','准备中'].includes(job.status),paused=job?.status==='已暂停'||d.pause_requested;
 const point=[[150,105],[650,105],[400,375]],phase=d.events?.[0]?.phase;
 const topology='<svg viewBox="0 0 800 470" role="img" aria-label="工厂节点向聚合中心上传参数并接收公共模型的动态拓扑">'+
 '<defs><radialGradient id="network-halo"><stop stop-color="#276398" stop-opacity=".5"/><stop offset="1" stop-color="#112139" stop-opacity="0"/></radialGradient></defs><ellipse cx="400" cy="230" rx="290" ry="200" fill="url(#network-halo)"/>'+
 d.nodes.map((n,i)=>{
  const [x,y]=point[i],active=running&&!paused&&n.online;const col=n.online?'#39d4b0':'#586982';
  return '<path d="M'+x+' '+y+' L400 230" fill="none" stroke="'+col+'" stroke-width="1.5" stroke-dasharray="5 7" opacity=".6"/>'+
   (active?'<circle r="4" fill="#4ee2bd"><animateMotion dur="1.8s" begin="-'+(i*.45).toFixed(2)+'s" repeatCount="indefinite" path="M'+x+' '+y+' L400 230"/></circle><circle r="3" fill="#61abff"><animateMotion dur="2.1s" repeatCount="indefinite" path="M400 230 L'+x+' '+y+'"/></circle>':'')+
   '<g class="network-node '+(n.online?'':'offline')+'"><rect x="'+(x-115)+'" y="'+(y-42)+'" width="230" height="88" rx="15"/><circle cx="'+(x-94)+'" cy="'+(y-20)+'" r="4" fill="'+col+'"/><text x="'+(x-79)+'" y="'+(y-15)+'" class="node-meta">'+(n.online?(paused?'等待继续':running?'参与训练':'节点在线'):'节点离线')+'</text><text x="'+x+'" y="'+(y+6)+'" text-anchor="middle" class="node-name">'+esc(n.name)+'</text><text x="'+x+'" y="'+(y+26)+'" text-anchor="middle" class="node-meta">本地训练样本 '+n.train_n+' 条</text></g>';
 }).join('')+'<circle cx="400" cy="230" r="62" fill="#153957" stroke="#4a98bd" stroke-width="1.5"/><circle cx="400" cy="230" r="72" fill="none" stroke="#2d6789" stroke-dasharray="4 8"/><text x="400" y="222" text-anchor="middle" class="cloud-title">云端聚合中心</text><text x="400" y="243" text-anchor="middle" class="node-meta">FedAvg · '+(job?job.round+'/'+job.total_rounds:'待开始')+'</text><text x="400" y="261" text-anchor="middle" class="node-meta">'+esc(paused?'已请求暂停':job?.status||'等待训练')+'</text></svg>';
 const controls=S.user.role==='admin'&&job&&['训练中','准备中','已暂停'].includes(job.status)?btn(paused?'继续训练':'暂停训练',paused?'resume-training':'pause-training'):'';
 return '<section class="federation-live"><div class="federation-live-head"><div><div class="eyebrow">FEDERATED LEARNING / LIVE</div><h2>动态联邦分析 · 联合建模可视化</h2><p>本地训练 → 参数上传 → 加权聚合 → 本厂验证</p></div>'+controls+'</div>'+
 '<div class="federation-live-stats">'+[['在线节点',d.nodes.filter(n=>n.online).length+' / '+d.nodes.length],['当前轮次',job?job.round+' / '+job.total_rounds:'—'],['验证准确率',pct(latest?.accuracy)],['验证损失',latest?latest.loss.toFixed(4):'—']].map(([k,v])=>'<div><span>'+k+'</span><strong>'+v+'</strong></div>').join('')+'</div>'+
 '<div class="federation-live-grid"><div class="network-canvas">'+topology+'<p>绿色：参数上传 · 蓝色：模型下发。动画表示协同过程，指标与日志来自实际计算。</p></div><div class="federation-events"><h3>训练日志</h3>'+(d.events?.length?d.events.slice(0,16).map(e=>'<div class="federation-event"><time>'+esc(e.created_at.slice(11))+'</time><strong>'+(e.factory_id?esc(d.nodes.find(n=>n.id===e.factory_id)?.name||'工厂节点'):'聚合中心')+'</strong><p>'+esc(e.detail)+'</p></div>').join(''):'<p class="monitor-empty">发起联合训练后显示各节点的实际事件。</p>')+'</div></div></section>';
}
function messageMarkup(m){
 const r=m.response;
 return '<article class="assistant-turn"><div class="question-bubble">'+esc(m.question)+'</div><div class="answer-bubble"><div class="answer-meta">'+icon('cause')+'<strong>因果分析助手</strong><span>'+esc(r.mode)+'</span></div>'+(r.warning?notice(r.warning,true):'')+'<p class="answer-text">'+esc(r.answer)+'</p><div class="answer-references">'+r.references.map(e=>'<details><summary>'+esc(e.label)+'</summary><p>'+esc(e.detail)+'</p></details>').join('')+'</div></div></article>';
}
export function assistantEvidence(message,S){
 if(!message)return '<div class="assistant-empty">'+icon('cause')+'<h3>从一个具体的问题开始</h3><p>选择异常、样本来源或预设场景，回答会展示依据和可执行的检查建议。</p></div>';
 const r=message.response;
 return (r.factors.length?r.factors.map(f=>'<details class="assistant-factor" '+(f.supported?'open':'')+'><summary><strong>'+esc(f.name)+'</strong><span>'+ (f.sufficient?(f.effect*100).toFixed(1)+' 个百分点':'样本不足')+'</span></summary><p>'+esc(f.action)+'</p><small>'+(f.sufficient?'95% 区间 '+(f.ci[0]*100).toFixed(1)+' 至 '+(f.ci[1]*100).toFixed(1)+' 个百分点':'请补充可比较的分层样本')+'</small></details>').join(''):'<p class="instruction">该场景暂不套用当前质量模型的数值结论。</p>')+
 '<h3 class="mt24 mb16">检查与优化建议</h3>'+r.recommendations.map(a=>'<div class="assistant-recommendation">'+icon('check')+'<div><strong>'+esc(a.title)+'</strong><p>'+esc(a.detail)+'</p></div></div>').join('')+
 (r.analysis&&S.user.role!=='operator'?'<div class="mt16">'+btn('将建议生成处置工单','assistant-task','data-id="'+message.id+'"','primary')+'</div>':'')+'<p class="muted tiny mt16">'+esc(r.limitations)+'</p>';
}
export async function renderAssistant(S,api){
 const query='?factory_id='+S.factory;
 const [d,samples,alerts]=await Promise.all([api('/assistant'+query),api('/samples'+query),api('/anomalies'+query)]);
 S.cache.assistant=d;
 const selected=alerts.find(a=>a.id===S.anomaly)||alerts.find(a=>a.order_id&&a.status!=='已关闭');
 return '<div class="page-head"><div><div class="eyebrow">CAUSAL INTELLIGENCE / ASSISTANT</div><h1>AI 因果问答与建议</h1><p>描述质量问题，沿着证据找到下一步行动。</p></div><span class="chip">'+esc(d.provider.mode)+'</span></div>'+
 '<div class="assistant-context card"><label>关联异常<select id="assistant-anomaly"><option value="">不关联具体异常</option>'+alerts.filter(a=>a.status!=='已关闭').map(a=>'<option value="'+a.id+'" '+(a.id===selected?.id?'selected':'')+'>'+esc(a.title)+'</option>').join('')+'</select></label><label>分析样本来源<select id="assistant-source">'+samples.sources.map(s=>'<option value="'+esc(s.source)+'">'+esc(s.source)+' · '+s.n+' 条</option>').join('')+'</select></label></div>'+
 '<div class="assistant-layout"><section class="card assistant-chat-card"><div class="card-head"><div><h2>因果分析助手</h2><p>支持继续追问，记录按账号与工厂分别保存</p></div>'+icon('cause')+'</div><div class="assistant-chat" id="assistant-chat" role="log" aria-label="因果问答记录">'+
 (d.messages.length?d.messages.map(messageMarkup).join(''):'<div class="assistant-welcome"><div class="assistant-orb">'+icon('cause')+'</div><h2>你好，今天想分析什么？</h2><p>我会结合本厂样本、异常记录与明确的因果假设，给出排查依据和现场建议。</p></div>')+'</div>'+
 '<div class="assistant-presets">'+d.presets.slice(0,4).map(([key,label,q])=>'<button type="button" data-action="assistant-preset" data-scenario="'+key+'" data-question="'+esc(q)+'">'+esc(label)+'</button>').join('')+'</div>'+
 '<form id="assistant-form"><label class="sr-only" for="assistant-question">输入质量问题</label><textarea id="assistant-question" name="question" maxlength="1500" required placeholder="例如：这次尺寸偏差升高，应该先排查温度还是原料？"></textarea><div class="assistant-composer-foot"><span id="assistant-mode">'+(d.provider.configured?'<label><input type="checkbox" id="assistant-model">使用 '+esc(d.provider.model)+'（发送所选证据摘要与当前对话）</label>':'本地证据助手 · 无须外部模型密钥')+'</span><button class="btn primary" type="submit">'+icon('arrow')+'发送问题</button></div><div class="form-error" hidden></div></form></section>'+
 '<aside class="stack"><div class="card"><div class="card-head"><h2>因果图与分析假设</h2><span class="chip">固定工艺假设</span></div>'+graph()+'<p class="muted tiny">当前图描述温度、压力、磨损与质量的假设关系；焊接、组装等场景需要对应数据和工艺审查。</p></div><div class="card"><h2 class="mb16">候选问题与优化建议</h2><div id="assistant-evidence">'+assistantEvidence(d.messages.at(-1),S)+'</div></div></aside></div>';
}
export function mountAssistant(S,api,toast){
 let disposed=false;const form=document.getElementById('assistant-form');if(!form)return ()=>{};
 const chat=document.getElementById('assistant-chat');chat.scrollTop=chat.scrollHeight;
 const factory=S.factory;
 const submit=async e=>{
  e.preventDefault();const question=form.querySelector('textarea').value.trim();if(!question)return;
  const button=form.querySelector('button[type=submit]'),error=form.querySelector('.form-error');button.disabled=true;button.textContent='正在分析…';error.hidden=true;chat.insertAdjacentHTML('beforeend','<div class="assistant-pending" role="status"><span class="spinner"></span>正在核对所选样本与异常证据…</div>');chat.scrollTop=chat.scrollHeight;
  const body={factory_id:factory,question,source:document.getElementById('assistant-source').value,anomaly_id:document.getElementById('assistant-anomaly').value||null,
   scenario:form.dataset.scenario||'quality',use_model:!!document.getElementById('assistant-model')?.checked};
  try{
   const m=await api('/assistant/ask',body);if(disposed)return;
   S.cache.assistant.messages.push(m);chat.querySelector('.assistant-welcome')?.remove();chat.insertAdjacentHTML('beforeend',messageMarkup(m));chat.scrollTop=chat.scrollHeight;
   document.getElementById('assistant-evidence').innerHTML=assistantEvidence(m,S);form.querySelector('textarea').value='';form.dataset.scenario='quality';
  }catch(err){if(!disposed){error.textContent=err.message;error.hidden=false}}
  finally{if(!disposed){chat.querySelector('.assistant-pending')?.remove();button.disabled=false;button.innerHTML=icon('arrow')+'发送问题'}}
 };
 form.addEventListener('submit',submit);
 return ()=>{disposed=true;form.removeEventListener('submit',submit)};
}
