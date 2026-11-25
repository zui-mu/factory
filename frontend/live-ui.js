// Update existing nodes so focus, scroll positions and SVG animations survive polling.
export function morph(target,html){
 const template=document.createElement('template');template.innerHTML=html;
 function patch(old,fresh){
  if(old.nodeType!==fresh.nodeType||old.nodeName!==fresh.nodeName){old.replaceWith(fresh.cloneNode(true));return}
  if(old.nodeType===3){if(old.data!==fresh.data)old.data=fresh.data;return}
  if(old.nodeType!==1)return;
  if(old.matches('input,textarea,select,video')||old.hasAttribute('data-live-preserve'))return;
  if(old.outerHTML===fresh.outerHTML)return;
  for(const a of [...old.attributes])if(!fresh.hasAttribute(a.name)&&!['open','hidden'].includes(a.name))old.removeAttribute(a.name);
  for(const a of [...fresh.attributes])if(old.getAttribute(a.name)!==a.value)old.setAttribute(a.name,a.value);
  children(old,fresh);
 }
 function children(old,fresh){
  const before=[...old.childNodes],after=[...fresh.childNodes];
  for(let i=0;i<Math.max(before.length,after.length);i++){
   if(!after[i])before[i].remove();else if(!before[i])old.append(after[i].cloneNode(true));else patch(before[i],after[i]);
  }
 }
 children(target,template.content);
}
export function liveBar(){return '<div class="live-status" data-live-preserve><span class="live-dot"></span><span class="live-state">业务数据自动同步</span><span class="live-detail">保留当前输入与滚动位置</span><button type="button" data-action="live-pause">暂停同步</button></div>'}
export function mountLivePage(S,api,renderPage,filter){
 let disposed=false,paused=false,timer;const factory=S.factory,page=S.page,container=document.getElementById('page');
 const bar=container.querySelector('.live-status');if(!bar)return()=>{};
 let previous='';
 const click=e=>{if(e.target.dataset.action==='live-pause'){paused=!paused;e.target.textContent=paused?'继续同步':'暂停同步';bar.querySelector('.live-state').textContent=paused?'同步已暂停':'业务数据自动同步'}};
 bar.addEventListener('click',click);
 const tick=async()=>{
  if(disposed)return;
  if(!paused&&!document.hidden&&!document.querySelector('dialog')){
   try{
    const shadow={...S,cache:{...S.cache}};const html=await renderPage(page,shadow,api);
    if(disposed)return;
    if(html!==previous){morph(container,html);S.cache=shadow.cache;filter();previous=html;container.dataset.liveUpdated=String(Date.now())}
    bar.dataset.state='ok';bar.querySelector('.live-state').textContent='业务数据已同步';bar.querySelector('.live-detail').textContent='查询成功 '+new Date().toLocaleTimeString('zh-CN')+' · 采集时间以记录为准';
   }catch(e){if(!disposed){bar.dataset.state='error';bar.querySelector('.live-state').textContent='连接中断，保留最近数据';bar.querySelector('.live-detail').textContent='正在重试'}}
  }
  if(!disposed)timer=setTimeout(tick,page==='federation'?1000:3000);
 };
 timer=setTimeout(tick,page==='federation'?1000:3000);
 return()=>{disposed=true;clearTimeout(timer);bar.removeEventListener('click',click)};
}
