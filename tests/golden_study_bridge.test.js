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
  assert.ok(studyHtml.includes("if(!$('agree').checked||!ROUTES[family])return"));
  assert.ok(studyHtml.includes("sessionStorage.setItem('paj_golden_study_v1'"));
  assert.ok(studyHtml.includes("consent_version:'golden-consent-v1'"));
  assert.ok(studyHtml.includes('crypto.randomUUID()'));
  assert.ok(!studyHtml.includes('localStorage.'));
  assert.ok(!studyHtml.includes('indexedDB'));
  assert.ok(!studyHtml.includes('PAJTransport'));
});

test('bridge lazy-loads normalizer and durable transport only inside consented flow',()=>{
  assert.ok(bridgeSource.includes("loadScript('golden-event-normalizer.js')"));
  assert.ok(bridgeSource.includes("loadScript('transport.js')"));
  assert.ok(bridgeSource.includes('await ensureDeps()'));
  assert.ok(bridgeSource.indexOf("if(!ctx)return {state:'preview'}") < bridgeSource.indexOf('await ensureDeps()'));
  assert.ok(bridgeSource.includes('createBrowserTransport(ENDPOINT)'));
  assert.ok(bridgeSource.includes('retryAll()'));
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