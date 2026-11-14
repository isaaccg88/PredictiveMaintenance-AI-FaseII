"""Comprueba que las seis etapas MLflow coincidan con incidentes.json medido."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import mlflow
from mlflow.tracking import MlflowClient
from .simulator import HERE


def main():
    base = HERE / "evidence"
    report = json.loads((base / "incidents.json").read_text(encoding="utf-8"))
    mapping = json.loads((base / "mlflow_incident_runs.json").read_text(encoding="utf-8"))
    if len(mapping["runs"]) != 6:
        raise AssertionError("Faltan runs de incidentes en MLflow")
    mlflow.set_tracking_uri((HERE / "mlruns").resolve().as_uri())
    client = MlflowClient()
    incidents = {x["incident_id"]: x for x in report["incidents"]}
    seen = set()
    for entry in mapping["runs"]:
        key = (entry["incident_id"], entry["stage"])
        if key in seen:
            raise AssertionError("Run duplicado en el resumen de incidentes")
        seen.add(key)
        run = client.get_run(entry["run_id"])
        if run.info.status != "FINISHED":
            raise AssertionError(f"Run incompleto: {entry['run_id']}")
        if run.data.tags.get("incident_id") != entry["incident_id"]:
            raise AssertionError("La etiqueta de incidente no coincide")
        if run.data.tags.get("stage") != entry["stage"]:
            raise AssertionError("La etiqueta de fase no coincide")
        if run.data.tags.get("synthetic") != "true":
            raise AssertionError("Falta aclaración de datos sintéticos")
        incident = incidents[entry["incident_id"]]
        phase = entry["stage"]
        if entry["incident_id"] == "INC-01":
            source = incident[{"baseline": "baseline", "degraded": "during", "recovered": "after"}[phase]]
            expected = float(source["p95_ms"])
            observed = run.data.metrics.get("p95_ms")
            breach = source["latency_breached"]
            limit = float(report["slo"]["max_latency_ms"])
            if phase == "degraded" and not breach:
                raise AssertionError("La etapa degradada no incumple el SLO")
            if phase != "degraded" and breach:
                raise AssertionError("La fase sana todavía incumple el SLO")
        else:
            expected = float(incident[{"baseline": "baseline_psi", "degraded": "during_psi", "recovered": "after_psi"}[phase]])
            observed = run.data.metrics.get("psi_temperature")
            limit = float(report["slo"]["drift_psi"])
            if (expected > limit) != (phase == "degraded"):
                raise AssertionError("La fase drift no coincide con el umbral")
        if observed is None or abs(observed - expected) > 1e-6:
            raise AssertionError(f"Valor MLflow diferente a evidencia: {entry['run_id']}")
        paths = [p.path for p in client.list_artifacts(entry["run_id"], "source_evidence")]
        if "source_evidence/incidents.json" not in paths:
            raise AssertionError("Falta incidents.json como artefacto en MLflow")
    expected_keys = {(i, p) for i in ("INC-01", "INC-02") for p in ("baseline", "degraded", "recovered")}
    if seen != expected_keys:
        raise AssertionError("No están todas las etapas de incidentes")
    summary = {
        "status": "VERIFIED",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_count": len(seen),
        "runs": [{"run_id": x["run_id"], "name": x["name"], "metrics": x["metrics"]}
                 for x in mapping["runs"]],
        "synthetic_data": True,
    }
    (base / "mlflow_incident_audit.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("MLFLOW INCIDENT AUDIT: PASS — 6 stages verified")
    return summary


if __name__ == "__main__":
    main()
