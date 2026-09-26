(function(root){
  const VERSION='golden-event-envelope-v1';
  const TYPE_ALIASES={
    provisional_commit:'provisional_action',
    workspace_transition:'transfer_world_entry'
  };
  function clone(value){return value==null?value:JSON.parse(JSON.stringify(value))}
  function normalizeEvent(meta,raw,index){
    if(!raw||typeof raw!=='object') throw new TypeError('raw event must be an object');
    const rawType=String(raw.type||raw.event||'').trim();
    if(!rawType) throw new TypeError('raw event type is required');
    const event=TYPE_ALIASES[rawType]||rawType;
    const seq=Number.isInteger(raw.seq)?raw.seq:index+1;
    const tMs=Number.isFinite(raw.t_ms)?raw.t_ms:Number.isFinite(raw.t)?raw.t:null;
    const world=raw.world||raw.screen||null;
    const target=raw.object||raw.target||raw.action||raw.choice||raw.to_world||null;
    return {
      envelope_version:VERSION,
      family:meta.family,
      locale:meta.locale,
      market:meta.market,
      instrument_version:meta.instrument_version,
      seq,
      t_ms:tMs,
      event,
      world,
      target,
      raw_event_type:rawType,
      raw_event:clone(raw)
    };
  }
  function validateMeta(meta){
    if(!meta||typeof meta!=='object') throw new TypeError('meta is required');
    for(const key of ['family','locale','market','instrument_version']){
      if(typeof meta[key]!=='string'||!meta[key].trim()) throw new TypeError(key+' is required');
    }
  }
  function normalizeTrace(meta,events){
    validateMeta(meta);
    if(!Array.isArray(events)) throw new TypeError('events must be an array');
    const normalized=events.map((e,i)=>normalizeEvent(meta,e,i));
    for(let i=1;i<normalized.length;i++){
      if(normalized[i].seq<=normalized[i-1].seq) throw new Error('event sequence must be strictly increasing');
      if(normalized[i].t_ms!=null&&normalized[i-1].t_ms!=null&&normalized[i].t_ms<normalized[i-1].t_ms) throw new Error('event time must be nondecreasing');
    }
    return {
      envelope_version:VERSION,
      family:meta.family,
      locale:meta.locale,
      market:meta.market,
      instrument_version:meta.instrument_version,
      events:normalized
    };
  }
  const api={VERSION,normalizeEvent,normalizeTrace};
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
  root.PAJGoldenEvents=api;
})(typeof window!=='undefined'?window:globalThis);
