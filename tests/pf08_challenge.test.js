const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const html=fs.readFileSync('docs/challenge-pf08.html','utf8');
const packsSource=fs.readFileSync('docs/pf08-packs.js','utf8');
const playerSource=fs.readFileSync('docs/pf08-player.js','utf8');

function loadPacks(){
  const sandbox={window:{}};
  vm.createContext(sandbox);
  new vm.Script(packsSource).runInContext(sandbox);
  return sandbox.window.PAJ_PF08_PACKS;
}

test('PF08 packs and player scripts are valid JavaScript',()=>{
  assert.doesNotThrow(()=>new vm.Script(packsSource));
  assert.doesNotThrow(()=>new vm.Script(playerSource));
  assert.ok(html.includes('src="pf08-packs.js"'));
  assert.ok(html.includes('src="pf08-player.js"'));
});

test('PF08 exposes exactly ten explicit markets',()=>{
  const p=loadPacks();
  assert.deepEqual(Object.keys(p).sort(),['de','en','es','fr','ja','ko','pt','ru','zh-CN','zh-TW'].sort());
  assert.deepEqual(Object.values(p).map(x=>x.market).sort(),['BR','CN','DE','ES','FR','JP','KR','RU','TW','US'].sort());
});

test('every PF08 market preserves three sparse six-object workspaces',()=>{
  const packs=loadPacks();
  for(const [locale,p] of Object.entries(packs)){
    for(const world of ['seed','near','far']){
      assert.equal(p[world].nav.length,6,`${locale} ${world} nav`);
      for(const key of ['records','history','groups','limits','outside','notes']) {
        assert.ok(Array.isArray(p[world][key]) && p[world][key].length>=3,`${locale} ${world} ${key}`);
      }
      for(const key of ['rg','rh','eg','lr']) assert.ok(p[world].relation[key],`${locale} ${world} relation ${key}`);
      for(const key of ['a','b','hold']) {
        assert.ok(p[world].actions[key],`${locale} ${world} action ${key}`);
        assert.ok(p[world].consequence[key],`${locale} ${world} consequence ${key}`);
      }
    }
  }
});

test('PF08 market packs localize physical worlds, not headings only',()=>{
  const p=loadPacks();
  assert.match(p['zh-CN'].near.crumb,/深圳/);
  assert.match(p['zh-CN'].far.crumb,/佛山/);
  assert.match(p['zh-TW'].near.crumb,/台北/);
  assert.match(p['zh-TW'].far.crumb,/新北/);
  assert.match(p.en.near.crumb,/San Francisco/);
  assert.match(p.en.far.crumb,/Los Angeles/);
  assert.match(p.ja.near.crumb,/東京/);
  assert.match(p.ja.far.crumb,/横浜/);
  assert.match(p.ko.near.crumb,/서울/);
  assert.match(p.ko.far.crumb,/판교/);
  assert.match(p.es.near.crumb,/Madrid/);
  assert.match(p.fr.near.crumb,/Paris/);
  assert.match(p.de.near.crumb,/Berlin/);
  assert.match(p.pt.near.crumb,/São Paulo/);
  assert.match(p.pt.far.crumb,/Campinas/);
  assert.match(p.ru.near.crumb,/Москва/);
});

test('PF08 does not force-open the first category',()=>{
  assert.ok(playerSource.includes("renderWorld('seed',-1,false)"));
  assert.ok(playerSource.includes("renderWorld(w,-1,false)"));
  assert.ok(!playerSource.includes("renderWorld('seed',0,true)"));
  assert.ok(playerSource.includes("view:{seed:-1,near:-1,far:-1}"));
});

test('PF08 captures first opening, revisits, relations and omissions',()=>{
  for(const token of [
    'first_open_category',
    'revisit_object',
    'revisit_detail',
    'relation_discovered',
    "d.includes('record_0')&&d.includes('group_1')",
    "d.includes('record_0')&&d.includes('history_1')",
    "d.includes('external_1')&&d.includes('group_1')",
    "d.includes('limit_0')&&d.includes('record_0')",
    'omissions',
    'relations:[...S.relations[world]]',
  ]) assert.ok(playerSource.includes(token),token);
});

test('PF08 uses a neutral transition rather than a structural intervention',()=>{
  assert.ok(playerSource.includes('neutral_transition'));
  assert.ok(!playerSource.includes('minimal_intervention'));
  assert.ok(!html.toLowerCase().includes('intervention'));
});

test('PF08 randomized action order reduces positional response bias',()=>{
  assert.ok(playerSource.includes("shuffled(['a','b','hold'])"));
  assert.ok(playerSource.includes("log('action_order'"));
});

test('PF08 participant journey remains local-only and construct-free',()=>{
  const all=(html+'\n'+playerSource).toLowerCase();
  for(const forbidden of ['pajtransport','ingest-probe','supabase','posterior','oracle','spontaneous opening','pf08 —']){
    assert.ok(!all.includes(forbidden),forbidden);
  }
  assert.ok(playerSource.includes("instrument:'golden-pf08-v1'"));
  assert.ok(html.includes('id="research" class="research hidden"'));
});