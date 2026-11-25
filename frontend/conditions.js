import {esc,pct,fmt} from './ui.js';
export function conditionSummary(l){
 const run=l.demo;
 if(!run)return '<div class="condition-strip idle"><strong>等待连续采集</strong><span>点击“启动演示产线”后，观察预热、生产、短停与换料。现有设备显示最后一次采集记录。</span></div>';
 return '<div class="condition-strip" data-phase="'+run.phase+'"><div><small>当前工况 · 模拟</small><strong>'+esc(run.phase_label)+'</strong></div><div class="condition-explain"><span>'+esc(run.reason)+'</span><small>'+esc(run.profile.name)+' · 模具温控回路 · 当前工况 '+run.phase_seconds+'s</small></div><div><small>当前批次 B'+String(run.batch).padStart(2,'0')+'</small><strong>'+pct(run.batch_rate)+'</strong></div><div><small>已检测 / 待汇总</small><strong>'+run.batch_samples+' / '+run.pending_samples+'<em>件</em></strong></div></div>';
}
function ticks(x0,x1,y0,y1,W=620){
 let out='';for(let i=0;i<4;i++){let v=y0+(y1-y0)*i/3,y=132-i*104/3;out+='<line x1="44" x2="'+(W-15)+'" y1="'+y+'" y2="'+y+'" stroke="#18315d" stroke-dasharray="3 5"/><text x="38" y="'+(y+3)+'" text-anchor="end" fill="#769bbf" font-size="10">'+v.toFixed(y1<10?2:1)+'</text>'}
 for(let i=0;i<4;i++){const t=x0+(x1-x0)*i/3;out+='<text x="'+(44+i*(W-60)/3)+'" y="152" text-anchor="middle" fill="#769bbf" font-size="9">'+new Date(t).toLocaleTimeString('zh-CN',{hour12:false})+'</text>'}return out;
}
function sensorChart(l,key){
 const config={temperature:['模具回路温度','℃',90,'#50d7e3',2],pressure:['液压回路压力','MPa',8,'#9a98ff',.3],vibration:['振动速度','mm/s',3,'#efcc75',.12]}[key];
 const [label,unit,limit,color,pad]=config,readings=l.recent_readings||[],values=readings.map(r=>r[key]);
 if(!values.length)return '<div class="cp-caption"><span>'+label+' · '+unit+'</span><span>最近15分钟无新采集</span></div><div class="trend-empty">等待当前设备采集<br><small>过期记录不会延伸成实时曲线</small></div>';
 const x1=new Date(l.server_time).getTime(),x0=Math.max(x1-900000,Math.min(x1-60000,new Date(readings[0].created_at).getTime()));
 const y0=Math.max(0,Math.min(...values)-pad),y1=Math.max(...values)+pad,x=t=>44+(t-x0)/(x1-x0)*560,y=v=>132-(v-y0)/(y1-y0)*104;
 let paths='',segment='',previous=null;
 for(const r of readings){const stamp=new Date(r.created_at).getTime();if(stamp<x0)continue;if(previous!==null&&stamp-previous>l.stale_after_seconds*1000){paths+='<path d="'+segment+'"/>';segment=''}segment+=(segment?' L':'M')+x(stamp).toFixed(1)+' '+y(r[key]).toFixed(1);previous=stamp}
 if(segment)paths+='<path d="'+segment+'"/>';
 return '<div class="cp-caption"><span>'+label+' · '+unit+'</span><span>时间轴随采集展开 · 最大15分钟</span></div><svg viewBox="0 0 620 160" role="img" aria-label="'+label+'实际采集时间曲线">'+ticks(x0,x1,y0,y1)+'<g fill="none" stroke="'+color+'" stroke-width="2">'+paths+'</g>'+(limit>y0&&limit<y1?'<line x1="44" x2="605" y1="'+y(limit)+'" y2="'+y(limit)+'" stroke="#ee9276" stroke-dasharray="5 4"/><text x="603" y="'+(y(limit)-5)+'" text-anchor="end" fill="#ee9276" font-size="9">演示上限 '+limit+unit+'</text>':'')+readings.slice(-1).map(r=>'<circle cx="'+x(new Date(r.created_at).getTime())+'" cy="'+y(r[key])+'" r="3" fill="'+color+'"/>').join('')+'</svg><div class="cp-caption"><span>纵轴 '+y0.toFixed(2)+'–'+y1.toFixed(2)+' '+unit+' · 局部范围</span><span>新鲜度 '+l.stale_after_seconds+'s · 缺口不连线</span></div>';
}
function minuteChart(l){
 const data=l.minute_output||[],max=Math.max(5,...data.map(r=>r.quantity));
 return '<div class="cp-caption"><span>近15分钟报工 / 件</span><span>末柱为当前分钟</span></div><svg viewBox="0 0 330 160" role="img" aria-label="每分钟报工量">'+[0,.5,1].map(v=>'<line x1="27" x2="320" y1="'+(132-v*100)+'" y2="'+(132-v*100)+'" stroke="#1b3556"/><text x="23" y="'+(135-v*100)+'" fill="#769bbf" font-size="9" text-anchor="end">'+Math.round(v*max)+'</text>').join('')+data.map((d,i)=>{const x=32+i*19,h=d.quantity/max*100;return '<rect x="'+x+'" y="'+(132-h)+'" width="11" height="'+h+'" fill="'+(d.partial?'#e3c267':'#39b9d0')+'"><title>'+d.time.slice(11)+'：'+d.quantity+'件'+(d.partial?'（本分钟未结束）':'')+'</title></rect>'+(i%4===0||i===14?'<text x="'+(x+5)+'" y="151" font-size="8" text-anchor="middle" fill="#769bbf">'+d.time.slice(11)+'</text>':'')}).join('')+'</svg><div class="cp-caption"><span>累计报工 '+fmt(data.reduce((n,r)=>n+r.quantity,0))+' 件</span><span>停机保持 · 无记录记0</span></div>';
}
function qualityChart(l){
 const rs=l.inspections||[],run=l.demo;
 return '<div class="cp-caption"><span>最近8组在线检测 · 0–100%</span><span>当前演示工单</span></div>'+(rs.length?'<svg viewBox="0 0 620 160" role="img" aria-label="分组质检合格率">'+[0,50,100].map(v=>'<line x1="45" x2="605" y1="'+(130-v)+'" y2="'+(130-v)+'" stroke="#1b3556"/><text x="38" y="'+(134-v)+'" font-size="10" text-anchor="end" fill="#7594b7">'+v+'%</text>').join('')+rs.map((r,i)=>{const rate=1-r.defects/r.sample_size,x=64+i*530/Math.max(1,rs.length-1);return '<line x1="'+x+'" x2="'+x+'" y1="130" y2="'+(130-rate*100)+'" stroke="#307f91" stroke-width="8"/><circle cx="'+x+'" cy="'+(130-rate*100)+'" r="4" fill="'+(rate<.95?'#f0ab71':'#5bddc4')+'"/><text x="'+x+'" y="'+(121-rate*100)+'" text-anchor="middle" fill="#acdbed" font-size="10">'+pct(rate)+'</text><text x="'+x+'" y="151" text-anchor="middle" fill="#769bbf" font-size="9">'+r.created_at.slice(11,19)+'</text><title>'+esc(r.batch)+'：'+r.sample_size+'件 / 不合格'+r.defects+'件</title>'}).join('')+'</svg>':'<div class="trend-empty">当前批次尚未完成检测汇总<br><small>'+(run?.mode==='defense'?'每累计 3 件记录一次抽检':'凑满10件、换料或停机结束时记录实际组数')+'</small></div>')+'<div class="cp-caption"><span>按检测记录更新，不做平滑插值</span><span>待汇总 '+(run?.pending_samples||0)+' 件</span></div>';
}
export function processCharts(l,mode='temperature'){return '<div class="bottom-chart conditions-charts"><div>'+(mode==='quality'?qualityChart(l):sensorChart(l,mode))+'</div><div>'+minuteChart(l)+'</div></div>'}

export function overviewConditions(l){
 return '<section class="card process-overview mb16"><div class="card-head"><div><h2>连续工况与当前批次</h2><p>指标按采集、完工和检测事件更新</p></div><a href="#monitor" class="btn small">进入大屏控制</a></div>'+conditionSummary(l)+'<div class="overview-process-chart">'+processCharts(l,'temperature')+'</div></section>';
}
