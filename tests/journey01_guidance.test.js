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
    for(const key of ['shopTitle','shopSub','careerTitle','careerSub','travelTitle','travelSub','recommended','checked','optional']){
      assert.ok(p.guide[key]&&p.guide[key].length>2,locale+' guide '+key);
    }
    for(const key of ['title','sub','opened','missed','decision','consequence','revisions','details','empty','shop','career','travel']){
      assert.ok(p.map[key]&&p.map[key].length>1,locale+' map '+key);
    }
  }
});

test('Journey 01 uses deterministic soft guidance instead of forced sequencing',()=>{
  for(const token of [
    'id="shopGuide" class="guideStrip"',
    'id="careerGuide" class="guideStrip"',
    'id="travelGuide" class="guideStrip"',
    'guideSpec(world)',
    "indices:[1,2,3]",
    "indices:[1,2,5]",
    "indices:[2,3,4]",
    'guideChip',
    'guideOptional',
    'guideFlow',
  ]) assert.ok(html.includes(token),token);
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
    'mapNode choice',
    'mapNode consequence',
    'mapNode missed',
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