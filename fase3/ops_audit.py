"""Auditoría de cambios entre versiones de modelo y recuperación real HTTP.

Los resultados son del runner Docker efímero. El umbral es diagnóstico.
"""
from __future__ import annotations
import json, statistics
from datetime import datetime,timezone
from pathlib import Path
import requests
from .release import verify_manifest
from .gitops import read,CANDIDATE

HERE=Path(__file__).resolve().parent
EV=HERE/"evidence"
def main():
    stable=verify_manifest()
    candidate=read(CANDIDATE)
    state=read(HERE/"runtime/desired-state.json")
    events=read(EV/"deployment_events.json")["events"]
    stages=[x["type"] for x in events]
    if stages!=["INITIALIZE","PROMOTE","ROLLBACK_MODEL","PROMOTE"]:
        raise AssertionError("Secuencia de promoción/rollback distinta a la validada")
    if state["active_slot"]!="candidate" or state["model_sha256"]!=candidate["model_sha256"]:
        raise AssertionError("La versión final no coincide con candidate")
    promoted=read(EV/"router_promoted.json")
    restored=read(EV/"router_restored.json")
    final=read(EV/"router_final.json")
    degraded=read(EV/"router_degradation.json")
    for item,expected in [(promoted,candidate),(restored,stable),(final,candidate)]:
        if item["status"]!="PASS" or item["model_sha256"]!=expected["model_sha256"]:
            raise AssertionError("El servicio no mostró el modelo correcto por HTTP")
    if stable["model_sha256"]==candidate["model_sha256"]:
        raise AssertionError("No hubo dos versiones reales de modelo")
    if degraded.get("p95_ms",0)<=500 or degraded["model_sha256"]!=candidate["model_sha256"]:
        raise AssertionError("Falta deterioro HTTP verificable asociado al candidato")
    online=requests.get("http://127.0.0.1:8010/model/info",timeout=10)
    online.raise_for_status()
    if online.json()["model_sha256"]!=candidate["model_sha256"]:
        raise AssertionError("Modelo final del router incorrecto")
    m=requests.get("http://127.0.0.1:8010/metrics",timeout=10).json()
    values=[x["duration_ms"] for x in m.get("measurements",[])]
    if len(values)<3:raise AssertionError("Muestra HTTP demasiado pequeña")
    valid=sum(x["status"]==200 for x in m["measurements"])
    p95=float(statistics.quantiles(values,n=100,method="inclusive")[94])
    o={"scope":"SYNTHETIC_EPHEMERAL_DOCKER_CI",
       "industrial_deployment":False,"synthetic_data":True,
       "observed_at_utc":datetime.now(timezone.utc).isoformat(),
       "release_version":candidate["version"],
       "model_sha256":candidate["model_sha256"],
       "stable_version":stable["version"],
       "stable_model_sha256":stable["model_sha256"],
       "versions_distinct":True,"active_slot":"candidate",
       "mlflow_run_id":stable["mlflow_run_id"],
       "api_predict_samples":len(values),
       "api_http_5xx":sum(x["status"]>=500 for x in m["measurements"]),
       "api_availability_ratio":valid/len(values),
       "api_timely_ratio":sum(x["status"]==200 and x["duration_ms"]<=500 for x in m["measurements"])/len(values),
       "api_latency_p95_ms":round(p95,3),
       "candidate_latency_regression_p95_ms":degraded["p95_ms"],
       "candidate_latency_threshold_ms":500,
       "promotions":stages.count("PROMOTE"),
       "rollback_events":stages.count("ROLLBACK_MODEL"),
       "model_version_rollback_verified":True,
       "rollback_from_sha256":candidate["model_sha256"],
       "rollback_to_sha256":stable["model_sha256"],
       "recovery_predictions":restored["successful_predictions"],
       "limitations":[
           "Candidate model is genuinely distinct (135 vs 130 trees), but both use a fixed synthetic dataset.",
           "Degradation is a controlled service latency fault injected AFTER promotion, not a natural accuracy decline.",
           "Rollback restores previous model hash via routing but does not migrate SQL state across slots.",
           "Backend /metrics omits the router-side regression; it is measured at the gateway separately.",
           "No multi-AZ, cloud deployment, sustained SLO measurement or live industrial data."],
       "evidence":{"version_comparison":"fase3/evidence/model_version_comparison.json",
          "degradation":"fase3/evidence/router_degradation.json",
          "promoted":"fase3/evidence/router_promoted.json",
          "restored":"fase3/evidence/router_restored.json",
          "final":"fase3/evidence/router_final.json",
          "events":"fase3/evidence/deployment_events.json"}}
    (EV/"operations_audit.json").write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n")
    print("OPERATIONS AUDIT PASS",stable["version"],"->",candidate["version"],"-> rollback -> candidate")
    return o
if __name__=="__main__":main()
