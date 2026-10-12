const test=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');

const normalizer=require(path.resolve('docs/golden-event-normalizer.js'));

const meta={family:'PF01',locale:'en',market:'US',instrument_version:'golden-challenge-v2'};

test('normalizer preserves the complete raw event while adding a canonical envelope',()=>{
  const raw={seq:2,t_ms:1450,type:'open_detail',world:'shop',object:'affected_devices',extra:{x:1}};
  const n=normalizer.normalizeEvent(meta,raw,1);
  assert.equal(n.envelope_version,'golden-event-envelope-v1');
  assert.equal(n.event,'open_detail');
  assert.equal(n.target,'affected_devices');
  assert.equal(n.world,'shop');
  assert.deepEqual(n.raw_event,raw);
  assert.notEqual(n.raw_event,raw);
});

test('normalizer aliases family-specific provisional and transition events without destroying originals',()=>{
  const p=normalizer.normalizeEvent(meta,{seq:1,t_ms:10,type:'provisional_commit',world:'shop',choice:'lite'},0);
  assert.equal(p.event,'provisional_action');
  assert.equal(p.raw_event_type,'provisional_commit');
  assert.equal(p.raw_event.choice,'lite');

  const w=normalizer.normalizeEvent({...meta,family:'PF08',instrument_version:'golden-pf08-v1'},{seq:2,t_ms:20,type:'workspace_transition',to_world:'near'},1);
  assert.equal(w.event,'transfer_world_entry');
  assert.equal(w.target,'near');
  assert.equal(w.raw_event_type,'workspace_transition');
});

test('normalizer accepts legacy canonical-player event field names',()=>{
  const n=normalizer.normalizeEvent(meta,{seq:3,t:200,event:'open_object',screen:'seed',target:'nav_2'},2);
  assert.equal(n.event,'open_object');
  assert.equal(n.t_ms,200);
  assert.equal(n.world,'seed');
  assert.equal(n.target,'nav_2');
});

test('trace normalization requires explicit family locale market and instrument version',()=>{
  for(const key of ['family','locale','market','instrument_version']){
    const bad={...meta,[key]:''};
    assert.throws(()=>normalizer.normalizeTrace(bad,[]),new RegExp(key));
  }
});

test('trace normalization rejects sequence and time reversal',()=>{
  assert.throws(()=>normalizer.normalizeTrace(meta,[
    {seq:2,t_ms:10,type:'open_object'},
    {seq:2,t_ms:20,type:'commit'}
  ]),/sequence/);
  assert.throws(()=>normalizer.normalizeTrace(meta,[
    {seq:1,t_ms:30,type:'open_object'},
    {seq:2,t_ms:20,type:'commit'}
  ]),/time/);
});

test('trace normalization produces a replayable canonical sequence',()=>{
  const raw=[
    {seq:1,t_ms:0,type:'session_start'},
    {seq:2,t_ms:20,type:'provisional_commit',world:'shop',choice:'lite'},
    {seq:3,t_ms:21,type:'consequence_exposed',world:'shop',consequence:'bridge'},
    {seq:4,t_ms:40,type:'post_consequence_action',world:'shop',action:'change'},
    {seq:5,t_ms:55,type:'commit',world:'shop',choice:'pro'}
  ];
  const out=normalizer.normalizeTrace(meta,raw);
  assert.equal(out.events.length,5);
  assert.deepEqual(out.events.map(x=>x.event),[
    'session_start','provisional_action','consequence_exposed','post_consequence_action','commit'
  ]);
  assert.deepEqual(out.events.map(x=>x.seq),[1,2,3,4,5]);
});