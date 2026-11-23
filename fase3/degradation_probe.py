"""Detecta regresión de latencia en el modelo candidato promovido.

Solicitudes HTTP de verdad al router, al menos 6; no fabrica respuestas.
La latencia extra es introducida por un flag local SOLO en candidate.
"""
from __future__ import annotations
import argparse,json,statistics,time
from pathlib import Path
from datetime import datetime,timezone
import requests
from .gitops import read,CANDIDATE

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    p.add_argument("--url",default="http://127.0.0.1:8010")
    p.add_argument("--samples",type=int,default=6)
    a=p.parse_args()
    if not 5<=a.samples<=30:raise ValueError("samples debe ser 5..30")
    url=a.url.rstrip("/")
    model=read(CANDIDATE)
    info=requests.get(url+"/model/info",timeout=12)
    info.raise_for_status()
    slot=info.headers.get("X-Serving-Slot")
    digest=info.json().get("model_sha256")
    if slot!="candidate" or digest!=model["model_sha256"]:
        raise AssertionError("La degradación no corresponde al modelo candidato")
    responses=[]
    for i in range(a.samples):
        r=requests.post(url+"/predict",json={"machine_id":f"PM-{49+i%12:03d}"},timeout=15)
        responses.append({"code":r.status_code,"elapsed_ms":round(1000*r.elapsed.total_seconds(),2),
             "slot":r.headers.get("X-Serving-Slot")})
    values=sorted(x["elapsed_ms"] for x in responses)
    p95=float(statistics.quantiles(values,n=100,method="inclusive")[94])
    ok=sum(200<=x["code"]<300 for x in responses)
    record={"status":"DEGRADED" if p95>500 and ok==a.samples else "NOT_DEGRADED",
        "endpoint":url,"model_sha256":digest,"serving_slot":slot,
        "threshold_ms":500,"samples":a.samples,"http_2xx_count":ok,
        "p50_ms":round(statistics.median(values),2),"p95_ms":round(p95,2),
        "responses":responses,"trigger":"controlled_candidate_only_runtime_latency",
        "at_utc":datetime.now(timezone.utc).isoformat()}
    path=Path(a.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if record["status"]!="DEGRADED":
        raise RuntimeError("No se detectó latencia degradada de candidata")
    print("MODEL CANDIDATE DEGRADED: p95",p95,"ms; hash",digest[:12])
    return record
if __name__=="__main__":main()
