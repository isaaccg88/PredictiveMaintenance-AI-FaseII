"""Verificación automática de consistencia del README publicado y evidencias.

Solo valida contenido técnico y enlaces, sin incluir checklist de evaluación
o notas internas en el README.
"""
from __future__ import annotations
import json,re
from pathlib import Path
from .gitops import read

ROOT=Path(__file__).resolve().parent.parent
EV=ROOT/"fase3/evidence"
def main():
    s=(ROOT/"README.md").read_text(encoding="utf-8")
    stable=read(EV/"release_manifest.json")
    candidate=read(EV/"candidate_release_manifest.json")
    ops=read(EV/"operations_audit.json")
    comp=read(EV/"model_version_comparison.json")
    if stable["model_sha256"]==candidate["model_sha256"]:
        raise AssertionError("No hay versiones diferenciadas")
    if not ops["model_version_rollback_verified"] or ops["rollback_to_sha256"]!=stable["model_sha256"]:
        raise AssertionError("No hay rollback verificable al modelo original")
    if comp["stable"]["sha256"]!=stable["model_sha256"] or comp["candidate"]["sha256"]!=candidate["model_sha256"]:
        raise AssertionError("Evaluación y manifests no corresponden")
    for token in ("<!-- F3-RELEASE-START -->","<!-- F3-RELEASE-END -->",
       "<!-- F3-OPERATIONS-START -->","<!-- F3-OPERATIONS-END -->",
       stable["version"],candidate["version"],stable["mlflow_run_id"],
       f"{ops['candidate_latency_regression_p95_ms']:.2f} ms",
       f"{ops['api_latency_p95_ms']:.3f} ms"):
        if token not in s:raise AssertionError("README desactualizado: "+token)
    internal=[]
    for m in re.finditer(r"!?(?:\[[^\]]*\])\(([^)]+)\)",s):
        path=m.group(1).split("#",1)[0]
        if not path or path.startswith(("http:","https:","mailto:")):continue
        internal.append(path)
        if not (ROOT/path).exists():
            raise AssertionError("Enlace local roto: "+path)
    for plot in ("fig_01_versiones_modelo.svg","fig_02_latencia_rollback.svg",
                 "fig_03_timeline_gitops.svg"):
        p=EV/plot
        if not p.exists() or p.stat().st_size<2000 or "<svg" not in p.read_text():
            raise AssertionError("Falta visualización reproducible: "+plot)
        if f"fase3/evidence/{plot}" not in s:raise AssertionError("La figura no se explica en el README")
    if re.search(r"rúbrica|el profesor|entrevista técnica|preguntas para entrevista|video pendiente",s,re.I):
        raise AssertionError("Se incluyeron notas editoriales externas al reporte técnico")
    check={"status":"PASS","source":"ci_report_integrity",
       "links_checked":len(internal),"broken_links":0,
       "plots_checked":3,"version_distinct":True,
       "rollback_sha_verified":True,"mlflow_run_id":stable["mlflow_run_id"],
       "readme_lines":len(s.splitlines())}
    (EV/"report_integrity.json").write_text(json.dumps(check,ensure_ascii=False,indent=2)+"\n")
    print("REPORT INTEGRITY PASS",check)
    return check
if __name__=="__main__":main()
