"""Tests de políticas de publicación, idempotencia GitOps y rollback registrado."""
from __future__ import annotations
import hashlib, json
import pytest
from fase3.release import check_model,QUALITY_GATES
from fase3 import gitops

def candidate_fixture(tmp_path):
    artifact=tmp_path/"model.joblib";artifact.write_bytes(b"test-model-content")
    model_hash=hashlib.sha256(artifact.read_bytes()).hexdigest()
    meta={"synthetic":True,"horizon_hours":72,"machines_holdout":12,
          "threshold_source":"validation_only","model_sha256":model_hash}
    metrics={"samples":4896,"failure_events_evaluable":35,
             "precision":.75,"recall":.80,"roc_auc":.97,"event_recall":.88}
    evidence={"status":"measured_on_synthetic_v2","not_directly_comparable":True,
              "metrics":{"test_pilot":metrics}}
    return artifact,meta,evidence

def test_gate_accepts_and_detects_tamper(tmp_path):
    file,metadata,evaluation=candidate_fixture(tmp_path)
    digest,results=check_model(evaluation,metadata,file)
    assert digest==metadata["model_sha256"]
    assert len(results)==4 and all(r["passed"] for r in results.values())
    file.write_bytes(file.read_bytes()+b"changed")
    with pytest.raises(ValueError,match="Hash"):check_model(evaluation,metadata,file)

def test_gate_rejects_degradation_and_scope(tmp_path):
    file,metadata,evaluation=candidate_fixture(tmp_path)
    evaluation["metrics"]["test_pilot"]["recall"]=.70
    with pytest.raises(ValueError,match="REJECTED"):check_model(evaluation,metadata,file)
    evaluation["metrics"]["test_pilot"]["recall"]=.8
    metadata["horizon_hours"]=24
    with pytest.raises(ValueError,match="horizonte"):check_model(evaluation,metadata,file)

def test_gitops_promotion_and_rollback_require_evidence(tmp_path,monkeypatch):
    monkeypatch.setattr(gitops,"EVIDENCE",tmp_path/"evidence")
    state_path=tmp_path/"state.json"
    fingerprint="a"*64
    state={"schema_version":1,"environment":"academic-ci-staging","synthetic":True,
           "active_slot":"stable","previous_slot":None,"model_sha256":fingerprint,
           "release_version":"v2-"+fingerprint[:12],
           "routes":{"stable":"http://api-stable:8008",
                     "candidate":"http://api-candidate:8008"},"history":[]}
    gitops.save(state,state_path)
    evidence=tmp_path/"candidate.json"
    evidence.write_text(json.dumps({"status":"PASS","model_sha256":fingerprint,
       "endpoint":"http://127.0.0.1:8009",
       "successful_predictions":3,"history_rows":3}))
    bad=tmp_path/"bad.json"
    bad.write_text(json.dumps({"status":"EXPECTED_FAILURE",
       "observed_status_code":502,"serving_slot":"candidate"}))
    with pytest.raises(ValueError,match="sin PASS"):
        evidence.write_text(json.dumps({"status":"REJECTED"}))
        gitops.promote(evidence,state_path)
    evidence.write_text(json.dumps({"status":"PASS","model_sha256":fingerprint,
       "endpoint":"http://127.0.0.1:8009",
       "successful_predictions":3,"history_rows":3}))
    promoted=gitops.promote(evidence,state_path)
    assert promoted["active_slot"]=="candidate"
    with pytest.raises(ValueError,match="ya promovido"):
        gitops.promote(evidence,state_path)
    restored=gitops.rollback(bad,state_path)
    assert restored["active_slot"]=="stable"
    assert [x["type"] for x in restored["history"]]==["PROMOTE","ROLLBACK"]
