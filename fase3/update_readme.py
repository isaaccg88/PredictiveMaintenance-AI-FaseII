"""Sincronizar el informe técnico con releases y métricas del mismo run CI/CD."""
from __future__ import annotations
import json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
README=ROOT/"README.md"
EVIDENCE=ROOT/"fase3"/"evidence"
BASE="https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII"
def read(n):return json.loads((EVIDENCE/n).read_text(encoding="utf-8"))
def block(text,label,updated):
    pat=r"<!-- F3-"+label+r"-START -->[\s\S]*?<!-- F3-"+label+r"-END -->"
    out,n=re.subn(pat,lambda _:f"<!-- F3-{label}-START -->\n{updated.strip()}\n<!-- F3-{label}-END -->",text)
    if n!=1:raise RuntimeError(f"Marcador {label} no encontrado exactamente una vez ({n})")
    return out
def main():
    stable=read("release_manifest.json")
    candidate=read("candidate_release_manifest.json")
    comparison=read("model_version_comparison.json")
    ops=read("operations_audit.json")
    events=read("deployment_events.json")
    if stable["model_sha256"]!=ops["stable_model_sha256"]:
        raise AssertionError("Release estable y auditoría no coinciden")
    if candidate["model_sha256"]!=ops["model_sha256"] or candidate["model_sha256"]==stable["model_sha256"]:
        raise AssertionError("El manifiesto candidato difiere del estado esperado")
    if events["state"]["active_slot"]!="candidate" or ops["rollback_events"]!=1:
        raise AssertionError("No se completó recuperación")
    run=stable["ci_run_id"]
    url=f"{BASE}/actions/runs/{run}"
    rel=f"""<details>
<summary>Identidad de los modelos y trazabilidad de la ejecución</summary>

| Modelo | Versión | SHA-256 |
|---|---|---|
| Stable · Random Forest 130 árboles | `{stable['version']}` | `{stable['model_sha256']}` |
| Candidate · Random Forest 135 árboles | `{candidate['version']}` | `{candidate['model_sha256']}` |

**Entrenamiento:** candidata construida con cinco árboles adicionales por `warm_start`, sin alterar el conjunto de entrenamiento y conservando el umbral fijado mediante validación. Los dos binarios son distintos y pasan los controles de integridad.

**Tracking MLflow:** experimento `{stable['mlflow_experiment']}`, run `{stable['mlflow_run_id']}`.  
**Commit de origen:** `{stable['source_commit']}`.  
**Ejecución completa:** [GitHub Actions #{run}]({url}).

</details>

[Manifest estable](fase3/evidence/release_manifest.json) · [Manifest candidato](fase3/evidence/candidate_release_manifest.json) · [Evaluación comparada](fase3/evidence/model_version_comparison.json).
"""
    ops_md=f"""| Métrica de la ejecución #{run} | Resultado |
|---|---:|
| Versión inicial | **`{stable['version']}`** |
| Versión candidata validada | **`{candidate['version']}`** |
| Modelos binarios distintos | **Sí, SHA-256 diferentes** |
| Solicitudes `/predict` en candidata final | **{ops['api_predict_samples']}** |
| Respuestas HTTP 5xx del backend final | **{ops['api_http_5xx']}** |
| Éxito backend de la muestra final | **{ops['api_availability_ratio']*100:.1f}%** |
| Latencia p95 backend final | **{ops['api_latency_p95_ms']:.3f} ms** |
| Latencia p95 degradada, medida en el router | **{ops['candidate_latency_regression_p95_ms']:.2f} ms** |
| Umbral diagnóstico de latencia | **{ops['candidate_latency_threshold_ms']} ms** |
| Promociones / rollback de modelo | **{ops['promotions']} / {ops['rollback_events']}** |
| SHA tras rollback | **`{ops['rollback_to_sha256'][:12]}` (stable)** |
| Slot después de recuperar candidata | **`{ops['active_slot']}`** |

**Interpretación:** el servicio enrutó dos versiones reales. La latencia adicional del candidato fue introducida deliberadamente después de su primera promoción para verificar una respuesta correctiva. El rollback devolvió el tráfico al **modelo estable de 130 árboles**, cuya identidad se verificó por HTTP, y más tarde se restauró la candidata sin degradación. No se interpreta esta inyección como una pérdida natural de precisión.

![Comparación de modelos sobre holdout sintético](fase3/evidence/fig_01_versiones_modelo.svg)

**Figura 10.** Métricas del piloto de 12 máquinas para dos versiones realmente evaluadas, con el mismo umbral.

![Degradación y recuperación de latencia](fase3/evidence/fig_02_latencia_rollback.svg)

**Figura 11.** p95 HTTP observado antes/durante/después del rollback; la línea indica el límite diagnóstico de 500 ms.

![Eventos GitOps registrados](fase3/evidence/fig_03_timeline_gitops.svg)

**Figura 12.** Secuencia verificable de promoción, degradación, rollback y re-promoción, con versiones y hashes.

[Auditoría completa](fase3/evidence/operations_audit.json) · [Muestras de latencia degradada](fase3/evidence/router_degradation.json) · [Estado restaurado](fase3/evidence/router_restored.json) · [GitHub Actions #{run}]({url}).
"""
    s=README.read_text(encoding="utf-8")
    s=block(s,"RELEASE",rel)
    s=block(s,"OPERATIONS",ops_md)
    README.write_text(s,encoding="utf-8")
    print("REPORT SYNC OK:",run,stable["version"],candidate["version"])
if __name__=="__main__":main()
