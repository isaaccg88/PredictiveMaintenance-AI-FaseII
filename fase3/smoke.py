"""Smoke HTTP end-to-end: salud, firma, 3 inferencias y persistencia SQLite.

--expect-failure permite probar una falla real del backend candidate
tras detener intencionalmente su contenedor, sin fabricar la respuesta 502.
"""
from __future__ import annotations
import argparse, json, time
from datetime import datetime,timezone
from pathlib import Path
import requests
from .release import verify_manifest

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--expect-failure",action="store_true")
    ap.add_argument("--expected-slot",default=None)
    args=ap.parse_args()
    url=args.url.rstrip("/")
    dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
    manifest=verify_manifest()
    start=time.perf_counter()
    if args.expect_failure:
        response=requests.post(url+"/predict",json={"machine_id":"PM-049"},timeout=15)
        slot=response.headers.get("X-Serving-Slot")
        if response.status_code!=502 or slot!="candidate":
            raise AssertionError(f"No se produjo 502 de candidata: {response.status_code}, {slot}")
        record={"status":"EXPECTED_FAILURE","endpoint":url,"serving_slot":slot,
                "observed_status_code":response.status_code,
                "elapsed_ms":round(1000*(time.perf_counter()-start),2),
                "at_utc":datetime.now(timezone.utc).isoformat()}
    else:
        info=requests.get(url+"/model/info",timeout=20)
        info.raise_for_status()
        sha=info.json().get("model_sha256")
        if sha!=manifest["model_sha256"]:
            raise AssertionError("Modelo en ejecución no coincide con SHA verificado")
        h=requests.get(url+"/health",timeout=20)
        h.raise_for_status()
        if h.json().get("status")!="ok":raise AssertionError("healthcheck incorrecto")
        machines=requests.get(url+"/machines",timeout=20)
        machines.raise_for_status()
        ids={x["machine_id"] for x in machines.json()}
        if ids!={f"PM-{i:03d}" for i in range(49,61)}:
            raise AssertionError("Piloto de 12 máquinas incorrecto")
        measures=[]
        for machine_id in ("PM-049","PM-050","PM-051"):
            r=requests.post(url+"/predict",json={"machine_id":machine_id},timeout=20)
            r.raise_for_status()
            row=r.json()
            if row.get("horizon_hours")!=72 or row.get("synthetic") is not True:
                raise AssertionError("Predicción carece de contexto esperado")
            if row.get("machine_id")!=machine_id or not (0<=row["probability_72h"]<=1):
                raise AssertionError("Respuesta de inferencia inválida")
            if not row.get("trace_id") or not row.get("record_id"):
                raise AssertionError("No existe trazabilidad/persistencia")
            measures.append({"machine_id":machine_id,"trace_id":row["trace_id"],
                             "probability_72h":row["probability_72h"],
                             "elapsed_ms":round(r.elapsed.total_seconds()*1000,3)})
        hist=requests.get(url+"/history",timeout=20)
        hist.raise_for_status()
        rows=hist.json()
        traces={x["trace_id"] for x in rows}
        if not all(x["trace_id"] in traces for x in measures):
            raise AssertionError("Predicciones no persistidas en SQLite")
        slot=(h.headers.get("X-Serving-Slot") or info.headers.get("X-Serving-Slot"))
        if args.expected_slot and slot!=args.expected_slot:
            raise AssertionError(f"Route esperada={args.expected_slot}, real={slot}")
        record={"status":"PASS","endpoint":url,"model_sha256":sha,
                "horizon_hours":72,"synthetic":True,"serving_slot":slot,
                "successful_predictions":len(measures),
                "history_rows":len(rows),"predictions":measures,
                "elapsed_ms":round(1000*(time.perf_counter()-start),2),
                "at_utc":datetime.now(timezone.utc).isoformat()}
    dest.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SMOKE",record["status"],"slot=",record.get("serving_slot"))
    return record
if __name__=="__main__":main()
