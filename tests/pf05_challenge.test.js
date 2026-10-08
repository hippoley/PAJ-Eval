const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const html=fs.readFileSync('docs/challenge-pf05.html','utf8');
const packsSource=fs.readFileSync('docs/pf05-packs.js','utf8');
const playerSource=fs.readFileSync('docs/pf05-player.js','utf8');

function loadPacks(){const sandbox={window:{}};vm.createContext(sandbox);new vm.Script(packsSource).runInContext(sandbox);return sandbox.window.PAJ_PF05_PACKS;}

test('PF05 packs and player scripts are valid JavaScript',()=>{
  assert.doesNotThrow(()=>new vm.Script(packsSource));
  assert.doesNotThrow(()=>new vm.Script(playerSource));
  assert.ok(html.includes('src="pf05-packs.js"'));
  assert.ok(html.includes('src="pf05-player.js"'));
});

test('PF05 exposes exactly ten explicit markets',()=>{
  const p=loadPacks();
  assert.deepEqual(Object.keys(p).sort(),['de','en','es','fr','ja','ko','pt','ru','zh-CN','zh-TW'].sort());
  assert.deepEqual(Object.values(p).map(x=>x.market).sort(),['BR','CN','DE','ES','FR','JP','KR','RU','TW','US'].sort());
});

test('every PF05 market has three constrained worlds and one experiment slot',()=>{
  const packs=loadPacks();
  for(const [locale,p] of Object.entries(packs)){
    for(const world of ['seed','near','far']){
      assert.equal(p[world].nav.length,6,`${locale} ${world} nav`);
      assert.equal(p[world].tests.length,3,`${locale} ${world} tests`);
      assert.equal(p[world].result.length,3,`${locale} ${world} results`);
      for(const key of ['a','b','hold']){
        assert.ok(p[world].actions[key],`${locale} ${world} action ${key}`);
        assert.ok(p[world].consequence[key],`${locale} ${world} consequence ${key}`);
      }
    }
    assert.ok(p.cue[1].length>12);
  }
});

test('PF05 market localization changes locations, money and physical worlds',()=>{
  const p=loadPacks();
  assert.match(p['zh-CN'].near.title,/佛山/);
  assert.match(p['zh-TW'].near.title,/桃園/);
  assert.match(p.en.near.title,/Tacoma/);
  assert.match(p.ja.near.title,/横浜/);
  assert.match(p.ko.near.title,/수원/);
  assert.match(p.es.near.title,/Getafe/);
  assert.match(p.fr.near.title,/Melun/);
  assert.match(p.de.near.title,/Potsdam/);
  assert.match(p.pt.near.title,/Campinas/);
  assert.match(p.ru.near.title,/Балаших/);
  assert.match(p['zh-CN'].seed.tests[0][1],/¥/);
  assert.match(p['zh-TW'].seed.tests[0][1],/NT\$/);
  assert.match(p.en.seed.tests[0][1],/\$/);
  assert.match(p.ja.seed.tests[0][1],/¥/);
  assert.match(p.ko.seed.tests[0][1],/₩/);
  assert.match(p.pt.seed.tests[0][1],/R\$/);
  assert.match(p.ru.seed.tests[0][1],/₽/);
});

test('PF05 experiment execution consumes real internal budget and slot',()=>{
  for(const token of [
    'budget_before',
    'budget_after',
    'slot_before:1',
    'slot_after:0',
    'experiment_run',
    'experiment_result_exposed',
    'COST=[18,48,72]',
    "if(S.run[world]!==null)return",
  ]) assert.ok(playerSource.includes(token),token);
});

test('PF05 keeps terminal action available without forcing an experiment',()=>{
  const renderActionIndex=playerSource.indexOf('function renderActions');
  const runIndex=playerSource.indexOf('function runExperiment');
  assert.ok(renderActionIndex>0 && runIndex>0);
  assert.ok(playerSource.includes("renderActions(world)"));
  assert.ok(!playerSource.includes('experiment_required'));
});

test('PF05 captures revision, unused resources and transfer',()=>{
  for(const token of [
    'provisional_action',
    'consequence_exposed',
    'post_consequence_action',
    'switch_decision',
    'minimal_intervention',
    'session_complete',
    'budgets:S.budget',
    'experiments:S.run',
  ]) assert.ok(playerSource.includes(token),token);
});

test('PF05 randomized action order reduces positional choice bias',()=>{
  assert.ok(playerSource.includes("shuffled(['a','b','hold'])"));
  assert.ok(playerSource.includes("log('action_order'"));
});

test('PF05 participant journey stays local-only and score-free',()=>{
  const all=(html+'\n'+playerSource).toLowerCase();
  for(const forbidden of ['pajtransport','ingest-probe','supabase','posterior','oracle','value of information','pf05 —']){
    assert.ok(!all.includes(forbidden),forbidden);
  }
  assert.ok(playerSource.includes("instrument:'golden-pf05-v1'"));
  assert.ok(html.includes('id="research" class="research hidden"'));
});
