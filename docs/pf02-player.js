(()=>{
const $=id=>document.getElementById(id);
document.body.dataset.instrument='pf02';
const packs=window.PAJ_PF02_PACKS;
const chrome=window.PAJ_PF02_CHROME;
const q=new URLSearchParams(location.search);
const dev=q.get('dev')==='1';
let locale=q.get('locale')&&packs[q.get('locale')]?q.get('locale'):'zh-CN';
let P=packs[locale],C=chrome[locale],pendingNextWorld='near';
const S={started:0,events:[],views:{seed:[],near:[],far:[]},detail:{seed:[],near:[],far:[]},action:{seed:null,near:null,far:null},actionOrder:{seed:[],near:[],far:[]},view:{seed:0,near:0,far:0},selection:{seed:null,near:null,far:null},worldState:{seed:{},near:{},far:{}},pressure:{seed:42,near:48,far:37},ping:{seed:0,near:0,far:0}}};
const now=()=>Math.round(performance.now()-S.started);
const log=(type,data={})=>S.events.push({seq:S.events.length+1,t_ms:now(),type,...data});
function show(id){document.querySelectorAll('.screen').forEach(s=>s.classList.add('hidden'));$(id).classList.remove('hidden');scrollTo(0,0)}
function active(el,i){
  const world=(el.id||'').replace('Nav','');
  el.querySelectorAll('button[data-i]').forEach(b=>{
    const n=Number(b.dataset.i),key='nav_'+n;
    b.classList.toggle('active',n===i);
    b.classList.toggle('visited',!!S.views[world]?.includes(key));
    b.classList.toggle('deep',S.detail[world]?.some(x=>x.includes('_'+n)||x===key));
  });
}
function markView(world,i){const key='nav_'+i;if(!S.views[world].includes(key)){S.views[world].push(key);bumpPressure(world,-2,'open_object')}log('open_object',{world,object:key});refreshSignal(world);refreshMissionHud(world);animateWorld(world,'investigate')}
function markDetail(world,key){if(!S.detail[world].includes(key)){S.detail[world].push(key);bumpPressure(world,-3,'open_detail')}log('open_detail',{world,object:key});refreshSignal(world);refreshMissionHud(world);animateWorld(world,'investigate')}
function metrics(rows){return `<div class="metricGrid">${rows.map(r=>`<div class="card metric"><span class="meta">${r[0]}</span><b>${r[1]}</b></div>`).join('')}</div>`}
function spark(values=[85,86,84,87,85,72,68]){return `<div class="spark">${values.map(v=>`<i style="height:${v}%"></i>`).join('')}</div>`}
function table(head,rows,detailClass='',detailLabel=''){return `<table class="table"><tr>${head.map(x=>`<th>${x}</th>`).join('')}${detailClass?'<th></th>':''}</tr>${rows.map((r,i)=>`<tr>${r.map(x=>`<td>${x}</td>`).join('')}${detailClass?`<td><button class="link ${detailClass}" data-j="${i}">${detailLabel||P.seed.open}</button></td>`:''}</tr>`).join('')}</table>`}
function logBox(rows){return `<div class="log">${rows.map(x=>`<div>${x}</div>`).join('')}</div>`}
function sliceBoard(w){
  return `<div class="sliceBoard">${w.slices.map((r,i)=>`<button class="sliceRow seedSlice" data-j="${i}">
    <span class="sliceName">${r[0]}</span><b>${r[1]}</b><span>${r[2]}</span><i>→</i>
  </button>`).join('')}</div><div id="seedDetail"></div>`;
}
function corpusBoard(w){
  return `<div class="corpusBoard">${w.corpus.map((r,i)=>`<div class="corpusMetric"><span>${r[0]}</span><b>${r[1]}</b><i>${i===0?'NEW':i===1?'UPDATED':'REMOVED'}</i></div>`).join('')}</div>`;
}
function releaseRail(w){
  return `<div class="releaseRail">${w.releases.map((x,i)=>`<div class="releaseEvent"><span class="releaseDot ${i===w.releases.length-1?'hot':''}"></span><b>${x}</b><small>0${i+1}</small></div>`).join('')}</div>`;
}
function requestBoard(w){
  return `<div class="requestBoard">${w.requests.map((r,i)=>`<button class="requestRow seedReq" data-j="${i}">
    <span class="requestQuery">${r[0]}</span><span class="requestType">${r[1]}</span><b>${r[2]}</b><i>↗</i>
  </button>`).join('')}</div><div id="seedDetail"></div>`;
}
function carrierBoard(w){
  return `<div class="carrierBoard">${w.carriers.map((r,i)=>`<div class="carrierRow"><span class="carrierBadge">0${i+1}</span><b>${r[0]}</b><strong>${r[1]}</strong><i style="--w:${55+i*18}%"></i></div>`).join('')}</div>`;
}
function contextPanel(label,text,tone=''){
  return `<div class="contextPanel ${tone}"><span>${label}</span><p>${text}</p></div>`;
}
function cityBoard(w){
  return `<div class="cityBoard">${w.cities.map((r,i)=>`<button class="cityRow nearCity" data-j="${i}">
    <span>${r[0]}</span><b>${r[1]}</b><small>${r[2]}</small><i>→</i>
  </button>`).join('')}</div><div id="nearDetail"></div>`;
}
function scheduleBoard(w){
  return `<div class="scheduleBoard">${w.schedules.map((r,i)=>`<button class="scheduleRow farRoom" data-j="${i}">
    <span class="roomIcon">${String(i+1).padStart(2,'0')}</span><b>${r[0]}</b><small>${r[1]}</small><i>→</i>
  </button>`).join('')}</div><div id="farDetail"></div>`;
}
function randomIndex(n){const a=new Uint32Array(1);crypto.getRandomValues(a);return a[0]%n}
function shuffled(items){const out=[...items];for(let i=out.length-1;i>0;i--){const j=randomIndex(i+1);[out[i],out[j]]=[out[j],out[i]]}return out}
function actionKeys(world){return world==='seed'?['rollback','repin','hold']:world==='near'?['rollback','reroute','hold']:['revert','schedule','hold']}
function resetActionOrders(){for(const world of ['seed','near','far'])S.actionOrder[world]=shuffled(actionKeys(world))}
function worldMode(world){return world==='seed'?'INCIDENT':world==='near'?'NETWORK':'ENERGY'}
function uiCopy(){
  if(locale==='zh-CN')return {
    objective:'任务目标',pressure:'现场压力',ping:'系统消息',
    obj:{seed:'判断检索质量下滑的主要原因，并先做一次可逆处置。',near:'在配送窗口继续收窄前，判断该回滚、改道还是继续观察。',far:'找出夜间基线异常的主要来源，并先改变一个变量。'},
    pingSeed:['SRE：serving-b 的异常请求仍在增加。','客服：长尾查询的失败反馈开始聚集。','发布系统：两个 serving pool 仍未完全收敛。'],
    pingNear:['运营：晚到订单正在继续累积。','站点：东侧区域的扫描等待仍偏高。','调度：新的改道窗口还剩一小段时间。'],
    pingFar:['家庭主机：夜间基线仍高于四周均值。','温控器：湿度补偿仍在工作。','能耗侧：下一小时将进入夜间高负荷窗口。'],
    pressureLow:'可控',pressureMid:'紧张',pressureHigh:'高压'
  };
  if(locale==='zh-TW')return {
    objective:'任務目標',pressure:'現場壓力',ping:'系統訊息',
    obj:{seed:'判斷檢索品質下滑的主要原因，並先做一次可逆處置。',near:'在配送窗口繼續收窄前，判斷該回滾、改道還是繼續觀察。',far:'找出夜間基線異常的主要來源，並先改變一個變數。'},
    pingSeed:['SRE：serving-b 的異常請求仍在增加。','客服：長尾查詢的失敗回饋開始聚集。','發佈系統：兩個 serving pool 仍未完全收斂。'],
    pingNear:['營運：晚到訂單正在繼續累積。','站點：東側區域的掃描等待仍偏高。','調度：新的改道路徑窗口正在縮小。'],
    pingFar:['家庭主機：夜間基線仍高於四週均值。','溫控器：濕度補償仍在工作。','能耗側：下一小時將進入夜間高負荷窗口。'],
    pressureLow:'可控',pressureMid:'緊張',pressureHigh:'高壓'
  };
  return {
    objective:'MISSION OBJECTIVE',pressure:'LIVE PRESSURE',ping:'SYSTEM PING',
    obj:{seed:'Identify the dominant retrieval failure mode and make one reversible mitigation.',near:'Choose rollback, reroute, or hold before the delivery window narrows further.',far:'Identify the source of the elevated night baseline and change one variable first.'},
    pingSeed:['SRE: anomalous requests on serving-b are still rising.','Support: long-tail search failures are clustering.','Release: serving pools have not fully converged.'],
    pingNear:['Ops: late orders are still accumulating.','Depot: east-side scan latency remains elevated.','Dispatch: the reroute window is narrowing.'],
    pingFar:['Home hub: night baseline remains above the four-week mean.','Thermostat: humidity compensation remains active.','Energy: the next hour enters the night-load window.'],
    pressureLow:'CONTROLLED',pressureMid:'TENSE',pressureHigh:'CRITICAL'
  };
}
function pressureLabel(v){
  const t=uiCopy(); return v>=72?t.pressureHigh:v>=52?t.pressureMid:t.pressureLow;
}
function missionHud(world){
  const t=uiCopy(),v=Math.max(0,Math.min(100,S.pressure[world]||0));
  const list=world==='seed'?t.pingSeed:world==='near'?t.pingNear:t.pingFar;
  const idx=Math.min(list.length-1,S.ping[world]||0);
  return `<section class="missionHud" data-pressure="${v}">
    <div class="missionObjective"><span>${t.objective}</span><b>${t.obj[world]}</b></div>
    <div class="missionPressure"><span>${t.pressure}</span><div class="pressureBar"><i style="width:${v}%"></i></div><b>${v} · ${pressureLabel(v)}</b></div>
    <div class="missionPing"><span>${t.ping}</span><b>${list[idx]}</b></div>
  </section>`;
}
function bumpPressure(world,delta,reason){
  S.pressure[world]=Math.max(18,Math.min(92,(S.pressure[world]||40)+delta));
  if(delta>0)S.ping[world]=Math.min(2,(S.ping[world]||0)+1);
  log('pressure_change',{world,delta,reason,pressure:S.pressure[world]});
}
function animateWorld(world,kind='pulse'){
  const content=$(world+'Content'); if(!content)return;
  content.classList.remove('worldMutate','worldInvestigate');
  void content.offsetWidth;
  content.classList.add(kind==='investigate'?'worldInvestigate':'worldMutate');
}
function refreshMissionHud(world){
  const main=$(world+'Content')?.closest('.main'),old=main?.querySelector('.missionHud');
  if(old)old.outerHTML=missionHud(world);
}
function renderIntroMission(){
  let el=document.querySelector('#intro .introMission');
  if(!el){el=document.createElement('div');el.className='introMission';$('introHelp').insertAdjacentElement('afterend',el)}
  const zh=locale.startsWith('zh');
  el.innerHTML=`<div class="introMissionStatus"><span class="liveDot"></span><b>${zh?'LIVE INCIDENT':'LIVE INCIDENT'}</b><small>02:13</small></div>
    <div class="introMissionGrid">
      <div><span>${zh?'当前状态':'STATUS'}</span><b>${zh?'生产质量异常，影响仍在扩大':'Production quality degraded and still spreading'}</b></div>
      <div><span>${zh?'你的角色':'ROLE'}</span><b>${zh?'接管现场，决定先看哪里、何时采取动作':'Take control, choose what to inspect, decide when to act'}</b></div>
      <div><span>${zh?'约束':'CONSTRAINT'}</span><b>${zh?'没有标准路径；你看到的结果会改变后续世界':'No required path; outcomes change what follows'}</b></div>
    </div>`;
}
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
  const sel=S.selection.near||0,state=S.worldState.near||{},action=state.action||'';
  const nodeClass=i=>{
    if(action==='reroute')return i===0?'recovered':i===1?'affected':'';
    if(action==='rollback')return i<2?'recovered':'';
    if(action==='hold')return 'watch';
    return '';
  };
  const linkOn=i=>action==='reroute'?i===0:action==='rollback'?i<2:sel===i;
  return `<div class="networkBoard ${action?'action-'+action:''}">
    <div class="networkHead"><span class="meta">NETWORK VIEW</span><b>${state.note||w.status}</b></div>
    <div class="networkLanes">
      <div class="networkCol"><span class="networkLabel">DEPOTS</span>${w.depots.map((r,i)=>`<button class="networkNode depotNode ${sel===i?'selected':''} ${nodeClass(i)}" data-j="${i}"><b>${r[0]}</b><small>${r[1]}</small></button>`).join('')}</div>
      <div class="networkLinks">${w.depots.map((_,i)=>`<i class="${linkOn(i)?'on':''} ${nodeClass(i)}"></i>`).join('')}</div>
      <div class="networkCol"><span class="networkLabel">REGIONS</span>${w.cities.map((r,i)=>`<button class="networkNode cityNode ${sel===i?'selected':''} ${nodeClass(i)}" data-j="${i}"><b>${r[0]}</b><small>${r[1]} · ${r[2]}</small></button>`).join('')}</div>
    </div>
    <div class="networkContext"><div><span>ROUTE</span><b>${w.routes}</b></div><div><span>WEATHER</span><b>${w.weather}</b></div></div>
    ${action?`<div class="networkImpact"><span>↳</span><b>${w.consequence[action]}</b></div>`:''}
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
    document.querySelectorAll('.depotNode').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);S.selection.near=j;markDetail('near','scan_'+j);renderWorld('near',1,false)});
    document.querySelectorAll('.cityNode').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);S.selection.near=j;markDetail('near','city_'+j);renderWorld('near',1,false)});
  }
  if(world==='far'){
    document.querySelectorAll('.energyRoom').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);S.selection.far=j;markDetail('far','room_'+j);renderWorld('far',0,false)});
  }
}
function applyPack(){P=packs[locale];C=chrome[locale];document.documentElement.lang=locale;$('market').textContent=P.market;$('introEy').textContent=P.intro.ey;$('introTitle').textContent=P.intro.title;$('introLead').textContent=P.intro.lead;$('start').textContent=P.intro.start;$('introHelp').textContent=P.intro.help;$('cueEy').textContent=P.cue.ey;$('cueLine').textContent=P.cue.line;$('cueNext').textContent=P.cue.next;$('seedCrumb').textContent=P.seed.crumb;$('nearCrumb').textContent=P.near.crumb;$('farCrumb').textContent=P.far.crumb;$('doneEy').textContent=P.done.ey;$('doneTitle').textContent=P.done.title;$('doneLead').textContent=P.done.lead;$('traceLabel').textContent=C.trace;$('journeyLabel').textContent=C.journey;$('export').textContent=P.done.export;$('again').textContent=P.done.again;renderIntroMission();renderNav('seed');renderNav('near');renderNav('far')}
function renderNav(world){const w=P[world],el=$(world+'Nav');el.innerHTML=`<div class="brand">${w.brand}</div>`+w.nav.map((n,i)=>`<button data-i="${i}"><span class="navMark"></span><span class="navLabel">${n}</span></button>`).join('');el.querySelectorAll('button[data-i]').forEach(b=>b.onclick=()=>renderWorld(world,Number(b.dataset.i),true));active(el,S.view[world])}
function startJourney(){S.started=performance.now();S.events=[];S.views={seed:[],near:[],far:[]};S.detail={seed:[],near:[],far:[]};S.action={seed:null,near:null,far:null};S.view={seed:0,near:0,far:0};S.selection={seed:null,near:null,far:null};S.worldState={seed:{},near:{},far:{}};S.pressure={seed:42,near:48,far:37};S.ping={seed:0,near:0,far:0};delete document.body.dataset.action;resetActionOrders();log('session_start',{locale,market:P.market});log('action_order',{orders:JSON.parse(JSON.stringify(S.actionOrder))});show('seed');renderWorld('seed',0,true)}
function decorateScene(world,i){
  document.body.dataset.world=world;
  const content=$(world+'Content'),main=content&&content.closest('.main'),w=P[world];
  if(!main||!w)return;
  let chrome=main.querySelector('.sceneChrome');
  if(!chrome){chrome=document.createElement('div');chrome.className='sceneChrome';main.insertBefore(chrome,main.querySelector('.crumb')?.nextSibling||main.firstChild)}
  const section=w.nav?.[i]||w.title||'';
  const mode=worldMode(world);
  chrome.innerHTML=`<div class="sceneIdentity"><span class="sceneDot"></span><b>${w.brand}</b></div><div class="sceneTrail">${section}</div><span class="sceneState">${mode}</span>`;
  let hud=main.querySelector('.missionHud');
  if(!hud){hud=document.createElement('div');hud.innerHTML=missionHud(world);main.insertBefore(hud.firstElementChild,content)}
  else hud.outerHTML=missionHud(world);
}
function renderWorld(world,i,track=false){S.view[world]=i;if(track)markView(world,i);active($(world+'Nav'),i);if(world==='seed')renderSeed(i);if(world==='near')renderNear(i);if(world==='far')renderFar(i);decorateScene(world,i);renderActions(world);bindWorldMicroInteractions(world)}
function renderSeed(i){const w=P.seed,c=$('seedContent');if(i===0)c.innerHTML=`<h2>${w.title}</h2><p class="lead">${w.status}</p>${signalStrip('seed')}${metrics(w.metrics)}${spark()}`;if(i===1)c.innerHTML=`<h2>${w.nav[1]}</h2>${sliceBoard(w)}`;if(i===2)c.innerHTML=`<h2>${w.nav[2]}</h2>${generationSurface(w)}`;if(i===3)c.innerHTML=`<h2>${w.nav[3]}</h2>${corpusBoard(w)}`;if(i===4)c.innerHTML=`<h2>${w.nav[4]}</h2>${releaseRail(w)}`;if(i===5)c.innerHTML=`<h2>${w.nav[5]}</h2>${requestBoard(w)}`;document.querySelectorAll('.seedSlice').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('seed','slice_'+j);$('seedDetail').innerHTML=`<div class="detailDrawer"><span>SLICE ${String(j+1).padStart(2,'0')}</span><h4>${w.slices[j][0]}</h4><div><b>${w.slices[j][1]}</b><small>${w.sliceCols[1]}</small><b>${w.slices[j][2]}</b><small>${w.sliceCols[2]}</small></div></div>`});document.querySelectorAll('.seedReq').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('seed','request_'+j);$('seedDetail').innerHTML=`<div class="detailDrawer"><span>REQUEST SAMPLE</span><h4>${w.requests[j][0]}</h4><div><b>${w.requests[j][1]}</b><small>segment</small><b>${w.requests[j][2]}</b><small>serving</small></div></div>`});if($('compareGen'))$('compareGen').onclick=()=>{markDetail('seed','serving_generation_compare');$('genDetail').innerHTML=`<div class="notice"><b>${w.generation.traffic}</b><p>${w.generation.detail}</p></div>`}}
function renderNear(i){const w=P.near,c=$('nearContent');if(i===0)c.innerHTML=`<h2>${w.title}</h2><p class="lead">${w.status}</p>${signalStrip('near')}${metrics(w.metrics)}${spark([83,84,85,84,82,72,69])}`;if(i===1)c.innerHTML=`<h2>${w.nav[1]}</h2>${fulfillmentSurface(w)}`;if(i===2)c.innerHTML=`<h2>${w.nav[2]}</h2>${carrierBoard(w)}`;if(i===3)c.innerHTML=`<h2>${w.nav[3]}</h2>${contextPanel('ROUTE CONDITIONS',w.routes,'routeContext')}`;if(i===4)c.innerHTML=`<h2>${w.nav[4]}</h2>${contextPanel('WEATHER WINDOW',w.weather,'weatherContext')}`;if(i===5)c.innerHTML=`<h2>${w.nav[5]}</h2>${cityBoard(w)}`;document.querySelectorAll('.nearScan').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('near','scan_'+j);$('nearDetail').innerHTML=`<div class="notice">${w.nested.scan}: ${w.depots[j].join(' · ')}</div>`});document.querySelectorAll('.nearCity').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('near','city_'+j);$('nearDetail').innerHTML=`<div class="detailDrawer light"><span>REGION DETAIL</span><h4>${w.cities[j][0]}</h4><div><b>${w.cities[j][1]}</b><small>delay</small><b>${w.cities[j][2]}</b><small>depot</small></div></div>`})}
function renderFar(i){const w=P.far,c=$('farContent');if(i===0)c.innerHTML=`<h2>${w.title}</h2><p class="lead">${w.status}</p>${signalStrip('far')}${metrics(w.metrics)}<div class="energyRoomTabs">${w.schedules.map((r,i)=>`<button class="energyRoom ${(S.selection.far||0)===i?'selected':''}" data-j="${i}"><b>${r[0]}</b><span>${r[1]}</span></button>`).join('')}</div>${energyTimeline()}<button id="interval" class="btn intervalBtn">${w.nested.interval}</button><div id="farDetail"></div>`;if(i===1)c.innerHTML=`<h2>${w.nav[1]}</h2>${contextPanel('OUTDOOR CONDITIONS',w.weather,'energyContext')}`;if(i===2)c.innerHTML=`<h2>${w.nav[2]}</h2>${scheduleBoard(w)}`;if(i===3)c.innerHTML=`<h2>${w.nav[3]}</h2>${contextPanel('THERMOSTAT FIRMWARE',w.firmware,'firmwareContext')}`;if(i===4)c.innerHTML=`<h2>${w.nav[4]}</h2>${contextPanel('OCCUPANCY',w.occupancy,'occupancyContext')}`;if(i===5)c.innerHTML=`<h2>${w.nav[5]}</h2>${contextPanel('TARIFF',w.tariff,'tariffContext')}`;if($('interval'))$('interval').onclick=()=>{markDetail('far','interval_15m');$('farDetail').innerHTML='<div class="intervalDetail"><span>00:00</span><b>1.0</b><span>00:15</span><b>1.1</b><span>00:30</span><b>1.2</b><span>00:45</span><b>1.2</b><span>01:00</span><b>1.3</b></div>'};document.querySelectorAll('.farRoom').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('far','room_'+j);$('farDetail').innerHTML=`<div class="detailDrawer light"><span>ROOM DETAIL</span><h4>${w.schedules[j][0]}</h4><p>${w.schedules[j][1]}</p></div>`})}
function renderActions(world){const w=P[world],el=$(world+'Actions'),a=S.action[world];if(!a){const order=S.actionOrder[world].length?S.actionOrder[world]:actionKeys(world);el.innerHTML=`<div class="actionHeader"><div><span class="meta">NEXT MOVE</span><h3>${w.actions.title}</h3></div><span class="actionHint">${S.detail[world].length} deep checks</span></div><div class="actionGrid">${order.map(key=>`<button class="btn worldAction" data-a="${key}"><span>${w.actions[key]}</span><i>→</i></button>`).join('')}</div>`;el.querySelectorAll('.worldAction').forEach(b=>b.onclick=()=>takeAction(world,b.dataset.a));return}const post=w.post;el.innerHTML=`${outcomePanel(world,a)}<div class="postActionBar"><button class="btn inspectCurrent">${post.inspect}</button><button class="btn switchAction">${post.switch}</button><button class="primary commitWorld">${post.commit}</button></div>`;const ins=el.querySelector('.inspectCurrent'),sw=el.querySelector('.switchAction'),co=el.querySelector('.commitWorld');ins.onclick=()=>{log('post_consequence_action',{world,action:'inspect_more',after:a});const target=world==='seed'?2:world==='near'?5:0;renderWorld(world,target,true)};sw.onclick=()=>{log('post_consequence_action',{world,action:'switch_mitigation',from:a});S.action[world]=null;S.worldState[world]={};bumpPressure(world,4,'switch_mitigation');delete document.body.dataset.action;refreshSignal(world);refreshMissionHud(world);if(world==='seed'&&S.view.seed===2)renderSeed(2);if(world==='near'&&S.view.near===1)renderNear(1);if(world==='far'&&S.view.far===0)renderFar(0);renderActions(world);bindWorldMicroInteractions(world)};co.onclick=()=>commitWorld(world)}
function takeAction(world,a){
  S.action[world]=a;document.body.dataset.action=a;
  const w=P[world],state=S.worldState[world]||{};
  state.action=a;state.note=w.consequence[a];
  if(world==='seed')state.primary=a==='repin'?'−3.2%':a==='rollback'?'−5.4%':'−7.1%';
  else if(world==='near')state.primary=a==='reroute'?'+5.8%':a==='rollback'?'+6.7%':'+10.1%';
  else state.primary=a==='revert'?'+11%':a==='schedule'?'+14%':'+22%';
  S.worldState[world]=state;
  bumpPressure(world,a==='hold'?8:-10,'action_'+a);
  log('provisional_action',{world,action:a});
  log('consequence_exposed',{world,action:a,outcome:'partial'});
  log('post_action_check',{world,action:a,outcome:'partial'});
  refreshSignal(world);refreshMissionHud(world);animateWorld(world,'pulse');
  if(world==='seed'&&S.view.seed===2)renderSeed(2);
  if(world==='near'&&S.view.near===1)renderNear(1);
  if(world==='far'&&S.view.far===0)renderFar(0);
  renderActions(world);bindWorldMicroInteractions(world);
}
function commitWorld(world){delete document.body.dataset.action;log('commit',{world,action:S.action[world],views:[...S.views[world]],details:[...S.detail[world]]});if(world==='seed'){
    const t=uiCopy(),a=S.action.seed;
    $('cueLine').textContent=locale.startsWith('zh')
      ? (a==='hold'?'你选择先观察。症状没有自己消失；下一个世界会把“等待”的代价放大。':'你刚让一个系统暂时稳定下来。下一个世界没有相同界面，但同样要求你分开“同时发生”和“真正驱动”。')
      : (a==='hold'?'You chose to wait. The symptom did not resolve itself; the next world makes the cost of waiting larger.':'You stabilized one system. The next world looks different, but still asks you to separate coincidence from cause.');
    show('cue');return
  }
  if(world==='near'){
    const a=S.action.near;
    const line=locale.startsWith('zh')
      ? (a==='reroute'?'改道让一部分网络恢复了，但不是所有节点。现在进入一个更安静、也更容易被忽略的系统。':'物流网络暂时停在一个不完全确定的状态。现在进入一个更安静、也更容易被忽略的系统。')
      : (a==='reroute'?'Rerouting restored part of the network, not all of it. Now enter a quieter system where drift is easier to miss.':'The delivery network remains only partially explained. Now enter a quieter system where drift is easier to miss.');
    $('cueEy').textContent=locale.startsWith('zh')?'第二次转场':'SECOND TRANSFER';
    $('cueLine').textContent=line;$('cueNext').textContent=locale.startsWith('zh')?'进入家庭能源系统 →':'Enter home energy →';
    show('cue');pendingNextWorld='far';return
  }
  finish()}
function finish(){
  log('session_complete',{market:P.market});
  window.PAJGoldenStudy?.complete({family:'PF02',instrument_version:'golden-pf02-v1',locale,market:P.market,world_variant:'golden-three-world-v1',terminal_action:S.action.far||'',events:S.events});
  $('trace').innerHTML=S.events.filter(e=>e.type!=='session_start').map(e=>`<div>#${e.seq} · ${e.t_ms}ms · ${e.type} · ${e.world||'journey'}${e.object?' / '+e.object:''}${e.action?' / '+e.action:''}</div>`).join('');
  const details=S.events.filter(e=>e.type==='open_detail').length,revisions=S.events.filter(e=>e.type==='post_consequence_action'&&e.action==='switch_mitigation').length;
  const worlds=['seed','near','far'];
  $('shape').innerHTML=`<div class="journeyReplay">${worlds.map((world,i)=>{
    const w=P[world],a=S.action[world],state=S.worldState[world]||{};
    return `<article class="replayStage"><div class="replayIndex">0${i+1}</div><div class="replayBrand">${w.brand}</div><h3>${w.title}</h3><div class="replayLine"><span>${C.details}</span><b>${S.detail[world].length}</b></div><div class="replayLine"><span>ACTION</span><b>${a?w.actions[a]:'—'}</b></div><div class="replayOutcome"><span>↳</span><p>${state.note||'—'}</p></div></article>`;
  }).join('<i class="replayArrow">→</i>')}</div><div class="replayTotals"><span class="pill">${C.details}: ${details}</span><span class="pill">${C.revisions}: ${revisions}</span></div>`;
  if(dev){$('research').classList.remove('hidden');$('research').innerHTML='<b>Research view</b><p>Seed incident → partial consequence → one structural sentence → fulfillment transfer → energy transfer. No participant-facing cause label or score is used.</p>'}
  show('done');
}
function exportTrace(){const payload={instrument:'golden-pf02-v1',locale,market:P.market,events:S.events,views:S.views,details:S.detail,actions:S.action,world_state:S.worldState,pressure:S.pressure,action_order:S.actionOrder};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),a=document.createElement('a'),u=URL.createObjectURL(blob);a.href=u;a.download=`paj-pf02-${P.market}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(u),500)}
Object.entries(packs).forEach(([k,v])=>{const o=document.createElement('option');o.value=k;o.textContent=v.native;$('locale').appendChild(o)});$('locale').value=locale;$('locale').onchange=e=>{locale=e.target.value;P=packs[locale];C=chrome[locale];history.replaceState(null,'',`?locale=${encodeURIComponent(locale)}${dev?'&dev=1':''}`);S.view={seed:0,near:0,far:0};S.worldState={seed:{},near:{},far:{}};delete document.body.dataset.action;applyPack();show('intro')};$('start').onclick=startJourney;$('cueNext').onclick=()=>{log('minimal_intervention',{dose:'one_sentence',next_world:pendingNextWorld});const next=pendingNextWorld;pendingNextWorld='near';show(next);renderWorld(next,0,true)};$('export').onclick=exportTrace;$('again').onclick=()=>location.reload();applyPack();
})();