const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const locales=['de','en','es','fr','ja','ko','pt','ru','zh-CN','zh-TW'].sort();
const markets=['BR','CN','DE','ES','FR','JP','KR','RU','TW','US'].sort();

const families=[
  {id:'PF01',html:'docs/challenge.html',pack:'docs/challenge-packs.js',global:'PAJ_CHALLENGE_PACKS',player:null,instrument:'golden-challenge-v2'},
  {id:'PF02',html:'docs/challenge-pf02.html',pack:'docs/pf02-packs.js',global:'PAJ_PF02_PACKS',player:'docs/pf02-player.js',instrument:'golden-pf02-v1'},
  {id:'PF03',html:'docs/challenge-pf03.html',pack:'docs/pf03-packs.js',global:'PAJ_PF03_PACKS',player:'docs/pf03-player.js',instrument:'golden-pf03-v1'},
  {id:'PF04',html:'docs/challenge-pf04.html',pack:'docs/pf04-packs.js',global:'PAJ_PF04_PACKS',player:'docs/pf04-player.js',instrument:'golden-pf04-v1'},
  {id:'PF05',html:'docs/challenge-pf05.html',pack:'docs/pf05-packs.js',global:'PAJ_PF05_PACKS',player:'docs/pf05-player.js',instrument:'golden-pf05-v1'},
  {id:'PF06',html:'docs/challenge-pf06.html',pack:'docs/pf06-packs.js',global:'PAJ_PF06_PACKS',player:'docs/pf06-player.js',instrument:'golden-pf06-v1'},
  {id:'PF07',html:'docs/challenge-pf07.html',pack:'docs/pf07-packs.js',global:'PAJ_PF07_PACKS',player:'docs/pf07-player.js',instrument:'golden-pf07-v1'},
  {id:'PF08',html:'docs/challenge-pf08.html',pack:'docs/pf08-packs.js',global:'PAJ_PF08_PACKS',player:'docs/pf08-player.js',instrument:'golden-pf08-v1'},
];

function source(f){
  return fs.readFileSync(f.html,'utf8')+'\n'+(f.player?fs.readFileSync(f.player,'utf8'):'');
}
function loadPack(f){
  const sandbox={window:{}};
  vm.createContext(sandbox);
  new vm.Script(fs.readFileSync(f.pack,'utf8')).runInContext(sandbox);
  return sandbox.window[f.global];
}
function visibleText(html){
  return html
    .replace(/<script[\s\S]*?<\/script>/gi,' ')
    .replace(/<style[\s\S]*?<\/style>/gi,' ')
    .replace(/<[^>]+>/g,' ')
    .replace(/\s+/g,' ');
}

test('all eight golden challenge families exist as playable participant surfaces',()=>{
  assert.equal(families.length,8);
  for(const f of families){
    assert.ok(fs.existsSync(f.html),f.id+' html');
    assert.ok(fs.existsSync(f.pack),f.id+' pack');
    if(f.player) assert.ok(fs.existsSync(f.player),f.id+' player');
    assert.ok(source(f).includes(f.instrument),f.id+' instrument version');
  }
});

test('all eight golden families expose exactly the same ten locale keys and ten market identities',()=>{
  for(const f of families){
    const p=loadPack(f);
    assert.deepEqual(Object.keys(p).sort(),locales,f.id+' locale keys');
    const ids=Object.values(p).map(x=>x.market).filter(Boolean).sort();
    assert.deepEqual(ids,markets,f.id+' market ids');
  }
});

test('participant HTML never exposes PF identifiers or researcher construct names',()=>{
  const forbidden=[
    /PF0[1-8]/i,
    /hidden downstream constraints/i,
    /competing causal frames/i,
    /omitted evidence/i,
    /anomaly triage/i,
    /experiment choice under real constraints/i,
    /premature stopping/i,
    /wrong problem/i,
    /spontaneous opening/i,
  ];
  for(const f of families){
    const html=visibleText(fs.readFileSync(f.html,'utf8'));
    for(const re of forbidden) assert.ok(!re.test(html),f.id+' leaks '+re);
  }
});

test('all eight journeys are wired to the consent-gated formal study bridge',()=>{
  for(const f of families){
    const html=fs.readFileSync(f.html,'utf8');
    assert.ok(html.includes('golden-study-bridge.js'),f.id+' missing study bridge');
    assert.ok(!html.includes('src="transport.js"'),f.id+' loads durable transport before consent');
    assert.ok(source(f).includes('PAJGoldenStudy?.complete'),f.id+' missing completion hook');
  }
});

test('golden challenge participant journeys remain local-only until instrument freeze',()=>{
  for(const f of families){
    const s=source(f).toLowerCase();
    for(const forbidden of ['pajtransport','ingest-probe','supabase.co','service_role']){
      assert.ok(!s.includes(forbidden),f.id+' contains '+forbidden);
    }
  }
});

test('PF02-PF07 preserve seed consequence, intervention, near transfer and far transfer',()=>{
  for(const f of families.filter(x=>/^PF0[2-7]$/.test(x.id))){
    const s=source(f);
    for(const token of ['provisional_action','minimal_intervention','post_consequence_action','session_complete']){
      assert.ok(s.includes(token),f.id+' missing '+token);
    }
    assert.ok(s.includes('consequence_exposed'),f.id+' missing consequence_exposed');
    assert.ok(s.includes("show('far')"),f.id+' missing far transfer');
  }
});

test('PF08 deliberately has no structural intervention and does not force a first object',()=>{
  const f=families.find(x=>x.id==='PF08'),s=source(f);
  assert.ok(s.includes('workspace_transition'));
  assert.ok(!s.includes('minimal_intervention'));
  assert.ok(s.includes("renderWorld('seed',-1,false)"));
  assert.ok(s.includes("renderWorld(w,-1,false)"));
  assert.ok(s.includes('first_open_category'));
  assert.ok(s.includes('relation_discovered'));
});

test('PF02-PF08 randomize terminal action presentation where order is not semantically fixed',()=>{
  for(const f of families.filter(x=>/^PF0[2-8]$/.test(x.id))){
    const s=source(f);
    assert.ok(s.includes('shuffled('),f.id+' no action shuffle');
    assert.ok(s.includes("log('action_order'"),f.id+' no action-order event');
  }
});

test('each PF02-PF08 full pack has six ordinary top-level objects per world',()=>{
  for(const f of families.filter(x=>/^PF0[2-8]$/.test(x.id))){
    const p=loadPack(f);
    for(const [locale,pack] of Object.entries(p)){
      for(const world of ['seed','near','far']){
        assert.equal(pack[world].nav.length,6,`${f.id} ${locale} ${world}`);
      }
    }
  }
});

test('golden suite preserves raw behavioral signals needed for downstream replay',()=>{
  const required={
    PF01:['open_object','open_detail','provisional_commit','consequence_exposed','post_consequence_action','commit','minimal_intervention'],
    PF02:['open_object','open_detail','provisional_action','post_consequence_action','commit'],
    PF03:['open_object','open_detail','request_missing_evidence','provisional_action','commit'],
    PF04:['open_object','open_detail','first_object','provisional_action','commit'],
    PF05:['open_object','open_detail','experiment_run','budget_after','provisional_action','commit'],
    PF06:['open_object','open_detail','delayed_check','window_remaining','provisional_action','commit'],
    PF07:['open_object','open_detail','objective_artifact_opened','provisional_action','commit'],
    PF08:['open_object','open_detail','revisit_object','relation_discovered','omitted','commit'],
  };
  for(const f of families){
    const s=source(f);
    for(const token of required[f.id]) assert.ok(s.includes(token),f.id+' missing raw signal '+token);
  }
});