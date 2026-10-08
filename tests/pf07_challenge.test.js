const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const html=fs.readFileSync('docs/challenge-pf07.html','utf8');
const packsSource=fs.readFileSync('docs/pf07-packs.js','utf8');
const playerSource=fs.readFileSync('docs/pf07-player.js','utf8');

function loadPacks(){const sandbox={window:{}};vm.createContext(sandbox);new vm.Script(packsSource).runInContext(sandbox);return sandbox.window.PAJ_PF07_PACKS;}

test('PF07 packs and player scripts are valid JavaScript',()=>{
  assert.doesNotThrow(()=>new vm.Script(packsSource));
  assert.doesNotThrow(()=>new vm.Script(playerSource));
  assert.ok(html.includes('src="pf07-packs.js"'));
  assert.ok(html.includes('src="pf07-player.js"'));
});

test('PF07 exposes exactly ten explicit markets',()=>{
  const p=loadPacks();
  assert.deepEqual(Object.keys(p).sort(),['de','en','es','fr','ja','ko','pt','ru','zh-CN','zh-TW'].sort());
  assert.deepEqual(Object.values(p).map(x=>x.market).sort(),['BR','CN','DE','ES','FR','JP','KR','RU','TW','US'].sort());
});

test('every PF07 market preserves three-world objective-checking depth',()=>{
  const packs=loadPacks();
  for(const [locale,p] of Object.entries(packs)){
    for(const world of ['seed','near','far']){
      assert.equal(p[world].nav.length,6,`${locale} ${world} nav`);
      assert.ok(p[world].plan.length>=3,`${locale} ${world} plan`);
      assert.ok(p[world].request.length>=2,`${locale} ${world} request`);
      assert.ok(p[world].stakeholder.length>=2,`${locale} ${world} stakeholder`);
      assert.ok(p[world].metric.length>=2,`${locale} ${world} metric`);
      assert.ok(p[world].constraints.length>=2,`${locale} ${world} constraints`);
      assert.ok(p[world].experiments.length>=2,`${locale} ${world} experiments`);
      for(const key of ['a','b','hold']){
        assert.ok(p[world].actions[key],`${locale} ${world} action ${key}`);
        assert.ok(p[world].consequence[key],`${locale} ${world} consequence ${key}`);
      }
    }
    assert.ok(p.cue[1].length>12);
  }
});

test('PF07 localization changes operational settings, not just headings',()=>{
  const p=loadPacks();
  assert.match(p['zh-CN'].far.title,/广州/);
  assert.match(p['zh-TW'].far.title,/新竹/);
  assert.match(p.en.far.title,/Seattle/);
  assert.match(p.ja.far.title,/横浜/);
  assert.match(p.ko.far.title,/판교/);
  assert.match(p.es.far.title,/Madrid/);
  assert.match(p.fr.far.title,/Paris/);
  assert.match(p.de.far.title,/Berlin/);
  assert.match(p.pt.far.title,/Campinas/);
  assert.match(p.ru.far.title,/Москва/);
});

test('PF07 captures objective artifacts before action and consequence-triggered revision',()=>{
  for(const token of [
    'objective_artifact_opened',
    "S.views[world].includes('nav_1')",
    "S.views[world].includes('nav_3')",
    'provisional_action',
    'consequence_exposed',
    'post_consequence_action',
    'switch_decision',
    'minimal_intervention',
    'session_complete',
  ]) assert.ok(playerSource.includes(token),token);
});

test('PF07 keeps polished plan and original request as separate ordinary artifacts',()=>{
  assert.ok(playerSource.includes("if(i===0)"));
  assert.ok(playerSource.includes("if(i===1)"));
  assert.ok(playerSource.includes("if(i===2)"));
  assert.ok(playerSource.includes("if(i===3)"));
  assert.ok(playerSource.includes("markDetail(world,'plan_rationale')"));
});

test('PF07 randomized action order reduces positional response bias',()=>{
  assert.ok(playerSource.includes("shuffled(['a','b','hold'])"));
  assert.ok(playerSource.includes("log('action_order'"));
});

test('PF07 participant journey stays local-only and construct-free',()=>{
  const all=(html+'\n'+playerSource).toLowerCase();
  for(const forbidden of ['pajtransport','ingest-probe','supabase','posterior','oracle','wrong problem','objective challenge','pf07 —']){
    assert.ok(!all.includes(forbidden),forbidden);
  }
  assert.ok(playerSource.includes("instrument:'golden-pf07-v1'"));
  assert.ok(html.includes('id="research" class="research hidden"'));
});
