const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const html=fs.readFileSync('docs/challenge.html','utf8');
const uiSource=fs.readFileSync('docs/journey01-ui.js','utf8');

function loadUi(){
  const sandbox={window:{}};
  vm.createContext(sandbox);
  new vm.Script(uiSource).runInContext(sandbox);
  return sandbox.window.PAJ_JOURNEY01_UI;
}

test('Journey 01 guidance pack is valid and covers exactly ten locales',()=>{
  assert.doesNotThrow(()=>new vm.Script(uiSource));
  const ui=loadUi();
  assert.deepEqual(Object.keys(ui).sort(),['de','en','es','fr','ja','ko','pt','ru','zh-CN','zh-TW'].sort());
});

test('every locale has soft guidance and visual decision-map copy',()=>{
  const ui=loadUi();
  for(const [locale,p] of Object.entries(ui)){
    for(const key of ['shopTitle','shopSub','careerTitle','careerSub','travelTitle','travelSub','recommended','checked','optional','open','back','focused','cue']){
      assert.ok(p.guide[key]&&p.guide[key].length>0,locale+' guide '+key);
    }
    for(const key of ['title','sub','opened','missed','decision','consequence','revisions','details','empty','shop','career','travel','stages']){
      assert.ok(p.map[key]&&p.map[key].length>1,locale+' map '+key);
    }
  }
});

test('Journey 01 has one clear hierarchy: navigation, primary canvas, contextual rail',()=>{
  for(const token of [
    'id="shopContext" class="contextRail"',
    'id="careerContext" class="contextRail"',
    'id="travelContext" class="contextRail"',
    'id="checkoutContext" class="contextRail"',
    'grid-template-columns:188px minmax(0,1fr) 282px',
    'contextActions',
    'contextHintNote',
    'guideSpec(world)',
    "indices:[1,2,3]",
    "indices:[1,2,5]",
    "indices:[2,3,4]",
  ]) assert.ok(html.includes(token),token);
  assert.ok(!html.includes('id="shopGuide" class="guideStrip"'));
  assert.ok(!html.includes('id="careerGuide" class="guideStrip"'));
  assert.ok(!html.includes('id="travelGuide" class="guideStrip"'));
  assert.ok(!html.includes('Math.random('));
  assert.ok(!html.includes('shuffled('));
});

test('participant result is an interactive state map, not a raw log',()=>{
  for(const token of [
    'id="journeyShape" class="decisionMap"',
    'id="mapInspector" class="mapInspector"',
    'renderDecisionMap()',
    'inspectMapWorld(world)',
    'mapWorldData(world)',
    'mapOrb',
    'mapChoice',
    'mapOutcome',
    'mapStat missed',
  ]) assert.ok(html.includes(token),token);
  assert.ok(html.includes('id="rawTraceCard" class="card hidden"'));
  assert.ok(html.includes("if(devMode){$('rawTraceCard').classList.remove('hidden')"));
});

test('state map derives observations omissions choices consequences and revisions from raw behavior',()=>{
  for(const token of [
    "S.views[world]",
    "e.type==='open_detail'&&e.world===world",
    "S.choices[world]",
    "e.type==='post_consequence_action'&&e.world===world",
    "choiceLabel(world,choice)",
    "consequenceLabel(world,choice)",
  ]) assert.ok(html.includes(token),token);
});

test('soft guidance stays inside ordinary participant language',()=>{
  const ui=JSON.stringify(loadUi()).toLowerCase();
  for(const forbidden of ['pf01','hidden downstream constraints','posterior','oracle','latent construct']){
    assert.ok(!ui.includes(forbidden),forbidden);
  }
});

test('offer opening is native to the inbox row rather than an experiment-style open button',()=>{
  assert.ok(html.includes('class="mailRow openOfferRow"'));
  assert.ok(html.includes("document.querySelectorAll('.openOfferRow')"));
  assert.ok(!html.includes('>打开 →</button>'));
});


test('three-world path replaces ambiguous unlabeled progress bars',()=>{
  assert.ok(html.includes('id="introPath" class="worldPath"'));
  assert.ok(html.includes('id="interventionPath" class="worldPath"'));
  assert.ok(html.includes("renderWorldPath('introPath','shop')"));
  assert.ok(html.includes("renderWorldPath('interventionPath','career')"));
  assert.ok(!html.includes('<div class="progress"><span class="on"></span><span></span><span></span><span></span><span></span></div>'));
});


test('guidance rail and subject canvas are behaviorally distinct',()=>{
  for(const token of [
    'contextLayerTag',
    'U.guide.cue',
    'function navigateEvidence(world,i,targetId)',
    "log('guidance_follow',{world,object:'nav_'+i})",
    "if(world==='shop'){if(targetId==='checkoutContext')show('shop');shopView(i);return}",
    "if(world==='career'){careerView(i);return}",
    'travelView(i);',
  ]) assert.ok(html.includes(token),token);
  assert.ok(!html.includes('function contextDetailContent(world,i)'));
  assert.ok(!html.includes('function openContextDetail(world,i,targetId)'));
  assert.ok(!html.includes('id="peekLayer" class="peekLayer hidden"'));
});

test('product cards have restrained tactile motion with reduced-motion fallback',()=>{
  assert.ok(html.includes('bindProductMotion()'));
  assert.ok(html.includes("matchMedia('(prefers-reduced-motion: reduce)').matches"));
  assert.ok(html.includes('--ry'));
  assert.ok(html.includes('--rx'));
  assert.ok(html.includes('@media(prefers-reduced-motion:reduce)'));
});


test('product visuals expose shoppable evidence hotspots',()=>{
  assert.ok(html.includes('class="visualHotspot"'));
  assert.ok(html.includes("navigateEvidence('shop',Number(b.dataset.peek))"));
  assert.ok(html.includes('@keyframes hotPulse'));
  assert.ok(html.includes('prefers-reduced-motion:reduce'));
});


test('product focus becomes a real product-detail page rather than a research focus state',()=>{
  assert.ok(html.includes('function focusProduct(j)'));
  assert.ok(html.includes('function renderProductDetail(j)'));
  assert.ok(html.includes('class="productDetail"'));
  assert.ok(html.includes('class="productDetailVisual"'));
  assert.ok(html.includes('class="productDetailActions"'));
  assert.ok(html.includes("log('focus_object',{world:'shop'"));
  assert.ok(!html.includes('function contextFocus(world)'));
});


test('state graph is overview-first and defers detail to the inspector',()=>{
  assert.ok(html.includes('class="mapOrb"'));
  assert.ok(html.includes('class="mapChoice"'));
  assert.ok(html.includes('class="mapOutcome"'));
  assert.ok(html.includes('class="mapStats"'));
  assert.ok(html.includes('class="mapInspector"'));
  assert.ok(!html.includes('class="mapLane"'));
});


test('soft guidance does not rank one evidence item as the prescribed next step',()=>{
  assert.ok(html.includes('contextListLabel'));
  assert.ok(html.includes('U.guide.recommended'));
  assert.ok(!html.includes("class=\"contextAction ${done?'done':''} ${isNext?'next':''}\""));
  assert.ok(!html.includes('contextAction.next'));
});


test('realistic subject apps keep inspection separate from commitment',()=>{
  for(const token of [
    'function focusProduct(j)',
    'function focusFlight(k)',
    "log('focus_object',{world:'shop'",
    "log('focus_object',{world:'career'",
    "log('focus_object',{world:'travel'",
    'class="mailRow openOfferRow"',
    'class="flightRow" data-k="${o.key}" tabindex="0"',
    'function addToCart(j)',
    'function chooseProduct(j)',
    'function careerCommit(k)',
    'function travelCommit(k)',
  ]) assert.ok(html.includes(token),token);
});


test('visual language makes guidance quieter than the subject canvas',()=>{
  assert.ok(html.includes('border-left:1px dashed #c8c1b5'));
  assert.ok(html.includes('background:linear-gradient(180deg,#f4f1ea 0,#eeebe4 100%)'));
  assert.ok(html.includes('background:var(--paper);box-shadow:14px 0 34px'));
  assert.ok(html.includes('class="contextLayerTag"'));
});


test('guidance can collapse without removing the playable subject',()=>{
  for(const token of [
    'workspace.guidanceCollapsed',
    'contextRail.collapsed',
    'contextCollapsedButton',
    "el.dataset.collapsed==='1'",
    "el.dataset.collapsed='1'",
    "el.dataset.collapsed='0'",
  ]) assert.ok(html.includes(token),token);
});


test('guidance is optional context rather than a completion meter',()=>{
  assert.ok(html.includes('contextHintNote'));
  assert.ok(!html.includes('contextMeter'));
  assert.ok(!html.includes('meterTrack'));
  assert.ok(!html.includes('Math.round((checked/g.indices.length)*100)'));
});


test('subject worlds are rendered as recognizable real applications',()=>{
  for(const token of [
    'class="storeApp"',
    'class="storeTop"',
    'class="storeSearch"',
    'class="storeTabs"',
    'class="cartLayer hidden"',
    'class="checkoutApp"',
    'class="checkoutPage"',
    'class="mailApp"',
    'class="mailTop"',
    'class="mailBody"',
    'class="mailSide"',
    'class="travelApp"',
    'class="tripBar"',
    'class="travelTabs"',
  ]) assert.ok(html.includes(token),token);
});

test('shop uses a realistic cart step before checkout consequence exposure',()=>{
  assert.ok(html.includes('function addToCart(j)'));
  assert.ok(html.includes("log('cart_add'"));
  assert.ok(html.includes('function renderCart()'));
  assert.ok(html.includes("$('cartCheckout').onclick"));
  assert.ok(html.includes('chooseProduct(j)'));
});

test('guidance defaults collapsed so it never competes with the subject app',()=>{
  assert.ok(html.includes("if(!('collapsed' in el.dataset))el.dataset.collapsed='1'"));
  assert.ok(html.includes('#shop .contextRail.collapsed'));
  assert.ok(html.includes('#career .contextRail.collapsed'));
  assert.ok(html.includes('#travel .contextRail.collapsed'));
});


test('every locale has explicit checkout decision language',()=>{
  const ui=loadUi();
  const keys=['secure','currentCart','decision','liteTitle','liteSub','optionA','optionB','liteBridge','liteBridgeMeta','proDirect','proDirectMeta','choose','affected','affectedTitle','notApplied','proTitle','proSub','tomorrow','keepProduct','pickup','otherModels','otherModelsTitle','switchLite','back','pickupCue'];
  for(const [locale,p] of Object.entries(ui)){
    for(const key of keys) assert.ok(p.checkout&&p.checkout[key]&&p.checkout[key].length>0,locale+' checkout '+key);
  }
});

test('checkout separates decisions from evidence and alternatives',()=>{
  for(const token of [
    'class="checkoutDecisionTitle"',
    'class="decisionOptions"',
    'id="chooseLiteBridge"',
    'id="choosePro"',
    'id="inspectDevices" class="evidenceLink"',
    'id="chooseTomorrow"',
    'id="choosePickup"',
    'id="otherModels" class="alternativeLink"',
    'function showAffectedDevices()',
    'function showAlternativeModels()',
    'function commitShop(choice,resolution)',
  ]) assert.ok(html.includes(token),token);
});

test('delivery problem does not mix product switching into the primary action row',()=>{
  assert.ok(html.includes("checkoutAction('tomorrow')"));
  assert.ok(html.includes("checkoutAction('pickup')"));
  assert.ok(html.includes("checkoutAction('other_models')"));
  assert.ok(html.includes("checkoutAction('switch_lite')"));
  assert.ok(html.includes("object:'alternative_models'"));
});
