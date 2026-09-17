const test=require('node:test');
const assert=require('node:assert/strict');
const {createTransport}=require('../docs/transport.js');

function memoryQueue(log=[]){
  const rows=new Map();
  return {
    async put(v){log.push('queue:put:'+v.client_submission_id);rows.set(v.client_submission_id,structuredClone(v));},
    async delete(id){log.push('queue:delete:'+id);rows.delete(id);},
    async all(){return [...rows.values()].map(v=>structuredClone(v));}
  };
}

test('queue commit precedes the first network attempt',async()=>{
  const log=[];const queue=memoryQueue(log);
  const t=createTransport({queue,idFactory:()=> 'first-id',post:async p=>{log.push('post:'+p.client_submission_id);return {ok:true,session_id:'s1'};}});
  const r=await t.submit({events:[]});
  assert.equal(r.state,'saved');
  assert.deepEqual(log,['queue:put:first-id','post:first-id','queue:delete:first-id']);
});

test('offline submission survives and retries with the same id',async()=>{
  const queue=memoryQueue();let online=false;const seen=[];
  const t=createTransport({
    queue,
    idFactory:()=> 'submission-1',
    now:()=>0,
    post:async p=>{seen.push(p.client_submission_id);if(!online)throw new Error('offline');return {ok:true,session_id:'session-1'};}
  });
  const payload={instrument_version:'probe-player-v4.1',probe_family:'PF01',events:[{seq:1,event:'probe_started'}]};
  const first=await t.submit(payload);
  assert.equal(first.state,'queued');
  assert.equal(await t.pending(),1);
  assert.equal((await queue.all())[0].client_submission_id,'submission-1');
  online=true;
  const retry=await t.retryAll();
  assert.equal(retry[0].state,'saved');
  assert.equal(retry[0].session_id,'session-1');
  assert.equal(await t.pending(),0);
  assert.deepEqual(seen,['submission-1','submission-1']);
});

test('concurrent duplicate submission is coalesced',async()=>{
  const queue=memoryQueue();let calls=0;
  const t=createTransport({queue,post:async p=>{calls++;await new Promise(r=>setTimeout(r,10));return {ok:true,session_id:'session-x'};}});
  const p={client_submission_id:'same-id',instrument_version:'probe-player-v4.1',events:[]};
  const [a,b]=await Promise.all([t.submit(p),t.submit(p)]);
  assert.equal(a.state,'saved');assert.equal(b.state,'saved');assert.equal(calls,1);assert.equal(await t.pending(),0);
});

test('retry preserves queue order and stops after the first failure',async()=>{
  const queue=memoryQueue();
  await queue.put({client_submission_id:'a',created_at_client:'2026-01-01T00:00:00.000Z'});
  await queue.put({client_submission_id:'b',created_at_client:'2026-01-01T00:00:01.000Z'});
  await queue.put({client_submission_id:'c',created_at_client:'2026-01-01T00:00:02.000Z'});
  const seen=[];
  const t=createTransport({queue,post:async p=>{seen.push(p.client_submission_id);if(p.client_submission_id==='b')throw new Error('network');return {ok:true,session_id:'s-'+p.client_submission_id};}});
  const out=await t.retryAll();
  assert.deepEqual(seen,['a','b']);
  assert.deepEqual(out.map(x=>x.state),['saved','queued']);
  assert.deepEqual((await queue.all()).map(x=>x.client_submission_id),['b','c']);
});
