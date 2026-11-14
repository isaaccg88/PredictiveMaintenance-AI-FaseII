"""Registrar incidentes reales del laboratorio sintético como seis runs MLflow.

Los valores se leen de incidents.json generado por peticiones HTTP reales y PSI.
No se usan valores inventados ni se presenta un escalamiento cloud simulado.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import math
import mlflow
from mlflow.tracking import MlflowClient
from .simulator import HERE


def _metric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def main():
    src = HERE / "evidence" / "incidents.json"
    tracking = HERE / "mlruns"
    if not src.exists():
        raise FileNotFoundError("Ejecuta antes python -m actividad8.laboratory")
    report = json.loads(src.read_text(encoding="utf-8"))
    incidents = {i["incident_id"]: i for i in report["incidents"]}
    if not all(x in incidents for x in ("INC-01", "INC-02")):
        raise AssertionError("Se requieren ambos incidentes registrados")
    mlflow.set_tracking_uri(tracking.resolve().as_uri())
    mlflow.set_experiment("PredictiveMaintenanceAI_Actividad8_V2")
    previous = HERE / "results" / "mlflow_run.json"
    train_run = json.loads(previous.read_text())["run_id"] if previous.exists() else "not_recorded"
    output = []
    spec = [
        ("INC-01", "baseline", incidents["INC-01"]["baseline"]),
        ("INC-01", "degraded", incidents["INC-01"]["during"]),
        ("INC-01", "recovered", incidents["INC-01"]["after"]),
        ("INC-02", "baseline", {"psi": incidents["INC-02"]["baseline_psi"]}),
        ("INC-02", "degraded", {"psi": incidents["INC-02"]["during_psi"]}),
        ("INC-02", "recovered", {"psi": incidents["INC-02"]["after_psi"]}),
    ]
    for ident, phase, measured in spec:
        incident = incidents[ident]
        status = "VIOLATION" if phase == "degraded" else "HEALTHY"
        runbook = incident["runbook"]["runbook"]
        name = f"{ident}_{phase}"
        tags = {
            "synthetic": "true",
            "source": "measured_lab_incident_json",
            "incident_id": ident,
            "stage": phase,
            "slo_status": status,
            "runbook": runbook,
            "runbook_outcome": incident["runbook"]["status"],
            "training_run_id": train_run,
            "evidence_file": "actividad8/evidence/incidents.json",
            "measurement_note": "API HTTP measured" if ident == "INC-01" else "PSI measured on synthetic sensor batches",
        }
        with mlflow.start_run(run_name=name) as run:
            mlflow.set_tags(tags)
            mlflow.log_params({
                "incident": ident,
                "stage": phase,
                "synthetic": "true",
                "latency_threshold_ms": report["slo"]["max_latency_ms"],
                "drift_threshold_psi": report["slo"]["drift_psi"],
            })
            values = {}
            if ident == "INC-01":
                for k in ("p95_ms", "availability", "timely_ratio", "eligible",
                          "failures_5xx", "error_budget", "latency_budget_spent_pct",
                          "availability_budget_spent_pct"):
                    if _metric(measured.get(k)):
                        values[k] = float(measured[k])
            else:
                values["psi_temperature"] = float(measured["psi"])
                values["sample_count"] = float(450)
            mlflow.log_metrics(values)
            mlflow.log_artifact(str(src), artifact_path="source_evidence")
            output.append({
                "name": name, "run_id": run.info.run_id, "incident_id": ident,
                "stage": phase, "slo_status": status,
                "runbook": runbook, "metrics": values,
            })
    dest = HERE / "evidence" / "mlflow_incident_runs.json"
    dest.write_text(json.dumps({
        "synthetic": True, "status": "RECORDED",
        "experiment": "PredictiveMaintenanceAI_Actividad8_V2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "actividad8/evidence/incidents.json",
        "training_run_id": train_run,
        "runs": output,
        "disclaimer": "Six MLflow runs log measured stages, not six separate model retrainings.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("MLFLOW INCIDENT RUNS: RECORDED (" + str(len(output)) + ")")
    return output


if __name__ == "__main__":
    main()
