(()=>{
const $=id=>document.getElementById(id);
const packs=window.PAJ_PF08_PACKS;
const q=new URLSearchParams(location.search);
const dev=q.get('dev')==='1';
let locale=q.get('locale')&&packs[q.get('locale')]?q.get('locale'):'zh-CN';
let P=packs[locale],pendingWorld=null;
const worlds=['seed','near','far'];
const S={started:0,events:[],view:{seed:-1,near:-1,far:-1},views:{seed:[],near:[],far:[]},counts:{seed:{},near:{},far:{}},first:{seed:null,near:null,far:null},detail:{seed:[],near:[],far:[]},relations:{seed:[],near:[],far:[]},action:{seed:null,near:null,far:null},actionOrder:{seed:[],near:[],far:[]}};
const now=()=>Math.round(performance.now()-S.started);
const log=(type,data={})=>S.events.push({seq:S.events.length+1,t_ms:now(),type,...data});
function show(id){document.querySelectorAll('.screen').forEach(s=>s.classList.add('hidden'));$(id).classList.remove('hidden');scrollTo(0,0)}
function randomIndex(n){const a=new Uint32Array(1);crypto.getRandomValues(a);return a[0]%n}
function shuffled(items){const out=[...items];for(let i=out.length-1;i>0;i--){const j=randomIndex(i+1);[out[i],out[j]]=[out[j],out[i]]}return out}
function resetOrders(){for(const w of worlds)S.actionOrder[w]=shuffled(['a','b','hold'])}
function active(el,i){el.querySelectorAll('button[data-i]').forEach(b=>b.classList.toggle('active',Number(b.dataset.i)===i))}
function markView(world,i){
  const key='nav_'+i;
  S.counts[world][key]=(S.counts[world][key]||0)+1;
  if(!S.first[world]){S.first[world]=key;log('first_open_category',{world,object:key,index:i})}
  if(!S.views[world].includes(key)){S.views[world].push(key);log('open_object',{world,object:key,index:i})}
  else log('revisit_object',{world,object:key,index:i,count:S.counts[world][key]});
}
function markDetail(world,key){
  if(!S.detail[world].includes(key)){S.detail[world].push(key);log('open_detail',{world,object:key})}
  else log('revisit_detail',{world,object:key});
  maybeRelations(world);
}
function addRelation(world,key){
  if(S.relations[world].includes(key))return;
  S.relations[world].push(key);
  log('relation_discovered',{world,relation:key});
}
function maybeRelations(world){
  const d=S.detail[world];
  if(d.includes('record_0')&&d.includes('group_1'))addRelation(world,'rg');
  if(d.includes('record_0')&&d.includes('history_1'))addRelation(world,'rh');
  if(d.includes('external_1')&&d.includes('group_1'))addRelation(world,'eg');
  if(d.includes('limit_0')&&d.includes('record_0'))addRelation(world,'lr');
}
function relationPanel(world){
  if(!S.relations[world].length)return '';
  const r=P[world].relation;
  return '<div class="notice good"><div class="relation">'+S.relations[world].map(k=>'<span>'+r[k]+'</span>').join('')+'</div></div>';
}
function detailList(world,items,prefix){
  return '<div class="card">'+items.map((x,i)=>'<div class="object"><span>'+x+'</span><button class="link detailBtn" data-world="'+world+'" data-key="'+prefix+'_'+i+'" data-text="'+String(x).replace(/"/g,'&quot;')+'">⋯</button></div>').join('')+'</div>';
}
function recordGrid(world,records){
  return '<div class="recordGrid">'+records.map((r,i)=>'<button class="record recordBtn" data-world="'+world+'" data-j="'+i+'"><b>'+r[0]+'</b><small>'+r[1]+'</small></button>').join('')+'</div>';
}
function applyPack(){
  P=packs[locale];document.documentElement.lang=locale;$('market').textContent=P.native;
  $('introEy').textContent=P.intro[0];$('introTitle').textContent=P.intro[1];$('introLead').textContent=P.intro[2];$('start').textContent=P.intro[3];$('introHelp').textContent=P.intro[4];
  $('transitionEy').textContent=P.transition[0];$('transitionLine').textContent=P.transition[1];$('transitionNext').textContent=P.transition[2];
  $('seedCrumb').textContent=P.seed.crumb;$('nearCrumb').textContent=P.near.crumb;$('farCrumb').textContent=P.far.crumb;
  $('doneEy').textContent=P.done[0];$('doneTitle').textContent=P.done[1];$('doneLead').textContent=P.done[2];$('export').textContent=P.done[3];$('again').textContent=P.done[4];
  for(const w of worlds)renderNav(w);
}
function renderNav(world){
  const w=P[world],el=$(world+'Nav');
  el.innerHTML='<div class="brand">'+w.brand+'</div>'+w.nav.map((n,i)=>'<button data-i="'+i+'">'+n+'</button>').join('');
  el.querySelectorAll('button[data-i]').forEach(b=>b.onclick=()=>renderWorld(world,Number(b.dataset.i),true));
  active(el,S.view[world]);
}
function resetState(){
  S.started=performance.now();S.events=[];S.view={seed:-1,near:-1,far:-1};S.views={seed:[],near:[],far:[]};S.counts={seed:{},near:{},far:{}};S.first={seed:null,near:null,far:null};S.detail={seed:[],near:[],far:[]};S.relations={seed:[],near:[],far:[]};S.action={seed:null,near:null,far:null};resetOrders();
}
function startJourney(){
  resetState();log('session_start',{locale,market:P.market});log('action_order',{orders:JSON.parse(JSON.stringify(S.actionOrder))});show('seed');renderWorld('seed',-1,false);
}
function renderWorld(world,i,track=false){
  S.view[world]=i;if(track)markView(world,i);active($(world+'Nav'),i);renderGeneric(world,i);bindEvidence(world);renderActions(world);
}
function renderGeneric(world,i){
  const w=P[world],c=$(world+'Content');
  if(i===-1){c.innerHTML='<h2>'+w.title+'</h2><p class="lead">'+w.status+'</p><div class="card"><span class="meta">'+P.intro[4]+'</span></div>';return}
  if(i===0)c.innerHTML='<h2>'+w.nav[0]+'</h2>'+recordGrid(world,w.records)+'<div id="'+world+'Detail"></div>'+relationPanel(world);
  if(i===1)c.innerHTML='<h2>'+w.nav[1]+'</h2>'+detailList(world,w.history,'history')+'<div id="'+world+'Detail"></div>'+relationPanel(world);
  if(i===2)c.innerHTML='<h2>'+w.nav[2]+'</h2>'+detailList(world,w.groups,'group')+'<div id="'+world+'Detail"></div>'+relationPanel(world);
  if(i===3)c.innerHTML='<h2>'+w.nav[3]+'</h2>'+detailList(world,w.limits,'limit')+'<div id="'+world+'Detail"></div>'+relationPanel(world);
  if(i===4)c.innerHTML='<h2>'+w.nav[4]+'</h2>'+detailList(world,w.outside,'external')+'<div id="'+world+'Detail"></div>'+relationPanel(world);
  if(i===5)c.innerHTML='<h2>'+w.nav[5]+'</h2>'+detailList(world,w.notes,'note')+'<div id="'+world+'Detail"></div>'+relationPanel(world);
}
function bindEvidence(world){
  document.querySelectorAll('.recordBtn').forEach(b=>b.onclick=()=>{
    const j=Number(b.dataset.j),r=P[world].records[j],key='record_'+j;markDetail(world,key);
    const el=$(world+'Detail');if(el)el.innerHTML='<div class="notice"><b>'+r[0]+'</b><p>'+r.slice(1).join(' · ')+'</p></div>'+relationPanel(world);
  });
  document.querySelectorAll('.detailBtn').forEach(b=>b.onclick=()=>{
    const key=b.dataset.key,text=b.dataset.text;markDetail(world,key);
    const el=$(world+'Detail');if(el)el.innerHTML='<div class="notice">'+text+'</div>'+relationPanel(world);
  });
}
function renderActions(world){
  const w=P[world],el=$(world+'Actions'),a=S.action[world];
  if(!a){
    const order=S.actionOrder[world].length?S.actionOrder[world]:['a','b','hold'];
    el.innerHTML='<h3>'+w.actions.title+'</h3><div class="row">'+order.map(k=>'<button class="btn worldAction" data-a="'+k+'">'+w.actions[k]+'</button>').join('')+'</div>';
    el.querySelectorAll('.worldAction').forEach(b=>b.onclick=()=>takeAction(world,b.dataset.a));return;
  }
  el.innerHTML='<div class="notice"><b>'+w.consequence[a]+'</b></div><div class="row"><button class="btn inspectCurrent">'+P.post.inspect+'</button><button class="btn switchAction">'+P.post.switch+'</button><button class="primary commitWorld">'+P.post.commit+'</button></div>';
  el.querySelector('.inspectCurrent').onclick=()=>{log('post_consequence_action',{world,action:'continue_browsing',from:a});S.action[world]=null;renderActions(world)};
  el.querySelector('.switchAction').onclick=()=>{log('post_consequence_action',{world,action:'switch_decision',from:a});S.action[world]=null;renderActions(world)};
  el.querySelector('.commitWorld').onclick=()=>commitWorld(world);
}
function takeAction(world,a){
  S.action[world]=a;
  log('provisional_action',{world,action:a,first_open:S.first[world],opened:[...S.views[world]],relations:[...S.relations[world]],details:S.detail[world].length});
  log('consequence_exposed',{world,action:a});renderActions(world);
}
function commitWorld(world){
  const omissions=P[world].nav.length-S.views[world].length;
  log('commit',{world,action:S.action[world],first_open:S.first[world],opened:[...S.views[world]],revisits:Object.values(S.counts[world]).reduce((n,v)=>n+Math.max(0,v-1),0),relations:[...S.relations[world]],omissions});
  if(world==='seed'){pendingWorld='near';show('transition');return}
  if(world==='near'){pendingWorld='far';show('transition');return}
  finish();
}
function enterPending(){
  if(!pendingWorld)return;
  const w=pendingWorld;pendingWorld=null;log('neutral_transition',{to_world:w});show(w);renderWorld(w,-1,false);
}
function finish(){
  log('session_complete',{market:P.market});
  $('trace').innerHTML=S.events.filter(e=>e.type!=='session_start').map(e=>'<div>#'+e.seq+' · '+e.t_ms+'ms · '+e.type+' · '+(e.world||e.to_world||'journey')+(e.object?' / '+e.object:'')+(e.relation?' / '+e.relation:'')+(e.action?' / '+e.action:'')+'</div>').join('');
  $('shape').innerHTML=worlds.map(w=>{
    const revisits=Object.values(S.counts[w]).reduce((n,v)=>n+Math.max(0,v-1),0),omissions=P[w].nav.length-S.views[w].length;
    return '<div class="card"><div class="ey">'+P[w].brand+'</div><div class="count">'+(S.first[w]||'—')+'</div><div class="meta">opened '+S.views[w].length+' · revisits '+revisits+' · links '+S.relations[w].length+' · omitted '+omissions+'</div></div>';
  }).join('');
  if(dev){$('research').classList.remove('hidden');$('research').innerHTML='<b>Research view</b><p>Descriptive only: first object category, cross-object links, targeted revisits, omissions, and sequence compression across unfamiliar workspaces. No live construct label or correctness score is shown.</p>'}
  show('done');
}
function exportTrace(){
  const payload={instrument:'golden-pf08-v1',locale,market:P.market,events:S.events,first:S.first,views:S.views,details:S.detail,relations:S.relations,counts:S.counts,actions:S.action,action_order:S.actionOrder};
  const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),a=document.createElement('a'),u=URL.createObjectURL(blob);a.href=u;a.download='paj-open-workspaces-'+P.market+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),500);
}
Object.entries(packs).forEach(([k,v])=>{const o=document.createElement('option');o.value=k;o.textContent=v.native;$('locale').appendChild(o)});
$('locale').value=locale;$('locale').onchange=e=>{locale=e.target.value;P=packs[locale];history.replaceState(null,'','?locale='+encodeURIComponent(locale)+(dev?'&dev=1':''));applyPack();show('intro')};
$('start').onclick=startJourney;$('transitionNext').onclick=enterPending;$('export').onclick=exportTrace;$('again').onclick=()=>location.reload();applyPack();
})();