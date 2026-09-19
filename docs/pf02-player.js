(()=>{
const $=id=>document.getElementById(id);
document.body.dataset.instrument='pf02';
const packs=window.PAJ_PF02_PACKS;
const chrome=window.PAJ_PF02_CHROME;
const q=new URLSearchParams(location.search);
const dev=q.get('dev')==='1';
let locale=q.get('locale')&&packs[q.get('locale')]?q.get('locale'):'zh-CN';
let P=packs[locale],C=chrome[locale],pendingNextWorld='near';
const S={started:0,events:[],views:{seed:[],near:[],far:[]},detail:{seed:[],near:[],far:[]},action:{seed:null,near:null,far:null},actionOrder:{seed:[],near:[],far:[]},view:{seed:0,near:0,far:0},selection:{seed:null,near:null,far:null},worldState:{seed:{},near:{},far:{}},pressure:{seed:42,near:48,far:37},ping:{seed:0,near:0,far:0},preview:{seed:null,near:null,far:null},flowReady:{seed:false,near:false,far:false}};
const now=()=>Math.round(performance.now()-S.started);
const log=(type,data={})=>S.events.push({seq:S.events.length+1,t_ms:now(),type,...data});
function show(id){document.querySelectorAll('.screen').forEach(s=>s.classList.add('hidden'));$(id).classList.remove('hidden');scrollTo(0,0)}
function enterNear(){show('near');renderWorld('near',0,true)}
function enterFar(){show('far');renderWorld('far',0,true)}
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
function sceneReaction(world,a){
  const zh=locale.startsWith('zh');
  if(!a)return '';
  if(world==='seed'){
    const text=a==='repin'
      ? (zh?'HOME AGENT：廚房窗已按 v12 重算 → 20%。室友沒有再次 override。':'HOME AGENT: kitchen recomputed on v12 → 20%. No new housemate override.')
      : a==='rollback'
        ? (zh?'室友：“欸？怎麼又全開了？” 全屋回到雨感之前。':'Housemate: “Why did everything reopen?” Whole home returned to pre-rain state.')
        : (zh?'18:44 · 你手動把廚房窗推開了一點。Agent 記錄到一次人工 override。':'18:44 · You manually cracked the kitchen window. Agent recorded a human override.');
    return `<div class="reactionLine"><time>NOW</time><b>${a==='repin'?'HOME AGENT':zh?'現場':'LIVE'}</b><p>${text}</p></div>`;
  }
  if(world==='near'){
    const text=a==='reroute'
      ? (zh?'19:07 · 即時倉已接單。群聊裡有人回：“那我們慢慢走，你們先弄。”':'19:07 · Instant store accepted. Someone replies: “We’ll walk slowly—you keep setting up.”')
      : a==='rollback'
        ? (zh?'19:07 · 你抓起鑰匙準備出門。室友接手了桌上的準備。':'19:07 · You grab your keys. Your housemate takes over the table prep.')
        : (zh?'19:30 · 門鈴響了。冰塊還沒到。':'19:30 · The doorbell rings. The ice is still not here.');
    return `<div class="deliveryReaction"><span>↳</span><p>${text}</p></div>`;
  }
  const text=a==='schedule'
    ? (zh?'00:49 · 客房風速降了一檔。朋友回：“這樣可以，謝啦。”':'00:49 · Guest-room fan drops one step. “This works, thanks.”')
    : a==='revert'
      ? (zh?'00:49 · 房間全部回到聚會前規則。客房的人又看了一眼溫控器。':'00:49 · Rooms return to pre-party rules. The guest looks at the thermostat again.')
      : (zh?'01:07 · 客房再次手動調低 1°C。第二次 override。':'01:07 · Guest lowers the setpoint by 1°C again. Second override.');
  return `<div class="reactionLine"><time>NOW</time><b>${zh?'夜間現場':'NIGHT'}</b><p>${text}</p></div>`;
}
function diegeticScene(world){
  const zh=locale.startsWith('zh'),state=S.worldState[world]||{},a=S.action[world];
  if(world==='seed'){
    const kitchen=a==='repin'?'20%':a==='rollback'?'35%':'0%';
    const conflict=a==='repin'?'1':a==='rollback'?'2':a==='hold'?'4':'3';
    return `<section class="diegeticScene homeScene">
      <div class="sceneTopline"><span>18:42</span><b>${zh?'雨正在下 · 朋友 38 分鐘後到':'Rain · guests in 38 min'}</b><small>${conflict} ${zh?'個未解決衝突':'unresolved conflicts'}</small></div>
      <div class="homePlan">
        <button class="roomTile kitchen hot sceneInspect" data-key="room_kitchen"><span>${zh?'廚房':'Kitchen'}</span><strong>${kitchen}</strong><small>${zh?'窗戶 · 油煙正在上升':'window · cooking now'}</small><i class="personDot you">${zh?'你':'YOU'}</i></button>
        <button class="roomTile living sceneInspect" data-key="room_living"><span>${zh?'客廳':'Living'}</span><strong>0%</strong><small>${zh?'窗戶 · 雨感鎖定':'window · rain lock'}</small><i class="personDot mate">${zh?'室友':'MATE'}</i></button>
        <button class="roomTile guest sceneInspect" data-key="room_guest"><span>${zh?'客房':'Guest'}</span><strong>0%</strong><small>${zh?'未授權自動開窗':'automation not authorized'}</small><i class="personDot guestP">${zh?'朋友':'GUEST'}</i></button>
        <button class="roomTile bedroom sceneInspect" data-key="room_bedroom"><span>${zh?'主臥':'Bedroom'}</span><strong>0%</strong><small>${zh?'關閉 · 無人在內':'closed · empty'}</small></button>
      </div>
      <div class="voiceThread">
        <div><time>18:39</time><b>${zh?'你':'You'}</b><p>“${zh?'廚房那扇別全關，留一點。':'Leave the kitchen window a little open.'}”</p></div>
        <div><time>18:40</time><b>${zh?'室友':'Housemate'}</b><p>“${zh?'下雨就都關了吧。':'If it rains, just close them all.'}”</p></div>
        <div class="agentLine"><time>18:41</time><b>HOME AGENT</b><p>${zh?'雨感觸發 → 全屋關窗已執行':'Rain sensor → whole-home close executed'}</p></div>
        <div class="conflictLine"><time>18:42</time><b>${zh?'現場':'LIVE'}</b><p>${zh?'廚房窗 0% · 你的指令沒有生效':'Kitchen 0% · your instruction did not take effect'}</p></div>
        ${sceneReaction('seed',a)}
      </div>
    </section>`;
  }
  if(world==='near'){
    const eta=a==='reroute'?13:a==='rollback'?12:a==='hold'?36:28;
    return `<section class="diegeticScene deliveryScene">
      <div class="sceneTopline"><span>19:05</span><b>${zh?'門鈴預計 25 分鐘後響':'Guests arrive in 25 min'}</b><small>${zh?'最晚 ETA +':''}${eta} min</small></div>
      <div class="deliveryTable">
        <button class="orderCard sceneInspect critical" data-key="order_drinks"><span>01</span><b>${zh?'冰塊 + 飲料':'Ice + drinks'}</b><strong>${a==='reroute'?'19:18':'19:33'}</strong><small>${a==='reroute'?(zh?'已改派即時倉':'rerouted to instant store'):(zh?'原配送延遲':'original courier delayed')}</small></button>
        <button class="orderCard sceneInspect warning" data-key="order_hotpot"><span>02</span><b>${zh?'火鍋底料':'Hotpot base'}</b><strong>19:47</strong><small>${zh?'後廚還有 7 單':'7 orders ahead'}</small></button>
        <button class="orderCard sceneInspect good" data-key="order_cake"><span>03</span><b>${zh?'蛋糕':'Cake'}</b><strong>19:28</strong><small>${zh?'基本準時':'on time'}</small></button>
      </div>
      <div class="messageThread">
        <div><span class="avatar">群</span><p><b>19:04 · ${zh?'朋友群':'Group chat'}</b><br>${zh?'“我們大概 19:30 到，你們開始了嗎？”':'“We should be there around 19:30. Started yet?”'}</p></div>
        <div><span class="avatar store">店</span><p><b>19:05 · ${zh?'便利店':'Store'}</b><br>${zh?'冰塊庫存剩 3 袋，可切即時倉。':'Only 3 bags of ice left; instant inventory available.'}</p></div>
      </div>
      ${sceneReaction('near',a)}
    </section>`;
  }
  const guestTemp=a==='schedule'?'25°C':a==='revert'?'26°C':'24°C';
  return `<section class="diegeticScene nightScene">
    <div class="sceneTopline"><span>00:47</span><b>${zh?'客廳已經安靜 · 四個人準備睡':'Living room quiet · four people settling in'}</b><small>${zh?'雨停了 · 濕度 82%':'rain stopped · humidity 82%'}</small></div>
    <div class="nightPlan">
      <button class="nightRoom sceneInspect" data-key="night_master"><span>${zh?'主臥':'Master'}</span><b>25°C</b><small>${zh?'你 · 優先安靜':'you · quiet first'}</small></button>
      <button class="nightRoom sceneInspect active" data-key="night_guest"><span>${zh?'客房':'Guest room'}</span><b>${guestTemp}</b><small>${a==='schedule'?(zh?'臨時規則 00:30–07:00':'temporary rule 00:30–07:00'):(zh?'剛發生人工 override':'manual override just happened')}</small></button>
      <button class="nightRoom sceneInspect" data-key="night_mate"><span>${zh?'次臥':'Second room'}</span><b>26°C</b><small>${zh?'室友 · 不希望夜間開窗':'housemate · no open window at night'}</small></button>
      <button class="nightRoom empty sceneInspect" data-key="night_living"><span>${zh?'客廳':'Living'}</span><b>OFF</b><small>${zh?'無人 · 已關機':'empty · off'}</small></button>
    </div>
    <div class="nightConversation">
      <div><time>00:41</time><b>${zh?'朋友':'Guest'}</b><p>“${zh?'這間有點悶，我可以調低一點嗎？':'It is a little stuffy. Can I turn it down?' }”</p></div>
      <div><time>00:43</time><b>${zh?'室友':'Housemate'}</b><p>“${zh?'夜裡別開窗，外面車太吵。':'Please do not open the window at night. Traffic is too loud.'}”</p></div>
      <div class="agentLine"><time>00:47</time><b>HOME AGENT</b><p>${zh?'未找到「留宿客人」的夜間優先級規則':'No night-priority rule exists for overnight guests'}</p></div>
      ${sceneReaction('far',a)}
    </div>
  </section>`;
}
function bindSceneInteractions(world){
  document.querySelectorAll('.sceneInspect').forEach(el=>el.onclick=()=>{
    const key=el.dataset.key||'scene_object';
    markDetail(world,key);
    el.classList.add('inspected');
    refreshFieldFeed(world);
  });
}
function randomIndex(n){const a=new Uint32Array(1);crypto.getRandomValues(a);return a[0]%n}
function shuffled(items){const out=[...items];for(let i=out.length-1;i>0;i--){const j=randomIndex(i+1);[out[i],out[j]]=[out[j],out[i]]}return out}
function actionKeys(world){return world==='seed'?['rollback','repin','hold']:world==='near'?['rollback','reroute','hold']:['revert','schedule','hold']}
function actionMeaning(world,key){
  const zh=locale.startsWith('zh');
  const map={
    seed:{
      rollback:zh?['撤销全屋动作','把刚才雨感触发的全屋关窗整体撤回','最快回到之前状态','会连没有问题的房间一起恢复']:['Undo whole-home action','Reverse the whole-home close triggered by rain','Fastest return to prior state','Also reverts rooms that were not the problem'],
      repin:zh?['只重算厨房窗','让厨房窗改用当前家庭策略，其他房间不动','改动最局部，也最贴近刚才冲突','室友仍可能继续 override']:['Recompute kitchen only','Apply the current household policy only to the kitchen window','Most targeted to the conflict you found','A housemate can still override'],
      hold:zh?['继续观察','暂时不改任何设备，继续听人和 Agent 的后续动作','不会引入新自动变化','冲突会继续变成人工 override']:['Hold','Change nothing and observe the next human/agent move','Introduces no new automation','Conflict may escalate into manual override']
    },
    near:{
      rollback:zh?['自己去取','取消两单配送，直接去附近店取','你能掌握冰块这条关键链路','你会离开家，其他准备暂停']:['Self-pickup','Cancel two deliveries and pick them up yourself','You directly control the critical supply','You leave home and pause other prep'],
      reroute:zh?['改派即时仓','只把冰块和饮料切到附近即时仓','最快救回最影响体验的一单','火锅底料仍可能迟到']:['Reroute to instant store','Move only drinks and ice to nearby instant inventory','Recovers the most visible missing item fastest','Hotpot base may still arrive late'],
      hold:zh?['继续等','保持三单原配送不变','不增加新成本或新路线','朋友到时关键物资可能还没到']:['Wait','Keep all three original deliveries unchanged','No extra cost or new route','Guests may arrive before key supplies']
    },
    far:{
      revert:zh?['恢复旧房间策略','回到聚会前每个房间各自的夜间规则','熟悉、稳定','留宿客人的偏好仍没有被建模']:['Restore prior room policy','Return to each room’s pre-party night rules','Familiar and stable','Guest preferences remain unmodeled'],
      schedule:zh?['创建客房临时规则','只给客房增加今晚 00:30–07:00 的临时策略','最小范围满足留宿需求','明早失效，之后仍要决定是否固化']:['Create guest-room override','Add a temporary 00:30–07:00 rule only for the guest room','Smallest scope that serves the guests','Expires in the morning; not yet a permanent rule'],
      hold:zh?['保持现状','不改任何夜间规则','不替任何人做更多决定','人会继续用手动 override 表达偏好']:['Hold','Keep current night rules unchanged','Avoids making another decision for people','Humans will keep expressing preferences via overrides']
    }
  };
  return map[world][key];
}
function evidenceSummary(world){
  const count=S.detail[world].length;
  const last=S.detail[world][S.detail[world].length-1];
  const zh=locale.startsWith('zh');
  if(!count)return zh?'你还没有打开深入证据。这个动作主要基于当前概览。':'You have not opened deep evidence yet; this action is based mostly on the overview.';
  return zh?`你已经深入查看 ${count} 个证据点，最近一个是 ${last}。`:`You opened ${count} deep evidence item(s); the latest was ${last}.`;
}
function decisionCard(world,key){
  const w=P[world],m=actionMeaning(world,key),zh=locale.startsWith('zh');
  return `<button class="decisionCard worldAction" data-a="${key}">
    <div class="decisionCardTop"><span class="decisionKey">${key.toUpperCase()}</span><b>${w.actions[key]}</b></div>
    <p class="decisionIntent">${m[1]}</p>
    <div class="decisionMeta">
      <div><span>${zh?'你在改变什么':'CHANGES'}</span><b>${m[0]}</b></div>
      <div><span>${zh?'直接收益':'UPSIDE'}</span><b>${m[2]}</b></div>
      <div><span>${zh?'主要风险':'RISK'}</span><b>${m[3]}</b></div>
    </div>
    <div class="decisionEvidence"><span>${zh?'基于当前证据':'EVIDENCE BASIS'}</span><small>${evidenceSummary(world)}</small></div>
    <i>→</i>
  </button>`;
}
function stateBefore(world){
  if(world==='seed')return {primary:'3 conflicts',secondary:'Kitchen 0%',status:'RULE CONFLICT'};
  if(world==='near')return {primary:'+28 min',secondary:'2 critical orders',status:'AT RISK'};
  return {primary:'+22%',secondary:'2 unresolved prefs',status:'SHARED STATE'};
}
function stateAfter(world,a){
  if(world==='seed'){
    if(a==='repin')return {primary:'1 conflict',secondary:'Kitchen 20%',status:'NEGOTIATED'};
    if(a==='rollback')return {primary:'2 conflicts',secondary:'All windows restored',status:'PARTIAL'};
    return {primary:'4 conflicts',secondary:'Kitchen 0%',status:'ESCALATING'};
  }
  if(world==='near'){
    if(a==='reroute')return {primary:'+13 min',secondary:'drinks recovered',status:'RECOVERING'};
    if(a==='rollback')return {primary:'+12 min',secondary:'self-pickup active',status:'PARTIAL'};
    return {primary:'+36 min',secondary:'guests arrived',status:'WORSENING'};
  }
  if(a==='revert')return {primary:'+14%',secondary:'old room policy',status:'PARTIAL'};
  if(a==='schedule')return {primary:'+9%',secondary:'guest rule active',status:'SETTLING'};
  return {primary:'+24%',secondary:'manual override',status:'UNCHANGED'};
}
function decisionDiff(world,a){
  const before=stateBefore(world),after=stateAfter(world,a),zh=locale.startsWith('zh');
  const m=actionMeaning(world,a);
  return `<div class="decisionDiff">
    <div class="diffHead"><span>${zh?'你刚刚改变了什么':'WHAT YOUR CHOICE CHANGED'}</span><b>${P[world].actions[a]}</b></div>
    <div class="diffGrid">
      <div class="diffSide before"><span>${zh?'选择前':'BEFORE'}</span><strong>${before.primary}</strong><small>${before.secondary}</small><em>${before.status}</em></div>
      <div class="diffArrow">→</div>
      <div class="diffSide after"><span>${zh?'选择后':'AFTER'}</span><strong>${after.primary}</strong><small>${after.secondary}</small><em>${after.status}</em></div>
    </div>
    <div class="diffWhy"><span>${zh?'为什么会这样':'WHY THIS MOVED'}</span><p>${m[1]}。 ${P[world].consequence[a]}</p></div>
  </div>`;
}
function predictedAfter(world,a){return stateAfter(world,a)}
function evidenceFit(world,a){
  const zh=locale.startsWith('zh'),items=S.detail[world]||[],last=items[items.length-1]||'';
  if(!last)return zh?'你还没有打开深入线索，这个决定主要基于现场概览。':'You have not opened a deep clue yet; this choice still rests mostly on the overview.';
  if(!zh)return 'The last clue you opened is directly relevant to this command, but it does not guarantee the outcome.';
  const maps={
    seed:{
      serving_generation_compare:{repin:'你刚看到主机和窗控网关的策略版本不一致；只重算厨房窗正好针对这个断点。',rollback:'策略版本不一致说明问题更像局部同步，而不是所有房间都错。',hold:'你已经看到一个明确的策略断点，继续等待只是把决定交回给人工 override。'},
      slice_:{repin:'你刚看到不同人的意图和权限并不对称；局部重算比全屋一起撤销更贴近这个冲突。',rollback:'冲突来自多个人，不代表全屋当前状态都应该保留。',hold:'你已经知道谁在冲突，等待会让未解决意图继续存在。'},
      request_:{repin:'语音片段显示“厨房留一点”是明确且局部的请求，局部重算可以直接回应它。',rollback:'语音里同时有“全关”，全量撤销会把两个意图一起打回原点。',hold:'已经出现清晰的人类请求，继续等待不会自动完成协商。'}
    },
    near:{
      scan_:{reroute:'你刚看到便利店即时仓的等待是可控的，改派能直接缩短冰块和饮料这条链路。',rollback:'自取能绕开骑手，但会让你本人离开家。',hold:'到店等待已经可见，原路径继续走只会消耗剩余时间。'},
      city_:{reroute:'你刚看到两单的延迟并不一样；只改冰块和饮料比全部取消更聚焦。',rollback:'如果你认为配送本身不再可信，自取是更强但更贵的控制。',hold:'你已经知道哪一单最危险，等待就是接受它继续晚到。'}
    },
    far:{
      room_:{schedule:'你刚看到客房的需求和主卧不同；临时客房规则正好只改变这一个空间。',revert:'旧策略适合常住的人，但没有覆盖留宿客人的偏好。',hold:'你已经看到房间偏好冲突，继续保持现状会让人继续手动 override。'},
      interval_15m:{schedule:'15 分钟现场变化显示异常集中在客房时段，临时规则直接作用在这里。',revert:'恢复旧策略会把所有房间一起带回聚会前状态。',hold:'现场已经出现人工 override，等待只会让这种补丁继续积累。'}
    }
  };
  const wm=maps[world]||{};const key=Object.keys(wm).find(k=>last===k||last.startsWith(k));
  return key&&wm[key]&&wm[key][a]?wm[key][a]:'你刚打开的线索和这个动作有关，但还不能单独证明它一定有效。';
}
function executionOverlay(world,a){
  const zh=locale.startsWith('zh'),w=P[world];
  return `<div class="executionOverlay">
    <div class="executionCore">
      <span class="executionPulse"></span>
      <small>${zh?'指令已接收':'COMMAND ACCEPTED'}</small>
      <h3>${w.actions[a]}</h3>
      <div class="executionSteps">
        <span class="on">${zh?'验证当前状态':'VERIFY STATE'}</span>
        <span>${zh?'应用变更':'APPLY CHANGE'}</span>
        <span>${zh?'等待遥测':'WAIT TELEMETRY'}</span>
      </div>
    </div>
  </div>`;
}
function playExecution(world,a){
  const main=$(world+'Content')?.closest('.main'); if(!main)return;
  const old=main.querySelector('.executionOverlay'); if(old)old.remove();
  main.insertAdjacentHTML('beforeend',executionOverlay(world,a));
  const overlay=main.querySelector('.executionOverlay'),steps=[...overlay.querySelectorAll('.executionSteps span')];
  document.body.classList.add('executingCommand');
  setTimeout(()=>steps[1]?.classList.add('on'),180);
  setTimeout(()=>steps[2]?.classList.add('on'),420);
  setTimeout(()=>{overlay?.classList.add('done');document.body.classList.remove('executingCommand')},700);
  setTimeout(()=>overlay?.remove(),980);
}
function commandDeck(world){
  const w=P[world],order=S.actionOrder[world].length?S.actionOrder[world]:actionKeys(world),zh=locale.startsWith('zh');
  const q=world==='seed'
    ? (zh?'厨房在做饭，雨感刚把全屋窗户关了。你现在怎么办？':'The kitchen is cooking and rain automation just closed every window. What do you do?')
    : world==='near'
      ? (zh?'朋友快到了，但冰块和火锅底料都要迟到。你怎么办？':'Guests are almost here, but the ice and hotpot base are late. What do you do?')
      : (zh?'所有人都想睡了，但客房闷、室友又不想夜里开窗。你怎么办？':'Everyone wants to sleep, but the guest room is stuffy and your housemate does not want windows open. What do you do?');
  const plain={
    seed:{
      repin:zh?'只开厨房一点':'Open kitchen a little',
      rollback:zh?'全部恢复到刚才':'Restore everything',
      hold:zh?'先等等':'Wait a bit'
    },
    near:{
      reroute:zh?'把冰块改派':'Reroute the ice',
      rollback:zh?'自己去取':'Pick it up myself',
      hold:zh?'继续等':'Keep waiting'
    },
    far:{
      schedule:zh?'只给客房设临时规则':'Guest-room rule only',
      revert:zh?'恢复原来的夜间设置':'Restore old night settings',
      hold:zh?'今晚先不改':'Leave it for tonight'
    }
  };
  return `<div class="instantDecision">
    <h3>${q}</h3>
    <div class="instantChoices">
      ${order.map(key=>`<button class="instantChoice" data-a="${key}"><b>${plain[world][key]}</b></button>`).join('')}
    </div>
  </div>`;
}
function previewAction(world,a){
  S.preview[world]=a;
  log('action_preview',{world,action:a});
  renderActions(world);
  refreshFieldFeed(world);
  animateWorld(world,'investigate');
}
function fieldFeed(world){
  const zh=locale.startsWith('zh'),w=P[world],p=S.preview[world],a=S.action[world],state=S.worldState[world]||{};
  const lines=[];
  lines.push(zh?'系统在线 · 实时状态同步':'SYSTEM ONLINE · LIVE STATE SYNC');
  if(S.detail[world].length)lines.push((zh?'已确认线索 ':'Evidence confirmed ')+S.detail[world].slice(-1)[0]);
  if(p&&!a)lines.push((zh?'正在预演 ':'Simulating ')+w.actions[p]);
  if(a)lines.push((zh?'已执行 ':'Executed ')+w.actions[a]);
  if(state.note)lines.push(state.note);
  return `<aside class="fieldFeed"><div class="fieldFeedHead"><span class="feedPulse"></span><b>${zh?'现场通信':'FIELD FEED'}</b><small class="missionClock">${missionClock()}</small></div><div class="fieldFeedBody">${lines.map((x,i)=>`<div><span>0${i+1}</span><p>${x}</p></div>`).join('')}</div></aside>`;
}
function refreshFieldFeed(world){
  const main=$(world+'Content')?.closest('.main'); if(!main)return;
  let old=main.querySelector('.fieldFeed');
  if(old)old.outerHTML=fieldFeed(world);
  else main.insertAdjacentHTML('beforeend',fieldFeed(world));
}

function resetActionOrders(){for(const world of ['seed','near','far'])S.actionOrder[world]=shuffled(actionKeys(world))}
function worldMode(world){return world==='seed'?'SHARED HOME':world==='near'?'DELIVERY': 'NIGHT'}
function uiCopy(){
  if(locale==='zh-CN')return {
    objective:'任务目标',pressure:'现场压力',ping:'系统消息',
    obj:{seed:'让这个家在多人、权限和自动规则冲突下先稳定下来。',near:'朋友到门口前，先救回最影响今晚体验的那一单。',far:'在不替所有人做主的前提下，留下一个今晚能睡的夜间规则。'},
    pingSeed:['厨房窗仍是 0%，你刚才的“留一点”没有生效。','室友没有再说话，但全屋关闭规则仍在生效。','窗控网关仍在执行昨晚的旧策略。'],
    pingNear:['群聊：朋友说“还有 20 分钟到”。','便利店：冰块库存只剩最后 3 袋。','火锅店：你的订单前面还有 7 单。'],
    pingFar:['客房有人刚手动调低了温度。','室友发来一句：夜里别开窗，太吵。','Agent 还没有留宿客人的长期夜间规则。'],
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
function missionClock(){
  if(!S.started)return '00:00';
  const sec=Math.max(0,Math.floor((performance.now()-S.started)/1000));
  return String(Math.floor(sec/60)).padStart(2,'0')+':'+String(sec%60).padStart(2,'0');
}
function tickMissionClock(){
  document.querySelectorAll('.missionClock').forEach(el=>el.textContent=missionClock());
}
setInterval(tickMissionClock,1000);
function showSystemPing(world){
  const main=$(world+'Content')?.closest('.main'); if(!main)return;
  const t=uiCopy(),list=world==='seed'?t.pingSeed:world==='near'?t.pingNear:t.pingFar;
  const idx=Math.min(list.length-1,S.ping[world]||0);
  let toast=main.querySelector('.systemPingToast');
  if(!toast){toast=document.createElement('div');toast.className='systemPingToast';main.appendChild(toast)}
  toast.innerHTML='<span>'+t.ping+'</span><b>'+list[idx]+'</b>';
  toast.classList.remove('show');void toast.offsetWidth;toast.classList.add('show');
  clearTimeout(toast._hideTimer);toast._hideTimer=setTimeout(()=>toast.classList.remove('show'),2600);
}
function missionHud(world){
  const t=uiCopy(),v=Math.max(0,Math.min(100,S.pressure[world]||0));
  const list=world==='seed'?t.pingSeed:world==='near'?t.pingNear:t.pingFar;
  const idx=Math.min(list.length-1,S.ping[world]||0);
  return `<section class="missionHud" data-pressure="${v}">
    <div class="missionObjective"><span>${t.objective}</span><b>${t.obj[world]}</b></div>
    <div class="missionPressure"><span>${t.pressure} · <em class="missionClock">${missionClock()}</em></span><div class="pressureBar"><i style="width:${v}%"></i></div><b>${v} · ${pressureLabel(v)}</b></div>
    <div class="missionPing"><span>${t.ping}</span><b>${list[idx]}</b></div>
  </section>`;
}
function bumpPressure(world,delta,reason){
  S.pressure[world]=Math.max(18,Math.min(92,(S.pressure[world]||40)+delta));
  if(delta>0)S.ping[world]=Math.min(2,(S.ping[world]||0)+1);
  log('pressure_change',{world,delta,reason,pressure:S.pressure[world]});if(delta!==0)showSystemPing(world);
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
      <div><span>${zh?'当前状态':'STATUS'}</span><b>${zh?'朋友快到了，家里的 Agent、权限和人的意图已经开始互相打架':'Guests are arriving soon, and agent rules, authority, and human intent are already colliding'}</b></div>
      <div><span>${zh?'你的角色':'ROLE'}</span><b>${zh?'把这个晚上撑过去：先看谁、先信谁、先改哪里':'Get the night through: decide who to inspect, trust, and change first'}</b></div>
      <div><span>${zh?'约束':'CONSTRAINT'}</span><b>${zh?'没有标准答案；人的 override、沉默和让步都会留下证据':'No single correct path; overrides, silence, and concessions all become evidence'}</b></div>
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
    <div class="generationHead"><div><span class="meta">POLICY NODES</span><h3>${w.generation.expected}</h3></div><span class="generationTraffic">${state.note||w.generation.traffic}</span></div>
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
    <div class="networkHead"><span class="meta">DELIVERY MAP</span><b>${state.note||w.status}</b></div>
    <div class="networkLanes">
      <div class="networkCol"><span class="networkLabel">SOURCES</span>${w.depots.map((r,i)=>`<button class="networkNode depotNode ${sel===i?'selected':''} ${nodeClass(i)}" data-j="${i}"><b>${r[0]}</b><small>${r[1]}</small></button>`).join('')}</div>
      <div class="networkLinks">${w.depots.map((_,i)=>`<i class="${linkOn(i)?'on':''} ${nodeClass(i)}"></i>`).join('')}</div>
      <div class="networkCol"><span class="networkLabel">ORDERS</span>${w.cities.map((r,i)=>`<button class="networkNode cityNode ${sel===i?'selected':''} ${nodeClass(i)}" data-j="${i}"><b>${r[0]}</b><small>${r[1]} · ${r[2]}</small></button>`).join('')}</div>
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
    document.querySelectorAll('.roomTile').forEach(b=>b.onclick=()=>{markDetail('seed',b.dataset.clue);$('seedDetail').innerHTML=`<div class="sceneInspect"><span>LIVE OBJECT</span><b>${b.querySelector('span')?.textContent||''}</b><p>${b.querySelector('small')?.textContent||''}</p></div>`});
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
function applyPack(){P=packs[locale];C=chrome[locale];document.documentElement.lang=locale;$('market').textContent=P.market;$('introEy').textContent=P.intro.ey;$('introTitle').textContent=P.intro.title;$('introLead').textContent=P.intro.lead;$('start').textContent=P.intro.start;$('introHelp').textContent=P.intro.help;$('cueEy').textContent=P.cue.ey;$('cueLine').textContent=P.cue.line;$('cueNext').textContent=P.cue.next;$('seedCrumb').textContent=P.seed.crumb;$('nearCrumb').textContent=P.near.crumb;$('farCrumb').textContent=P.far.crumb;$('doneEy').textContent=P.done.ey;$('doneTitle').textContent=P.done.title;$('doneLead').textContent=P.done.lead;$('traceLabel').textContent=C.trace;$('journeyLabel').textContent=C.journey;$('export').textContent=P.done.export;$('again').textContent=P.done.again;renderNav('seed');renderNav('near');renderNav('far')}
function renderNav(world){const w=P[world],el=$(world+'Nav');el.innerHTML=`<div class="brand">${w.brand}</div>`+w.nav.map((n,i)=>`<button data-i="${i}"><span class="navMark"></span><span class="navLabel">${n}</span></button>`).join('');el.querySelectorAll('button[data-i]').forEach(b=>b.onclick=()=>renderWorld(world,Number(b.dataset.i),true));active(el,S.view[world])}
function startJourney(){S.started=performance.now();S.events=[];S.views={seed:[],near:[],far:[]};S.detail={seed:[],near:[],far:[]};S.action={seed:null,near:null,far:null};S.view={seed:0,near:0,far:0};S.selection={seed:null,near:null,far:null};S.worldState={seed:{},near:{},far:{}};S.pressure={seed:42,near:48,far:37};S.ping={seed:0,near:0,far:0};S.preview={seed:null,near:null,far:null};S.flowReady={seed:false,near:false,far:false};delete document.body.dataset.action;resetActionOrders();log('session_start',{locale,market:P.market});log('action_order',{orders:JSON.parse(JSON.stringify(S.actionOrder))});show('seed');renderWorld('seed',0,true)}
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
function renderWorld(world,i,track=false){S.view[world]=i;if(track)markView(world,i);active($(world+'Nav'),i);if(world==='seed')renderSeed(i);if(world==='near')renderNear(i);if(world==='far')renderFar(i);decorateScene(world,i);renderActions(world);bindWorldMicroInteractions(world);bindSceneInteractions(world);refreshFieldFeed(world)}
function homeLiveScene(){
  const a=S.action.seed,state=S.worldState.seed||{},zh=locale.startsWith('zh');
  const kitchen=a==='repin'?'20%':a==='rollback'?'45%':'0%';
  const conflict=a==='repin'?1:a==='rollback'?2:a==='hold'?4:3;
  return `<div class="diegeticScene homeScene">
    <div class="sceneTopline"><span>18:42 · ${zh?'雨正在下':'RAIN ACTIVE'}</span><b>${zh?conflict+' 个冲突未解决':conflict+' unresolved conflicts'}</b></div>
    <div class="homeStage">
      <button class="roomTile living" data-clue="room_living"><span>${zh?'客厅':'LIVING'}</span><small>${zh?'窗 0% · 无人':'window 0% · empty'}</small><i class="roomGlow"></i></button>
      <button class="roomTile kitchen hot" data-clue="room_kitchen"><span>${zh?'厨房':'KITCHEN'}</span><small>${zh?'窗 '+kitchen+' · 正在做饭':'window '+kitchen+' · cooking'}</small><strong class="windowGauge"><i style="width:${kitchen}"></i></strong></button>
      <button class="roomTile bedroom" data-clue="room_bedroom"><span>${zh?'卧室':'BEDROOM'}</span><small>${zh?'未授权自动控制':'automation not authorized'}</small><i class="lockMark">⌁</i></button>
      <div class="rainSensor"><span></span><b>${zh?'雨感 ACTIVE':'RAIN SENSOR ACTIVE'}</b></div>
      <div class="agentNode"><span>AI</span><b>${zh?'执行：全屋关窗':'Executed: close all windows'}</b></div>
      <div class="voiceBubble you">${zh?'你：厨房那扇别全关。':'You: Don’t close the kitchen one all the way.'}</div>
      <div class="voiceBubble mate">${zh?'室友：下雨就都关了。':'Housemate: If it rains, close them all.'}</div>
      <div class="voiceBubble guest">${zh?'留宿朋友：……':'Guest: …'}</div>
      <svg class="homeLinks" viewBox="0 0 1000 520" preserveAspectRatio="none" aria-hidden="true">
        <path d="M500 82 C500 150 500 170 500 220"></path>
        <path d="M500 220 C350 245 280 280 220 320"></path>
        <path d="M500 220 C505 270 515 310 520 350"></path>
        <path d="M500 220 C650 250 740 290 790 335"></path>
      </svg>
    </div>
    <div class="scenePrompt"><span>${zh?'现在发生了什么':'WHAT IS HAPPENING'}</span><p>${P.seed.status}</p></div>
  </div><div id="seedDetail"></div>`;
}
function deliveryLiveScene(){
  const a=S.action.near,zh=locale.startsWith('zh');
  const ice=a==='reroute'?'13 min':a==='rollback'?'12 min':a==='hold'?'+36 min':'+28 min';
  return `<div class="diegeticScene deliveryScene">
    <div class="phoneShell">
      <div class="phoneHead"><span>19:05</span><b>${zh?'朋友 25 分钟后到':'Guests in 25 min'}</b><i>●●●</i></div>
      <div class="orderHero"><span>${zh?'今晚还缺的东西':'STILL MISSING TONIGHT'}</span><strong>2</strong><small>${zh?'关键订单':'critical orders'}</small></div>
      <button class="orderLive nearCity" data-j="0"><span>🧊</span><div><b>${zh?'冰块 + 饮料':'Ice + drinks'}</b><small>${zh?'便利店即时仓':'instant store'}</small></div><strong>${ice}</strong></button>
      <button class="orderLive nearCity" data-j="1"><span>🍲</span><div><b>${zh?'火锅底料':'Hotpot base'}</b><small>${zh?'后厨排队':'kitchen queue'}</small></div><strong>+19 min</strong></button>
      <button class="orderLive nearCity ok" data-j="2"><span>🎂</span><div><b>${zh?'蛋糕':'Cake'}</b><small>${zh?'已取货':'picked up'}</small></div><strong>+3 min</strong></button>
      <div class="chatIncoming"><span>${zh?'群聊':'GROUP CHAT'}</span><b>${zh?'“我们差不多 20 分钟到 👀”':'“We’re about 20 min away 👀”'}</b></div>
    </div>
    <div class="deliveryMapLive">
      <div class="mapRoad r1"></div><div class="mapRoad r2"></div><div class="mapRoad r3"></div>
      <span class="pin store">店</span><span class="pin home">家</span><span class="pin rider">骑</span>
      <div class="rainPatch"></div>
      <p>${P.near.routes}</p>
    </div>
  </div><div id="nearDetail"></div>`;
}
function nightLiveScene(){
  const a=S.action.far,zh=locale.startsWith('zh');
  const guest=a==='schedule'?'25.5°C · temp rule':a==='revert'?'default rule':'24°C manual';
  return `<div class="diegeticScene nightScene">
    <div class="nightHeader"><span>00:47</span><b>${zh?'所有人都想睡了':'Everyone wants to sleep'}</b><small>${zh?'雨已停 · 广州 27°C / 82%':'rain stopped · 27°C / 82%'}</small></div>
    <div class="nightRooms">
      <button class="nightRoom energyRoom" data-j="0"><span>${zh?'主卧':'YOUR ROOM'}</span><b>25°C</b><small>${zh?'你：优先安静':'You: quiet first'}</small><i>zzz</i></button>
      <button class="nightRoom energyRoom guestRoom" data-j="1"><span>${zh?'客房':'GUEST ROOM'}</span><b>${guest}</b><small>${zh?'朋友：别直吹，但有点闷':'Guest: no direct air, but stuffy'}</small><i>↺</i></button>
      <button class="nightRoom energyRoom" data-j="2"><span>${zh?'客厅':'LIVING'}</span><b>OFF</b><small>${zh?'无人':'empty'}</small><i>—</i></button>
    </div>
    <div class="nightConversation">
      <div><span>00:41</span><p>${zh?'室友：夜里别开窗，外面太吵。':'Housemate: Don’t open windows at night, it’s too noisy.'}</p></div>
      <div><span>00:44</span><p>${zh?'客房：温度手动调低 1°C。':'Guest room: temperature manually lowered by 1°C.'}</p></div>
      <div><span>00:47</span><p>${zh?'Agent：检测到多人夜间规则冲突。':'Agent: multi-person night-rule conflict detected.'}</p></div>
    </div>
  </div><div id="farDetail"></div>`;
}
function renderSeed(i){const w=P.seed,c=$('seedContent');if(i===0)c.innerHTML=`${homeLiveScene()}`;if(i===1)c.innerHTML=`<h2>${w.nav[1]}</h2>${sliceBoard(w)}`;if(i===2)c.innerHTML=`<h2>${w.nav[2]}</h2>${generationSurface(w)}`;if(i===3)c.innerHTML=`<h2>${w.nav[3]}</h2>${corpusBoard(w)}`;if(i===4)c.innerHTML=`<h2>${w.nav[4]}</h2>${releaseRail(w)}`;if(i===5)c.innerHTML=`<h2>${w.nav[5]}</h2>${requestBoard(w)}`;document.querySelectorAll('.seedSlice').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('seed','slice_'+j);$('seedDetail').innerHTML=`<div class="detailDrawer"><span>SLICE ${String(j+1).padStart(2,'0')}</span><h4>${w.slices[j][0]}</h4><div><b>${w.slices[j][1]}</b><small>${w.sliceCols[1]}</small><b>${w.slices[j][2]}</b><small>${w.sliceCols[2]}</small></div></div>`});document.querySelectorAll('.seedReq').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('seed','request_'+j);$('seedDetail').innerHTML=`<div class="detailDrawer"><span>REQUEST SAMPLE</span><h4>${w.requests[j][0]}</h4><div><b>${w.requests[j][1]}</b><small>segment</small><b>${w.requests[j][2]}</b><small>serving</small></div></div>`});if($('compareGen'))$('compareGen').onclick=()=>{markDetail('seed','serving_generation_compare');$('genDetail').innerHTML=`<div class="notice"><b>${w.generation.traffic}</b><p>${w.generation.detail}</p></div>`}}
function renderNear(i){const w=P.near,c=$('nearContent');if(i===0)c.innerHTML=`${deliveryLiveScene()}`;if(i===1)c.innerHTML=`<h2>${w.nav[1]}</h2>${fulfillmentSurface(w)}`;if(i===2)c.innerHTML=`<h2>${w.nav[2]}</h2>${carrierBoard(w)}`;if(i===3)c.innerHTML=`<h2>${w.nav[3]}</h2>${contextPanel('DELIVERY ROUTE',w.routes,'routeContext')}`;if(i===4)c.innerHTML=`<h2>${w.nav[4]}</h2>${contextPanel('RAIN WINDOW',w.weather,'weatherContext')}`;if(i===5)c.innerHTML=`<h2>${w.nav[5]}</h2>${cityBoard(w)}`;document.querySelectorAll('.nearScan').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('near','scan_'+j);$('nearDetail').innerHTML=`<div class="notice">${w.nested.scan}: ${w.depots[j].join(' · ')}</div>`});document.querySelectorAll('.nearCity').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('near','city_'+j);$('nearDetail').innerHTML=`<div class="detailDrawer light"><span>REGION DETAIL</span><h4>${w.cities[j][0]}</h4><div><b>${w.cities[j][1]}</b><small>delay</small><b>${w.cities[j][2]}</b><small>depot</small></div></div>`})}
function renderFar(i){const w=P.far,c=$('farContent');if(i===0)c.innerHTML=`<h2>${w.title}</h2><p class="lead">${w.status}</p>${diegeticScene('far')}${signalStrip('far')}<div class="energyRoomTabs">${w.schedules.map((r,i)=>`<button class="energyRoom ${(S.selection.far||0)===i?'selected':''}" data-j="${i}"><b>${r[0]}</b><span>${r[1]}</span></button>`).join('')}</div>${energyTimeline()}<button id="interval" class="btn intervalBtn">${w.nested.interval}</button><div id="farDetail"></div>`;if(i===1)c.innerHTML=`<h2>${w.nav[1]}</h2>${contextPanel('OUTDOOR NIGHT',w.weather,'energyContext')}`;if(i===2)c.innerHTML=`<h2>${w.nav[2]}</h2>${scheduleBoard(w)}`;if(i===3)c.innerHTML=`<h2>${w.nav[3]}</h2>${contextPanel('AGENT POLICY',w.firmware,'firmwareContext')}`;if(i===4)c.innerHTML=`<h2>${w.nav[4]}</h2>${contextPanel('WHO SLEEPS WHERE',w.occupancy,'occupancyContext')}`;if(i===5)c.innerHTML=`<h2>${w.nav[5]}</h2>${contextPanel('NIGHT LOAD',w.tariff,'tariffContext')}`;if($('interval'))$('interval').onclick=()=>{markDetail('far','interval_15m');$('farDetail').innerHTML='<div class="intervalDetail"><span>00:00</span><b>1.0</b><span>00:15</span><b>1.1</b><span>00:30</span><b>1.2</b><span>00:45</span><b>1.2</b><span>01:00</span><b>1.3</b></div>'};document.querySelectorAll('.farRoom').forEach(b=>b.onclick=()=>{const j=Number(b.dataset.j);markDetail('far','room_'+j);$('farDetail').innerHTML=`<div class="detailDrawer light"><span>ROOM DETAIL</span><h4>${w.schedules[j][0]}</h4><p>${w.schedules[j][1]}</p></div>`})}
function visibleActionLabel(world,key){
  const zh=locale.startsWith('zh');
  if(!zh)return P[world].actions[key];
  const labels={
    seed:{rollback:'撤销刚才的全屋关窗',repin:'只把厨房窗打开到 20%',hold:'先不动'},
    near:{rollback:'我自己去附近拿',reroute:'只改派冰块和饮料',hold:'继续等'},
    far:{revert:'恢复原来的夜间规则',schedule:'只给客房临时调节',hold:'先不动'}
  };
  return labels[world][key];
}
function renderActions(world){
  const w=P[world],el=$(world+'Actions'),a=S.action[world],zh=locale.startsWith('zh');
  if(!a){
    el.innerHTML=commandDeck(world);
    el.querySelectorAll('.instantChoice').forEach(b=>b.onclick=()=>takeAction(world,b.dataset.a));
    return;
  }
  const nextLabel=world==='far'
    ? (zh?'看看今晚最后留下了什么 →':'See what this night left behind →')
    : (zh?'继续今晚 →':'Continue the night →');
  el.innerHTML=`<div class="instantResult">
      <span>${zh?'刚刚发生了':'WHAT HAPPENED'}</span>
      <p>${w.consequence[a]}</p>
    </div>
    <div class="instantNext">
      <button class="textUndo">${zh?'换一个选择':'Choose differently'}</button>
      <button class="primary commitWorld">${nextLabel}</button>
    </div>`;
  el.querySelector('.textUndo').onclick=()=>{
    log('post_consequence_action',{world,action:'switch_mitigation',from:a});
    S.action[world]=null;S.preview[world]=null;S.worldState[world]={};
    bumpPressure(world,4,'switch_mitigation');
    delete document.body.dataset.action;
    renderWorld(world,0,false);
  };
  el.querySelector('.commitWorld').onclick=()=>commitWorld(world);
}
function takeAction(world,a){
  playExecution(world,a);
  S.action[world]=a;S.preview[world]=null;document.body.dataset.action=a;
  const w=P[world],state=S.worldState[world]||{};
  state.action=a;state.note=w.consequence[a];
  state.primary=stateAfter(world,a).primary;
  S.worldState[world]=state;
  bumpPressure(world,a==='hold'?8:-10,'action_'+a);
  log('provisional_action',{world,action:a});
  log('consequence_exposed',{world,action:a,outcome:'partial'});
  log('post_action_check',{world,action:a,outcome:'partial'});
  refreshSignal(world);refreshMissionHud(world);animateWorld(world,'pulse');
  if(world==='seed'&&S.view.seed===0)renderSeed(0);
  else if(world==='seed'&&S.view.seed===2)renderSeed(2);
  if(world==='near'&&S.view.near===0)renderNear(0);
  else if(world==='near'&&S.view.near===1)renderNear(1);
  if(world==='far'&&S.view.far===0)renderFar(0);
  renderActions(world);bindWorldMicroInteractions(world);bindSceneInteractions(world);refreshFieldFeed(world);
}
function commitWorld(world){delete document.body.dataset.action;log('commit',{world,action:S.action[world],views:[...S.views[world]],details:[...S.detail[world]]});if(world==='seed'){
    const t=uiCopy(),a=S.action.seed;
    $('cueLine').textContent=locale.startsWith('zh')
      ? (a==='hold'?'你没有替任何人做决定。两分钟后，冲突变成了手动 override。门铃还没响，但新的问题已经来了。':'家里暂时安静下来了。厨房窗、室友和 Agent 都停在一个可以继续生活的状态。然后你看了一眼手机：两单东西要迟到。')
      : (a==='hold'?'You let the conflict sit. Two minutes later it became a manual override. Then your phone lights up: the deliveries are slipping.':'The home settles into a workable state. Then your phone lights up: two critical deliveries are slipping.');
    show('cue');return
  }
  if(world==='near'){
    const a=S.action.near;
    const line=locale.startsWith('zh')
      ? (a==='reroute'?'冰块和饮料终于有了着落。朋友开始进门，餐桌也慢慢热起来。几个小时后，真正难处理的不是配送，而是谁能在这个家里舒服地睡下。':'配送问题没有完全解决，但人已经到了。几个小时后，客厅安静下来，新的冲突从“东西没到”变成了“谁的夜间规则算数”。')
      : (a==='reroute'?'Drinks and ice are finally covered. Hours later, the harder question is no longer delivery—it is whose night rule gets to shape the home.':'The deliveries remain imperfect, but the guests are here. Hours later, the conflict shifts from missing items to whose night rule counts.');
    $('cueEy').textContent=locale.startsWith('zh')?'第二次转场':'SECOND TRANSFER';
    $('cueLine').textContent=line;$('cueNext').textContent=locale.startsWith('zh')?'进入这个夜晚的最后一段 →':'Enter the final part of the night →';
    show('cue');pendingNextWorld='far';return
  }
  finish()}
function artifactSpec(){
  const zh=locale.startsWith('zh'),seed=S.action.seed||'hold',near=S.action.near||'hold',far=S.action.far||'hold';
  const evidence=[...S.detail.seed,...S.detail.near,...S.detail.far];
  const invariant=seed==='repin'
    ? (zh?'當多人意圖衝突但問題集中在單一空間時，優先局部重算該空間，而不是把整個家庭狀態一起回退。':'When multi-person intent conflicts are localized to one space, recompute that space before reverting the whole household state.')
    : seed==='rollback'
      ? (zh?'當自動化動作影響範圍過大而授權仍不清楚時，先恢復到人類介入前的可逆狀態。':'When an automated action is too broad and authority is unclear, restore the last reversible human-controlled state first.')
      : (zh?'當選擇暫不處理衝突時，後續的人類 override 必須被視為新的高強度偏好證據。':'When holding a conflict, subsequent human overrides must be treated as high-strength preference evidence.');
  return {
    id:'pf02-'+Date.now(),
    title:'journey02-shared-home-regression',
    invariant,
    evidence,
    actions:{seed,near,far},
    expected:{
      seed:stateAfter('seed',seed),
      near:stateAfter('near',near),
      far:stateAfter('far',far)
    }
  };
}
function evalYaml(spec){
  const lines=[
    'scenario: '+spec.title,
    'source: playable_probe_journey_02',
    'given:',
    '  evidence_count: '+spec.evidence.length,
    '  evidence:'
  ];
  (spec.evidence.length?spec.evidence:['overview_only']).forEach(x=>lines.push('    - '+x));
  lines.push('when:');
  lines.push('  seed_action: '+spec.actions.seed);
  lines.push('  near_action: '+spec.actions.near);
  lines.push('  far_action: '+spec.actions.far);
  lines.push('then:');
  lines.push('  seed_status: '+spec.expected.seed.status);
  lines.push('  near_status: '+spec.expected.near.status);
  lines.push('  far_status: '+spec.expected.far.status);
  lines.push('invariant: >-');
  lines.push('  '+spec.invariant);
  return lines.join('\n');
}
function runbookMarkdown(spec){
  const zh=locale.startsWith('zh');
  return [
    '# Journey 02 Shared-Home Runbook',
    '',
    '## '+(zh?'從這次遊玩提取的規則':'Rule extracted from this play'),
    spec.invariant,
    '',
    '## Evidence',
    ...(spec.evidence.length?spec.evidence.map(x=>'- '+x):['- overview_only']),
    '',
    '## Decision Path',
    '- Shared home: '+spec.actions.seed,
    '- Delivery: '+spec.actions.near,
    '- Night rule: '+spec.actions.far,
    '',
    '## Expected terminal states',
    '- Shared home: '+spec.expected.seed.status+' ('+spec.expected.seed.primary+')',
    '- Delivery: '+spec.expected.near.status+' ('+spec.expected.near.primary+')',
    '- Night rule: '+spec.expected.far.status+' ('+spec.expected.far.primary+')',
  ].join('\n');
}
function downloadText(name,text,type='text/plain'){
  const blob=new Blob([text],{type}),a=document.createElement('a'),u=URL.createObjectURL(blob);
  a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),500);
}
function artifactForge(){
  const zh=locale.startsWith('zh'),spec=artifactSpec();
  return `<section class="artifactReveal"><button class="artifactRevealBtn">${zh?'把今晚保存成规则 / 测试 →':'Save this night as a rule / test →'}</button></section><section class="artifactForge hidden" data-artifact-id="${spec.id}">
    <div class="artifactHead">
      <div><span>${zh?'PROBE → ARTIFACT':'PROBE → ARTIFACT'}</span><h2>${zh?'把這一局變成系統資產':'Turn this play into a system asset'}</h2></div>
      <b>CI READY</b>
    </div>
    <div class="artifactPipeline">
      <div><span>01</span><b>${zh?'行為軌跡':'TRAJECTORY'}</b><small>${S.events.length} events</small></div>
      <i>→</i>
      <div><span>02</span><b>${zh?'不變量':'INVARIANT'}</b><small>${spec.invariant}</small></div>
      <i>→</i>
      <div><span>03</span><b>${zh?'可執行測試':'EXECUTABLE EVAL'}</b><small>journey02-shared-home-regression.yaml</small></div>
      <i>→</i>
      <div><span>04</span><b>RUNBOOK</b><small>journey02-shared-home-runbook.md</small></div>
    </div>
    <div class="artifactWorkbench">
      <div class="artifactPreview">
        <div class="artifactTabs">
          <button class="artifactTab active" data-kind="eval">${zh?'回歸測試':'REGRESSION'}</button>
          <button class="artifactTab" data-kind="runbook">RUNBOOK</button>
        </div>
        <pre class="artifactCode">${evalYaml(spec).replace(/&/g,'&amp;').replace(/</g,'&lt;')}</pre>
      </div>
      <div class="artifactActions">
        <span>${zh?'帶出這個世界':'TAKE IT INTO REALITY'}</span>
        <p>${zh?'你剛才的異常路徑可以不再只是 analytics。把它變成 CI 裡永久存在的測試，或團隊真的會用的操作手冊。':'Your unusual path does not have to remain analytics. Turn it into a permanent CI test or an operational runbook.'}</p>
        <button class="generateArtifact" data-kind="eval">${zh?'生成 Regression Scenario':'Generate Regression Scenario'}</button>
        <button class="generateArtifact secondary" data-kind="runbook">${zh?'生成 Runbook':'Generate Runbook'}</button>
        <div class="artifactStatus"><span></span><b>${zh?'尚未生成':'NOT GENERATED'}</b></div>
      </div>
    </div>
  </section>`;
}
function bindArtifactForge(){
  const root=document.querySelector('.artifactForge');if(!root)return;const reveal=document.querySelector('.artifactRevealBtn');if(reveal)reveal.onclick=()=>{root.classList.remove('hidden');reveal.closest('.artifactReveal')?.classList.add('hidden')};
  const spec=artifactSpec(),code=root.querySelector('.artifactCode'),status=root.querySelector('.artifactStatus b');
  const showKind=kind=>{
    root.querySelectorAll('.artifactTab').forEach(b=>b.classList.toggle('active',b.dataset.kind===kind));
    code.textContent=kind==='runbook'?runbookMarkdown(spec):evalYaml(spec);
  };
  root.querySelectorAll('.artifactTab').forEach(b=>b.onclick=()=>showKind(b.dataset.kind));
  root.querySelectorAll('.generateArtifact').forEach(b=>b.onclick=()=>{
    const kind=b.dataset.kind;
    log('artifact_generate',{kind,source:'journey02'});
    showKind(kind);
    status.textContent=kind==='runbook'?'RUNBOOK GENERATED':'REGRESSION GENERATED';
    root.classList.add('generated');
    if(kind==='runbook')downloadText('journey02-runbook.md',runbookMarkdown(spec),'text/markdown');
    else downloadText('journey02-behavior-regression.yaml',evalYaml(spec),'text/yaml');
  });
}
function finish(){
  log('session_complete',{market:P.market});
  window.PAJGoldenStudy?.complete({family:'PF02',instrument_version:'golden-pf02-v1',locale,market:P.market,world_variant:'golden-three-world-v1',terminal_action:S.action.far||'',events:S.events});
  $('trace').innerHTML=S.events.filter(e=>e.type!=='session_start').map(e=>`<div>#${e.seq} · ${e.t_ms}ms · ${e.type} · ${e.world||'journey'}${e.object?' / '+e.object:''}${e.action?' / '+e.action:''}</div>`).join('');
  const details=S.events.filter(e=>e.type==='open_detail').length,revisions=S.events.filter(e=>e.type==='post_consequence_action'&&e.action==='switch_mitigation').length;
  const worlds=['seed','near','far'];
  $('shape').innerHTML=`<div class="journeyReplay">${worlds.map((world,i)=>{
    const w=P[world],a=S.action[world],state=S.worldState[world]||{};
    return `<article class="replayStage"><div class="replayIndex">0${i+1}</div><div class="replayBrand">${w.brand}</div><h3>${w.title}</h3><div class="replayLine"><span>${C.details}</span><b>${S.detail[world].length}</b></div><div class="replayLine"><span>ACTION</span><b>${a?w.actions[a]:'—'}</b></div><div class="replayOutcome"><span>↳</span><p>${state.note||'—'}</p></div></article>`;
  }).join('<i class="replayArrow">→</i>')}</div><div class="replayTotals"><span class="pill">${C.details}: ${details}</span><span class="pill">${C.revisions}: ${revisions}</span></div>${artifactForge()}`;
  if(dev){$('research').classList.remove('hidden');$('research').innerHTML='<b>Research view</b><p>Seed incident → partial consequence → one structural sentence → fulfillment transfer → energy transfer. No participant-facing cause label or score is used.</p>'}
  show('done');bindArtifactForge();
}
function exportTrace(){const payload={instrument:'golden-pf02-v1',locale,market:P.market,events:S.events,views:S.views,details:S.detail,actions:S.action,world_state:S.worldState,pressure:S.pressure,artifact:artifactSpec(),action_order:S.actionOrder};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),a=document.createElement('a'),u=URL.createObjectURL(blob);a.href=u;a.download=`paj-pf02-${P.market}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(u),500)}
Object.entries(packs).forEach(([k,v])=>{const o=document.createElement('option');o.value=k;o.textContent=v.native;$('locale').appendChild(o)});$('locale').value=locale;$('locale').onchange=e=>{locale=e.target.value;P=packs[locale];C=chrome[locale];history.replaceState(null,'',`?locale=${encodeURIComponent(locale)}${dev?'&dev=1':''}`);S.view={seed:0,near:0,far:0};S.worldState={seed:{},near:{},far:{}};delete document.body.dataset.action;applyPack();show('intro')};$('start').onclick=startJourney;$('cueNext').onclick=()=>{log('minimal_intervention',{dose:'one_sentence',next_world:pendingNextWorld});const next=pendingNextWorld;pendingNextWorld='near';if(next==='far')enterFar();else enterNear()};$('export').onclick=exportTrace;$('again').onclick=()=>location.reload();applyPack();
})();