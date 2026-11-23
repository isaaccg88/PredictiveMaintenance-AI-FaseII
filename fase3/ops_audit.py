"""Auditoría operativa: separar métricas del API de los fallos del router.

No reporta servicio 24/7 ni extrapola la muestra CI a un SLA industrial.
"""
from __future__ import annotations
import json, statistics
from datetime import datetime, timezone
from pathlib import Path
import requests
from .release import verify_manifest
from .gitops import read

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
def main():
    manifest=verify_manifest()
    state=read(HERE/"runtime/desired-state.json")
    events=read(HERE/"evidence/deployment_events.json")["events"]
    if [x["type"] for x in events].count("ROLLBACK")<1:
        raise AssertionError("No se verificó rollback con incidente")
    if [x["type"] for x in events].count("PROMOTE")<2:
        raise AssertionError("Falta re-promoción luego de recuperación")
    if state["active_slot"]!="candidate":
        raise AssertionError("Despliegue final no quedó en candidate")
    route=requests.get("http://127.0.0.1:8010/health",timeout=10).json()
    if route["active_slot"]!="candidate":raise AssertionError("Deseado vs observado divergente")
    m=requests.get("http://127.0.0.1:8010/metrics",timeout=10).json()
    values=[row["duration_ms"] for row in m.get("measurements",[])]
    if len(values)<3:raise AssertionError("Faltan mediciones reales HTTP")
    successful=[row for row in m["measurements"] if row["status"]==200]
    timely=sum(row["duration_ms"]<=500 for row in successful)
    ops={"scope":"SIMULATED_STAGING_GITHUB_ACTIONS",
         "synthetic_data":True,"industrial_deployment":False,
         "observed_at_utc":datetime.now(timezone.utc).isoformat(),
         "release_version":manifest["version"],"model_sha256":manifest["model_sha256"],
         "active_slot":state["active_slot"],"model_quality_gates":manifest["quality_gates"],
         "mlflow_run_id":manifest["mlflow_run_id"],
         "api_predict_samples":len(values),
         "api_http_5xx":sum(x["status"]>=500 for x in m["measurements"]),
         "api_availability_ratio":len(successful)/len(values),
         "api_timely_ratio":timely/len(values),
         "api_latency_p95_ms":round(statistics.quantiles(values,n=100,method="inclusive")[94],3) if len(values)>=2 else values[0],
         "router_outage_observed_in_separate_smoke":True,
         "router_outage_status":502,
         "rollback_events":len([x for x in events if x["type"]=="ROLLBACK"]),
         "promotions":len([x for x in events if x["type"]=="PROMOTE"]),
         "limitations":[
            "API /metrics counts backend /predict only; router 502 is recorded in failure smoke separately.",
            "Small HTTP sample: does not establish monthly SLA nor industrial reliability.",
            "Stable and candidate use same model binary, so rollback demonstrates routing recovery, not model downgrade.",
            "Both containers share one runner; neither multi-AZ nor cloud is deployed.",
            "A9 FinOps amounts remain estimates, not an AWS invoice."],
         "evidence":{
          "failed_candidate":"fase3/evidence/router_failure.json",
          "restored_router":"fase3/evidence/router_restored.json",
          "final_router":"fase3/evidence/router_final.json",
          "gitops_history":"fase3/evidence/deployment_events.json",
          "previous_slo_history":"actividad8/evidence/incidents.json"}}
    out=HERE/"evidence"/"operations_audit.json"
    out.write_text(json.dumps(ops,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("OPERATIONS AUDIT PASS:",ops["release_version"],
          "api_p95=",ops["api_latency_p95_ms"])
    return ops
if __name__=="__main__":main()
