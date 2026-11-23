"""Construye dos releases de Random Forest realmente diferentes, en datos 100% sintéticos.

Stable = 130 árboles ya evaluados. Candidate = warm-start +5 árboles con los
mismos datos de entrenamiento; su receta es fija, NO se escoge sobre holdout.
Se genera un reporte completo de candidata sin sobreescribir el modelo estable.
"""
from __future__ import annotations
import hashlib, json, shutil
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
from .release import A8, OUT, check_model, load, sha
from actividad8.simulator import generate, split, FEATURES
from actividad8.train_v2 import metrics, event_recall

HERE=Path(__file__).resolve().parent
BUILD=HERE/"build"/"candidate"
CANDIDATE_MANIFEST=OUT/"candidate_release_manifest.json"

def build_candidate():
    BUILD.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    stable_manifest=load(OUT/"release_manifest.json")
    stable_hash,_=check_model()
    if stable_manifest["model_sha256"]!=stable_hash:
        raise ValueError("Manifest stable no coincide con artefacto")
    df=generate()
    partitions=split(df)
    model=joblib.load(A8/"artifacts/model_v2.joblib")
    forest=model.named_steps["model"]
    if forest.n_estimators!=130:
        raise ValueError("El baseline esperado usa 130 árboles")
    original_threshold=float(load(A8/"artifacts/metadata_v2.json")["threshold"])
    # Incremento fijo y explícito: nuevo binario y predicciones recalculadas.
    X=model.named_steps["prepare"].transform(partitions["train"][FEATURES])
    y=partitions["train"].failure_next_72h.astype(int).to_numpy()
    forest.set_params(warm_start=True,n_estimators=135)
    forest.fit(X,y)
    candidate_path=BUILD/"model_v2.joblib"
    joblib.dump(model,candidate_path,compress=3)
    candidate_hash=sha(candidate_path)
    if candidate_hash==stable_hash:
        raise AssertionError("La candidata no cambió realmente de versión")
    metadata=load(A8/"artifacts/metadata_v2.json")
    metadata.update(model_sha256=candidate_hash,model_variant="RF_135_trees_warm_start",
       stable_parent_sha256=stable_hash)
    (BUILD/"metadata_v2.json").write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+"\n")
    shutil.copy2(A8/"artifacts/pilot_v2.json",BUILD/"pilot_v2.json")
    evaluation=load(A8/"results/evaluation_v2.json")
    result={}
    for name in ("validation","test_temporal","test_pilot"):
        part=partitions[name]
        p=model.predict_proba(part[FEATURES])[:,1]
        y=part.failure_next_72h.astype(int).to_numpy()
        values=metrics(y,p,original_threshold)
        if name!="validation":values.update(event_recall(df,part,p,original_threshold))
        result[name]=values
    evaluation["metrics"]=result
    evaluation["model"]=metadata
    evaluation["candidate_recipe"]="Stable RF 130 trees plus 5 trees with warm_start, same training partition; threshold fixed from stable validation"
    evaluation["evaluation_kind"]="synthetic_fixed_recipe_experiment"
    candidate_eval=OUT/"candidate_evaluation.json"
    candidate_eval.write_text(json.dumps(evaluation,indent=2,ensure_ascii=False)+"\n")
    digest,gates=check_model(evaluation,metadata,candidate_path)
    assert digest==candidate_hash
    manifest={
       "schema_version":1,"version":"v2c-"+candidate_hash[:12],
       "model_sha256":candidate_hash,"stable_parent_sha256":stable_hash,
       "model_relative_path":"fase3/build/candidate/model_v2.joblib",
       "metadata_relative_path":"fase3/build/candidate/metadata_v2.json",
       "synthetic":True,"horizon_hours":72,
       "variant":"RandomForest_135_trees_warm_start",
       "quality_gates":gates,"candidate_evaluation":"fase3/evidence/candidate_evaluation.json",
       "industrial_release_authorized":False,
       "approval_scope":"academic_staging_only",
       "created_at_utc":datetime.now(timezone.utc).isoformat()
    }
    CANDIDATE_MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
    stable_eval=load(A8/"results/evaluation_v2.json")["metrics"]["test_pilot"]
    candidate_pilot=result["test_pilot"]
    comparison={"scope":"measured_on_synthetic_12_machine_pilot",
      "stable":{"version":stable_manifest["version"],"sha256":stable_hash,
                "trees":130,"pilot":stable_eval},
      "candidate":{"version":manifest["version"],"sha256":candidate_hash,
                   "trees":135,"pilot":candidate_pilot},
      "same_binary":False,
      "same_training_data":True,
      "same_threshold":True,
      "candidate_passed_quality_gates":all(v["passed"] for v in gates.values()),
      "important_limitations":[
        "The synthetic holdout is used as acceptance evidence, not unbiased production validation.",
        "Candidate recipe is fixed (5 more trees), not optimized on pilot metrics.",
        "Latency degradation after release is injected on candidate service, not a measured natural model defect.",
        "No real industrial hardware or continuously available production is deployed."
      ]}
    (OUT/"model_version_comparison.json").write_text(json.dumps(comparison,ensure_ascii=False,indent=2)+"\n")
    print("CANDIDATE RELEASE PASS",manifest["version"],"ROC-AUC",candidate_pilot["roc_auc"])
    return manifest

def verify_candidate():
    m=load(CANDIDATE_MANIFEST)
    metadata=load(BUILD/"metadata_v2.json")
    evaluation=load(OUT/"candidate_evaluation.json")
    digest,gates=check_model(evaluation,metadata,BUILD/"model_v2.joblib")
    stable=load(OUT/"release_manifest.json")
    if m["model_sha256"]!=digest or m["stable_parent_sha256"]!=stable["model_sha256"]:
        raise ValueError("Candidata no corresponde a stable")
    if digest==stable["model_sha256"] or m["quality_gates"]!=gates:
        raise ValueError("Versiones no distintas o gates alterados")
    return m

if __name__=="__main__":
    build_candidate()
    verify_candidate()
