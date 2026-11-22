"""Entregables académicos PDF, anexo PDF, diagrama PNG/PDF, ZIP.

El documento se genera a partir de evidencia JSON/CSV de una ejecución CI; no
presenta valores inventados como mediciones cloud ni como facturación real.
"""
from __future__ import annotations
import json, math, zipfile, textwrap
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak,KeepTogether,Image

BASE=Path(__file__).resolve().parent
OUT=BASE/"entregables"
DATA=BASE/"evidence"
A8=BASE.parent/"actividad8"
BLUE=colors.HexColor("#17324D"); TEAL=colors.HexColor("#167E88"); INK=colors.HexColor("#27313F")
LIGHT=colors.HexColor("#E9F2F3"); GRAY=colors.HexColor("#657482")

def read(p):return json.loads(p.read_text(encoding="utf-8"))
def n(x,nd=2):return "N/D" if x is None else f"{x:,.{nd}f}"
def pp(x):return "N/D" if x is None else f"{x*100:.1f}%"

def font_setup():
    possible=[("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")]
    for a,b in possible:
        if Path(a).exists() and Path(b).exists():
            pdfmetrics.registerFont(TTFont("DejaVu",a))
            pdfmetrics.registerFont(TTFont("DejaVuBold",b))
            return "DejaVu","DejaVuBold"
    return "Helvetica","Helvetica-Bold"
FONT,BOLD=font_setup()
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name="A9Title",fontName=BOLD,fontSize=19,leading=25,textColor=BLUE,spaceAfter=13))
styles.add(ParagraphStyle(name="A9H1",fontName=BOLD,fontSize=12,leading=17,textColor=BLUE,spaceBefore=14,spaceAfter=8))
styles.add(ParagraphStyle(name="A9H2",fontName=BOLD,fontSize=9.5,leading=14,textColor=TEAL,spaceBefore=11,spaceAfter=5))
styles.add(ParagraphStyle(name="A9Body",fontName=FONT,fontSize=8.7,leading=13.2,textColor=INK,spaceAfter=8))
styles.add(ParagraphStyle(name="A9Tiny",fontName=FONT,fontSize=7,leading=10,textColor=GRAY,spaceAfter=4))
styles.add(ParagraphStyle(name="A9Cell",fontName=FONT,fontSize=7.1,leading=10,textColor=INK))
styles.add(ParagraphStyle(name="A9White",fontName=BOLD,fontSize=7,leading=10,textColor=colors.white))
styles.add(ParagraphStyle(name="A9Cover",fontName=FONT,fontSize=10.5,leading=16,textColor=TEAL,spaceAfter=9))

def P(text,style="A9Body"):
    return Paragraph(escape(str(text)).replace("\n","<br/>"),styles[style])
def H(text,lev=1):return P(text,"A9H1" if lev==1 else "A9H2")
def txt(text):return P(text)
def bullet(text):return P("• "+text)
def make_table(headers,rows,widths=None):
    entries=[[P(h,"A9White") for h in headers]]
    for row in rows:entries.append([P(v,"A9Cell") for v in row])
    table=Table(entries,colWidths=widths,repeatRows=1,hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,LIGHT]),
        ("GRID",(0,0),(-1,-1),.25,colors.HexColor("#D6E0E5")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    return table

def foot(canvas,doc):
    canvas.setStrokeColor(colors.HexColor("#DDE5E9"))
    canvas.line(1.7*cm,1.3*cm,A4[0]-1.7*cm,1.3*cm)
    canvas.setFont(FONT,7);canvas.setFillColor(GRAY)
    canvas.drawString(1.7*cm,1*cm,"Predictive Maintenance AI · Actividad 9 · Datos y costos simulados")
    canvas.drawRightString(A4[0]-1.7*cm,1*cm,f"Página {doc.page}")

def build_pdf(path,story):
    SimpleDocTemplate(str(path),pagesize=A4,rightMargin=1.7*cm,leftMargin=1.7*cm,
       topMargin=1.5*cm,bottomMargin=1.7*cm,
       title=path.stem,author="Proyecto académico Predictive Maintenance AI"
       ).build(story,onFirstPage=foot,onLaterPages=foot)

def architecture():
    from matplotlib.patches import Rectangle
    fig,axes=plt.subplots(1,2,figsize=(16,8),dpi=165)
    titles=["ARQUITECTURA ACTUAL · PROTOTIPO LOCAL","REDISEÑO PROPUESTO · AWS SIMULADO"]
    for ax,title in zip(axes,titles):
        ax.set_xlim(0,10);ax.set_ylim(0,12);ax.axis("off")
        ax.text(5,11.45,title,ha="center",fontsize=13,weight="bold",color="#17324D")
        ax.add_patch(FancyBboxPatch((.35,.85),9.3,9.95,boxstyle="round,pad=.18",
            linewidth=1.5,edgecolor="#AACCD1",facecolor="#F5FAFA"))
    def box(ax,x,y,w,h,label,sub="",fill="#D9EDF0"):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=.13",lw=1,
          edgecolor="#3A7080",facecolor=fill))
        ax.text(x+w/2,y+h*.64,label,ha="center",va="center",fontsize=10,weight="bold",color="#17324D")
        if sub:ax.text(x+w/2,y+h*.25,sub,ha="center",va="center",fontsize=8,color="#375D6B")
    def ar(ax,x1,y1,x2,y2):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",
                 mutation_scale=14,linewidth=1.5,color="#167E88"))
    a,b=axes
    box(a,3.15,9.1,3.7,1,"Usuario local","localhost 8510")
    box(a,3.15,7.1,3.7,1.15,"Streamlit","1 contenedor Docker")
    box(a,3.15,5.1,3.7,1.15,"FastAPI + modelo","1 contenedor Docker")
    box(a,.85,2.95,3.3,1.2,"SQLite + JSONL","Volumen local")
    box(a,5.5,2.95,3.7,1.2,"MLflow + scripts","GitHub Actions efímero")
    ar(a,5,9.1,5,8.3);ar(a,5,7.1,5,6.3);ar(a,4.2,5.1,2.5,4.15);ar(a,5.8,5.1,7.1,4.15)
    a.text(5,1.9,"Punto único de falla · sin autoescalado",ha="center",fontsize=10,color="#9E4242")
    box(b,3.1,9.3,3.8,1.0,"HTTPS + WAF","Autenticación y cuotas","#E3EAF9")
    box(b,3.1,7.65,3.8,1.0,"Application Load Balancer","Healthcheck + routing","#D9EDF0")
    box(b,.8,5.7,3.7,1.25,"ECS Fargate · AZ A","API réplica 1","#D8F2E3")
    box(b,5.45,5.7,3.7,1.25,"ECS Fargate · AZ B","API réplica 2+","#D8F2E3")
    box(b,.8,3.6,3.7,1.0,"RDS PostgreSQL","Multi-AZ (supuesto)","#F3E9FF")
    box(b,5.45,3.6,3.7,1.0,"S3 + MLflow","Modelo versionado","#F3E9FF")
    box(b,2.1,1.8,5.9,1.0,"CloudWatch + FinOps + IAM","SLO · presupuestos · auditoría","#E8EEF2")
    ar(b,5,9.3,5,8.65);ar(b,3.9,7.65,2.65,6.95);ar(b,6.1,7.65,7.25,6.95)
    ar(b,2.65,5.7,2.65,4.6);ar(b,7.25,5.7,7.25,4.6)
    ar(b,2.65,3.6,4.0,2.8);ar(b,7.25,3.6,6.0,2.8)
    fig.text(.5,.045,"Diseño propuesto, NO desplegado · Proteger trazas, datos y aprobaciones humanas",ha="center",fontsize=11,color="#17324D")
    fig.tight_layout(rect=(0,.07,1,1))
    fig.savefig(OUT/"03_arquitectura_actual_vs_propuesta.png",bbox_inches="tight",dpi=175)
    fig.savefig(OUT/"03_arquitectura_actual_vs_propuesta.pdf",bbox_inches="tight")
    plt.close(fig)

def report():
    fairness=read(DATA/"fairness_machine_types.json")
    costs=read(DATA/"finops_model.json")
    bench=read(DATA/"load_benchmark.json")
    ev=read(A8/"results"/"evaluation_v2.json")
    es=costs["estimates"]
    growth=[x for x in es if x["scenario"]=="crecimiento"]
    temp={x["architecture_name"]:x for x in growth}
    a=temp["ha_without_rightsizing"]; b=temp["proposed_rightsized_arm"]
    s=[P("ACTIVIDAD 9 · REPORTE TÉCNICO","A9Title"),
       P("Rediseño integral de escalabilidad, costos FinOps y gobernanza responsable","A9Cover"),
       P("Universidad Tecmilenio · Módulo 3 / Semana 11 · Estudio académico totalmente simulado","A9Tiny"),
       H("Resumen ejecutivo"),txt(
        "Se evalúa el prototipo Predictive Maintenance AI de la Actividad 8 y una arquitectura AWS propuesta, sin desplegar infraestructura de pago. "
        "El prototipo actual utiliza FastAPI, Random Forest, Streamlit, SQLite, Docker, logs y MLflow. Se miden cargas HTTP locales y disparidades técnicas "
        "entre tipos de máquina; se estiman costos bajo supuestos explícitos. La revisión integra los cuatro criterios oficiales de 25 puntos."),
       H("1. Diagnóstico arquitectónico"),
       txt("Estado actual: una API y un dashboard en contenedores locales, SQLite en volumen y seguimiento MLflow efímero en CI. "
           "Es reproducible para un piloto, pero carece de balanceador, redundancia multizona, autoescalado, gestión centralizada de secretos, observabilidad agregada e IAM cloud."),
       txt("Escalabilidad vertical: aumentar CPU/RAM del contenedor puede mejorar la capacidad de una réplica hasta límites físicos y económicos. "
           "Escalabilidad horizontal: múltiples réplicas sin estado frente a ALB con base de datos externa y modelo versionado. "
           "SQLite local y artefactos en disco impiden asumir escalado horizontal sin rediseño de persistencia."),
       H("2. Rediseño propuesto de nube (simulado)"),
       txt("AWS: ALB y WAF para entrada controlada; ECS/Fargate con al menos dos tareas API en distintas zonas; RDS PostgreSQL Multi-AZ para predicciones y auditoría; "
           "S3 cifrado para modelos y datasets; IAM y KMS para permisos/cifrado; CloudWatch para métricas, logs y alarmas; despliegue con canary y rollback aprobado. "
           "El dashboard se despliega independientemente, con autenticación. Este diseño todavía no fue implementado en AWS."),
       H("3. Latencia, throughput y uso de recursos medidos"),
       txt("El benchmark ejecuta solicitudes POST /predict contra servidores FastAPI reales en loopback, con concurrencia 1, 4, 8 y 16. "
           "En el escenario dual alterna solicitudes entre dos procesos que comparten el runner. No mide ECS, ARM ni un balanceador real."),
       make_table(["Escenario","Concurrencia","p95 (ms)","Throughput (req/s)","Disponibilidad"],[
          [label,str(z["concurrency"]),n(z["p95_ms"],1),n(z["throughput_rps"],1),pp(z["availability"])]
          for label,rows in [("1 API",bench["single"]["levels"]),("2 API",bench["dual"]["levels"])] for z in rows
       ],[3.1*cm,2.4*cm,3.0*cm,4.0*cm,3.0*cm]),
       txt("La disponibilidad y los tiempos son propiedades del banco de prueba, no garantías de SLA. "
           "El reporte de recursos del benchmark describe procesos locales y no reservas de recursos Fargate."),
       H("4. FinOps: costos contra demanda y SLA"),
       txt("Se comparan tres arquitecturas: cloud_naive (1 réplica, single-AZ), ha_without_rightsizing (HA x86) y proposed_rightsized_arm (HA ARM). "
           "La comparación legítima de optimización es HA x86 vs HA ARM, porque ambas incorporan redundancia. Las tarifas verificadas "
           "corresponden a Fargate x86/ARM y ALB us-east-1; los importes de RDS, logs, egreso y almacenamiento son hipótesis, no cotizaciones."),
       make_table(["Arquitectura (10M req/mes)","Tareas API","USD/mes","USD/1000"],[
         [x["architecture_name"],str(x["replicas_estimated"]),n(x["total_usd_month"]),
          n(x["usd_per_1000_requests"],4)] for x in growth
       ],[7.1*cm,2.5*cm,3.3*cm,3.1*cm]),
       txt(f"En el escenario de crecimiento, HA x86 = USD {a['total_usd_month']:.2f}/mes y HA ARM = USD {b['total_usd_month']:.2f}/mes: "
           f"diferencia simulada USD {a['total_usd_month']-b['total_usd_month']:.2f}/mes. "
           "Esta estimación NO verifica compatibilidad/throughput en ARM. Deben incluirse NAT, WAF, respaldos, soporte, personal e impuestos antes de contratar."),
       H("5. Auditoría ética, técnica y legal"),
       txt("El dataset V2 es 100% sintético y no contiene categorías protegidas de personas. Se evalúa fairness OPERACIONAL por machine_type A/B/C: "
           "diferencias de recall (igualdad de oportunidad) y tasas de falsos positivos. Esto no constituye una evaluación de sesgos demográficos."),
       make_table(["Tipo","Equipos","Positivos","TPR","FPR","Precision"],[
         [g,str(x["machines"]),str(x["positive"]),pp(x["recall_tpr"]),pp(x["fpr"]),pp(x["precision"])]
         for g,x in fairness["groups"].items()
       ],[2.1*cm,2.3*cm,2.4*cm,2.8*cm,2.7*cm,3.2*cm]),
       txt("Los cuatro equipos piloto por tipo y la correlación temporal limitan inferencia estadística. "
           "Un desbalance de TPR no prueba discriminación real, pero requiere análisis antes de operar. "
           "Gobernanza recomendada: NIST AI RMF (GOVERN, MAP, MEASURE, MANAGE), sistema de gestión ISO/IEC 42001, gestión de accesos, "
           "registro de versiones y revisión humana de alertas de mantenimiento."),
       txt("Marco mexicano: la Ley Federal de Protección de Datos Personales en Posesión de los Particulares (publicación 2025, "
           "reforma de 2025) es pertinente si una futura implantación procesa datos personales (operadores, usuarios o identificadores de personal). "
           "El piloto de datos sintéticos no acredita cumplimiento legal de una organización real; debe realizarse análisis legal específico."),
       H("6. Plan por etapas, puertas de aprobación y responsables"),
       make_table(["Fase","Actividades y evidencia","Puerta de salida"],[
         ["0 · Baseline","Perfilar p95, RPS, CPU/RSS y grupos sintéticos; inventario de datos","Métricas reproducibles y riesgo registrado"],
         ["1 · Seguridad","Authn/Authz, secretos, cifrado, retención, minimización de datos","Revisión Security/Legal aprobada"],
         ["2 · Piloto cloud","Staging multizona, pruebas de carga/recuperación y cálculo AWS Calculator","p95 ≤500 ms, éxito ≥99%; costo presupuestado"],
         ["3 · Escalado","Autoscaling gradual, canary, registro MLflow y rollback con aprobación","SLO sustentado, fairness revisada, costo/1000 estable"],
         ["4 · Operación","FinOps semanal, drift, revisión postincidente y auditoría trimestral","KPIs continuos y plan de mejora"],
       ],[2.7*cm,8.9*cm,5.4*cm]),
       txt("Roles: Product Owner define riesgo y presupuesto; SRE opera infraestructura, SLO y rollback; ML Lead valida modelo/fairness; "
           "Security y Legal aprueban tratamiento de datos; FinOps controla costo unitario. La promoción del modelo no es automática."),
       H("7. Conclusión crítica"),
       txt("La arquitectura propuesta resuelve las barreras conceptuales de escala de la solución local, pero su viabilidad económica "
           "está condicionada a confirmación de precios, pruebas ARM, carga real y rediseño de persistencia. "
           "El enfoque correcto no es minimizar costo absoluto sino optimizar USD/1000 predicciones con SLO y gobernanza satisfechos. "
           "Ninguna cifra estimada demuestra por sí sola disponibilidad o retorno económico real."),
       H("8. Fuentes de tarifas y marcos"),
       txt("AWS Fargate: https://aws.amazon.com/fargate/pricing/"),
       txt("AWS ELB: https://aws.amazon.com/elasticloadbalancing/pricing/"),
       txt("AWS RDS: https://aws.amazon.com/rds/postgresql/pricing/"),
       txt("FinOps Foundation: https://www.finops.org/framework/phases/"),
       txt("NIST AI RMF: https://airc.nist.gov/airmf-resources/airmf/5-sec-core/"),
       txt("ISO/IEC 42001: https://www.iso.org/standard/42001"),
       txt("México LFPDPPP: https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf"),
       txt("El anexo PDF contiene tablas de 9 escenarios de costo, desempeño y métricas de fairness."),
    ]
    from .academic_extension import extra_sections
    s.extend(extra_sections(fairness,costs,bench,ev,P,H,make_table,
                            OUT/"03_arquitectura_actual_vs_propuesta.png"))
    build_pdf(OUT/"01_reporte_tecnico_actividad9.pdf",s)

def annex():
    a=read(DATA/"finops_model.json");b=read(DATA/"load_benchmark.json");c=read(DATA/"fairness_machine_types.json")
    s=[P("ANEXO TÉCNICO · ACTIVIDAD 9","A9Title"),
       P("Escenarios de costos, cargas HTTP, métricas de recursos y fairness","A9Cover"),
       H("A. Tarifas y supuestos auditables"),
       txt("Las tarifas oficiales empleadas son referencias públicas para us-east-1, calculadas sin descuentos ni impuestos. "
           "Las hipótesis de servicios administrados, tráfico y almacenamiento NO son una cotización del proveedor."),
       make_table(["Parámetro","USD","Naturaleza"],[
          [k,str(v),("Referencia tarifaria" if k.startswith("fargate_") or k.startswith("alb_") else "Supuesto editable")]
          for k,v in a["rates"].items() if isinstance(v,(float,int)) and k not in ("hours_month",)
       ],[7.2*cm,3*cm,6.5*cm]),
       H("B. Costos mensuales de los 9 escenarios"),
       make_table(["Escenario","Arquitectura","Réplicas","USD total","USD/1000"],[
          [r["scenario"],r["architecture_name"],str(r["replicas_estimated"]),n(r["total_usd_month"]),
           n(r["usd_per_1000_requests"],4)] for r in a["estimates"]
       ],[2.3*cm,6.0*cm,2.2*cm,3.0*cm,3.4*cm]),
       txt("Ecuación: costo mensual = horas × réplicas × (vCPU × tarifa vCPU-h + RAM × tarifa GB-h) "
           "+ ALB fijo/LCU + base de datos + logs + S3 + egreso. Costos excluidos: NAT, WAF, backups, "
           "soporte, tránsito privado, CI y personas. La escala horizontal es una proyección basada en benchmarks locales, no una validación cloud."),
       H("C. Rendimiento HTTP por concurrencia"),
       make_table(["Réplicas","Clientes","p50 ms","p95 ms","p99 ms","req/s","HTTP ok"],[
          [str(nrep),str(r["concurrency"]),n(r["p50_ms"],1),n(r["p95_ms"],1),
           n(r["p99_ms"],1),n(r["throughput_rps"],1),pp(r["availability"])]
          for nrep,key in [(1,"single"),(2,"dual")] for r in b[key]["levels"]
       ],[1.7*cm,2.0*cm,2.4*cm,2.4*cm,2.4*cm,2.4*cm,2.8*cm]),
       txt("1 vs 2 endpoints usan el mismo runner; las mediciones son una prueba reproducible de HTTP y no prueban "
           "que 2 tareas de Fargate en AZ distintas cumplan SLA. Consumo de recursos de procesos disponible en load_benchmark.json."),
       H("D. Fairness técnica entre tipos A/B/C"),
       make_table(["Grupo","N","Positivos","TP","FP","FN","TN","TPR","FPR"],[
         [name,str(g["n"]),str(g["positive"]),str(g["tp"]),str(g["fp"]),
          str(g["fn"]),str(g["tn"]),pp(g["recall_tpr"]),pp(g["fpr"])]
         for name,g in c["groups"].items()
       ],[1.6*cm,1.3*cm,2.0*cm,1.3*cm,1.3*cm,1.3*cm,1.3*cm,2.0*cm,2.0*cm]),
       txt(f"Brecha TPR (máx−mín) = {c['gaps']['equal_opportunity_tpr_gap']:.3f}; "
           f"brecha FPR = {c['gaps']['false_positive_rate_gap']:.3f}. "
           "Son estadísticas descriptivas sobre cuatro máquinas por tipo, no un examen de atributos humanos protegidos."),
       H("E. Matriz de riesgos y controles"),
       make_table(["Riesgo","Impacto","Control","Responsable"],[
         ["Inaccesibilidad / AZ","Alto","2 AZ + healthchecks + backup + drills","SRE"],
         ["Sobrepaso de costo","Medio/Alto","Presupuesto, tags, USD/1000, alarma","FinOps"],
         ["Sesgo entre tipos","Medio","TPR/FPR por tipo + revisión de muestra","ML Lead"],
         ["Data drift","Alto","PSI, cuarentena y revisión humana","ML Lead"],
         ["Datos personales futuros","Alto","Minimización, IAM, cifrado, privacidad","Legal/Security"],
         ["Promoción incorrecta","Alto","Evaluación holdout y aprobación canary","ML Lead/SRE"],
       ],[3.8*cm,2.0*cm,7.4*cm,3.6*cm]),
       H("F. Reproducibilidad"),
       txt("Archivos: actividad9/benchmark.py, actividad9/finops.py, actividad9/fairness.py, "
           "actividad9/evidence/*.json, arquitectura fuente e historial de GitHub Actions. "
           "El reporte y el anexo se crean automáticamente en el ejecutor de CI. "
           "Sin AWS real, no existe facturación, SLA observado en nube ni garantía de comportamiento ARM."),
       H("G. Gráficas y lectura crítica de escenarios"),
       Image(str(DATA/"fig_04_costos_finops.png"),width=14.5*cm,height=7.5*cm),
       txt("Figura A1. Los costos son estimaciones parametrizadas: la arquitectura sin HA no equivale a las opciones con redundancia. El dimensionamiento ARM está pendiente de pruebas en esa plataforma."),
       Image(str(DATA/"fig_05_fairness_tpr.png"),width=14.5*cm,height=7.5*cm),
       txt("Figura A2. Las barras de incertidumbre corresponden al remuestreo por máquina (cuatro clústeres por tipo), no a miles de ventanas independientes."),
       H("H. Confiabilidad estadística de la prueba de carga"),
       txt("Cada prueba comprende 60 solicitudes. Aunque 60 de 60 tengan éxito, con una cota unilateral binomial del 95% el porcentaje de éxito poblacional podría ser tan bajo como 95.13%, suponiendo observaciones independientes. Esto NO demuestra un SLA de 99%. Para esa cota teórica se requerirían al menos 299 éxitos de 299, y aun así el tráfico dependiente y las condiciones variables exigirían pruebas sostenidas."),
       txt("Las figuras y tablas tienen su fuente medible en load_benchmark.json, fairness_machine_types.json y finops_model.json. Los documentos y diagramas son generados en GitHub Actions y no contienen medidas de producción."),
    ]
    build_pdf(OUT/"02_anexo_tecnico_actividad9.pdf",s)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name in ("finops_model.json","fairness_machine_types.json","load_benchmark.json"):
        if not (DATA/name).exists():raise FileNotFoundError("Falta evidencia "+name)
    from .visualizations import main as generate_visualizations
    generate_visualizations()
    architecture();report();annex()
    items=[p for p in OUT.iterdir() if p.suffix in (".pdf",".png")]
    with zipfile.ZipFile(OUT/"Actividad9_Entregables_Tecmilenio.zip","w",zipfile.ZIP_DEFLATED) as z:
        for p in sorted(items):z.write(p,p.name)
    for p in sorted(OUT.iterdir()):
        print(f"{p.name}: {p.stat().st_size:,} bytes")
if __name__=="__main__":main()
