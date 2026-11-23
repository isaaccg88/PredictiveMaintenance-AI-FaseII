"""Actualizar solo bloques marcados con evidencia del MISMO job GitHub Actions.

No crea nuevos reportes. El README es el documento técnico y portfolio.
"""
from __future__ import annotations
import json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
README=ROOT/"README.md"
EVIDENCE=ROOT/"fase3"/"evidence"
BASE="https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII"
def read(name):return json.loads((EVIDENCE/name).read_text(encoding="utf-8"))
def block(text,label,updated):
    pat=r"<!-- F3-"+label+r"-START -->[\s\S]*?<!-- F3-"+label+r"-END -->"
    out,count=re.subn(pat,lambda _:f"<!-- F3-{label}-START -->\n{updated.strip()}\n<!-- F3-{label}-END -->",text)
    if count!=1:raise RuntimeError(f"Bloque {label} esperado una vez, encontrado {count}")
    return out

def main():
    r=read("release_manifest.json")
    o=read("operations_audit.json")
    events=read("deployment_events.json")
    if r["model_sha256"]!=o["model_sha256"] or r["version"]!=o["release_version"]:
        raise AssertionError("README: evidencia release vs operación incongruente")
    if events["state"]["active_slot"]!="candidate":
        raise AssertionError("README: operación final no promovida")
    id=r["ci_run_id"]
    url=f"{BASE}/actions/runs/{id}"
    rel=f"""<details>
<summary>Manifest de la última release validada</summary>

- **Versión:** `{r['version']}`
- **SHA-256 completo:** `{r['model_sha256']}`
- **Experimento MLflow:** `{r['mlflow_experiment']}`
- **Run MLflow de esta ejecución:** `{r['mlflow_run_id']}`
- **Commit origen:** `{r['source_commit']}`
- **Alcance:** `{r['approval_scope']}` (autorización industrial = `false`)
- **GitHub Actions:** [ejecución #{id}]({url})

</details>

[JSON de release](fase3/evidence/release_manifest.json) · [MLflow auditado por el pipeline](actividad8/mlflow_audit.py) · [Evidencia operativa](fase3/evidence/operations_audit.json).
"""
    ops=f"""| Campo medido en última ejecución #{id} | Resultado |
|---|---:|
| Backend `/predict` registrado | **{o['api_predict_samples']} solicitudes** |
| Respuestas HTTP 5xx del backend | **{o['api_http_5xx']}** |
| Disponibilidad backend de la muestra | **{o['api_availability_ratio']*100:.1f}%** |
| Oportunidad backend de la muestra | **{o['api_timely_ratio']*100:.1f}%** |
| Latencia p95 backend | **{o['api_latency_p95_ms']:.3f} ms** |
| Caída observada desde router (fuera del contador backend) | **HTTP {o['router_outage_status']}** |
| Transiciones verificadas | **{o['promotions']} promociones y {o['rollback_events']} rollback** |
| Slot final | **`{o['active_slot']}`** |

Estas cifras proceden de [la misma ejecución aprobada]({url}); no son promedios de un servicio permanente. El error 502 se conserva en el [smoke del router](fase3/evidence/router_failure.json), por separado de `/metrics` del backend apagado.
"""
    s=README.read_text(encoding="utf-8")
    s=block(s,"RELEASE",rel)
    s=block(s,"OPERATIONS",ops)
    README.write_text(s,encoding="utf-8")
    print("README sincronizado con ejecución",id)
if __name__=="__main__":main()
