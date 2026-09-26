const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html=fs.readFileSync('docs/challenge-pf04.html','utf8');
const packsSource=fs.readFileSync('docs/pf04-packs.js','utf8');
const playerSource=fs.readFileSync('docs/pf04-player.js','utf8');

function loadPacks(){const sandbox={window:{}};vm.createContext(sandbox);new vm.Script(packsSource).runInContext(sandbox);return sandbox.window.PAJ_PF04_PACKS;}

test('PF04 packs and player scripts are valid JavaScript',()=>{
  assert.doesNotThrow(()=>new vm.Script(packsSource));
  assert.doesNotThrow(()=>new vm.Script(playerSource));
  assert.ok(html.includes('src="pf04-packs.js"'));
  assert.ok(html.includes('src="pf04-player.js"'));
});

test('PF04 exposes exactly the ten explicit markets',()=>{
  const p=loadPacks();
  assert.deepEqual(Object.keys(p).sort(),['de','en','es','fr','ja','ko','pt','ru','zh-CN','zh-TW'].sort());
  assert.deepEqual(Object.values(p).map(x=>x.market).sort(),['BR','CN','DE','ES','FR','JP','KR','RU','TW','US'].sort());
});

test('every PF04 market preserves three-world golden depth',()=>{
  const packs=loadPacks();
  for(const [locale,p] of Object.entries(packs)){
    for(const world of ['seed','near','far']){
      assert.equal(p[world].nav.length,6,`${locale} ${world} nav`);
      assert.ok(p[world].actions.a && p[world].actions.b && p[world].actions.hold);
      assert.ok(p[world].consequence.a && p[world].consequence.b && p[world].consequence.hold);
      assert.ok(p[world].post.inspect && p[world].post.switch && p[world].post.commit);
    }
    assert.equal(p.seed.tickets.length,3);
    assert.equal(p.seed.segments.length,3);
    assert.equal(p.near.depots.length,3);
    assert.equal(p.near.cities.length,3);
    assert.equal(p.far.timeline.length,4);
    assert.ok(p.cue[1].length>12);
  }
});

test('PF04 market packs localize physical operations rather than headings only',()=>{
  const p=loadPacks();
  assert.match(p['zh-CN'].near.depots[0][0],/广州/);
  assert.match(p['zh-TW'].near.depots[0][0],/南港/);
  assert.match(p.en.near.depots[0][0],/Kent/);
  assert.match(p.ja.near.depots[0][0],/市川/);
  assert.match(p.ko.near.depots[0][0],/김포/);
  assert.match(p.es.near.depots[0][0],/Getafe/);
  assert.match(p.fr.near.depots[0][0],/Rungis/);
  assert.match(p.de.near.depots[0][0],/Großbeeren/);
  assert.match(p.pt.near.depots[0][0],/Cajamar/);
  assert.match(p.ru.near.depots[0][0],/Балашиха/);
  assert.match(p['zh-CN'].far.title,/上海/);
  assert.match(p['zh-TW'].far.title,/高雄/);
  assert.match(p.en.far.title,/San Francisco/);
  assert.match(p.ja.far.title,/大阪/);
  assert.match(p.ko.far.title,/부산/);
  assert.match(p.es.far.title,/Barcelona/);
  assert.match(p.fr.far.title,/Lyon/);
  assert.match(p.de.far.title,/München/);
  assert.match(p.pt.far.title,/Rio/);
  assert.match(p.ru.far.title,/Санкт-Петербург/);
});

test('PF04 captures triage order, nested evidence, consequences and revision',()=>{
  for(const token of [
    'first_object',
    'provisional_action',
    'consequence_exposed',
    'post_consequence_action',
    'switch_mitigation',
    'minimal_intervention',
    "markDetail('seed','ticket_'",
    "markDetail('seed','segment_'",
    "markDetail('near','scan_'",
    "markDetail('near','city_'",
    "markDetail('far','road_'",
    "markDetail('far','timeline_'",
    'session_complete',
  ]) assert.ok(playerSource.includes(token),token);
});

test('PF04 randomized action placement reduces positional choice confounding',()=>{
  assert.ok(playerSource.includes("shuffled(['a','b','hold'])"));
  assert.ok(playerSource.includes("log('action_order'"));
});

test('PF04 participant journey stays local-only and construct-free',()=>{
  const all=(html+'\n'+playerSource).toLowerCase();
  for(const forbidden of ['pajtransport','ingest-probe','supabase','posterior','oracle','anomaly triage','pf04 —']){
    assert.ok(!all.includes(forbidden),forbidden);
  }
  assert.ok(playerSource.includes("instrument:'golden-pf04-v1'"));
  assert.ok(html.includes('id="research" class="research hidden"'));
});
