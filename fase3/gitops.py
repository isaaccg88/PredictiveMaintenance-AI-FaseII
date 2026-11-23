"""Estado declarativo GitOps académico y registro de promoción/rollback.

Un router real usa este archivo para decidir el backend al recibir HTTP.
No es un operador Kubernetes ni prueba rollback de una VERSION diferente.
"""
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from .release import verify_manifest

HERE=Path(__file__).resolve().parent
STATE=HERE/"runtime"/"desired-state.json"
EVIDENCE=HERE/"evidence"
def read(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def atomic_write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    os.replace(tmp,path)
def utc():return datetime.now(timezone.utc).isoformat()
def event(state,kind,reason):
    entry={"at_utc":utc(),"type":kind,"reason":reason,
           "active_slot":state["active_slot"],"model_sha256":state["model_sha256"]}
    state["history"].append(entry)
    return entry
def save(state,path=STATE):
    atomic_write(path,state)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    atomic_write(EVIDENCE/"deployment_events.json",{
        "scope":"SIMULATED_EPHEMERAL_RUNNER",
        "events":state["history"],"state":state
    })
def init(path=STATE):
    manifest=verify_manifest()
    state={
        "schema_version":1, "environment":"academic-ci-staging", "synthetic":True,
        "industrial_release_authorized":False,
        "release_version":manifest["version"],
        "model_sha256":manifest["model_sha256"],"active_slot":"stable",
        "previous_slot":None,
        "routes":{
          "stable":"http://api-stable:8008",
          "candidate":"http://api-candidate:8008"
        },
        "history":[]
    }
    event(state,"INITIALIZE","Ambos contenedores reciben el mismo artefacto versionado")
    save(state,path);return state
def check_smoke(path,expected_sha,expected_endpoint):
    item=read(path)
    if item.get("status")!="PASS" or item.get("model_sha256")!=expected_sha:
        raise ValueError("Gate de despliegue sin PASS o hash distinto")
    if item.get("endpoint")!=expected_endpoint:
        raise ValueError("La prueba no examinó la URL esperada")
    if item.get("successful_predictions",0)<3:
        raise ValueError("Menos de tres predicciones comprobadas")
    if item.get("history_rows",0)<3:
        raise ValueError("SQLite no registra las inferencias")
    return item
def promote(validation,path=STATE):
    state=read(path)
    if state["active_slot"]!="stable":raise ValueError("No se promueve sobre un slot ya promovido")
    check_smoke(validation,state["model_sha256"],"http://127.0.0.1:8009")
    state["previous_slot"]="stable"
    state["active_slot"]="candidate"
    event(state,"PROMOTE","Candidate aprobado por modelo, API, inferencias y persistencia")
    save(state,path);return state
def rollback(failure,path=STATE):
    state=read(path);data=read(failure)
    if state["active_slot"]!="candidate" or state["previous_slot"]!="stable":
        raise ValueError("No hay candidata activa con stable al cual regresar")
    if not (data.get("status")=="EXPECTED_FAILURE"
        and data.get("serving_slot")=="candidate"
        and data.get("observed_status_code")==502):
        raise ValueError("No existe evidencia HTTP del fallo de candidata")
    state["active_slot"]="stable";state["previous_slot"]="candidate"
    event(state,"ROLLBACK","Respuesta 502 observada y restauración de tráfico a stable")
    save(state,path);return state
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=["init","promote","rollback","status"])
    parser.add_argument("--validation")
    parser.add_argument("--failure")
    parser.add_argument("--state",default=str(STATE))
    args=parser.parse_args()
    if args.command=="init":state=init(args.state)
    elif args.command=="promote":
        if not args.validation:parser.error("--validation obligatorio")
        state=promote(args.validation,args.state)
    elif args.command=="rollback":
        if not args.failure:parser.error("--failure obligatorio")
        state=rollback(args.failure,args.state)
    else:state=read(args.state)
    print(json.dumps({"active_slot":state["active_slot"],
        "version":state["release_version"],"events":len(state["history"])}))
if __name__=="__main__":main()
