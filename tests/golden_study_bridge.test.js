const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const bridgeSource=fs.readFileSync('docs/golden-study-bridge.js','utf8');
const studyHtml=fs.readFileSync('docs/study.html','utf8');

test('Golden study bridge is valid JavaScript',()=>{
  assert.doesNotThrow(()=>new vm.Script(bridgeSource));
});

test('preview mode does not load persistence dependencies',()=>{
  const loaded=[];
  const store=new Map();
  const sandbox={
    window:null,
    location:{search:'?locale=en'},
    sessionStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)},
    document:{
      head:{appendChild:el=>loaded.push(el.src)},
      body:{appendChild(){}},
      createElement:()=>({style:{},dataset:{},hidden:false}),
      getElementById:()=>null
    },
    URLSearchParams,Date,Promise,
    queueMicrotask:fn=>{sandbox.queued=fn},
    addEventListener(){},
  };
  sandbox.window=sandbox;
  vm.createContext(sandbox);
  new vm.Script(bridgeSource).runInContext(sandbox);
  assert.equal(sandbox.PAJGoldenStudy.readContext(),null);
  assert.deepEqual(loaded,[]);
  assert.equal(sandbox.queued,undefined);
});

test('formal context requires explicit study flag, consent version, family, UUID and freshness',()=>{
  const store=new Map();
  const now=Date.now();
  const sandbox={
    window:null,
    location:{search:'?study=1&locale=en'},
    sessionStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)},
    document:{head:{appendChild(){}},body:{appendChild(){}},createElement:()=>({style:{},dataset:{}}),getElementById:()=>null},
    URLSearchParams,Date,Promise,queueMicrotask:()=>{},addEventListener(){},
  };
  sandbox.window=sandbox;
  vm.createContext(sandbox);
  new vm.Script(bridgeSource).runInContext(sandbox);
  const key=sandbox.PAJGoldenStudy.STUDY_KEY;
  store.set(key,JSON.stringify({consent_version:'golden-consent-v1',client_submission_id:'11111111-1111-4111-8111-111111111111',family:'PF06',locale:'en',issued_at:now,completed:false}));
  const ctx=sandbox.PAJGoldenStudy.readContext();
  assert.equal(ctx.family,'PF06');
  assert.equal(ctx.locale,'en');
  store.set(key,JSON.stringify({...ctx,consent_version:'wrong'}));
  assert.equal(sandbox.PAJGoldenStudy.readContext(),null);
  store.set(key,JSON.stringify({...ctx,consent_version:'golden-consent-v1',issued_at:now-(5*60*60*1000)}));
  assert.equal(sandbox.PAJGoldenStudy.readContext(),null);
});

test('study launcher writes sessionStorage only after explicit consent click',()=>{
  assert.ok(studyHtml.includes('id="agree" type="checkbox"'));
  assert.ok(studyHtml.includes("$('begin').disabled=true"));
  assert.ok(studyHtml.includes("if(!$('agree').checked||!JOURNEYS.has(journey))return"));
  assert.ok(studyHtml.includes("sessionStorage.setItem('paj_golden_study_v1'"));
  assert.ok(studyHtml.includes("consent_version:'golden-consent-v1'"));
  assert.ok(studyHtml.includes('crypto.randomUUID()'));
  assert.ok(studyHtml.includes("location.href='run.html?journey='"));
  assert.ok(!studyHtml.includes('?family=PF'));
  assert.ok(!studyHtml.includes('localStorage.'));
  assert.ok(!studyHtml.includes('indexedDB'));
  assert.ok(!studyHtml.includes('PAJTransport'));
});

test('bridge lazy-loads normalizer and durable transport only inside consented flow',()=>{
  assert.ok(bridgeSource.includes("loadScript('golden-event-normalizer.js')"));
  assert.ok(bridgeSource.includes("loadScript('transport.js')"));
  assert.ok(bridgeSource.includes('await ensureDeps()'));
  assert.ok(bridgeSource.indexOf("if(!ctx)return {state:'preview'}") < bridgeSource.indexOf('await ensureDeps()'));
  assert.ok(bridgeSource.includes("createBrowserTransport(ENDPOINT,{dbName:'paj-golden-study-queue-v1'})"));
  assert.ok(bridgeSource.includes('retryAll()'));
  assert.ok(bridgeSource.includes('lockFormalSurface(ctx)'));
  assert.ok(bridgeSource.includes("sel.disabled=true"));
});

test('formal submission carries stable consent and rich normalized raw events',()=>{
  for(const token of [
    'client_submission_id:ctx.client_submission_id',
    'consent_version:ctx.consent_version',
    'probe_family:ctx.family',
    "study_version:'golden-study-v1'",
    'raw_event:e.raw_event',
    'raw_event_type:e.raw_event_type',
    'envelope_version:e.envelope_version',
  ]) assert.ok(bridgeSource.includes(token),token);
});

test('consented completion submits one stable rich payload through the formal queue',async()=>{
  const store=new Map();
  const ctx={consent_version:'golden-consent-v1',client_submission_id:'22222222-2222-4222-8222-222222222222',family:'PF08',locale:'en',issued_at:Date.now(),completed:false};
  store.set('paj_golden_study_v1',JSON.stringify(ctx));
  const submitted=[];
  const statusEl={style:{},dataset:{},hidden:true,textContent:''};
  const localeEl={value:'en',disabled:false,setAttribute(){}};
  const sandbox={
    window:null,
    location:{search:'?study=1&locale=en'},
    sessionStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)},
    document:{
      readyState:'complete',
      head:{appendChild(){}},
      body:{appendChild(){}},
      createElement:()=>statusEl,
      getElementById:id=>id==='locale'?localeEl:id==='goldenStudyStatus'?null:null
    },
    URLSearchParams,Date,Promise,
    queueMicrotask:()=>{},
    addEventListener(){},
    PAJGoldenEvents:{normalizeTrace:(meta,events)=>({events:events.map(e=>({
      seq:e.seq,t_ms:e.t_ms,event:e.type,world:e.world,target:e.object,
      envelope_version:'golden-event-envelope-v1',raw_event_type:e.type,raw_event:e
    }))})},
    PAJTransport:{createBrowserTransport:(endpoint,opts)=>{
      assert.equal(opts.dbName,'paj-golden-study-queue-v1');
      return {
        submit:async payload=>{submitted.push(payload);return {state:'saved',session_id:'33333333-3333-4333-8333-333333333333',client_submission_id:payload.client_submission_id}},
        retryAll:async()=>[]
      };
    }}
  };
  sandbox.window=sandbox;
  vm.createContext(sandbox);
  new vm.Script(bridgeSource).runInContext(sandbox);
  const result=await sandbox.PAJGoldenStudy.complete({
    family:'PF08',instrument_version:'golden-pf08-v1',locale:'en',market:'US',
    world_variant:'golden-open-workspaces-v1',terminal_action:'hold',
    events:[{seq:1,t_ms:15,type:'open_detail',world:'seed',object:'record_r17',relation:'rg'}]
  });
  assert.equal(result.state,'saved');
  assert.equal(submitted.length,1);
  const payload=submitted[0];
  assert.equal(payload.client_submission_id,ctx.client_submission_id);
  assert.equal(payload.consent_version,'golden-consent-v1');
  assert.equal(payload.probe_family,'PF08');
  assert.equal(payload.market,'US');
  assert.equal(payload.events[0].raw_event.relation,'rg');
  const stored=JSON.parse(store.get('paj_golden_study_v1'));
  assert.equal(stored.completed,true);
  assert.equal(stored.session_id,'33333333-3333-4333-8333-333333333333');
  assert.equal(localeEl.disabled,true);
});

test('formal completion refuses a family or locale mismatch before submission',async()=>{
  const store=new Map();
  store.set('paj_golden_study_v1',JSON.stringify({consent_version:'golden-consent-v1',client_submission_id:'44444444-4444-4444-8444-444444444444',family:'PF06',locale:'en',issued_at:Date.now(),completed:false}));
  let calls=0;
  const localeEl={value:'en',disabled:false,setAttribute(){}};
  const sandbox={
    window:null,location:{search:'?study=1&locale=en'},
    sessionStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)},
    document:{readyState:'complete',head:{appendChild(){}},body:{appendChild(){}},createElement:()=>({style:{},dataset:{},hidden:true}),getElementById:id=>id==='locale'?localeEl:null},
    URLSearchParams,Date,Promise,queueMicrotask:()=>{},addEventListener(){},
    PAJGoldenEvents:{normalizeTrace:()=>({events:[]})},
    PAJTransport:{createBrowserTransport:()=>({submit:async()=>{calls++;return {state:'saved',session_id:'x'}},retryAll:async()=>[]})}
  };
  sandbox.window=sandbox;vm.createContext(sandbox);new vm.Script(bridgeSource).runInContext(sandbox);
  await assert.rejects(()=>sandbox.PAJGoldenStudy.complete({family:'PF07',instrument_version:'golden-pf07-v1',locale:'en',market:'US',events:[{type:'x'}]}),/study_family_mismatch/);
  await assert.rejects(()=>sandbox.PAJGoldenStudy.complete({family:'PF06',instrument_version:'golden-pf06-v1',locale:'fr',market:'FR',events:[{type:'x'}]}),/study_locale_mismatch/);
  assert.equal(calls,0);
});
