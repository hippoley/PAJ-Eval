const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const html=fs.readFileSync('docs/challenge-pf06.html','utf8');
const packsSource=fs.readFileSync('docs/pf06-packs.js','utf8');
const playerSource=fs.readFileSync('docs/pf06-player.js','utf8');

function loadPacks(){const sandbox={window:{}};vm.createContext(sandbox);new vm.Script(packsSource).runInContext(sandbox);return sandbox.window.PAJ_PF06_PACKS;}

test('PF06 packs and player scripts are valid JavaScript',()=>{
  assert.doesNotThrow(()=>new vm.Script(packsSource));
  assert.doesNotThrow(()=>new vm.Script(playerSource));
  assert.ok(html.includes('src="pf06-packs.js"'));
  assert.ok(html.includes('src="pf06-player.js"'));
});

test('PF06 exposes exactly ten explicit markets',()=>{
  const p=loadPacks();
  assert.deepEqual(Object.keys(p).sort(),['de','en','es','fr','ja','ko','pt','ru','zh-CN','zh-TW'].sort());
  assert.deepEqual(Object.values(p).map(x=>x.market).sort(),['BR','CN','DE','ES','FR','JP','KR','RU','TW','US'].sort());
});

test('every PF06 market has three evolving worlds and delayed states',()=>{
  const packs=loadPacks();
  for(const [locale,p] of Object.entries(packs)){
    for(const world of ['seed','near','far']){
      assert.equal(p[world].nav.length,6,`${locale} ${world} nav`);
      assert.equal(p[world].states.length,3,`${locale} ${world} states`);
      assert.ok(p[world].window>=45,`${locale} ${world} recovery window`);
      assert.ok(p[world].actions.a && p[world].actions.b && p[world].actions.wait);
      assert.ok(p[world].consequence.a && p[world].consequence.b);
    }
    assert.ok(p.cue[1].length>12);
  }
});

test('PF06 localization changes operational sites, not headings only',()=>{
  const p=loadPacks();
  assert.match(p['zh-CN'].near.title,/广州/);
  assert.match(p['zh-TW'].near.title,/南港/);
  assert.match(p.en.near.title,/Kent/);
  assert.match(p.ja.near.title,/市川/);
  assert.match(p.ko.near.title,/김포/);
  assert.match(p.es.near.title,/Getafe/);
  assert.match(p.fr.near.title,/Rungis/);
  assert.match(p.de.near.title,/Großbeeren/);
  assert.match(p.pt.near.title,/Cajamar/);
  assert.match(p.ru.near.title,/Балаших/);
  assert.match(p['zh-CN'].far.title,/广州/);
  assert.match(p.en.far.title,/Seattle/);
  assert.match(p.ja.far.title,/東京/);
  assert.match(p.ko.far.title,/서울/);
});

test('PF06 delayed checks consume recovery window and expose delayed state',()=>{
  for(const token of [
    'minute_before',
    'minute_after',
    'window_before',
    'window_after',
    'delayed_check',
    'delayed_state_exposed',
    'S.minute[world]+=15',
    'windowLeft(world)',
    'S.minute[world]>=30',
  ]) assert.ok(playerSource.includes(token),token);
});

test('PF06 supports stopping without requiring wait, and continued monitoring as a real action',()=>{
  assert.ok(playerSource.includes("shuffled(['a','b','wait'])"));
  assert.ok(playerSource.includes("if(key==='wait'){delayedCheck(world);return}"));
  assert.ok(playerSource.includes('provisional_action'));
  assert.ok(playerSource.includes('stop_minute'));
});

test('PF06 captures history inspection, revision and transfer',()=>{
  for(const token of [
    "plainList(w.history",
    "markDetail(world,key)",
    'post_consequence_action',
    'switch_decision',
    'minimal_intervention',
    'session_complete',
    'window_remaining',
  ]) assert.ok(playerSource.includes(token),token);
});

test('PF06 participant journey stays local-only and score-free',()=>{
  const all=(html+'\n'+playerSource).toLowerCase();
  for(const forbidden of ['pajtransport','ingest-probe','supabase','posterior','oracle','premature stopping','pf06 —']){
    assert.ok(!all.includes(forbidden),forbidden);
  }
  assert.ok(playerSource.includes("instrument:'golden-pf06-v1'"));
  assert.ok(html.includes('id="research" class="research hidden"'));
});
