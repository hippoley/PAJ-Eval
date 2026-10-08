const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('docs/challenge-pf03.html','utf8');
const packsSource = fs.readFileSync('docs/pf03-packs.js','utf8');
const playerSource = fs.readFileSync('docs/pf03-player.js','utf8');

function loadPacks(){
  const sandbox={window:{}};
  vm.createContext(sandbox);
  new vm.Script(packsSource).runInContext(sandbox);
  return sandbox.window.PAJ_PF03_PACKS;
}

test('PF03 packs and player scripts are valid JavaScript',()=>{
  assert.doesNotThrow(()=>new vm.Script(packsSource));
  assert.doesNotThrow(()=>new vm.Script(playerSource));
  assert.ok(html.includes('src="pf03-packs.js"'));
  assert.ok(html.includes('src="pf03-player.js"'));
});

test('PF03 exposes exactly the ten explicit markets',()=>{
  const packs=loadPacks();
  assert.deepEqual(Object.keys(packs).sort(),['de','en','es','fr','ja','ko','pt','ru','zh-CN','zh-TW'].sort());
  assert.deepEqual(Object.values(packs).map(p=>p.market).sort(),['BR','CN','DE','ES','FR','JP','KR','RU','TW','US'].sort());
});

test('every PF03 market preserves golden interaction depth',()=>{
  const packs=loadPacks();
  for(const [locale,p] of Object.entries(packs)){
    assert.equal(p.seed.nav.length,6,`${locale} seed nav`);
    assert.equal(p.near.nav.length,6,`${locale} near nav`);
    assert.equal(p.far.nav.length,6,`${locale} far nav`);
    assert.equal(p.seed.vendors.length,3,`${locale} vendors`);
    assert.ok(p.seed.sourceNotes.length>=3,`${locale} source notes`);
    assert.ok(p.seed.references.length>=3,`${locale} references`);
    assert.equal(p.near.options.length,3,`${locale} workspace options`);
    assert.ok(p.near.sources.length>=4,`${locale} workspace sources`);
    assert.equal(p.far.providers.length,3,`${locale} providers`);
    assert.ok(p.far.exit.length>=3,`${locale} exit rows`);
    for(const world of ['seed','near','far']){
      for(const key of ['a','b','hold']){
        assert.ok(p[world].actions[key],`${locale} ${world} action ${key}`);
        assert.ok(p[world].consequence[key],`${locale} ${world} consequence ${key}`);
      }
      assert.ok(p[world].post.inspect && p[world].post.switch && p[world].post.commit);
    }
    assert.ok(p.cue.line.length>12,`${locale} minimal cue`);
  }
});

test('PF03 localization changes real market surfaces, not headings only',()=>{
  const p=loadPacks();
  assert.match(p['zh-CN'].near.title,/广州/);
  assert.match(p['zh-TW'].near.title,/台北/);
  assert.match(p.en.near.title,/Seattle/);
  assert.match(p.ja.near.title,/東京/);
  assert.match(p.ko.near.title,/서울/);
  assert.match(p.es.near.title,/Madrid/);
  assert.match(p.fr.near.title,/Paris/);
  assert.match(p.de.near.title,/Berlin/);
  assert.match(p.pt.near.title,/São Paulo/);
  assert.match(p.ru.near.title,/Москв/);
  assert.match(p['zh-CN'].seed.vendors[0][1],/¥/);
  assert.match(p['zh-TW'].seed.vendors[0][1],/NT\$/);
  assert.match(p.en.seed.vendors[0][1],/\$/);
  assert.match(p.ja.seed.vendors[0][1],/¥/);
  assert.match(p.ko.seed.vendors[0][1],/₩/);
  assert.match(p.pt.seed.vendors[0][1],/R\$/);
  assert.match(p.ru.seed.vendors[0][1],/₽/);
});

test('PF03 journey captures missing-evidence request, consequence and revision',()=>{
  for(const token of [
    'request_missing_evidence',
    'provisional_action',
    'consequence_exposed',
    'post_consequence_action',
    'minimal_intervention',
    'switch_choice',
    'session_complete',
    "requestEvidence('seed'",
    "requestEvidence('near'",
    "requestEvidence('far'",
  ]) assert.ok(playerSource.includes(token),token);
});

test('PF03 supports nested provenance inspection in all three worlds',()=>{
  for(const token of [
    "markDetail('seed','source_'",
    "markDetail('seed','reference_'",
    "markDetail('near','source_'",
    "markDetail('near','noise_'",
    "markDetail('near','note_'",
    "markDetail('far','incident_'",
    "markDetail('far','exit_'",
  ]) assert.ok(playerSource.includes(token),token);
});

test('PF03 action presentation order is randomized without changing action semantics',()=>{
  assert.ok(playerSource.includes("return ['a','b','hold']"));
  assert.ok(playerSource.includes('resetActionOrders'));
  assert.ok(playerSource.includes('shuffled(actionKeys())'));
  assert.ok(playerSource.includes("log('action_order'"));
});

test('PF03 participant journey remains local-only and score-free',()=>{
  const all=(html+'\n'+playerSource).toLowerCase();
  for(const forbidden of ['pajtransport','ingest-probe','supabase','posterior','oracle','omitted evidence']){
    assert.ok(!all.includes(forbidden),forbidden);
  }
  assert.ok(playerSource.includes("instrument:'golden-pf03-v1'"));
  assert.ok(html.includes('id="research" class="research hidden"'));
  assert.ok(!html.includes('PF03 —'));
});
