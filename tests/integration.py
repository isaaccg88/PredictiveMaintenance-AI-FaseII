"""End-to-end validation against real HTTP endpoints launched by Docker Compose."""
import json
import os
import time
import urllib.error
import urllib.request

BASE=os.getenv("API_TEST_URL","http://127.0.0.1:8000").rstrip("/")
WEB=os.getenv("WEB_TEST_URL","http://127.0.0.1:8501").rstrip("/")
def request(path,method="GET",body=None):
    payload=json.dumps(body).encode("utf-8") if body is not None else None
    req=urllib.request.Request(BASE+path,data=payload,method=method,
             headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=15) as r:
        return r.status,json.load(r)
def main():
    for i in range(45):
        try:
            status,health=request("/health")
            if health["status"]=="ok" and health["model_loaded"]:break
        except (urllib.error.URLError,TimeoutError):
            time.sleep(2)
    else:raise AssertionError("API Docker no está lista")
    _,machines=request("/machines")
    assert len(machines)==12
    assert len(set(x["machine_id"] for x in machines))==12
    assert all(x["probability_72h"]>=0 and x["probability_72h"]<=1 for x in machines)
    before=request("/predictions?limit=200")[1]
    original=request("/telemetry/PM-049")[1]["machine"]
    _,r=request("/predict",method="POST",body={"machine_id":"PM-049"})
    assert r["horizon_hours"]==72 and r["synthetic"] and r["record_id"]>=1
    _,history=request("/predictions?limit=200")
    assert len(history)==len(before)+1
    assert history[0]["machine_id"]=="PM-049"
    assert abs(history[0]["probability_72h"]-r["probability_72h"])<1e-9
    _,sim=request("/predict",method="POST",body={
        "machine_id":"PM-049",
        "overrides":{"temperature_c":110,"vibration_mm_s":8,"wear_index":0.99}
    })
    assert 0<=sim["probability_72h"]<=1
    assert sim["input_features"]["temperature_c"]==110
    assert sim["input_features"]["vibration_mm_s"]==8
    assert sim["input_features"]["wear_index"]==0.99
    _,after_whatif=request("/predictions?limit=200")
    assert after_whatif[0]["source"]=="simulated_whatif"
    assert after_whatif[0]["machine_id"]=="PM-049"
    assert request("/telemetry/PM-049")[1]["machine"]==original
    for body,code in [
        ({"machine_id":"PM-001"},404),
        ({"machine_id":"PM-049","overrides":{"wear_index":1.5}},422),
        ({"machine_id":"PM-049","overrides":{"temperature_c":-100}},422),
        ({"machine_id":"PM-049","overrides":{"future_failure":True}},422),
    ]:
        try:request("/predict",method="POST",body=body)
        except urllib.error.HTTPError as e:assert e.code==code,(e.code,code)
        else:raise AssertionError(f"Expected error {code} for {body}")
    assert request("/predictions?limit=200")[1][0]["id"]==after_whatif[0]["id"], "La petición inválida generó un registro"
    with urllib.request.urlopen(WEB+"/_stcore/health",timeout=20) as r:
        assert r.status==200
    print(json.dumps({"status":"PASS","machines":len(machines),
                      "real_api_inference":True,"sqlite_persistence":True,
                      "error_cases":4,"dashboard_http_status":200,
                      "mode":"simulated educational prototype"},indent=2))
if __name__=="__main__":
    main()
