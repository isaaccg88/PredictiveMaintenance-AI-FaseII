"""Capturas AUTÉNTICAS de MLflow UI para el README (se ejecuta en CI).

No genera imágenes sintéticas de la interfaz: automatiza Chromium sobre el servidor
MLflow del runner y comprueba contenido antes de guardar. Si falla no publica.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from .simulator import HERE


def main():
    host = os.environ.get("MLFLOW_UI_URL", "http://127.0.0.1:5000").rstrip("/")
    dest = HERE / "evidence" / "screenshots"
    dest.mkdir(parents=True, exist_ok=True)
    records = json.loads((HERE / "evidence" / "mlflow_incident_runs.json").read_text())
    training = json.loads((HERE / "results" / "mlflow_run.json").read_text())
    validated = json.loads((HERE / "evidence" / "mlflow_validation.json").read_text())
    experiment_id = validated["experiment_id"]
    run_id = training["run_id"]
    degraded = next(x["run_id"] for x in records["runs"]
                    if x["name"] == "INC-01_degraded")
    drift_degraded = next(x["run_id"] for x in records["runs"]
                          if x["name"] == "INC-02_degraded")
    saved = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1600, "height": 1450},
                                device_scale_factor=1)
        page.goto(host, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(3800)
        body = page.locator("body").inner_text(timeout=20000)
        if "MLflow" not in body and "Experiments" not in body:
            raise AssertionError("La página capturada no parece ser la interfaz MLflow")
        # MLflow tiene distintas rutas según su versión; el enlace hash funciona
        # con MLflow 3.6.0. Se valida el texto visible, no solo HTTP 200.
        page.goto(host + "/#/experiments/" + str(experiment_id),
                  wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(5000)
        body = page.locator("body").inner_text(timeout=20000)
        if "PredictiveMaintenanceAI_Actividad8_V2" not in body:
            raise AssertionError("El listado MLflow no muestra nuestro experimento")
        # MLflow 3.6 muestra a veces un globo de confirmación de tipo.
        # Se descarta antes de tomar evidencia legible del listado de runs.
        confirm = page.get_by_role("button", name="Confirm")
        if confirm.count() and confirm.first.is_visible():
            confirm.first.click()
            page.wait_for_timeout(800)
        file = dest / "MLflow_experimento_runs.png"
        page.screenshot(path=str(file), full_page=True)
        saved.append(str(file))
        for label, target in [
            ("MLflow_modelo_v2_metricas.png", run_id),
            ("MLflow_incidente_latencia.png", degraded),
            ("MLflow_incidente_drift.png", drift_degraded),
        ]:
            page.goto(host + "/#/experiments/" + str(experiment_id) +
                      "/runs/" + str(target),
                      wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(5000)
            body = page.locator("body").inner_text(timeout=20000)
            if target not in body and not any(x in body for x in
                    ("Metrics", "Parameters", "Métricas", "Parámetros")):
                raise AssertionError("MLflow no mostró detalle del run " + target)
            file = dest / label
            page.screenshot(path=str(file), full_page=True)
            saved.append(str(file))
        browser.close()
    manifest = {"type": "real_mlflow_ui_screenshots",
                "mlflow_run_id_training": run_id,
                "mlflow_run_id_incident": degraded,
                "mlflow_run_id_drift": drift_degraded,
                "experiment_id": experiment_id,
                "files": [Path(x).name for x in saved],
                "source": "Chromium headless against MLflow 3.6 local runner",
                "data_scope": "synthetic",
                "no_manual_image_modification": True}
    (HERE / "evidence" / "mlflow_screenshots_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print("AUTHENTIC MLFLOW UI SCREENSHOTS: PASS; " + ", ".join(manifest["files"]))


if __name__ == "__main__":
    main()
