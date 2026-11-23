"""Estado declarativo GitOps académico: dos versiones reales y rollback de modelo.

El router enruta por desired-state.json. Cada slot expone un modelo con SHA
diferente y la reversión exige evidencia cuantitativa de degradación HTTP.
El entorno permanece efímero; no sustituye un reconciliador GitOps cloud.
"""
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
from .release import verify_manifest

HERE=Path(__file__).resolve().parent
STATE=HERE/"runtime"/"desired-state.json"
EVIDENCE=HERE/"evidence"
CANDIDATE=EVIDENCE/"candidate_release_manifest.json"

def read(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def atomic_write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    os.replace(tmp,path)
def utc():return datetime.now(timezone.utc).isoformat()

def versions():
    stable=verify_manifest()
    candidate=read(CANDIDATE)
    p=HERE/"build/candidate/model_v2.joblib"
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=candidate["model_sha256"]:
        raise ValueError("Artefacto candidate alterado")
    if candidate["stable_parent_sha256"]!=stable["model_sha256"] or candidate["model_sha256"]==stable["model_sha256"]:
        raise ValueError("Se requieren dos modelos diferentes relacionados")
    if not all(v["passed"] for v in candidate["quality_gates"].values()):
        raise ValueError("Candidate no aprobó métricas offline")
    if stable.get("industrial_release_authorized") is not False or candidate.get("industrial_release_authorized") is not False:
        raise ValueError("Solo se autorizó staging académico")
    return {"stable":{"version":stable["version"],"sha256":stable["model_sha256"]},
            "candidate":{"version":candidate["version"],"sha256":candidate["model_sha256"]}}

def sync_active(state):
    current=state["models"][state["active_slot"]]
    state["model_sha256"]=current["sha256"]
    state["release_version"]=current["version"]

def event(state,kind,reason):
    sync_active(state)
    entry={"at_utc":utc(),"type":kind,"reason":reason,
           "active_slot":state["active_slot"],
           "model_sha256":state["model_sha256"],
           "release_version":state["release_version"]}
    state["history"].append(entry)
    return entry

def save(state,path=STATE):
    sync_active(state)
    atomic_write(path,state)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    atomic_write(EVIDENCE/"deployment_events.json",{
        "scope":"SIMULATED_EPHEMERAL_RUNNER_TWO_REAL_MODEL_VERSIONS",
        "events":state["history"],"state":state
    })

def init(path=STATE):
    models=versions()
    state={"schema_version":2,"environment":"academic-ci-staging",
        "synthetic":True,"industrial_release_authorized":False,
        "active_slot":"stable","previous_slot":None,"models":models,
        "routes":{"stable":"http://api-stable:8008",
                  "candidate":"http://api-candidate:8008"},
        "history":[]}
    event(state,"INITIALIZE","Stable 130 árboles y candidata 135 árboles: SHA distintos")
    save(state,path)
    return state

def check_smoke(path,expected_sha,expected_endpoint):
    item=read(path)
    if item.get("status")!="PASS" or item.get("model_sha256")!=expected_sha:
        raise ValueError("Smoke no aprobó o hash incompatible")
    if item.get("endpoint")!=expected_endpoint or item.get("successful_predictions",0)<3:
        raise ValueError("Endpoint incorrecto o pocas inferencias")
    if item.get("history_rows",0)<3:raise ValueError("No existe persistencia de predicciones")
    return item

def promote(validation,path=STATE):
    state=read(path)
    if state["active_slot"]!="stable":raise ValueError("El slot ya fue promovido")
    check_smoke(validation,state["models"]["candidate"]["sha256"],"http://127.0.0.1:8009")
    state["previous_slot"]="stable";state["active_slot"]="candidate"
    event(state,"PROMOTE","Modelo candidato distinto promovido después de quality gates y smoke")
    save(state,path)
    return state

def rollback(failure,path=STATE):
    state=read(path)
    evidence=read(failure)
    if state["active_slot"]!="candidate" or state["previous_slot"]!="stable":
        raise ValueError("No existe candidata activa para revertir")
    if not (
        evidence.get("status")=="DEGRADED"
        and evidence.get("serving_slot")=="candidate"
        and evidence.get("model_sha256")==state["models"]["candidate"]["sha256"]
        and evidence.get("endpoint")=="http://127.0.0.1:8010"
        and evidence.get("samples",0)>=5
        and evidence.get("http_2xx_count")==evidence.get("samples")
        and evidence.get("p95_ms",0)>evidence.get("threshold_ms",500)
    ):
        raise ValueError("Rollback rechazado: no se demostró degradación de candidata")
    state["active_slot"]="stable";state["previous_slot"]="candidate"
    event(state,"ROLLBACK_MODEL","Degradación p95 HTTP medida; recuperación de SHA estable previo")
    save(state,path)
    return state

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("command",choices=["init","promote","rollback","status"])
    ap.add_argument("--validation");ap.add_argument("--failure")
    ap.add_argument("--state",default=str(STATE))
    args=ap.parse_args()
    if args.command=="init":state=init(args.state)
    elif args.command=="promote":
        if not args.validation:ap.error("--validation requerido")
        state=promote(args.validation,args.state)
    elif args.command=="rollback":
        if not args.failure:ap.error("--failure requerido")
        state=rollback(args.failure,args.state)
    else:state=read(args.state)
    print(json.dumps({"active_slot":state["active_slot"],
      "version":state["release_version"],"sha":state["model_sha256"],"events":len(state["history"])}))
if __name__=="__main__":main()
