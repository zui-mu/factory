export const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const fmt=v=>Number(v||0).toLocaleString('zh-CN');
export const pct=(v,d=1)=>v==null?'—':(v*100).toFixed(d)+'%';
export const date=v=>v?String(v).replace('T',' ').slice(0,16):'—';
const paths={
 home:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
 cube:'<path d="m12 3 9 5v8l-9 5-9-5V8zM3 8l9 5 9-5M12 13v8M7.5 5.5l9 5"/>',
 order:'<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V2h6v2M9 10h6M9 14h6M9 18h3"/>',
 device:'<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4M7 9h3v4H7zM14 9h3M14 12h3"/>',
 quality:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',
 cause:'<circle cx="12" cy="5" r="2"/><circle cx="5" cy="18" r="2"/><circle cx="19" cy="18" r="2"/><path d="M12 7v5M5 16v-4h14v4"/>',
 tasks:'<path d="M9 5h12M9 12h12M9 19h12M2 5l1 1 2-2M2 12l1 1 2-2M2 19l1 1 2-2"/>',
 network:'<circle cx="12" cy="12" r="3"/><circle cx="4" cy="4" r="2"/><circle cx="20" cy="4" r="2"/><circle cx="4" cy="20" r="2"/><circle cx="20" cy="20" r="2"/><path d="m6 6 4 4m4 4 4 4m0-12-4 4m-4 4-4 4"/>',
 box:'<path d="M3 8h18v13H3zM2 3h20v5H2zM9 12h6"/>',
 data:'<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v7c0 4 18 4 18 0V5M3 12v7c0 4 18 4 18 0v-7"/>',
 settings:'<path d="m9 3-1 3-3 1v4l-2 1 2 2v4l3 1 1 3h6l1-3 3-1v-4l2-2-2-1V7l-3-1-1-3z"/><circle cx="12" cy="12" r="3"/>',
 arrow:'<path d="M4 12h16M14 6l6 6-6 6"/>',
 chevron:'<path d="m9 5 7 7-7 7"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',
 refresh:'<path d="M20 8a9 9 0 1 0 0 8M20 3v5h-5"/>',
 download:'<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
 search:'<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
 bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 8h18s-3-1-3-8M10 21h4"/>',
 logout:'<path d="M9 4H4v16h5M10 12h11m-4-4 4 4-4 4"/>',
 close:'<path d="m5 5 14 14M19 5 5 19"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
 alert:'<path d="m12 3 10 18H2zM12 9v5M12 17h.01"/>',
 check:'<path d="m5 12 4 4L19 6"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 user:'<circle cx="12" cy="7" r="4"/><path d="M4 21v-3c0-6 16-6 16 0v3"/>',
 menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
 trend:'<path d="m3 17 6-6 4 4 8-10M15 5h6v6"/>',
 play:'<path d="m8 4 12 8-12 8z"/>',
 phone:'<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M10 18h4"/>',
 camera:'<path d="M3 7h4l2-3h6l2 3h4v14H3z"/><circle cx="12" cy="13" r="4"/>',
 history:'<path d="M3 12a9 9 0 1 0 3-6M3 3v5h5M12 7v5l4 2"/>'
};
export function icon(name,cls=''){return '<svg class="icon '+cls+'" viewBox="0 0 24 24" aria-hidden="true">'+(paths[name]||paths.cube)+'</svg>'}
export function badge(s){const style=['预警','高','紧急','失败'].includes(s)?'bad':['待分析','待处置','处理中','待复检','训练中','准备中','中','已暂停'].includes(s)?'warn':['待排产','待接单','待机','已取消','中断','离线'].includes(s)?'neutral':'';return '<span class="status '+style+'">'+esc(s)+'</span>'}
export function btn(label,action,attrs='',kind=''){return '<button class="btn '+kind+'" data-action="'+action+'" '+attrs+'>'+label+'</button>'}
export function empty(message='暂无记录'){return '<div class="empty">'+icon('box')+'<p>'+esc(message)+'</p></div>'}
export function notice(message,warn=false){return '<div class="notice '+(warn?'warn':'')+'">'+icon('info')+'<p>'+esc(message)+'</p></div>'}
export function table(headers,body){return '<div class="table-wrap"><table class="table"><thead><tr>'+headers.map(h=>'<th>'+h+'</th>').join('')+'</tr></thead><tbody>'+body+'</tbody></table></div>'}
export function field(label,name,type='text',value='',extra=''){return '<div class="field '+(type==='textarea'?'full':'')+'"><label for="f-'+name+'">'+label+'</label>'+(type==='textarea'?'<textarea id="f-'+name+'" name="'+name+'" '+extra+'>'+esc(value)+'</textarea>':'<input id="f-'+name+'" name="'+name+'" type="'+type+'" value="'+esc(value)+'" '+extra+'>')+'</div>'}
export function select(label,name,options,value=''){return '<div class="field"><label for="f-'+name+'">'+label+'</label><select id="f-'+name+'" name="'+name+'">'+options.map(o=>'<option value="'+esc(o[0])+'" '+(String(o[0])===String(value)?'selected':'')+'>'+esc(o[1])+'</option>').join('')+'</select></div>'}
export function chartLine(data,keys,colors=['#548765','#d5ac73'],percent=false){
 if(!data.length)return empty('暂无趋势数据');
 const W=600,H=204,L=40,R=14,T=18,B=30;let values=data.flatMap(d=>keys.map(k=>Number(d[k]||0)));
 const max=percent?1:Math.max(...values,1)*1.15;
 const x=i=>L+i*(W-L-R)/Math.max(data.length-1,1),y=v=>H-B-v/max*(H-T-B);
 let out='<svg class="chart" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="数据趋势图">';
 for(let i=0;i<=4;i++){let val=max*i/4;out+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+y(val)+'" y2="'+y(val)+'" stroke="#edf1e9" stroke-dasharray="3 4"/><text x="0" y="'+(y(val)+3)+'">'+(percent?Math.round(val*100)+'%':val<2?val.toFixed(2):Math.round(val))+'</text>'}
 keys.forEach((k,j)=>{let pts=data.map((d,i)=>[x(i),y(Number(d[k]||0))]);let d=pts.map((p,i)=>(i?'L':'M')+p.join(',')).join(' ');if(j===0)out+='<path d="'+d+' L'+x(data.length-1)+','+(H-B)+' L'+L+','+(H-B)+'Z" fill="'+colors[j]+'" opacity=".06"/>';out+='<path d="'+d+'" fill="none" stroke="'+colors[j]+'" stroke-width="2.3" stroke-linejoin="round"/>';pts.forEach((p,i)=>{out+='<circle cx="'+p[0]+'" cy="'+p[1]+'" r="2.5" fill="'+colors[j]+'"><title>'+esc(data[i].date||'第 '+(i+1)+' 轮')+'：'+(percent?pct(data[i][k]):Number(data[i][k]).toFixed(3))+'</title></circle>'})});
 data.forEach((d,i)=>{if(i%Math.max(1,Math.floor(data.length/6))===0||i===data.length-1)out+='<text x="'+x(i)+'" y="'+(H-7)+'" text-anchor="middle">'+esc(d.date?d.date.slice(5):i+1)+'</text>'});
 return out+'</svg>';
}
export function scene(devices=[],large=false){
 const colors={运行:['#90b89a','#568166','#c4d8c4'],预警:['#e5bd87','#ad7b42','#efdbc0'],待机:['#bbc9bf','#80998a','#dbe5dc']};
 let html='<svg class="scene" viewBox="0 0 620 330" role="img" aria-label="车间设备空间示意图，点击设备查看采集数据"><defs><pattern id="floor" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="matrix(1 .42 -1 .42 310 30)"><path d="M 28 0 L 0 0 0 28" fill="none" stroke="#d6e3d3" stroke-width=".8"/></pattern></defs><path d="M35 180 310 57 590 180 310 311Z" fill="#e6eee1" stroke="#d5e0cd"/><path d="M35 180 310 57 590 180 310 311Z" fill="url(#floor)"/><path d="M35 180v12l275 123v-4z" fill="#cfddc8"/><path d="M310 311v4l280-123v-12z" fill="#d9e5d3"/><path d="m78 179 229-101 240 104" fill="none" stroke="#b9ccae" stroke-width="1.5" stroke-dasharray="5 5"/><path d="m153 180 156 71 155-70M234 144l155 71" fill="none" stroke="#fff" stroke-width="10"/><path d="m153 180 156 71 155-70" fill="none" stroke="#bfcead" stroke-width="1" stroke-dasharray="7 6"/>';
 const positions=[[230,143],[389,139],[219,214],[386,213]];
 for(let i=0;i<(devices.length?Math.min(4,devices.length):4);i++){const d=devices[i]||{id:i+1,name:['精密成型','数控加工','自动装配','在线检测'][i],status:i===0?'预警':'运行',code:'EQ-0'+(i+1)};const [x,y]=positions[i],col=colors[d.display_status||d.status]||colors.待机;
 html+='<g '+(devices.length?'data-action="device-detail" data-id="'+d.id+'" tabindex="0" role="button"':'')+' aria-label="'+esc(d.name)+'"><ellipse cx="'+x+'" cy="'+(y+21)+'" rx="51" ry="18" fill="#80967a" opacity=".12"/><path d="M'+(x-42)+' '+y+'v-46l43 19v46z" fill="'+col[1]+'"/><path d="M'+(x+1)+' '+(y+19)+'v-46l43-19V'+y+'z" fill="'+col[0]+'"/><path d="M'+(x-42)+' '+(y-46)+'l43-19 43 19-43 19z" fill="'+col[2]+'"/><path d="M'+(x-30)+' '+(y-38)+'l20 9v26l-20-9z" fill="#2d5141"/><path d="M'+(x-27)+' '+(y-33)+'l14 6v17l-14-6z" fill="#789c81"/><path d="M'+(x+13)+' '+(y-23)+'l19-8v14l-19 8z" fill="#e2eadb"/><path d="M'+(x+17)+' '+(y-19)+'l10-4M'+(x+17)+' '+(y-14)+'l10-4" stroke="#7a9c74" stroke-width="2"/><circle cx="'+(x+3)+'" cy="'+(y-72)+'" r="4" fill="'+((d.display_status||d.status)==='预警'?'#dc9850':(d.display_status||d.status)==='运行'?'#619971':'#8a98a6')+'"/><path d="M'+(x+3)+' '+(y-66)+'v8" stroke="#b1c4a7"/><text x="'+x+'" y="'+(y+41)+'" text-anchor="middle" fill="#778b6a" font-size="9">'+esc(d.code)+' · '+esc(d.name)+'</text></g>'}
 html+='<text x="30" y="28" fill="#8ba07a" font-size="10" letter-spacing="2">WORKSHOP / 01</text><text x="590" y="313" text-anchor="end" fill="#8ba07a" font-size="9">设备状态映射 · 点击查看详情</text></svg>';return html;
}
export function graph(){
 return '<svg class="causal-graph" viewBox="0 0 640 190" role="img" aria-label="固定因果假设图"><defs><marker id="arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0 6 3 0 6" fill="none" stroke="#9ab18e"/></marker></defs><g fill="none" stroke="#adc29f" stroke-width="1.4" marker-end="url(#arr)"><path d="M140 47 C210 47 195 42 263 42M140 140C210 140 195 97 263 97M140 140 C190 140 192 42 263 42M140 47C210 47 420 12 512 85M140 140C210 185 425 185 512 106M370 42 512 86M370 97h142M370 151 512 108"/></g>'+[[30,28,110,'原料等级'],[30,120,110,'产品规格'],[263,23,108,'温度偏高'],[263,78,108,'压力偏高'],[263,133,108,'设备磨损'],[512,78,100,'质量结果']].map(([x,y,w,s],i)=>'<rect x="'+x+'" y="'+y+'" width="'+w+'" height="38" rx="9" fill="'+(i===5?'#285e45':'#fff')+'" stroke="'+(i===5?'#285e45':'#dce7d5')+'"/><text x="'+(x+w/2)+'" y="'+(y+24)+'" text-anchor="middle" fill="'+(i===5?'#fff':'#66815e')+'" font-size="11">'+s+'</text>').join('')+'</svg>';
}
