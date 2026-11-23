"""Smoke HTTP real para dos versiones distintas de IA con rastreo SQLite."""
from __future__ import annotations
import argparse, json, time
from datetime import datetime,timezone
from pathlib import Path
import requests
from .release import verify_manifest
from .gitops import CANDIDATE, read

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--expected-slot",choices=("stable","candidate"))
    ap.add_argument("--expected-model",choices=("stable","candidate"),required=True)
    args=ap.parse_args()
    url=args.url.rstrip("/")
    dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
    stable=verify_manifest()
    candidate=read(CANDIDATE)
    expected={"stable":stable["model_sha256"],"candidate":candidate["model_sha256"]}
    start=time.perf_counter()
    info=requests.get(url+"/model/info",timeout=20)
    info.raise_for_status()
    digest=info.json()["model_sha256"]
    if digest!=expected[args.expected_model]:
        raise AssertionError(f"Modelo errado: esperado={args.expected_model} recibido={digest}")
    health=requests.get(url+"/health",timeout=20)
    health.raise_for_status()
    if health.json().get("status")!="ok":raise AssertionError("Health no saludable")
    machines=requests.get(url+"/machines",timeout=20)
    machines.raise_for_status()
    ids={x["machine_id"] for x in machines.json()}
    if ids!={f"PM-{i:03d}" for i in range(49,61)}:
        raise AssertionError("Piloto esperado de 12 máquinas ausente")
    predictions=[]
    for mid in ("PM-049","PM-050","PM-051"):
        resp=requests.post(url+"/predict",json={"machine_id":mid},timeout=20)
        resp.raise_for_status()
        item=resp.json()
        if item.get("horizon_hours")!=72 or item.get("synthetic") is not True:
            raise AssertionError("Horizonte o tipo de datos incorrecto")
        if item.get("machine_id")!=mid or not (0<=item["probability_72h"]<=1):
            raise AssertionError("Predicción inconsistente")
        if not item.get("trace_id") or not item.get("record_id"):
            raise AssertionError("Se perdió trazabilidad")
        predictions.append({"machine_id":mid,"trace_id":item["trace_id"],
            "probability_72h":item["probability_72h"],
            "elapsed_ms":round(resp.elapsed.total_seconds()*1000,3)})
    history=requests.get(url+"/history",timeout=20)
    history.raise_for_status()
    rows=history.json()
    traces={x["trace_id"] for x in rows}
    if any(x["trace_id"] not in traces for x in predictions):
        raise AssertionError("No se persistieron todas las trazas en SQLite")
    slot=health.headers.get("X-Serving-Slot") or info.headers.get("X-Serving-Slot")
    if args.expected_slot and slot!=args.expected_slot:
        raise AssertionError(f"El router sirvió {slot}; se esperaba {args.expected_slot}")
    record={"status":"PASS","endpoint":url,"model_sha256":digest,
        "model_slot":args.expected_model,"serving_slot":slot,
        "horizon_hours":72,"synthetic":True,"successful_predictions":len(predictions),
        "history_rows":len(rows),"predictions":predictions,
        "elapsed_ms":round(1000*(time.perf_counter()-start),2),
        "at_utc":datetime.now(timezone.utc).isoformat()}
    dest.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SMOKE PASS",args.expected_model,digest[:12],"slot=",slot)
    return record
if __name__=="__main__":main()
