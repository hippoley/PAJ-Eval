import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.116.0";

const ALLOWED_ORIGINS=new Set(["https://hippoley.github.io","http://localhost:8000","http://127.0.0.1:8000"]);
const ALLOWED_LOCALES=new Set(["en","zh-CN","zh-TW","ja","ko","es","fr","de","pt","ru"]);
const originHeaders=(req:Request)=>{const o=req.headers.get("origin")||"";return {"Access-Control-Allow-Origin":ALLOWED_ORIGINS.has(o)?o:"https://hippoley.github.io","Vary":"Origin","Access-Control-Allow-Headers":"content-type","Access-Control-Allow-Methods":"POST,OPTIONS"}};
const reply=(req:Request,x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{...originHeaders(req),"Content-Type":"application/json","Cache-Control":"no-store"}});
const clean=(v:unknown,n:number)=>typeof v==="string"?v.slice(0,n):"";
const finiteMs=(v:unknown)=>{const n=Number(v);return Number.isFinite(n)?Math.min(86400000,Math.max(0,Math.trunc(n))):0};
const safeNumber=(v:unknown)=>{const n=Number(v);return Number.isFinite(n)?Math.max(-1e12,Math.min(1e12,n)):null};

const sanitizeJson=(value:unknown,depth=0):unknown=>{
  if(depth>4)return null;
  if(value===null||typeof value==="boolean")return value;
  if(typeof value==="string")return value.slice(0,500);
  if(typeof value==="number")return safeNumber(value);
  if(Array.isArray(value))return value.slice(0,32).map(v=>sanitizeJson(v,depth+1));
  if(value&&typeof value==="object"){
    const out:Record<string,unknown>={};
    for(const [k,v] of Object.entries(value as Record<string,unknown>).slice(0,40)){
      if(!/^[A-Za-z0-9_:-]{1,80}$/.test(k))continue;
      out[k]=sanitizeJson(v,depth+1);
    }
    return out;
  }
  return null;
};

Deno.serve(async(req)=>{
  const origin=req.headers.get("origin")||"";
  if(origin&&!ALLOWED_ORIGINS.has(origin))return reply(req,{error:"origin_not_allowed"},403);
  if(req.method==="OPTIONS")return new Response("ok",{headers:originHeaders(req)});
  if(req.method!=="POST")return reply(req,{error:"method_not_allowed"},405);
  const len=Number(req.headers.get("content-length")||0);
  if(Number.isFinite(len)&&len>131072)return reply(req,{error:"payload_too_large"},413);
  try{
    const body=await req.json();
    const locale=clean(body?.locale,16), instrument=clean(body?.instrument_version||"probe-player-v4.1",80), family=clean(body?.probe_family,16), world=clean(body?.world_variant||"default",100), terminal=clean(body?.terminal_action,160), submission=clean(body?.client_submission_id,36);
    const raw=body?.events;
    if(!ALLOWED_LOCALES.has(locale)||!family||!submission||!Array.isArray(raw)||raw.length<1||raw.length>250)return reply(req,{error:"invalid_payload"},400);
    if(!/^[0-9a-f-]{36}$/i.test(submission)||!/^PF0[1-8]$/.test(family))return reply(req,{error:"invalid_identifier"},400);
    const events=raw.map((e:any,i:number)=>{
      const safe=(sanitizeJson(e,0)||{}) as Record<string,unknown>;
      const rawEvent=String(e?.event||e?.type||"");
      const rawTarget=e?.target??e?.object??e?.action??e?.choice??e?.to_world;
      const rawScreen=e?.screen??e?.world;
      const clientSeq=Number(e?.seq);
      return {
        ...safe,
        seq:i+1,
        client_seq:Number.isFinite(clientSeq)?Math.max(1,Math.trunc(clientSeq)):i+1,
        t:finiteMs(e?.t??e?.t_ms),
        event:/^[a-z][a-z0-9_:-]{0,79}$/i.test(rawEvent)?clean(rawEvent,80):"unknown",
        target:clean(rawTarget,160),
        screen:clean(rawScreen,80),
        locale:ALLOWED_LOCALES.has(clean(e?.locale,16))?clean(e.locale,16):locale,
        phase:clean(e?.phase,40)
      };
    });
    const sb=createClient(Deno.env.get("SUPABASE_URL")!,Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
    const {data,error}=await sb.rpc("ingest_probe_atomic",{
      p_submission:submission,p_locale:locale,p_instrument:instrument,p_family:family,p_world:world,p_terminal:terminal,p_events:events
    });
    if(error)throw error;
    const row=Array.isArray(data)?data[0]:data;
    if(!row?.session_id)throw new Error("missing_session_id");
    return reply(req,{ok:true,duplicate:Boolean(row.duplicate),session_id:row.session_id,event_count:Number(row.event_count||events.length)});
  }catch(e){console.error(e);return reply(req,{error:"ingest_failed"},500)}
});
