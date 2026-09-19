(()=>{
const $=id=>document.getElementById(id);
document.body.dataset.instrument='pf02';
const packs=window.PAJ_PF02_PACKS;
const chrome=window.PAJ_PF02_CHROME;
const q=new URLSearchParams(location.search);
const dev=q.get('dev')==='1';
let locale=q.get('locale')&&packs[q.get('locale')]?q.get('locale'):'zh-CN';
let P=packs[locale],C=chrome[locale];
const S={started:0,events:[],views:{seed:[],near:[],far:[]},detail:{seed:[],near:[],far:[]},action:{seed:null,near:null,far:null},actionOrder:{seed:[],near:[],far:[]},view:{seed:0,near:0,far:0},selection:{seed:null,near:null,far:null},worldState:{seed:{},near:{},far:{}}};
const now=()=>Math.round(performance.now()-S.started);
const log=(type,data={})=>S.events.push({seq:S.events.length+1,t_ms:now(),type,...data});
function show(id){document.querySelectorAll('.screen').forEach(s=>s.classList.add('hidden'));$(id).classList.remove('hidden');scrollTo(0,0)}
function active(el,i){el.querySelectorAll('button[data-i]').forEach(b=>b.classList.toggle('active',Number(b.dataset.i)===i))}
function markView(world,i){const key='nav_'+i;if(!S.views[world].includes(key))S.views[world].push(key);log('open_object',{world,object:key});refreshSignal(world)}
function markDetail(world,key){if(!S.detail[world].includes(key))S.detail[world].push(key);log('open_detail',{world,object:key});refreshSignal(world)}
function metrics(rows){return `<div class="metricGrid">${rows.map(r=>`<div class="card metric"><span class="meta">${r[0]}</span><b>${r[1]}</b></div>`).join('')}</div>`}
function spark(values=[85,86,84,87,85,72,68]){return `<div class="spark">${values.map(v=>`<i style="height:${v}%"></i>`).join('')}</div>`}
function table(head,rows,detailClass='',detailLabel=''){return `<table class="table"><tr>${head.map(x=>`<th>${x}</th>`).join('')}${detailClass?'<th></th>':''}</tr>${rows.map((r,i)=>`<tr>${r.map(x=>`<td>${x}</td>`).join('')}${detailClass?`<td><button class="link ${detailClass}" data-j="${i}">${detailLabel||P.seed.open}</button></td>`:''}</tr>`).join('')}</table>`}
function logBox(rows){return `<div class="log">${rows.map(x=>`<div>${x}</div>`).join('')}</div>`}
function randomIndex(n){const a=new Uint32Array(1);crypto.getRandomValues(a);return a[0]%n}
function shuffled(items){const out=[...items];for(let i=out.length-1;i>0;i--){const j=randomIndex(i+1);[out[i],out[j]]=[out[j],out[i]]}return out}
function actionKeys(world){return world==='seed'?['rollback','repin','hold']:world==='near'?['rollback','reroute','hold']:['revert','schedule','hold']}
function resetActionOrders(){for(const world of ['seed','near','far'])S.actionOrder[world]=shuffled(actionKeys(world))}
function worldMode(world){return world==='seed'?'INCIDENT':world==='near'?'NETWORK':'ENERGY'}
function signalStrip(world){
  const w=P[world],opened=S.views[world].length,deep=S.detail[world].length,action=S.action[world],state=S.worldState[world]||{};
  const primary=state.primary||(w.metrics?.[0]?.[1]||'—');
  return `<div id="${world}Signal" class="signalStrip">
    <div class="signalIdentity"><span class="signalPulse"></span><b>${worldMode(world)}</b><small>LIVE</small></div>
    <div class="signalStat"><span>PRIMARY</span><b>${primary}</b></div>
    <div class="signalStat"><span>OPENED</span><b>${opened}</b></div>
    <div class="signalStat"><span>DEEP</span><b>${deep}</b></div>
    <div class="signalAction ${action?'active':''}"><span>ACTION</span><b>${action?w.actions[action]:'—'}</b></div>
  </div>`;
}
function refreshSignal(world){
  const el=$(world+'Signal'); if(el) el.outerHTML=signalStrip(world);
}
function outcomePanel(world,a){
  const w=P[world];
  return `<div class="outcomePanel">
    <div class="outcomeTag"><span>YOUR MOVE</span><b>${w.actions[a]}</b></div>
    <div class="outcomeArrow">→</div>
    <div class="outcomeResult"><span>WORLD RESPONSE</span><b>${w.consequence[a]}</b></div>
  </div>`;
}
function generationSurface(w){
  const s=S.selection.seed||'A',state=S.worldState.seed||{},action=state.action;
  let shares={A:'82%',B:'18%'},tones={A:'stable',B:'risk'};
  if(action==='repin'){shares={A:'100%',B:'0%'};tones={A:'stable',B:'stable'}}
  if(action==='rollback'){tones={A:'warn',B:'risk'}}
  const rows=[
    {k:'A',name:w.generation.a,share:shares.A,tone:tones.A},
    {k:'B',name:w.generation.b,share:shares.B,tone:tones.B}
  ];
  return `<div class="generationSurface">
    <div class="generationHead"><div><span class="meta">SERVING POOLS</span><h3>${w.generation.expected}</h3></div><span class="generationTraffic">${state.note||w.generation.traffic}</span></div>
    <div class="generationRows">${rows.map(r=>`<button class="generationRow ${s===r.k?'selected':''}" data-k="${r.k}">
      <span class="genPool">${r.k}</span><span class="genName">${r.name}</span><span class="genShare">${r.share}</span><span class="genTone ${r.tone}">${r.tone==='risk'?'MISMATCH':r.tone==='warn'?'PARTIAL':'CURRENT'}</span>
    </button>`).join('')}</div>
    <div class="generationCompare"><span>${w.generation.detail}</span><button id="compareGen" class="btn">${w.generation.compare}</button></div>
    <div id="genDetail"></div>
  </div>`;
}
function fulfillmentSurface(w){
  const sel=S.selection.near||0;
  return `<div class="networkBoard">
    <div class="networkHead"><span class="meta">NETWORK VIEW</span><b>${w.status}</b></div>
    <div class="networkLanes">
      <div class="networkCol"><span class="networkLabel">DEPOTS</span>${w.depots.map((r,i)=>`<button class="networkNode depotNode ${sel===i?'selected':''}" data-j="${i}"><b>${r[0]}</b><small>${r[1]}</small></button>`).join('')}</div>
      <div class="networkLinks">${w.depots.map((_,i)=>`<i class="${sel===i?'on':''}"></i>`).join('')}</div>
      <div class="networkCol"><span class="networkLabel">REGIONS</span>${w.cities.map((r,i)=>`<button class="networkNode cityNode ${sel===i?'selected':''}" data-j="${i}"><b>${r[0]}</b><small>${r[1]} · ${r[2]}</small></button>`).join('')}</div>
    </div>
    <div class="networkContext"><div><span>ROUTE</span><b>${w.routes}</b></div><div><span>WEATHER</span><b>${w.weather}</b></div></div>
    <div id="nearDetail"></div>
  </div>`;
}
function energyTimeline(){
  const room=S.selection.far||0,state=S.worldState.far||{},action=state.action;
  let series=[
    [42,44,43,46,55,62,58,50],
    [30,31,30,34,39,41,37,33],
    [22,22,23,25,35,48,52,34]
  ][room]||[42,44,43,46,55,62,58,50];
  if(action==='revert')series=series.map((v,i)=>Math.max(14,v-(i<4?8:4)));
  if(action==='schedule'&&room===1)series=series.map((v,i)=>Math.max(14,v-(i<4?7:2)));
  if(action==='hold')series=series.map((v,i)=>v+(i>4?4:1));
  return `<div class="energyTimeline"><div class="energyAxis"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span></div><div class="energyBars">${series.map((v,i)=>`<i style="height:${v}%"><b>${v}</b></i>`).join('')}</div></div>`;
}
function bindWorldMicroInteractions(world){
  if(world==='seed'){
    document.querySelectorAll('.generationRow').forEach(b=>b.onclick=()=>{S.selection.seed=b.dataset.k;log('open_detail',{world:'seed',object:'serving_pool_'+b.dataset.k});renderWorld('seed',2,false)});
  }
  if(world==='near'){
    document.querySelectorAll('.depotNode,.cityNode').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);S.selection.near=j;markDetail('near','network_'+j);renderWorld('near',1,false)});
  }
  if(world==='far'){
    document.querySelectorAll('.energyRoom').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);S.selection.far=j;markDetail('far','room_'+j);renderWorld('far',0,false)});
  }
}
function applyPack(){P=packs[locale];C=chrome[locale];document.documentElement.lang=locale;$('market').textContent=P.market;$('introEy').textContent=P.intro.ey;$('introTitle').textContent=P.intro.title;$('introLead').textContent=P.intro.lead;$('start').textContent=P.intro.start;$('introHelp').textContent=P.intro.help;$('cueEy').textContent=P.cue.ey;$('cueLine').textContent=P.cue.line;$('cueNext').textContent=P.cue.next;$('seedCrumb').textContent=P.seed.crumb;$('nearCrumb').textContent=P.near.crumb;$('farCrumb').textContent=P.far.crumb;$('doneEy').textContent=P.done.ey;$('doneTitle').textContent=P.done.title;$('doneLead').textContent=P.done.lead;$('traceLabel').textContent=C.trace;$('journeyLabel').textContent=C.journey;$('export').textContent=P.done.export;$('again').textContent=P.done.again;renderNav('seed');renderNav('near');renderNav('far')}
function renderNav(world){const w=P[world],el=$(world+'Nav');el.innerHTML=`<div class="brand">${w.brand}</div>`+w.nav.map((n,i)=>`<button data-i="${i}">${n}</button>`).join('');el.querySelectorAll('button[data-i]').forEach(b=>b.onclick=()=>renderWorld(world,Number(b.dataset.i),true));active(el,S.view[world])}
function startJourney(){S.started=performance.now();S.events=[];S.views={seed:[],near:[],far:[]};S.detail={seed:[],near:[],far:[]};S.action={seed:null,near:null,far:null};S.view={seed:0,near:0,far:0};S.selection={seed:null,near:null,far:null};S.worldState={seed:{},near:{},far:{}};delete document.body.dataset.action;resetActionOrders();log('session_start',{locale,market:P.market});log('action_order',{orders:JSON.parse(JSON.stringify(S.actionOrder))});show('seed');renderWorld('seed',0,true)}
function decorateScene(world,i){
  document.body.dataset.world=world;
  const content=$(world+'Content'),main=content&&content.closest('.main'),w=P[world];
  if(!main||!w)return;
  let chrome=main.querySelector('.sceneChrome');
  if(!chrome){chrome=document.createElement('div');chrome.className='sceneChrome';main.insertBefore(chrome,main.querySelector('.crumb')?.nextSibling||main.firstChild)}
  const section=w.nav?.[i]||w.title||'';
  const mode=worldMode(world);
  chrome.innerHTML=`<div class="sceneIdentity"><span class="sceneDot"></span><b>${w.brand}</b></div><div class="sceneTrail">${section}</div><span class="sceneState">${mode}</span>`;
}
function renderWorld(world,i,track=false){S.view[world]=i;if(track)markView(world,i);active($(world+'Nav'),i);if(world==='seed')renderSeed(i);if(world==='near')renderNear(i);if(world==='far')renderFar(i);decorateScene(world,i);renderActions(world);bindWorldMicroInteractions(world)}
function renderSeed(i){const w=P.seed,c=$('seedContent');if(i===0)c.innerHTML=`<h2>${w.title}</h2><p class="lead">${w.status}</p>${signalStrip('seed')}${metrics(w.metrics)}${spark()}`;if(i===1)c.innerHTML=`<h2>${w.nav[1]}</h2><div class="card">${table(w.sliceCols,w.slices,'seedSlice',w.open)}</div><div id="seedDetail"></div>`;if(i===2)c.innerHTML=`<h2>${w.nav[2]}</h2>${generationSurface(w)}`;if(i===3)c.innerHTML=`<h2>${w.nav[3]}</h2><div class="card">${table(['',''],w.corpus)}</div>`;if(i===4)c.innerHTML=`<h2>${w.nav[4]}</h2>${logBox(w.releases)}`;if(i===5)c.innerHTML=`<h2>${w.nav[5]}</h2><div class="card">${table(['','',''],w.requests,'seedReq',w.open)}</div><div id="seedDetail"></div>`;document.querySelectorAll('.seedSlice').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('seed','slice_'+j);$('seedDetail').innerHTML=`<div class="notice">${w.slices[j][0]} · ${w.slices[j][1]} · ${w.slices[j][2]}</div>`});document.querySelectorAll('.seedReq').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('seed','request_'+j);$('seedDetail').innerHTML=`<div class="notice">${w.requests[j].join(' · ')}</div>`});if($('compareGen'))$('compareGen').onclick=()=>{markDetail('seed','serving_generation_compare');$('genDetail').innerHTML=`<div class="notice"><b>${w.generation.traffic}</b><p>${w.generation.detail}</p></div>`}}
function renderNear(i){const w=P.near,c=$('nearContent');if(i===0)c.innerHTML=`<h2>${w.title}</h2><p class="lead">${w.status}</p>${signalStrip('near')}${metrics(w.metrics)}${spark([83,84,85,84,82,72,69])}`;if(i===1)c.innerHTML=`<h2>${w.nav[1]}</h2>${fulfillmentSurface(w)}`;if(i===2)c.innerHTML=`<h2>${w.nav[2]}</h2><div class="card">${table(['',''],w.carriers)}</div>`;if(i===3)c.innerHTML=`<h2>${w.nav[3]}</h2><div class="panel">${w.routes}</div>`;if(i===4)c.innerHTML=`<h2>${w.nav[4]}</h2><div class="panel">${w.weather}</div>`;if(i===5)c.innerHTML=`<h2>${w.nav[5]}</h2><div class="card">${table(['','',''],w.cities,'nearCity',w.nested.city)}</div><div id="nearDetail"></div>`;document.querySelectorAll('.nearScan').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('near','scan_'+j);$('nearDetail').innerHTML=`<div class="notice">${w.nested.scan}: ${w.depots[j].join(' · ')}</div>`});document.querySelectorAll('.nearCity').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('near','city_'+j);$('nearDetail').innerHTML=`<div class="notice">${w.nested.city}: ${w.cities[j].join(' · ')}</div>`})}
function renderFar(i){const w=P.far,c=$('farContent');if(i===0)c.innerHTML=`<h2>${w.title}</h2><p class="lead">${w.status}</p>${signalStrip('far')}${metrics(w.metrics)}<div class="energyRoomTabs">${w.schedules.map((r,i)=>`<button class="energyRoom ${(S.selection.far||0)===i?'selected':''}" data-j="${i}"><b>${r[0]}</b><span>${r[1]}</span></button>`).join('')}</div>${energyTimeline()}<button id="interval" class="btn intervalBtn">${w.nested.interval}</button><div id="farDetail"></div>`;if(i===1)c.innerHTML=`<h2>${w.nav[1]}</h2><div class="panel">${w.weather}</div>`;if(i===2)c.innerHTML=`<h2>${w.nav[2]}</h2><div class="card">${table(['',''],w.schedules,'farRoom',w.nested.room)}</div><div id="farDetail"></div>`;if(i===3)c.innerHTML=`<h2>${w.nav[3]}</h2><div class="panel">${w.firmware}</div>`;if(i===4)c.innerHTML=`<h2>${w.nav[4]}</h2><div class="panel">${w.occupancy}</div>`;if(i===5)c.innerHTML=`<h2>${w.nav[5]}</h2><div class="panel">${w.tariff}</div>`;if($('interval'))$('interval').onclick=()=>{markDetail('far','interval_15m');$('farDetail').innerHTML='<div class="intervalDetail"><span>00:00</span><b>1.0</b><span>00:15</span><b>1.1</b><span>00:30</span><b>1.2</b><span>00:45</span><b>1.2</b><span>01:00</span><b>1.3</b></div>'};document.querySelectorAll('.farRoom').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('far','room_'+j);$('farDetail').innerHTML=`<div class="notice">${w.nested.room}: ${w.schedules[j].join(' · ')}</div>`})}
function renderActions(world){const w=P[world],el=$(world+'Actions'),a=S.action[world];if(!a){const order=S.actionOrder[world].length?S.actionOrder[world]:actionKeys(world);el.innerHTML=`<div class="actionHeader"><div><span class="meta">NEXT MOVE</span><h3>${w.actions.title}</h3></div><span class="actionHint">${S.detail[world].length} deep checks</span></div><div class="actionGrid">${order.map(key=>`<button class="btn worldAction" data-a="${key}"><span>${w.actions[key]}</span><i>→</i></button>`).join('')}</div>`;el.querySelectorAll('.worldAction').forEach(b=>b.onclick=()=>takeAction(world,b.dataset.a));return}const post=w.post;el.innerHTML=`${outcomePanel(world,a)}<div class="postActionBar"><button class="btn inspectCurrent">${post.inspect}</button><button class="btn switchAction">${post.switch}</button><button class="primary commitWorld">${post.commit}</button></div>`;const ins=el.querySelector('.inspectCurrent'),sw=el.querySelector('.switchAction'),co=el.querySelector('.commitWorld');ins.onclick=()=>{log('post_consequence_action',{world,action:'inspect_more',after:a});const target=world==='seed'?2:world==='near'?5:0;renderWorld(world,target,true)};sw.onclick=()=>{log('post_consequence_action',{world,action:'switch_mitigation',from:a});S.action[world]=null;S.worldState[world]={};delete document.body.dataset.action;refreshSignal(world);if(world==='seed'&&S.view.seed===2)renderSeed(2);if(world==='far'&&S.view.far===0)renderFar(0);renderActions(world);bindWorldMicroInteractions(world)};co.onclick=()=>commitWorld(world)}
function takeAction(world,a){
  S.action[world]=a;document.body.dataset.action=a;
  const w=P[world],state=S.worldState[world]||{};
  state.action=a;state.note=w.consequence[a];
  if(world==='seed')state.primary=a==='repin'?'−3.2%':a==='rollback'?'−5.4%':'−7.1%';
  else if(world==='near')state.primary=a==='reroute'?'+5.8%':a==='rollback'?'+6.7%':'+10.1%';
  else state.primary=a==='revert'?'+11%':a==='schedule'?'+14%':'+22%';
  S.worldState[world]=state;
  log('provisional_action',{world,action:a});
  log('consequence_exposed',{world,action:a,outcome:'partial'});
  log('post_action_check',{world,action:a,outcome:'partial'});
  refreshSignal(world);
  if(world==='seed'&&S.view.seed===2)renderSeed(2);
  if(world==='far'&&S.view.far===0)renderFar(0);
  renderActions(world);bindWorldMicroInteractions(world);
}
function commitWorld(world){log('commit',{world,action:S.action[world],views:[...S.views[world]],details:[...S.detail[world]]});if(world==='seed'){show('cue');return}if(world==='near'){show('far');renderWorld('far',0,true);return}finish()}
function finish(){log('session_complete',{market:P.market});window.PAJGoldenStudy?.complete({family:'PF02',instrument_version:'golden-pf02-v1',locale,market:P.market,world_variant:'golden-three-world-v1',terminal_action:S.action.far||'',events:S.events});$('trace').innerHTML=S.events.filter(e=>e.type!=='session_start').map(e=>`<div>#${e.seq} · ${e.t_ms}ms · ${e.type} · ${e.world||'journey'}${e.object?' / '+e.object:''}${e.action?' / '+e.action:''}</div>`).join('');const details=S.events.filter(e=>e.type==='open_detail').length,revisions=S.events.filter(e=>e.type==='post_consequence_action'&&e.action==='switch_mitigation').length;$('shape').innerHTML=`<div class="card"><span class="meta">${P.seed.brand}</span><div class="count">${S.detail.seed.length}</div></div><div class="card"><span class="meta">${P.near.brand}</span><div class="count">${S.detail.near.length}</div></div><div class="card"><span class="meta">${P.far.brand}</span><div class="count">${S.detail.far.length}</div></div><div class="row"><span class="pill">${C.details}: ${details}</span><span class="pill">${C.revisions}: ${revisions}</span></div>`;if(dev){$('research').classList.remove('hidden');$('research').innerHTML='<b>Research view</b><p>Seed incident → partial consequence → one structural sentence → fulfillment transfer → energy transfer. No participant-facing cause label or score is used.</p>'}show('done')}
function exportTrace(){const payload={instrument:'golden-pf02-v1',locale,market:P.market,events:S.events,views:S.views,details:S.detail,actions:S.action,world_state:S.worldState,action_order:S.actionOrder};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),a=document.createElement('a'),u=URL.createObjectURL(blob);a.href=u;a.download=`paj-pf02-${P.market}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(u),500)}
Object.entries(packs).forEach(([k,v])=>{const o=document.createElement('option');o.value=k;o.textContent=v.native;$('locale').appendChild(o)});$('locale').value=locale;$('locale').onchange=e=>{locale=e.target.value;P=packs[locale];C=chrome[locale];history.replaceState(null,'',`?locale=${encodeURIComponent(locale)}${dev?'&dev=1':''}`);S.view={seed:0,near:0,far:0};applyPack();show('intro')};$('start').onclick=startJourney;$('cueNext').onclick=()=>{log('minimal_intervention',{dose:'one_sentence'});show('near');renderWorld('near',0,true)};$('export').onclick=exportTrace;$('again').onclick=()=>location.reload();applyPack();
})();