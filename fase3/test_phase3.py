"""Pruebas de firma hash, quality gates y rollback REAL entre versiones distintas."""
from __future__ import annotations
import hashlib,json
import pytest
from fase3.release import check_model
from fase3 import gitops

def candidate_fixture(tmp_path):
    artifact=tmp_path/"model.joblib";artifact.write_bytes(b"test-model-content")
    digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
    meta={"synthetic":True,"horizon_hours":72,"machines_holdout":12,
        "threshold_source":"validation_only","model_sha256":digest}
    values={"samples":4896,"failure_events_evaluable":35,
        "precision":.75,"recall":.80,"roc_auc":.97,"event_recall":.88}
    ev={"status":"measured_on_synthetic_v2","not_directly_comparable":True,
        "metrics":{"test_pilot":values}}
    return artifact,meta,ev

def test_release_accepts_and_detects_tamper(tmp_path):
    f,m,e=candidate_fixture(tmp_path)
    digest,gates=check_model(e,m,f)
    assert digest==m["model_sha256"] and all(x["passed"] for x in gates.values())
    f.write_bytes(f.read_bytes()+b"tamper")
    with pytest.raises(ValueError,match="Hash"):check_model(e,m,f)

def test_release_rejects_quality_and_wrong_horizon(tmp_path):
    f,m,e=candidate_fixture(tmp_path)
    e["metrics"]["test_pilot"]["recall"]=.70
    with pytest.raises(ValueError,match="REJECTED"):check_model(e,m,f)
    e["metrics"]["test_pilot"]["recall"]=.80
    m["horizon_hours"]=24
    with pytest.raises(ValueError,match="horizonte"):check_model(e,m,f)

def test_promote_and_rollback_between_distinct_hashes(tmp_path,monkeypatch):
    monkeypatch.setattr(gitops,"EVIDENCE",tmp_path/"evidence")
    state_path=tmp_path/"desired.json"
    stable_hash="a"*64
    candidate_hash="b"*64
    state={"schema_version":2,"environment":"academic-ci-staging",
        "synthetic":True,"active_slot":"stable","previous_slot":None,
        "models":{"stable":{"sha256":stable_hash,"version":"v2-"+stable_hash[:12]},
                  "candidate":{"sha256":candidate_hash,"version":"v2c-"+candidate_hash[:12]}},
        "routes":{"stable":"http://api-stable:8008","candidate":"http://api-candidate:8008"},
        "history":[]}
    gitops.save(state,state_path)
    clean=tmp_path/"candidate.json"
    clean.write_text(json.dumps({"status":"PASS","endpoint":"http://127.0.0.1:8009",
        "model_sha256":candidate_hash,"successful_predictions":3,"history_rows":3}))
    bad=tmp_path/"degradation.json"
    bad.write_text(json.dumps({"status":"DEGRADED","endpoint":"http://127.0.0.1:8010",
        "serving_slot":"candidate","model_sha256":candidate_hash,
        "samples":6,"http_2xx_count":6,"p95_ms":700,"threshold_ms":500}))
    promoted=gitops.promote(clean,state_path)
    assert promoted["active_slot"]=="candidate"
    assert promoted["model_sha256"]==candidate_hash
    with pytest.raises(ValueError,match="ya fue promovido"):gitops.promote(clean,state_path)
    restored=gitops.rollback(bad,state_path)
    assert restored["active_slot"]=="stable"
    assert restored["model_sha256"]==stable_hash
    final=gitops.promote(clean,state_path)
    assert final["model_sha256"]==candidate_hash
    assert [x["type"] for x in final["history"]]==["PROMOTE","ROLLBACK_MODEL","PROMOTE"]

def test_rollback_rejects_fabricated_or_wrong_model(tmp_path,monkeypatch):
    monkeypatch.setattr(gitops,"EVIDENCE",tmp_path/"evidence")
    path=tmp_path/"state.json"
    state={"schema_version":2,"active_slot":"candidate","previous_slot":"stable",
        "models":{"stable":{"sha256":"a"*64,"version":"stable"},
                  "candidate":{"sha256":"b"*64,"version":"candidate"}},
        "history":[]}
    gitops.save(state,path)
    bad=tmp_path/"failure.json"
    bad.write_text(json.dumps({"status":"DEGRADED","endpoint":"http://127.0.0.1:8010",
        "serving_slot":"candidate","model_sha256":"a"*64,
        "samples":6,"http_2xx_count":6,"p95_ms":999,"threshold_ms":500}))
    with pytest.raises(ValueError,match="Rollback rechazado"):gitops.rollback(bad,path)
    assert gitops.read(path)["active_slot"]=="candidate"
