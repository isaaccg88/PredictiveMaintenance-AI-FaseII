"""Figuras reproducibles, construidas exclusivamente con JSON del laboratorio A9.

Se generan en GitHub Actions; las figuras no contienen datos inventados.
"""
from __future__ import annotations

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
NAVY="#1C3449"; TEAL="#087F8C"; CORAL="#D16B47"; GREY="#526577"; GREEN="#2F7962"

def data(file):
    return json.loads((EVIDENCE/file).read_text(encoding="utf-8"))

def prepare(ax, title, ylabel):
    ax.set_title(title,loc="left",fontsize=12,fontweight="bold",color=NAVY,pad=15)
    ax.set_ylabel(ylabel,color=NAVY)
    ax.grid(True,axis="y",alpha=.18)
    ax.set_axisbelow(True)
    ax.spines[['top','right']].set_visible(False)

def foot(fig, message):
    fig.text(.09,.01,message,fontsize=7.7,color=GREY)

def output(fig, name):
    fig.savefig(EVIDENCE/name,dpi=175,bbox_inches="tight",facecolor="white")
    plt.close(fig)

def main():
    EVIDENCE.mkdir(exist_ok=True,parents=True)
    b=data("load_benchmark.json")
    x=[r["concurrency"] for r in b["single"]["levels"]]
    s=b["single"]["levels"]; d=b["dual"]["levels"]
    fig,ax=plt.subplots(figsize=(9.0,4.9))
    prepare(ax,"Figura 2. Latencia HTTP p95 bajo diferentes niveles de carga","Latencia p95 (ms)")
    ax.plot(x,[r["p95_ms"] for r in s],marker="o",lw=2.2,color=NAVY,label="Una instancia")
    ax.plot(x,[r["p95_ms"] for r in d],marker="s",lw=2.2,color=TEAL,label="Dos instancias")
    ax.axhline(500,color=CORAL,ls="--",lw=1.4,label="Umbral diagnóstico: 500 ms")
    ax.set_xticks(x);ax.set_xlabel("Solicitudes simultáneas")
    ax.legend(frameon=False,loc="upper left",fontsize=9)
    foot(fig,"60 solicitudes por ventana; dos instancias comparten el mismo runner. No representa AWS ni prueba SLA cloud.")
    output(fig,"fig_02_latencia_p95.png")

    fig,ax=plt.subplots(figsize=(9.0,4.9))
    prepare(ax,"Figura 3. Throughput medido frente a concurrencia","Solicitudes completadas por segundo (RPS)")
    ax.plot(x,[r["throughput_rps"] for r in s],marker="o",lw=2.2,color=NAVY,label="Una instancia")
    ax.plot(x,[r["throughput_rps"] for r in d],marker="s",lw=2.2,color=TEAL,label="Dos instancias")
    ax.set_xticks(x);ax.set_xlabel("Solicitudes simultáneas")
    ax.legend(frameon=False,loc="upper left",fontsize=9)
    foot(fig,"Medición loopback de corta duración en CI; requiere replicación estadística y prueba sostenida.")
    output(fig,"fig_03_throughput.png")

    costs=data("finops_model.json")["estimates"]
    scenarios=["piloto","crecimiento","expansion"]
    names=[("cloud_naive","Sin HA / x86"),("ha_without_rightsizing","HA / x86"),
           ("proposed_rightsized_arm","HA / ARM + right-sizing")]
    positions=np.arange(len(scenarios));w=.25
    fig,ax=plt.subplots(figsize=(9.0,5.0))
    prepare(ax,"Figura 4. Proyección FinOps por escenario y arquitectura","Costo mensual estimado (USD)")
    for i,(key,label) in enumerate(names):
        vals=[next(r["total_usd_month"] for r in costs
                   if r["scenario"]==sc and r["architecture_name"]==key) for sc in scenarios]
        bars=ax.bar(positions+(i-1)*w,vals,width=w,
                    color=[GREY,NAVY,TEAL][i],label=label)
        for bar,val in zip(bars,vals):
            ax.text(bar.get_x()+bar.get_width()/2,val+7,f"${val:.0f}",ha="center",fontsize=7.8,color=NAVY)
    ax.set_xticks(positions,["0.5 M","10 M","60 M"])
    ax.set_xlabel("Peticiones mensuales: tres escenarios sintéticos")
    ax.set_ylim(0,max(r["total_usd_month"] for r in costs)*1.25)
    ax.legend(frameon=False,fontsize=8.8,loc="upper left")
    foot(fig,"Modelo incompleto de TCO: excluye NAT, WAF, backups, soporte y personas. ARM no validado en AWS.")
    output(fig,"fig_04_costos_finops.png")

    fairness=data("fairness_machine_types.json")
    groups=fairness["groups"];names=list("ABC")
    vals=[groups[g]["recall_tpr"]*100 for g in names]
    lower=[(groups[g]["recall_tpr"]-groups[g]["tpr_cluster_bootstrap_95ci"][0])*100 for g in names]
    upper=[(groups[g]["tpr_cluster_bootstrap_95ci"][1]-groups[g]["recall_tpr"])*100 for g in names]
    fig,ax=plt.subplots(figsize=(9.0,4.9))
    prepare(ax,"Figura 5. Recall por tipo de máquina con incertidumbre","Recall de eventos etiquetados por ventana (%)")
    bars=ax.bar(names,vals,color=[NAVY,TEAL,GREEN],width=.55)
    ax.errorbar(names,vals,yerr=[lower,upper],fmt="none",capsize=6,color=CORAL,lw=2)
    for b,g,val in zip(bars,names,vals):
        ax.text(b.get_x()+b.get_width()/2,3,f"n={groups[g]['machines']} máquinas",ha="center",
                fontsize=8.5,color="white")
        ax.text(b.get_x()+b.get_width()/2,val+3,f"{val:.1f}%",ha="center",fontsize=9,color=NAVY)
    ax.set_ylim(0,105)
    foot(fig,"IC 95% bootstrap de máquina (4 clústeres por tipo); intervalos ilustrativos, no certificación de fairness.")
    output(fig,"fig_05_fairness_tpr.png")
    print("FIGURAS A9 verificadas:",*[x.name for x in sorted(EVIDENCE.glob("fig_*.png"))])
if __name__ == "__main__":
    main()
