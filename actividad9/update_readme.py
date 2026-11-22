"""Mantener el README sincronizado con la corrida que generó la evidencia.

Evita números obsoletos en tablas después de que GitHub Actions vuelve a medir
throughput y p95 en un runner de capacidades variables.
"""
from __future__ import annotations

import json, os, re, math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
EVIDENCE=HERE/"evidence"
README=ROOT/"README.md"
BASE="https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII"

def get(name):
    return json.loads((EVIDENCE/name).read_text(encoding="utf-8"))

def fmt(x,places=1): return f"{x:,.{places}f}"
def run_link():
    key=os.getenv("GITHUB_RUN_ID","")
    return f"[GitHub Actions #{key}]({BASE}/actions/runs/{key})" if key else "[Workflow de la Actividad 9]("+BASE+"/actions/workflows/actividad9.yml)"

def section(code,body):
    return "<!-- A9-"+code+"-START -->\n"+body.strip()+"\n<!-- A9-"+code+"-END -->"

def benchmark():
    z=get("load_benchmark.json")
    rows=["| Configuración | Concurrencia | N | p95 (ms) | p99 (ms) | Throughput (req/s) | SLI oportuno (2xx ≤500 ms) |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for label,key in (("Una API","single"),("Dos API, mismo runner","dual")):
        for x in z[key]["levels"]:
            rows.append(f"| {label} | {x['concurrency']} | {x['samples']} | {x['p95_ms']:.1f} | {x['p99_ms']:.1f} | {x['throughput_rps']:.2f} | {100*x['timely_ratio']:.1f}% |")
    a={x["concurrency"]:x for x in z["single"]["levels"]}
    b={x["concurrency"]:x for x in z["dual"]["levels"]}
    gain=(b[4]["throughput_rps"]/a[4]["throughput_rps"]-1)*100
    n=z["single"]["levels"][0]["samples"]
    limit=100*(.05**(1/n))
    return section("BENCH",f"""### Tabla 1. Baseline y pruebas de carga de la última ejecución verificada

Los resultados provienen de {run_link()}. Se realizaron **{n} solicitudes por ventana**, con concurrencia de 1, 4, 8 y 16. Dos procesos FastAPI comparten el **mismo runner**; esto no representa infraestructura desplegada en ECS, un ALB ni tolerancia a fallos multizona.

{chr(10).join(rows)}

![Figura 2. Latencia p95 con umbral de 500 ms](actividad9/evidence/fig_02_latencia_p95.png)

**Figura 2 — Latencia:** muestra la evolución de p95 conforme aumenta el número de solicitudes simultáneas. La línea punteada de 500 ms es un umbral diagnóstico; la regla de oportunidad de la Actividad 8 comprueba el porcentaje de solicitudes 2xx que llegan a tiempo. Una prueba aislada no valida el SLO mensual.

![Figura 3. Rendimiento RPS vs concurrencia](actividad9/evidence/fig_03_throughput.png)

**Figura 3 — Throughput:** a concurrencia 4, una instancia procesó **{a[4]['throughput_rps']:.2f} req/s**, frente a **{b[4]['throughput_rps']:.2f} req/s** con dos, diferencia relativa del **{gain:.1f}%**. Se trata de una comparación experimental con 60 solicitudes, no una razón de escalado garantizada ni lineal.

**Alcance estadístico:** aun si las {n} respuestas fueran correctas y oportunas, con una cota binomial unilateral del 95% y suponiendo independencia, el límite inferior aproximado de la tasa real es **{limit:.2f}%**. Por tanto, mostrar 100% observado **no acredita estadísticamente el SLO de 99%**. Se requieren pruebas largas, bajo carga realista y entre zonas; un cálculo ideal necesitaría al menos 299 de 299 éxitos para superar esa cota del 99%, aunque la independencia tampoco estaría garantizada.

**CPU/RAM:** el [archivo del benchmark](actividad9/evidence/load_benchmark.json) registra RSS y tiempo de CPU de los procesos Linux, no capacidad Fargate reservada. No se realizó una prueba real de escalabilidad vertical. La capacidad ARM y el escalamiento por AZ siguen pendientes de validación.
""")

def cost():
    z=get("finops_model.json")
    rows=["| Tráfico mensual | Arquitectura | Réplicas API calculadas | USD/mes | USD/1000 solicitudes |",
          "|---|---|---:|---:|---:|"]
    for x in z["estimates"]:
        rows.append(f"| {x['scenario']} ({x['monthly_requests']/1e6:g} M) | \`{x['architecture_name']}\` | {x['replicas_estimated']} | {x['total_usd_month']:.2f} | {x['usd_per_1000_requests']:.5f} |".replace("\\`","`"))
    grow={x["architecture_name"]:x for x in z["estimates"] if x["scenario"]=="crecimiento"}
    baseline=grow["ha_without_rightsizing"]
    proposal=grow["proposed_rightsized_arm"]
    diff=baseline["total_usd_month"]-proposal["total_usd_month"]
    saving=100*diff/baseline["total_usd_month"]
    arch=proposal["architecture"]
    extra=2*z["rates"]["hours_month"]*(arch["api_vcpu"]*z["rates"]["fargate_arm_vcpu_hour"]+arch["api_gb"]*z["rates"]["fargate_arm_gb_hour"])
    if arch["replicas_min"]!=2:
        raise AssertionError("Revisar escenario de sensibilidad: mínimo de 2 réplicas requerido")
    test_cost=proposal["total_usd_month"]+extra
    secondary=100*(baseline["total_usd_month"]-test_cost)/baseline["total_usd_month"]
    return section("COST",f"""### Tabla 2. Proyección FinOps: nueve combinaciones de arquitectura y carga

{chr(10).join(rows)}

![Figura 4. Comparativo de costos en los escenarios de volumen](actividad9/evidence/fig_04_costos_finops.png)

**Figura 4 — Costos modelados:** el costo aumenta al incorporar redundancia y al dimensionar más tareas. Las diferencias entre HA-x86 y HA-ARM son **hipótesis de costos**, no ahorros cobrados ni cotizaciones completas.

**Comparación con resiliencia equiparable, escenario de 10 M:** HA-x86 = **US${baseline['total_usd_month']:.2f}/mes** vs. HA-ARM con *right-sizing* = **US${proposal['total_usd_month']:.2f}/mes**; diferencia = **US${diff:.2f}/mes ({saving:.1f}%)**. Atención: esa diferencia combina **menor tarifa ARM y menor vCPU por tarea**; no demuestra que el mismo trabajo alcance igual latencia.

**Sensibilidad:** si el modelo ARM necesitara **dos tareas API adicionales** para sostener la carga (de 2 a 4), el costo modelado subiría a **US${test_cost:.2f}/mes** y la reducción frente al HA-x86 bajaría a **{secondary:.1f}%**. Si hubiera US$100 mensuales de otros componentes excluidos para ambas arquitecturas, el porcentaje de ahorro nominal sería aproximadamente **{100*diff/(baseline['total_usd_month']+100):.1f}%**. Son perturbaciones **hipotéticas**, no cotizaciones.

**Advertencias FinOps:** el código usa precios tarifarios de Fargate/ALB como referencias, pero **RDS Multi-AZ, logs, almacenamiento y egreso son supuestos**. No incluye NAT, WAF, respaldos, cargas interzona, soporte, personal, impuestos ni precios negociados. Tampoco calcula el cobro real de LCU según dimensiones. La configuración `cloud_naive` es **sin alta disponibilidad** incluso si el modelo asigna varias tareas en la expansión: en ese caso seguirían concentradas en un único dominio de falla.

**Guía operativa:** antes de invertir se debe realizar un presupuesto en AWS Pricing Calculator, medir ECS/Graviton con carga realista y aprobar presupuesto/SLO conjuntamente. [Modelo reproducible](actividad9/finops.py) y [descomposición JSON](actividad9/evidence/finops_model.json).
""")

def fairness():
    z=get("fairness_machine_types.json")
    rows=["| Tipo | Máquinas | Ventanas | Positivos | Recall/TPR | FPR | Precision | IC bootstrap 95% del TPR |",
          "|---|---:|---:|---:|---:|---:|---:|---|"]
    for label,d in z["groups"].items():
        ci=d.get("tpr_cluster_bootstrap_95ci")
        ci_label=f"[{ci[0]*100:.1f}%, {ci[1]*100:.1f}%]" if ci else "No estimado"
        rows.append(f"| {label} | {d['machines']} | {d['n']} | {d['positive']} | {d['recall_tpr']*100:.1f}% | {d['fpr']*100:.2f}% | {d['precision']*100:.1f}% | {ci_label} |")
    gap=z["gaps"]["equal_opportunity_tpr_gap"]*100
    fpr=z["gaps"]["false_positive_rate_gap"]*100
    return section("FAIR",f"""### Tabla 3. Fairness operacional medida sobre el holdout sintético

{chr(10).join(rows)}

![Figura 5. Recall por tipo con incertidumbre de cuatro máquinas](actividad9/evidence/fig_05_fairness_tpr.png)

**Figura 5 — Equidad de detección:** brecha TPR entre grupos = **{gap:.2f} puntos porcentuales**; brecha FPR = **{fpr:.2f} puntos**. El tipo con menor TPR puede requerir más investigación, pero no sería metodológicamente válido concluir que el sistema es equitativo porque la brecha es inferior al umbral propuesto de 10 puntos.

**Límites:** los intervalos por tipo son **exploratorios** al existir solo cuatro máquinas en cada grupo. El bootstrap utiliza máquinas como clúster para reducir seudorreplicación de ventanas; su cobertura puede ser imprecisa con tan pocas unidades independientes. Este análisis **no constituye fairness demográfica** ni evidencia de desempeño industrial real.
""")

def replace(contents,code,replacement):
    pattern=r"<!-- A9-"+code+r"-START -->[\s\S]*?<!-- A9-"+code+r"-END -->"
    s,n=re.subn(pattern,lambda match:replacement,contents)
    if n!=1: raise AssertionError(f"README: esperaba un bloque {code}, encontré {n}")
    return s

def main():
    text=README.read_text(encoding="utf-8")
    for code,func in (("BENCH",benchmark),("COST",cost),("FAIR",fairness)):
        text=replace(text,code,func())
    README.write_text(text,encoding="utf-8")
    print("README A9 sincronizado con evidencia:",run_link())
if __name__=="__main__":
    main()
