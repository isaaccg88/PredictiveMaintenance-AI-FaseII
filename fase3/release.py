"""Calidad, firma y trazabilidad de una versión candidata de modelo sintético.

La huella se calcula sobre el modelo serializado utilizado en Docker. No se
declara listo para producción industrial; los gates aplican solo al holdout V2.
"""
from __future__ import annotations
import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

A8=Path(__file__).resolve().parent.parent/"actividad8"
HERE=Path(__file__).resolve().parent
OUT=HERE/"evidence"
QUALITY_GATES={"precision":.70,"recall":.75,"roc_auc":.95,"event_recall":.85}
def load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check_model(evaluation=None,metadata=None,model_path=None):
    evaluation=evaluation or load(A8/"results/evaluation_v2.json")
    metadata=metadata or load(A8/"artifacts/metadata_v2.json")
    model_path=Path(model_path or A8/"artifacts/model_v2.joblib")
    if evaluation.get("status")!="measured_on_synthetic_v2":
        raise ValueError("El reporte no es la evaluación V2 medida")
    if evaluation.get("not_directly_comparable") is not True:
        raise ValueError("Debe preservar advertencia comparabilidad V1/V2")
    if not metadata.get("synthetic") or metadata.get("horizon_hours")!=72:
        raise ValueError("El modelo no tiene el horizonte/scope esperado")
    if metadata.get("machines_holdout")!=12 or metadata.get("threshold_source")!="validation_only":
        raise ValueError("No está documentado el holdout o la selección de umbral")
    model_hash=sha(model_path)
    if metadata.get("model_sha256")!=model_hash:
        raise ValueError("Hash del artefacto no coincide con metadata")
    m=evaluation["metrics"]["test_pilot"]
    if m.get("samples")!=4896 or m.get("failure_events_evaluable",0)<20:
        raise ValueError("Muestra de holdout incompatible")
    results={k:{"actual":float(m[k]),"minimum":v,"passed":float(m[k])>=v}
             for k,v in QUALITY_GATES.items()}
    if not all(r["passed"] for r in results.values()):
        raise ValueError("REJECTED: el modelo no pasa el control de calidad")
    return model_hash,results
def create_release():
    OUT.mkdir(parents=True,exist_ok=True)
    evaluation=load(A8/"results/evaluation_v2.json")
    metadata=load(A8/"artifacts/metadata_v2.json")
    model_hash,gates=check_model(evaluation,metadata)
    run_file=A8/"results/mlflow_run.json"
    run=load(run_file) if run_file.exists() else {}
    if not run.get("run_id"):raise ValueError("MLflow run ID ausente")
    version="v2-"+model_hash[:12]
    release={
        "schema_version":1, "version":version, "model_sha256":model_hash,
        "model_relative_path":"actividad8/artifacts/model_v2.joblib",
        "metadata_relative_path":"actividad8/artifacts/metadata_v2.json",
        "source_commit":os.getenv("GITHUB_SHA","local-unversioned"),
        "ci_run_id":os.getenv("GITHUB_RUN_ID","local"),
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "generator":"synthetic_V2_seed_20261114",
        "evaluation_partition":"12_unseen_machines_pilot",
        "time_horizon_hours":72,"synthetic":True,
        "mlflow_run_id":run["run_id"],"mlflow_experiment":run.get("experiment"),
        "quality_gates":gates,
        "approval_scope":"academic_staging_only",
        "industrial_release_authorized":False
    }
    (OUT/"release_manifest.json").write_text(json.dumps(release,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("RELEASE CANDIDATE VALIDATED:",version)
    return release
def verify_manifest(path=OUT/"release_manifest.json"):
    r=load(path)
    digest,gates=check_model()
    if r.get("model_sha256")!=digest or r.get("version")!="v2-"+digest[:12]:
        raise ValueError("Release manifest alterado o artefacto no reproducido")
    if r.get("synthetic") is not True or r.get("industrial_release_authorized") is not False:
        raise ValueError("Alcance de release incorrecto")
    if r.get("quality_gates")!=gates:raise ValueError("Gates manipulados")
    return r
if __name__=="__main__":create_release();verify_manifest()
