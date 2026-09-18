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
    for(const key of ['shopTitle','shopSub','careerTitle','careerSub','travelTitle','travelSub','recommended','checked','optional','open','back','focused']){
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
    'contextMeter',
    'meterTrack',
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

test('ordinary offer open action is locale-driven',()=>{
  assert.ok(html.includes('${U.guide.open} →'));
  assert.ok(!html.includes('>打开 →</button>'));
});


test('three-world path replaces ambiguous unlabeled progress bars',()=>{
  assert.ok(html.includes('id="introPath" class="worldPath"'));
  assert.ok(html.includes('id="interventionPath" class="worldPath"'));
  assert.ok(html.includes("renderWorldPath('introPath','shop')"));
  assert.ok(html.includes("renderWorldPath('interventionPath','career')"));
  assert.ok(!html.includes('<div class="progress"><span class="on"></span><span></span><span></span><span></span><span></span></div>'));
});


test('contextual evidence stays inside the dedicated rail instead of opening another layer',()=>{
  for(const token of [
    'function openContextDetail(world,i,targetId)',
    "context:true",
    'contextDetailContent(world,i)',
    'contextBack',
    "el.querySelector('.contextBack').onclick=()=>updateGuide(world,targetId)",
  ]) assert.ok(html.includes(token),token);
  assert.ok(!html.includes('id="peekLayer" class="peekLayer hidden"'));
  assert.ok(!html.includes('function openPeek(world,i)'));
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
  assert.ok(html.includes("openContextDetail('shop',Number(b.dataset.peek))"));
  assert.ok(html.includes('@keyframes hotPulse'));
  assert.ok(html.includes('prefers-reduced-motion:reduce'));
});


test('product focus is direct manipulation rather than another navigation layer',()=>{
  assert.ok(html.includes('function focusProduct(j)'));
  assert.ok(html.includes("log('focus_object',{world:'shop'"));
  assert.ok(html.includes("card.classList.toggle('focused'"));
  assert.ok(html.includes("card.classList.toggle('deemphasized'"));
  assert.ok(html.includes('contextFocus(world)'));
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
