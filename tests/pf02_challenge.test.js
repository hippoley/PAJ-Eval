const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('docs/challenge-pf02.html','utf8');
const packsSource = fs.readFileSync('docs/pf02-packs.js','utf8');
const chromeSource = fs.readFileSync('docs/pf02-chrome.js','utf8');
const playerSource = fs.readFileSync('docs/pf02-player.js','utf8');

function loadPacks(){
  const sandbox={window:{}};
  vm.createContext(sandbox);
  new vm.Script(packsSource).runInContext(sandbox);
  return sandbox.window.PAJ_PF02_PACKS;
}

test('PF02 packs, chrome and player scripts are valid JavaScript',()=>{
  assert.doesNotThrow(()=>new vm.Script(packsSource));
  assert.doesNotThrow(()=>new vm.Script(chromeSource));
  assert.doesNotThrow(()=>new vm.Script(playerSource));
  assert.ok(html.includes('src="pf02-packs.js"'));
  assert.ok(html.includes('src="pf02-chrome.js"'));
  assert.ok(html.includes('src="pf02-player.js"'));
});

test('PF02 exposes exactly the ten explicit markets',()=>{
  const packs=loadPacks();
  assert.deepEqual(Object.keys(packs).sort(),['de','en','es','fr','ja','ko','pt','ru','zh-CN','zh-TW'].sort());
  assert.deepEqual(Object.values(packs).map(p=>p.market).sort(),['BR','CN','DE','ES','FR','JP','KR','RU','TW','US'].sort());
});

test('every PF02 market preserves golden interaction depth',()=>{
  const packs=loadPacks();
  for(const [locale,p] of Object.entries(packs)){
    assert.equal(p.seed.nav.length,6,`${locale} seed nav`);
    assert.equal(p.near.nav.length,6,`${locale} near nav`);
    assert.equal(p.far.nav.length,6,`${locale} far nav`);
    assert.ok(p.seed.slices.length>=3,`${locale} query slices`);
    assert.ok(p.seed.requests.length>=3,`${locale} request samples`);
    assert.ok(p.near.depots.length>=3,`${locale} depots`);
    assert.ok(p.near.cities.length>=3,`${locale} city slices`);
    assert.ok(p.far.schedules.length>=3,`${locale} room schedules`);
    for(const key of ['rollback','repin','hold']){
      assert.ok(p.seed.actions[key],`${locale} seed action ${key}`);
      assert.ok(p.seed.consequence[key],`${locale} seed consequence ${key}`);
    }
    for(const key of ['rollback','reroute','hold']){
      assert.ok(p.near.actions[key],`${locale} near action ${key}`);
      assert.ok(p.near.consequence[key],`${locale} near consequence ${key}`);
    }
    for(const key of ['revert','schedule','hold']){
      assert.ok(p.far.actions[key],`${locale} far action ${key}`);
      assert.ok(p.far.consequence[key],`${locale} far consequence ${key}`);
    }
    assert.ok(p.cue.line.length>20,`${locale} minimal cue`);
  }
});

test('PF02 localization changes operational and physical worlds, not headings only',()=>{
  const p=loadPacks();
  assert.match(p['zh-CN'].near.routes,/杭州|苏州|上海|宁波/);
  assert.match(p['zh-TW'].near.routes,/台北|桃園|新竹|基隆/);
  assert.match(p.en.near.routes,/Portland|Seattle|Kent|Vancouver/);
  assert.match(p.ja.near.routes,/東京|横浜|湘南|市川/);
  assert.match(p.ko.near.routes,/서울|인천|수원|용인|김포/);
  assert.match(p.es.near.routes,/Madrid|Guadalajara|Getafe|Alcalá/);
  assert.match(p.fr.near.routes,/Paris|Melun|Rungis|Gennevilliers/);
  assert.match(p.de.near.routes,/Berlin|Oderland|Großbeeren|Hoppegarten/);
  assert.match(p.pt.near.routes,/São Paulo|Guarulhos|Cajamar/);
  assert.match(p.ru.near.routes,/Москва|Ногинск|Балашиха|Химки/);
  assert.match(p.ru.far.weather,/холоднее/);
  assert.match(p.en.far.weather,/8°F/);
  assert.match(p['zh-CN'].far.weather,/广州/);
});

test('PF02 journey uses provisional action, partial outcome, revision and transfer',()=>{
  for(const token of [
    'provisional_action',
    'consequence_exposed',
    'post_action_check',
    'post_consequence_action',
    'minimal_intervention',
    'serving_generation_compare',
    "markDetail('near','scan_'",
    "markDetail('near','city_'",
    "markDetail('far','interval_15m'",
    "markDetail('far','room_'",
    'switch_mitigation',
    'session_complete',
  ]) assert.ok(playerSource.includes(token),token);
});

test('PF02 action keys are valid for each world and presentation order is randomized',()=>{
  assert.ok(playerSource.includes("world==='seed'?['rollback','repin','hold']"));
  assert.ok(playerSource.includes("world==='near'?['rollback','reroute','hold']"));
  assert.ok(playerSource.includes("['revert','schedule','hold']"));
  assert.ok(playerSource.includes('resetActionOrders'));
  assert.ok(playerSource.includes('shuffled(actionKeys(world))'));
  assert.ok(!playerSource.includes("$('.x')"));
});

test('PF02 participant journey remains local-only and score-free',()=>{
  const allCode=(html+'\n'+playerSource+'\n'+chromeSource).toLowerCase();
  for(const forbidden of ['pajtransport','ingest-probe','supabase','posterior','oracle']){
    assert.ok(!allCode.includes(forbidden),forbidden);
  }
  const participantHtml=html.replace(/<script[^>]*><\/script>/g,'');
  assert.ok(!participantHtml.toLowerCase().includes('pf02'));
  assert.ok(playerSource.includes("instrument:'golden-pf02-v1'"));
  assert.ok(html.includes('id="research" class="research hidden"'));
});
