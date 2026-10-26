"""Read-only sensitivity analysis of the actual trained 72-hour model.

Run inside the FastAPI Docker container:
    docker compose cp ./tests/sensitivity_whatif.py api:/tmp/sensitivity_whatif.py
    docker compose exec -T api python /tmp/sensitivity_whatif.py

Does not call the prediction endpoint and never writes to the SQLite database.
These are synthetic, potentially nonphysical independent feature interventions,
not evidence of real industrial effectiveness or calibrated counterfactuals.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import pandas as pd


MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/artifacts/risk72h_model.joblib"))
SNAPSHOT_PATH = Path(os.getenv("SNAPSHOT_PATH", "/app/artifacts/pilot_snapshot.json"))
META_PATH = Path(os.getenv("META_PATH", "/app/artifacts/model_metadata.json"))
OUTPUT_PATH = Path("/tmp/sensitivity_pm049.json")


def main() -> None:
    metadata = json.loads(META_PATH.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert snapshot["synthetic"] is True
    assert metadata["horizon_hours"] == 72
    selected = next(m for m in snapshot["machines"] if m["machine_id"] == "PM-049")
    features = {name: selected[name] for name in metadata["features"]}
    model = joblib.load(MODEL_PATH)  # trusted project artifact only
    threshold = float(metadata["threshold"])

    def evaluate(changes: dict[str, float]) -> float:
        data = dict(features)
        data.update(changes)
        return round(float(model.predict_proba(pd.DataFrame([data]))[0, 1]), 6)

    scenarios = [
        ("Original sin cambios", {}),
        ("Temperatura 110 C", {"temperature_c": 110.0}),
        ("Vibracion 8 mm/s", {"vibration_mm_s": 8.0}),
        ("Desgaste 0.99", {"wear_index": 0.99}),
        ("Tres sensores severos", {
            "temperature_c": 110.0,
            "vibration_mm_s": 8.0,
            "wear_index": 0.99,
        }),
        ("Primer escenario del usuario", {
            "temperature_c": 53.5,
            "vibration_mm_s": 3.3,
            "wear_index": 0.57,
        }),
    ]

    base = evaluate({})
    records = []
    print("DIAGNOSTICO DE SENSIBILIDAD — PM-049 — MODELO REAL, DATOS SINTETICOS")
    print("Ninguna consulta crea un registro en SQLite.")
    print(f"Riesgo base: {base:.2%}; umbral de alerta: {threshold:.2%}")
    print()
    print(f"{'Escenario':33} {'Probabilidad':>13} {'Cambio (pp)':>13} {'Nivel':>8}")
    print("-" * 74)
    for name, changes in scenarios:
        p = evaluate(changes)
        level = "ALTO" if p >= threshold else ("MEDIO" if p >= threshold / 2 else "BAJO")
        record = {
            "scenario": name,
            "overrides": changes,
            "probability_72h": p,
            "delta_percentage_points": round(100 * (p - base), 3),
            "risk_level": level,
        }
        records.append(record)
        print(f"{name:33} {p:>12.2%} {100*(p-base):>+12.2f} {level:>8}")

    grids = {
        "temperature_c": [50, 60, 70, 80, 90, 100, 110],
        "vibration_mm_s": [0.5, 1, 1.5, 2, 3, 4, 6, 8],
        "wear_index": [0.40, 0.55, 0.65, 0.75, 0.85, 0.95, 0.99],
    }
    sweeps = {}
    print("\nBARRIDO DE UNA VARIABLE A LA VEZ (otras 11 sin cambios)")
    for field, values in grids.items():
        probabilities = [evaluate({field: float(value)}) for value in values]
        decreases = sum(
            later < earlier - 1e-9
            for earlier, later in zip(probabilities, probabilities[1:])
        )
        sweeps[field] = {
            "inputs": values,
            "probability_72h": probabilities,
            "downward_steps_as_input_increases": decreases,
        }
        print(f"{field}:")
        for value, p in zip(values, probabilities):
            print(f"  {value:>7}: {p:>7.2%}")
        print(f"  Descensos al aumentar la variable: {decreases}")

    result = {
        "academic_synthetic_only": True,
        "machine_id": selected["machine_id"],
        "horizon_hours": 72,
        "threshold": threshold,
        "base_features": features,
        "scenarios": records,
        "single_feature_sweeps": sweeps,
        "interpretation_limitations": [
            "Random Forest does not impose monotonic relationships.",
            "The simulation's failure mechanism depends mainly on wear, load and machine vulnerability.",
            "Historical rolling features remain unchanged in one-at-a-time interventions.",
            "Extreme interventions may be outside the synthetic training distribution.",
            "The exercise is sensitivity analysis, not industrial prognostic validation.",
        ],
    }
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nReporte JSON guardado en: {OUTPUT_PATH}")
    print("ESTADO: DIAGNOSTICO COMPLETADO (sin escrituras en la base de datos)")


if __name__ == "__main__":
    main()
