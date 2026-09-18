(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  root.PAJTransport=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  function sleep(ms){return new Promise(r=>setTimeout(r,ms));}

  function createTransport(opts){
    const queue=opts.queue;
    const post=opts.post;
    const idFactory=opts.idFactory||(()=>crypto.randomUUID());
    const now=opts.now||(()=>Date.now());
    const inFlight=new Map();

    async function submit(payload){
      const item={...payload};
      if(!item.client_submission_id) item.client_submission_id=idFactory();
      if(!item.created_at_client) item.created_at_client=new Date(now()).toISOString();
      const id=item.client_submission_id;
      if(inFlight.has(id)) return inFlight.get(id);
      const work=(async()=>{
        // Durable queue commit happens before any network attempt.
        await queue.put(item);
        try{
          const ack=await post(item);
          if(!ack||ack.ok!==true||!ack.session_id) throw new Error('invalid_ack');
          await queue.delete(id);
          return {state:'saved',session_id:ack.session_id,client_submission_id:id};
        }catch(error){
          return {state:'queued',error:String(error&&error.message||error),client_submission_id:id};
        }finally{
          inFlight.delete(id);
        }
      })();
      inFlight.set(id,work);
      return work;
    }

    async function retryAll(){
      const rows=(await queue.all()).slice().sort((a,b)=>String(a.created_at_client||'').localeCompare(String(b.created_at_client||'')));
      const out=[];
      for(const item of rows){
        const r=await submit(item);
        out.push(r);
        if(r.state!=='saved') break;
      }
      return out;
    }

    async function pending(){return (await queue.all()).length;}
    return {submit,retryAll,pending};
  }

  function openBrowserQueue(dbName='paj-eval-queue-v2',storeName='submissions'){
    let dbPromise;
    function db(){
      if(dbPromise) return dbPromise;
      dbPromise=new Promise((resolve,reject)=>{
        const r=indexedDB.open(dbName,1);
        r.onupgradeneeded=()=>{
          const d=r.result;
          if(!d.objectStoreNames.contains(storeName)) d.createObjectStore(storeName,{keyPath:'client_submission_id'});
        };
        r.onsuccess=()=>resolve(r.result);
        r.onerror=()=>reject(r.error);
      });
      return dbPromise;
    }
    async function tx(mode,fn){
      const d=await db();
      return new Promise((resolve,reject)=>{
        const t=d.transaction(storeName,mode);const s=t.objectStore(storeName);let request,result;
        try{request=fn(s);}catch(e){reject(e);return;}
        if(request&&typeof request.onsuccess!=='undefined') request.onsuccess=()=>{result=request.result;};
        if(request&&typeof request.onerror!=='undefined') request.onerror=()=>reject(request.error);
        t.oncomplete=()=>resolve(result);
        t.onerror=()=>reject(t.error);
        t.onabort=()=>reject(t.error||new Error('indexeddb_aborted'));
      });
    }
    return {
      put:item=>tx('readwrite',s=>s.put(item)),
      delete:id=>tx('readwrite',s=>s.delete(id)),
      all:()=>tx('readonly',s=>s.getAll())
    };
  }

  function createBrowserTransport(endpoint,opts={}){
    const queue=openBrowserQueue(opts.dbName||'paj-eval-queue-v2',opts.storeName||'submissions');
    const post=async payload=>{
      const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      let j={};try{j=await r.json();}catch{}
      if(!r.ok||!j.ok) throw new Error(j.error||('http_'+r.status));
      return j;
    };
    return createTransport({queue,post});
  }

  return {createTransport,openBrowserQueue,createBrowserTransport,sleep};
});
