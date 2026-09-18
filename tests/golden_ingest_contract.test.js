const test=require('node:test');
const assert=require('node:assert/strict');

async function load(){
  return import('../supabase/functions/ingest-probe/contract.mjs?ts='+Date.now());
}

function validEvent(seq,type,t=seq*10){
  return {
    seq,t,event:type,locale:'en',market:'US',study_version:'golden-study-v1',
    envelope_version:'golden-event-envelope-v1',raw_event_type:type,
    raw_event:{seq,t_ms:t,type,world:'seed'}
  };
}

test('strict Golden contract accepts a complete PF08 trace',async()=>{
  const {validateGoldenSubmission}=await load();
  const events=[
    validEvent(1,'session_start'),
    validEvent(2,'open_object'),
    validEvent(3,'commit'),
    validEvent(4,'session_complete')
  ];
  assert.equal(validateGoldenSubmission({
    locale:'en',consent:'golden-consent-v1',instrument:'golden-pf08-v1',
    family:'PF08',world:'golden-open-workspaces-v1',studyVersion:'golden-study-v1',
    market:'US',events
  }),null);
});

test('Golden instrument family world consent and market are bound together',async()=>{
  const {validateGoldenSubmission}=await load();
  const events=[validEvent(1,'session_start'),validEvent(2,'open_object'),validEvent(3,'commit'),validEvent(4,'session_complete')];
  const base={locale:'en',consent:'golden-consent-v1',instrument:'golden-pf08-v1',family:'PF08',world:'golden-open-workspaces-v1',studyVersion:'golden-study-v1',market:'US',events};
  assert.equal(validateGoldenSubmission({...base,family:'PF07'}),'golden_contract_mismatch');
  assert.equal(validateGoldenSubmission({...base,world:'golden-three-world-v1'}),'golden_contract_mismatch');
  assert.equal(validateGoldenSubmission({...base,consent:'v1'}),'golden_consent_required');
  assert.equal(validateGoldenSubmission({...base,market:'GB'}),'golden_market_mismatch');
});

test('Golden trace requires normalized envelope raw evidence and terminal shape',async()=>{
  const {validateGoldenSubmission}=await load();
  const base={locale:'en',consent:'golden-consent-v1',instrument:'golden-challenge-v2',family:'PF01',world:'golden-three-world-v1',studyVersion:'golden-study-v1',market:'US'};
  const ok=[validEvent(1,'session_start'),validEvent(2,'open_object'),validEvent(3,'commit'),validEvent(4,'session_complete')];
  assert.equal(validateGoldenSubmission({...base,events:ok.map((e,i)=>({...e,seq:i+1}))}),null);
  assert.equal(validateGoldenSubmission({...base,events:ok.map((e,i)=>i===1?{...e,envelope_version:'bad'}:e)}),'golden_envelope_required');
  assert.equal(validateGoldenSubmission({...base,events:ok.slice(1)}),'golden_trace_too_short');
  const noCommit=[validEvent(1,'session_start'),validEvent(2,'open_object'),validEvent(3,'open_detail'),validEvent(4,'session_complete')];
  assert.equal(validateGoldenSubmission({...base,events:noCommit}),'golden_commit_required');
});

test('Golden trace rejects sequence time locale and event metadata drift',async()=>{
  const {validateGoldenSubmission}=await load();
  const base={locale:'en',consent:'golden-consent-v1',instrument:'golden-pf06-v1',family:'PF06',world:'golden-three-world-v1',studyVersion:'golden-study-v1',market:'US'};
  const ok=[validEvent(1,'session_start',0),validEvent(2,'open_object',10),validEvent(3,'commit',20),validEvent(4,'session_complete',30)];
  assert.equal(validateGoldenSubmission({...base,events:ok.map((e,i)=>i===2?{...e,seq:2}:e)}),'golden_sequence_invalid');
  assert.equal(validateGoldenSubmission({...base,events:ok.map((e,i)=>i===2?{...e,t:5}:e)}),'golden_time_invalid');
  assert.equal(validateGoldenSubmission({...base,events:ok.map((e,i)=>i===1?{...e,locale:'fr'}:e)}),'golden_event_locale_mismatch');
  assert.equal(validateGoldenSubmission({...base,events:ok.map((e,i)=>i===1?{...e,market:'FR'}:e)}),'golden_event_market_mismatch');
});

test('legacy non-Golden submissions are not forced through the Golden contract',async()=>{
  const {validateGoldenSubmission,isGoldenAttempt}=await load();
  assert.equal(isGoldenAttempt({consent:'v1',instrument:'probe-player-v4.4',studyVersion:''}),false);
  assert.equal(validateGoldenSubmission({locale:'en',consent:'v1',instrument:'probe-player-v4.4',family:'PF01',world:'default',studyVersion:'',market:'',events:[]}),null);
});
