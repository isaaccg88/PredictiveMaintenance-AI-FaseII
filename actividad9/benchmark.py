"""Benchmark HTTP real de API FastAPI con uno y dos endpoints; NUNCA cloud.

Mide carga por concurrencia y recursos del proceso conocido en un runner.
'2 endpoints' es un proxy local de escalado horizontal; no prueba ECS/ALB.
"""
from __future__ import annotations
import argparse, concurrent.futures, json, os, statistics, time
from pathlib import Path
import requests
try: import psutil
except ImportError: psutil=None

OUT=Path(__file__).resolve().parent/"evidence"

def one_call(url,i):
    started=time.perf_counter()
    try:
        rsp=requests.post(url+"/predict",json={"machine_id":f"PM-{49+i%12:03d}"},timeout=12)
        ok=rsp.status_code==200
        return (round(1000*(time.perf_counter()-started),3),rsp.status_code,ok)
    except requests.RequestException:
        return (round(1000*(time.perf_counter()-started),3),599,False)

def percentile(sorted_values,q):
    if not sorted_values:return None
    pos=(len(sorted_values)-1)*q; lo=int(pos); hi=min(len(sorted_values)-1,lo+1)
    return sorted_values[lo]*(hi-pos)+sorted_values[hi]*(pos-lo)

def benchmark(urls,concurrency,requests_per_test):
    # Warm-up calls excluded from measurement; their inclusion can distort SLA.
    for url in urls:
        for _ in range(3): one_call(url,0)
    t0=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        results=list(ex.map(lambda i:one_call(urls[i%len(urls)],i),range(requests_per_test)))
    wall=time.perf_counter()-t0
    durations=sorted(r[0] for r in results)
    good=sum(r[2] for r in results)
    return {"concurrency":concurrency,"samples":len(results),"ok_2xx":good,
        "errors":len(results)-good,"availability":good/len(results),
        "p50_ms":round(percentile(durations,.50),2),
        "p95_ms":round(percentile(durations,.95),2),
        "p99_ms":round(percentile(durations,.99),2),
        "throughput_rps":round(len(results)/wall,3),
        "elapsed_seconds":round(wall,3),
        "status_codes":{str(z):sum(x[1]==z for x in results)
                        for z in sorted(set(x[1] for x in results))}}

def proc_info():
    if not psutil:return {"status":"PSUTIL_UNAVAILABLE"}
    pids=os.getenv("A9_API_PIDS","").split(",")
    out=[]
    for pid in pids:
        if not pid.strip():continue
        try:
            p=psutil.Process(int(pid))
            out.append({"pid":int(pid),"rss_mb":round(p.memory_info().rss/1048576,2),
                        "cpu_time_seconds":round(sum(p.cpu_times()[:2]),3)})
        except (ValueError,psutil.Error):out.append({"pid":pid,"status":"UNAVAILABLE"})
    return {"processes":out,"scope":"host_process_not_Fargate"}

def main():
    args=argparse.ArgumentParser()
    args.add_argument("--single",default="http://127.0.0.1:8008")
    args.add_argument("--second",default="http://127.0.0.1:8009")
    args.add_argument("--samples",type=int,default=60)
    opts=args.parse_args()
    if not 20<=opts.samples<=1000:raise ValueError("samples must be 20..1000")
    urls=[opts.single.rstrip("/"),opts.second.rstrip("/")]
    for u in urls:
        r=requests.get(u+"/health",timeout=12)
        r.raise_for_status()
        if r.json().get("status")!="ok":raise RuntimeError("unhealthy "+u)
    results={}
    for title,targets in [("single",urls[:1]),("dual",urls)]:
        before=proc_info()
        levels=[benchmark(targets,n,opts.samples) for n in (1,4,8,16)]
        results[title]={"endpoints":len(targets),"levels":levels,
                        "resources_before":before,"resources_after":proc_info()}
    OUT.mkdir(exist_ok=True,parents=True)
    data={"scope":"REAL_LOOPBACK_HTTP_IN_CI_NOT_CLOUD",
          "requests_per_load_level":opts.samples,
          "slo_p95_ms_diagnostic":500,
          "no_claim_of_vertical_scalability_measurement":True,
          "notes":["Both API replicas run on the same shared CI host.",
                   "They share host CPU/network and are not isolated containers.",
                   "Two endpoints simulated by alternating requests, not measured AWS ALB.",
                   "CPU and memory scope = host process, not reserved Fargate tasks.",
                   "Peak and cost projections remain assumptions."],**results}
    (OUT/"load_benchmark.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v["levels"] for k,v in results.items()},indent=2))
    return data

if __name__=="__main__":main()
