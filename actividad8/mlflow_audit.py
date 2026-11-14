"""Validación de la evidencia real de MLflow, sin depender de capturas ficticias.

Uso: python -m actividad8.mlflow_audit
Requiere: python -m actividad8.train_v2 --mlflow, ejecutado previamente.
"""
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
import mlflow
from mlflow.tracking import MlflowClient
from .simulator import HERE

def main():
    run_path=HERE/"results"/"mlflow_run.json"
    report_path=HERE/"results"/"evaluation_v2.json"
    if not run_path.exists() or not report_path.exists():
        raise RuntimeError("Faltan mlflow_run.json/evaluation_v2.json: entrenar con --mlflow.")
    record=json.loads(run_path.read_text(encoding="utf-8"))
    report=json.loads(report_path.read_text(encoding="utf-8"))
    mlflow.set_tracking_uri((HERE/"mlruns").resolve().as_uri())
    client=MlflowClient()
    run=client.get_run(record["run_id"])
    experiment=client.get_experiment(run.info.experiment_id)
    expected_experiment=record["experiment"]
    if experiment.name!=expected_experiment:
        raise AssertionError("El experimento registrado no coincide con el export.")
    if run.info.status!="FINISHED":
        raise AssertionError("La corrida de MLflow no terminó satisfactoriamente.")
    expected_params={
        "seed":str(report["seed"]),
        "horizon_hours":str(report["model"]["horizon_hours"]),
        "holdout_machines":str(report["model"]["machines_holdout"]),
        "threshold":str(report["model"]["threshold"]),
    }
    for key,value in expected_params.items():
        if run.data.params.get(key)!=value:
            raise AssertionError(f"Parámetro MLflow incorrecto: {key}")
    verified={}
    for group in ("validation","test_temporal","test_pilot"):
        verified[group]={}
        for metric in ("precision","recall","f1","roc_auc","average_precision"):
            key=f"{group}_{metric}"
            observed=run.data.metrics.get(key)
            expected=float(report["metrics"][group][metric])
            if observed is None or abs(observed-expected)>1e-9:
                raise AssertionError(f"Métrica MLflow no coincide con reporte: {key}")
            verified[group][metric]=observed
    artifacts=sorted(item.path for item in client.list_artifacts(record["run_id"]))
    for required in ("evaluation_v2.json","metadata_v2.json","model_v2.joblib"):
        if required not in artifacts:
            raise AssertionError(f"Falta artefacto MLflow: {required}")
    export={
        "status":"VERIFIED_MLFLOW_FILE_STORE",
        "verified_at_utc":datetime.now(timezone.utc).isoformat(),
        "source":"local MLflow file tracking store inside CI runner",
        "experiment":experiment.name,"experiment_id":run.info.experiment_id,
        "run_id":run.info.run_id,"run_status":run.info.status,
        "params":expected_params,"metrics":verified,"artifacts":artifacts,
        "synthetic_data":True,
        "limitations":"CI creates its own ephemeral run; download Actions artifact for raw MLflow evidence.",
    }
    folder=HERE/"evidence"
    folder.mkdir(exist_ok=True)
    (folder/"mlflow_validation.json").write_text(
        json.dumps(export,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    table=["| Métrica | Validación | Prueba temporal | Piloto |",
           "|---|---:|---:|---:|"]
    for metric in ("precision","recall","f1","roc_auc","average_precision"):
        table.append("| "+metric+" | "+" | ".join(
            f"{verified[group][metric]:.6f}" for group in
            ("validation","test_temporal","test_pilot"))+" |")
    markdown=[
        "# Exportación y verificación de MLflow (CI)",
        "",
        f"**Experimento:** `{experiment.name}`  ",
        f"**Run ID:** `{run.info.run_id}`  ",
        f"**Estado MLflow:** `{run.info.status}`  ",
        "",
        "La comprobación consulta el tracking store de MLflow y compara las 15",
        "métricas registradas contra el archivo de evaluación del mismo entrenamiento.",
        "Una discrepancia hace fallar el workflow.",
        "",
        *table,"",
        "**Parámetros:** "+", ".join(f"{k}={v}" for k,v in expected_params.items())+".",
        "",
        "**Artefactos registrados:** "+", ".join(artifacts)+".",
        "",
        "**Alcance:** experimento 100% sintético; MLflow se ejecuta en el runner",
        "de GitHub Actions. No corresponde a un servidor MLflow siempre encendido.",
        "Descargar el artefacto de la ejecución para inspeccionar el tracking store.",
        "",
    ]
    (folder/"mlflow_validation.md").write_text("\n".join(markdown),encoding="utf-8")
    print("MLFLOW TRACKING AUDIT: PASS; run="+run.info.run_id)
    return export

if __name__=="__main__":
    main()
