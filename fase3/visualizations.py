"""Evidencia gráfica SVG reproducible basada únicamente en JSON de CI.

No son screenshots: son gráficas derivadas de mediciones y eventos verificables.
"""
from __future__ import annotations
import json
from pathlib import Path
from xml.sax.saxutils import escape
from datetime import datetime

HERE=Path(__file__).resolve().parent
OUT=HERE/"evidence"
NAVY="#17334c";TEAL="#117b87";ORANGE="#cb6e42";WHITE="#fff";MUTED="#51687d"
def read(x):return json.loads((OUT/x).read_text(encoding="utf-8"))
def elem(x,y,text,size=15,color=NAVY,anchor="start",bold=False):
    return f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{"700" if bold else "400"}">{escape(str(text))}</text>'
def bar(x,y,w,h,color):
    return f'<rect x="{x}" y="{y}" width="{max(w,0):.2f}" height="{h}" fill="{color}" rx="3"/>'
def frame(title,subtitle,width=1020,height=570):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
        elem(45,55,title,25,NAVY,bold=True),elem(45,83,subtitle,13,MUTED)]
def save(data,name): (OUT/name).write_text("\n".join(data+["</svg>"])+"\n",encoding="utf-8")

def versions_chart():
    x=read("model_version_comparison.json")
    a=x["stable"];b=x["candidate"]
    content=frame("Modelos versionados: evaluación en el piloto sintético",
       "Misma partición / umbral; RF estable de 130 árboles frente a RF candidato de 135 árboles",height=590)
    content += [bar(45,111,20,14,NAVY),elem(72,124,a["version"]+" · estable",14),
                bar(360,111,20,14,TEAL),elem(386,124,b["version"]+" · candidato",14)]
    metrics=[("precision","Precisión"),("recall","Recall por ventana"),
      ("roc_auc","ROC-AUC"),("event_recall","Recall por evento")]
    for i,(key,name) in enumerate(metrics):
        y=175+i*95
        content.append(elem(45,y,name,15,bold=True))
        va=a["pilot"][key];vb=b["pilot"][key]
        content += [bar(265,y-26,620*va,24,NAVY),bar(265,y+6,620*vb,24,TEAL),
                    elem(905,y-7,f"{va:.3f}",15,NAVY,anchor="end"),
                    elem(905,y+25,f"{vb:.3f}",15,TEAL,anchor="end")]
    content +=[elem(45,557,"SHA estable: "+a["sha256"][:20]+"…",12,MUTED),
       elem(525,557,"SHA candidato: "+b["sha256"][:20]+"…",12,MUTED)]
    save(content,"fig_01_versiones_modelo.svg")

def latency_chart():
    initial=read("router_promoted.json")
    degraded=read("router_degradation.json")
    recovery=read("router_restored.json")
    final=read("router_final.json")
    def p95(data):
        z=sorted(p["elapsed_ms"] for p in data["predictions"])
        return z[0]*.05+z[-1]*.95 if len(z)==2 else z[-1]*.9+z[-2]*.1
    values=[p95(initial),degraded["p95_ms"],p95(recovery),p95(final)]
    labels=["Candidato sano","Candidato degradado","Rollback a estable","Candidato recuperado"]
    colors=[TEAL,ORANGE,NAVY,TEAL]
    maxv=max(max(values)*1.20,800)
    content=frame("Degradación controlada y rollback del modelo",
       "p95 HTTP medido desde el router en GitHub Actions; cuatro momentos del mismo despliegue",height=510)
    y0=380
    for i,(val,label,color) in enumerate(zip(values,labels,colors)):
        x=60+i*241;h=235*val/maxv
        content.append(bar(x,y0-h,127,h,color))
        content.append(elem(x+64,y0-h-12,f"{val:.1f} ms",16,color,anchor="middle",bold=True))
        content.append(elem(x+64,410,label,13,NAVY,anchor="middle"))
    yline=y0-235*500/maxv
    content += [f'<line x1="40" y1="{yline:.1f}" x2="985" y2="{yline:.1f}" stroke="{ORANGE}" stroke-dasharray="7,6" stroke-width="1.6"/>',
       elem(45,yline-8,"Umbral de 500 ms",12,ORANGE)]
    content.append(elem(45,484,"El deterioro es una inyección de latencia en candidate, no una caída natural de ROC-AUC.",12,MUTED))
    save(content,"fig_02_latencia_rollback.svg")

def events_chart():
    raw=read("deployment_events.json")
    events=raw["events"]
    content=frame("Registro de promoción y recuperación GitOps",
      "Eventos versionados en Git y comprobados con respuestas HTTP y huellas SHA-256",height=500)
    positions=[115,350,585,820]
    for i,e in enumerate(events):
        x=positions[i] if i<len(positions) else 115+i*180
        kind=e["type"]
        color=ORANGE if kind=="ROLLBACK_MODEL" else (TEAL if kind=="PROMOTE" else NAVY)
        content +=[bar(x,160,175,64,color),
             elem(x+87,188,kind,15,WHITE,anchor="middle",bold=True),
             elem(x+87,210,e["active_slot"],13,WHITE,anchor="middle"),
             elem(x+87,259,e["release_version"],12,NAVY,anchor="middle"),
             elem(x+87,279,e["model_sha256"][:12]+"…",12,MUTED,anchor="middle"),
             elem(x+87,310,e["at_utc"].split("T")[-1][:12]+" UTC",11,MUTED,anchor="middle")]
        if i<len(events)-1:
            content.append(f'<path d="M {x+180} 192 L {x+227} 192" stroke="{NAVY}" stroke-width="2" fill="none"/>')
    content.append(elem(45,410,"El modelo estable y el candidato son binarios diferentes y el rollback recupera el SHA anterior.",14,NAVY))
    content.append(elem(45,454,"Duraciones observadas en un runner efímero; no prueban RTO de una planta real.",12,MUTED))
    save(content,"fig_03_timeline_gitops.svg")

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    versions_chart();latency_chart();events_chart()
    for p in sorted(OUT.glob("fig_0*.svg")):print("SVG",p.name,p.stat().st_size)
if __name__=="__main__":main()
