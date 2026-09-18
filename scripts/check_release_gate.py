import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GATE=json.loads((ROOT/"RELEASE_GATE.json").read_text(encoding="utf-8"))

def require(cond,msg):
    if not cond:
        raise SystemExit("release-gate source contract failed: "+msg)

def main():
    require(GATE["schema_version"]=="paj-release-gate-v1","unexpected schema version")
    source=GATE["source_contract"]
    for key,val in source.items():
        require(val is True,f"{key} must be true before merge")

    backend=GATE["deployed_backend"]
    require(backend["consent_aware_ingestion_v4"] is True,"v4 ingestion migration not recorded")
    require(backend["research_replay_indexes"] is True,"replay indexes not recorded")
    require(backend["ingest_probe_version"]>=4,"ingest-probe version must be >=4")
    require(backend["research_sessions_version"]>=3,"research-sessions version must be >=3")
    require(backend["database_rpc_smoke"] is True,"database/RPC smoke not recorded")

    op=GATE["operational"]
    blockers=[]
    if int(op.get("researcher_accounts",0))<1:
        blockers.append("researcher_account_missing")
    if not op.get("consented_browser_http_smoke"):
        blockers.append("consented_browser_http_smoke_missing")
    if not op.get("authenticated_researcher_replay_smoke"):
        blockers.append("authenticated_researcher_replay_smoke_missing")

    release=GATE["release"]
    expected_status="ready" if not blockers else "blocked"
    require(release.get("status")==expected_status,"release.status disagrees with operational evidence")
    require(sorted(release.get("blockers",[]))==sorted(blockers),"release.blockers disagree with operational evidence")

    print(json.dumps({
        "source_gate":"pass",
        "backend_gate":"pass",
        "operational_release":expected_status,
        "blockers":blockers,
    },ensure_ascii=False))

if __name__=="__main__":
    main()
