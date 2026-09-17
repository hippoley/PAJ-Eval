import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.116.0";

const ALLOWED_ORIGINS=new Set(["https://hippoley.github.io","http://localhost:8000","http://127.0.0.1:8000"]);
const cors=(req:Request)=>{const o=req.headers.get("origin")||"";return {"Access-Control-Allow-Origin":ALLOWED_ORIGINS.has(o)?o:"https://hippoley.github.io","Vary":"Origin","Access-Control-Allow-Headers":"authorization,content-type","Access-Control-Allow-Methods":"GET,OPTIONS"}};
const json=(req:Request,x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{...cors(req),"Content-Type":"application/json","Cache-Control":"no-store"}});

Deno.serve(async(req)=>{
  if(req.method==="OPTIONS")return new Response("ok",{headers:cors(req)});
  const origin=req.headers.get("origin")||"";
  if(origin&&!ALLOWED_ORIGINS.has(origin))return json(req,{error:"origin_not_allowed"},403);
  if(req.method!=="GET")return json(req,{error:"method_not_allowed"},405);
  const auth=req.headers.get("authorization")||"";
  const token=auth.startsWith("Bearer ")?auth.slice(7):"";
  if(!token)return json(req,{error:"missing_user_token"},401);

  const sb=createClient(Deno.env.get("SUPABASE_URL")!,Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const {data:{user},error:ue}=await sb.auth.getUser(token);
  if(ue||!user)return json(req,{error:"invalid_user"},401);
  if(user.app_metadata?.role!=="researcher")return json(req,{error:"researcher_role_required"},403);

  const url=new URL(req.url);
  const sessionId=url.searchParams.get("session_id");
  if(sessionId){
    const {data:s,error:se}=await sb.from("sessions").select("session_id,created_at,completed_at,locale,consent_version,instrument_version,assignment_id,treatment_arm,status").eq("session_id",sessionId).single();
    if(se)return json(req,{error:"not_found"},404);
    const {data:r}=await sb.from("probe_runs").select("probe_run_id,probe_family,world_variant,started_at,completed_at,terminal_action").eq("session_id",sessionId).order("started_at");
    const {data:e}=await sb.from("events").select("event_id,probe_run_id,seq,occurred_at,elapsed_ms,event_type,object_id,payload_json").eq("session_id",sessionId).order("seq");
    const runIds=(r||[]).map(x=>x.probe_run_id);
    let features:any[]=[];
    if(runIds.length){const q=await sb.from("derived_features").select("feature_id,probe_run_id,extractor_version,feature_name,feature_value,evidence_event_ids").in("probe_run_id",runIds);features=q.data||[]}
    const {data:v}=await sb.from("evaluations").select("evaluation_id,scoring_version,construct,estimate,uncertainty,evidence_feature_ids,validation_status").eq("session_id",sessionId);
    return json(req,{session:s,probe_runs:r||[],events:e||[],derived_features:features,evaluations:v||[]});
  }

  const limit=Math.min(100,Math.max(1,Number(url.searchParams.get("limit")||50)));
  const {data,error}=await sb.from("sessions").select("session_id,created_at,completed_at,locale,instrument_version,status").order("created_at",{ascending:false}).limit(limit);
  if(error)throw error;
  return json(req,{sessions:data||[]});
});
