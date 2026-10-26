"""Genera los dos PDF oficiales de la Fase II desde artefactos y pruebas reales.

Uso: python -m src.reports
El informe NO es evidencia de funcionamiento en hardware industrial.
"""
from __future__ import annotations
import html
import json
from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,
    Image,KeepTogether
)
from .simulation import ROOT,RESULTS

DOCS=ROOT/"docs"
DOCS.mkdir(parents=True,exist_ok=True)
BLUE=colors.HexColor("#175A72")
INK=colors.HexColor("#1B3642")
GRAY=colors.HexColor("#5A6C74")
LIGHT=colors.HexColor("#E9F2F5")
BORDER=colors.HexColor("#CCDCE1")
S=getSampleStyleSheet()
S.add(ParagraphStyle(name="PhaseTitle",fontName="Helvetica-Bold",fontSize=21,
    leading=26,alignment=TA_CENTER,textColor=INK,spaceAfter=16))
S.add(ParagraphStyle(name="PhaseSub",fontName="Helvetica-Bold",fontSize=13,
    leading=17,textColor=BLUE,spaceBefore=8,spaceAfter=8,keepWithNext=True))
S.add(ParagraphStyle(name="PhaseBody",fontName="Helvetica",fontSize=9.3,
    leading=14,textColor=INK,spaceAfter=9))
S.add(ParagraphStyle(name="PhaseSmall",fontName="Helvetica",fontSize=8.1,
    leading=11.4,textColor=GRAY,spaceAfter=5))
S.add(ParagraphStyle(name="PhaseCaption",fontName="Helvetica-Oblique",
    fontSize=8,leading=11,textColor=GRAY,spaceAfter=9))

def para(txt): return Paragraph(txt,S["PhaseBody"])
def head(txt): return Paragraph(txt,S["PhaseSub"])
def small(txt): return Paragraph(txt,S["PhaseSmall"])
def title(txt): return Paragraph(txt,S["PhaseTitle"])
def page(story):story.append(PageBreak())
def para_add(story,txt):story.append(para(txt))
def sub(story,txt):story.append(head(txt))

def tab(story,header,rows,widths):
    a=[[small(html.escape(str(c))) for c in header]]
    a += [[small(html.escape(str(v))) for v in row] for row in rows]
    tb=Table(a,colWidths=widths,hAlign="LEFT",repeatRows=1)
    tb.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),LIGHT),
        ("GRID",(0,0),(-1,-1),.38,BORDER),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),7)
    ]))
    story.append(tb);story.append(Spacer(1,.23*cm))

def fig(story,filename,caption,maxw=16.2*cm,maxh=8.2*cm):
    if not filename.is_file():raise FileNotFoundError(filename)
    w,h=ImageReader(str(filename)).getSize()
    f=min(maxw/w,maxh/h)
    story.append(KeepTogether([
        Image(str(filename),width=w*f,height=h*f),
        Paragraph(caption,S["PhaseCaption"])
    ]))

def build(filename,story):
    def decorate(c,d):
        c.saveState()
        w,h=A4
        c.setStrokeColor(BLUE);c.setLineWidth(.9)
        c.line(2*cm,h-1.32*cm,w-2*cm,h-1.32*cm)
        c.setFont("Helvetica",8);c.setFillColor(GRAY)
        c.drawString(2*cm,1.07*cm,"Predictive Maintenance AI | Fase II | Simulación académica")
        c.drawRightString(w-2*cm,1.07*cm,f"Página {d.page}")
        c.restoreState()
    doc=SimpleDocTemplate(str(filename),pagesize=A4,
        topMargin=1.75*cm,bottomMargin=1.7*cm,
        leftMargin=1.95*cm,rightMargin=1.95*cm,
        title=filename.stem,
        author="Predictive Maintenance AI - proyecto académico")
    doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
    print("Documento publicado:",filename,filename.stat().st_size,"bytes")

def manual():
    st=[]
    st.extend([Spacer(1,1.6*cm),
               title("MANUAL DE DESPLIEGUE"),
               title("Docker local y estrategia de nube"),
               para("<b>Predictive Maintenance AI - Fase II / Módulo 2, Semana 8.</b>"),
               para("Objetivo: instalar, ejecutar y verificar una aplicación académica de "
                    "mantenimiento predictivo que estima el riesgo de al menos una falla "
                    "en las próximas <b>72 horas</b> en doce máquinas sintéticas."),
               para("<b>Alcance:</b> máquina de desarrollo Windows 11 con Docker Desktop/WSL 2 "
                    "o Linux con Docker Engine y Compose. La aplicación consta de "
                    "dos contenedores y SQLite persistente. Ningún despliegue cloud "
                    "comercial ha sido ejecutado."),
               head("Resumen de arquitectura")])
    tab(st,["Componente","Servicio","Responsabilidad"],[
        ["Interfaz web","Streamlit :8501","Riesgo de 12 máquinas, escenarios y alertas"],
        ["API","FastAPI :8000","Validación, inferencia y endpoints Swagger"],
        ["Machine Learning","RandomForest","Riesgo futuro a 72 h con artefacto joblib"],
        ["Persistencia","SQLite","Registro de inferencias y fecha de lectura simulada"],
        ["Contenedores","Docker Compose","API y web con red interna y healthcheck"]
    ],[3.6*cm,4.3*cm,8.4*cm])
    para_add(st,"<b>Restricción:</b> datos, equipos y eventos completamente sintéticos. "
        "No se afirma desempeño productivo ni seguridad industrial demostrada.")
    page(st)

    sub(st,"1. Requisitos y preparación del anfitrión")
    para_add(st,"Windows 11, Docker Desktop con WSL 2 y Engine running, puertos locales "
        "8000 y 8501 libres, acceso inicial para descargar las imágenes Python, "
        "Git o GitHub Desktop y recursos suficientes para los dos contenedores.")
    tab(st,["Comprobación","Comando PowerShell","Criterio"],[
        ["Docker","docker --version","Cliente disponible"],
        ["Compose","docker compose version","Plugin instalado"],
        ["Motor real","docker run --rm hello-world","Hello from Docker!"],
        ["Archivos","git clone [URL del repo]","Modelo, Dockerfiles, compose y código"]
    ],[3.0*cm,6.5*cm,6.9*cm])
    sub(st,"2. Ejecución completa local")
    para_add(st,"Desde PowerShell, clonar el repositorio público "
        "https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII y ejecutar:")
    for c in [
        "git clone https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII.git",
        "cd PredictiveMaintenance-AI-FaseII",
        "docker compose up --build -d --wait",
        "docker compose ps"
    ]:st.append(Paragraph(html.escape(c),S["PhaseSmall"]))
    para_add(st,"Abrir <b>http://localhost:8501</b> para el dashboard. "
        "Abrir <b>http://localhost:8000/docs</b> para el contrato API. "
        "El endpoint GET /health debe indicar status=ok, database=ok "
        "y model_loaded=true.")
    sub(st,"3. Cierre seguro sin perder registros")
    para_add(st,"Usar <b>docker compose down</b> para cerrar. "
        "El volumen <b>prediction_state</b> conserva SQLite. "
        "No utilizar la opción '-v' si se quiere mantener el historial de predicciones.")
    page(st)

    sub(st,"4. Diseño de contenedores y conectividad")
    para_add(st,"Dockerfile.api empaqueta FastAPI y el artefacto de modelo "
        "previamente entrenado. Dockerfile.web empaqueta Streamlit. Compose levanta "
        "la API primero y espera que el endpoint health responda antes de iniciar "
        "la interfaz. La UI consulta la API por el nombre de servicio "
        "<b>http://api:8000</b>, no por localhost dentro del contenedor.")
    para_add(st,"Los puertos host usan la dirección 127.0.0.1, de modo que "
        "los servicios no se exponen intencionalmente a la red local. "
        "SQLite reside en <b>/state/predictions.sqlite</b> dentro de "
        "un volumen persistente. Ningún secreto se incluye en el contenedor.")
    sub(st,"5. Endpoints para comprobación")
    tab(st,["Método y ruta","Uso","Resultado esperado"],[
        ["GET /health","Salud de API/modelo/BD","HTTP 200; model_loaded=true"],
        ["GET /machines","Listado del piloto","12 máquinas sintéticas"],
        ["GET /telemetry/PM-049","Sensores de una máquina","Lectura fechada, simulada"],
        ["POST /predict","Predicción y registro","72 h, probabilidad, ID de SQLite"],
        ["GET /predictions","Auditoría de consultas","Historial persistente"],
        ["GET /model/info","Trazabilidad","Umbral, características, condición sintética"]
    ],[4.8*cm,5.0*cm,6.5*cm])
    sub(st,"6. Casos de error previstos")
    para_add(st,"Máquina ajena al piloto responde 404. Sensores fuera de "
        "los límites declarados o campos desconocidos responden 422. "
        "La API no acepta silenciosamente una máquina inexistente. "
        "El dashboard diferencia una nueva simulación hipotética "
        "de la última lectura generada.")
    page(st)

    sub(st,"7. Estrategia cloud: contenedores o PaaS")
    para_add(st,"Se plantea una migración futura a un proveedor capaz de "
        "ejecutar imágenes OCI (por ejemplo Azure Container Apps, Cloud Run o AWS "
        "App Runner). Esta descripción no afirma que el proyecto esté desplegado "
        "ni que se hayan contratado servicios.")
    tab(st,["Paso","Actividad técnica","Control / evidencia"],[
        ["1","Versionar una etiqueta Git inmutable","SHA del modelo y del código"],
        ["2","Construir/publicar dos imágenes OCI","Registry con permisos mínimos"],
        ["3","Crear servicios backend/frontend","HTTPS, rutas y healthchecks"],
        ["4","Configurar variables y secretos","Secret manager, nunca en Git"],
        ["5","Provisionar persistencia administrada","Migrar SQLite a PostgreSQL si hay réplicas"],
        ["6","Pruebas de humo y carga","Predicción, 404/422, logs y latencia"],
        ["7","Monitorear y controlar costos","Alertas, limites, presupuestos, rollback"]
    ],[1.5*cm,7.1*cm,7.7*cm])
    sub(st,"8. Requisitos adicionales antes de producción")
    para_add(st,"Identidad y autenticación de técnicos, cifrado TLS, auditoría, "
        "autorizaciones por rol, control de versiones de modelos, métricas de "
        "calibración, drift, observabilidad, respaldo y recuperación, "
        "cumplimiento industrial y datos reales. La construcción de datos "
        "sintéticos sirve para aprendizaje y demostración técnica solamente.")
    sub(st,"9. Herramientas de documentación y declaración de IA")
    para_add(st,"ChatGPT (OpenAI) apoyó el diseño de arquitectura, código, "
        "Docker y documentos; la ejecución y los resultados son verificables "
        "en GitHub Actions y, posteriormente, con capturas locales auténticas. "
        "El usuario conserva responsabilidad sobre la entrega y conclusiones.")
    page(st)

    sub(st,"10. Diagnóstico rápido y referencias")
    tab(st,["Síntoma","Verificación / solución"],[
        ["API unhealthy","docker compose logs api; comprobar que artifacts/model.joblib está presente"],
        ["Puertos ocupados","Revisar procesos de Windows o ajustar puertos host de Compose"],
        ["Error frontend -> API","Confirmar API_URL=http://api:8000 dentro de Docker"],
        ["Sin historial","Revisar volumen prediction_state y /state/predictions.sqlite"],
        ["Modelo ausente","Revisar Actions: archivo serializado se publica tras CI aprobada"],
        ["Pérdida de volumen","No ejecutar docker compose down -v salvo borrado intencional"]
    ],[5.0*cm,11.3*cm])
    para_add(st,"Comprobar el código de forma pública: "
        "<link href='https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII'>"
        "PredictiveMaintenance-AI-FaseII (GitHub)</link>. Los logs y artefactos "
        "de CI están en la pestaña Actions. "
        "Docker, Compose y FastAPI cuentan con documentación oficial de sus "
        "respectivos proyectos.")
    para_add(st,"<b>Conclusión:</b> la solución se empaqueta en dos imágenes "
        "Docker y admite ejecución conjunta con una sola orden, con API y persistencia. "
        "El manual prepara un despliegue cloud realista, pero se limita "
        "a una aplicación académica sin telemetría industrial.")
    return st

def validation():
    ev=json.loads((RESULTS/"evaluation.json").read_text(encoding="utf-8"))
    ds=json.loads((RESULTS/"dataset_manifest.json").read_text(encoding="utf-8"))
    val=ev["metrics"]["validation"]
    te=ev["metrics"]["test_temporal"]
    hold=ev["metrics"]["test_unseen_machines"]
    m=json.loads((ROOT/"artifacts/model_metadata.json").read_text(encoding="utf-8"))
    assert m["horizon_hours"]==72 and ds["rows"]==129600 and len(ev["metrics"])==3
    st=[title("VALIDACIÓN Y PRUEBAS"),
        title("Modelo de fallas futuras a 72 h"),
        para("<b>Fase II - Semana 8.</b> Documento reproducible "
             "con cifras de la ejecución verificada por GitHub Actions. "
             "Las fallas, sensores y máquinas son simulados."),
        head("1. Resultados principales"),
        para("Se generaron <b>129,600</b> observaciones de 60 máquinas "
             "cada seis horas y <b>"+str(ds["failure_events"])+"</b> eventos de falla "
             "sintéticos. La etiqueta mira exclusivamente "
             "las siguientes doce mediciones (72 horas)."),
    ]
    rows=[]
    for name,v in [("Validación",val),("Prueba temporal",te),
                   ("Piloto 12 máquinas no vistas",hold)]:
        rows.append([name,str(v["samples"]),f"{v['roc_auc']:.3f}",
                     f"{v['average_precision']:.3f}",f"{v['precision']:.3f}",
                     f"{v['recall']:.3f}",f"{v['f1']:.3f}"])
    tab(st,["Conjunto","n","ROC-AUC","AP","Prec.","Recall","F1"],
        rows,[5.0*cm,2.05*cm,1.95*cm,1.5*cm,1.85*cm,2.0*cm,2.0*cm])
    para_add(st,f"Umbral elegido en validación: <b>{m['threshold']:.2f}</b>, "
        "maximizando F2 con precisión mínima del 20% cuando es factible. "
        "No se recalibró con test temporal ni con máquinas piloto.")
    sub(st,"2. Anticipación antes del evento")
    tab(st,["Conjunto","Fallas detectadas","Recall de eventos","Anticipación media"],[
        ["Prueba temporal",
         f"{te['failure_events_detected']} / {te['failure_events_evaluable']}",
         f"{te['event_recall']:.1%}",f"{te['mean_first_alert_lead_time_hours']:.1f} h"],
        ["Piloto no visto",
         f"{hold['failure_events_detected']} / {hold['failure_events_evaluable']}",
         f"{hold['event_recall']:.1%}",f"{hold['mean_first_alert_lead_time_hours']:.1f} h"]
    ],[4.2*cm,4.0*cm,4.05*cm,4.1*cm])
    para_add(st,"Estas métricas corresponden a eventos de falla sintéticos "
        "elegibles con al menos 72 horas de historia previa en el periodo "
        "de prueba. El reducido número de eventos piloto exige cautela "
        "al interpretar su recall.")
    page(st)

    sub(st,"3. Construcción causal de la etiqueta y contención de fuga")
    para_add(st,"Para una lectura t de una máquina, failure_next_72h=1 "
        "solo si existe un evento en (t,t+72h]. Se excluyen el propio "
        "instante de falla y los períodos de máquina detenida. "
        "Los últimos doce registros se censuran porque su futuro es "
        "desconocido. Los indicadores de temperatura/vibración y desgaste "
        "usan únicamente lecturas hasta t.")
    tab(st,["Conjunto","Registros","Positivos"],[
        [k,f"{v['rows']:,}",str(v["positives"])]
        for k,v in ds["splits"].items()
    ],[6.6*cm,4.2*cm,5.5*cm])
    para_add(st,"Se usaron 48 máquinas para entrenar y validar en períodos "
        "cronológicos; existe una purga de 12 lecturas al cambiar de "
        "partición. Las 12 máquinas PM-049 a PM-060 quedaron "
        "completamente excluidas del ajuste y sirven como evaluación "
        "separada de generalización a equipos simulados no vistos.")
    sub(st,"4. Interpretación de costos operativos")
    para_add(st,f"En test temporal se observaron {te['fp']} alertas "
        f"positivas falsas por ventana de seis horas, equivalentes a "
        f"{te['false_alerts_per_machine_week']:.2f} ventanas por "
        "máquina/semana. Una ventana repetida no representa necesariamente "
        "otra orden de mantenimiento: deduplicar episodios y validar "
        "con técnicos antes de cualquier intervención.")
    para_add(st,f"En el piloto de doce máquinas no vistas la precisión "
        f"de alerta fue {hold['precision']:.1%} y el F1 "
        f"{hold['f1']:.3f}. Estos indicadores limitan la utilidad "
        "potencial aun cuando la curva ROC muestre capacidad de ranking.")
    page(st)

    sub(st,"5. Curvas Precision-Recall y desbalance")
    fig(st,RESULTS/"figures/pr_test_temporal.png",
        "Figura 1. Curva PR de prueba temporal; la línea horizontal es prevalencia sintética.",
        maxh=7.0*cm)
    fig(st,RESULTS/"figures/pr_test_unseen_machines.png",
        "Figura 2. Curva PR del piloto de 12 máquinas no vistas. Sin inferencia industrial.",
        maxh=7.0*cm)
    para_add(st,f"La prevalencia de fallas futuras observables fue "
        f"{te['prevalence']:.2%} en test temporal y "
        f"{hold['prevalence']:.2%} en el piloto. AP fue "
        f"{te['average_precision']:.3f} y "
        f"{hold['average_precision']:.3f}, respectivamente. "
        "Es más informativo evaluar AP/precision-recall que apoyarse "
        "solo en exactitud ante eventos poco frecuentes.")
    page(st)

    sub(st,"6. Matrices de confusión")
    tab(st,["Conjunto","TN","FP","FN","TP"],[
        [name,str(v["tn"]),str(v["fp"]),str(v["fn"]),str(v["tp"])]
        for name,v in [("Temporal",te),("12 máquinas no vistas",hold)]
    ],[5.6*cm,2.7*cm,2.7*cm,2.7*cm,2.7*cm])
    para_add(st,"Un FP representa una alarma emitida en una ventana "
        "sin falla dentro de 72 horas. Un FN representa una ventana "
        "con falla futura que no genera alarma. La misma falla "
        "puede generar múltiples ventanas positivas consecutivas; "
        "por eso se reporta por separado la detección de eventos.")
    sub(st,"7. Pruebas funcionales reales con Docker")
    tab(st,["Caso","Verificación automatizada","Esperado"],[
        ["T01","Docker Compose construye API y Streamlit","2 servicios ejecutados"],
        ["T02","GET /health","Modelo cargado y SQLite healthy"],
        ["T03","GET /machines","Doce máquinas no vistas"],
        ["T04","POST /predict PM-049","72h; registro persistido"],
        ["T05","POST /predict what-if","Nueva predicción aceptada"],
        ["T06","GET /predictions","Consulta auditada en SQLite"],
        ["T07","Máquina ajena al piloto","HTTP 404"],
        ["T08","Desgaste fuera de rango","HTTP 422"],
        ["T09","Temperatura o campo inválidos","HTTP 422"],
        ["T10","GET Streamlit /_stcore/health","HTTP 200"]
    ],[2.0*cm,9.1*cm,5.2*cm])
    para_add(st,"El workflow de integración se declara aprobado solo cuando "
        "los casos anteriores terminan sin error. Evidencia verificable "
        "en GitHub Actions del repositorio, no capturas simuladas.")
    page(st)

    sub(st,"8. Casos extremos, interpretación y deuda técnica")
    para_add(st,"Se validaron límites de entrada en API mediante Pydantic: "
        "desgaste mayor a 1 y temperaturas fuera de rango reciben "
        "422, identificadores inexistentes reciben 404 y un campo "
        "no declarado es rechazado. Los escenarios extremos "
        "dentro de rangos se aceptan para análisis hipotético; "
        "no se inventa una probabilidad fija para ellos.")
    sub(st,"9. Riesgos de validez de la solución")
    para_add(st,"El generador sintético contiene una dinámica explícita de "
        "degradación que correlaciona vibración y temperatura con fallas "
        "futuras. El modelo puede aprender esa regla; su desempeño "
        "no prueba capacidad predictiva en una planta real. "
        "Las máquinas no vistas comparten la lógica generadora, "
        "por lo que la generalización externa sigue sin comprobar.")
    para_add(st,"La frecuencia de evaluación es de 6 horas y el "
        "horizonte predice la presencia de alguna falla durante las "
        "72 horas posteriores, no la hora exacta. Los umbrales "
        "BAJO/MEDIO son orientativos; la frontera ALTO corresponde "
        "al umbral seleccionado en validación.")
    sub(st,"10. Recomendaciones de evolución y MLOps")
    para_add(st,"Incorporar sensores históricos reales etiquetados por "
        "evento de falla, identificación de reparaciones, ventanas "
        "de mantenimiento, revisión por ingenieros de confiabilidad, "
        "prueba prospectiva y monitoreo de drift. Separar "
        "alertas repetidas en episodios para estimar carga real "
        "de trabajo. Mantener aprobación humana.")
    sub(st,"11. Evidencias locales pendientes")
    para_add(st,"La aplicación se probó en contenedores reales "
        "dentro de GitHub Actions. Para demostrar ejecución en "
        "la computadora del estudiante se requieren capturas "
        "auténticas de Docker Desktop, navegador Streamlit y Swagger. "
        "No se fabrican capturas ni se declara una prueba local "
        "aún no realizada.")
    sub(st,"12. Bibliografía y declaración de IA")
    para_add(st,"Código, manifiesto SHA256 y CI: "
        "<link href='https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII'>"
        "Predictive Maintenance AI Fase II</link>. "
        "ChatGPT ayudó a construir y revisar código, pruebas y documentación; "
        "todas las métricas provienen de ejecuciones reproducibles.")
    # Capturas AUTÉNTICAS del entorno local Windows; nunca fabricarlas.
    evidence=ROOT/"docs/local_evidence"
    requested=[
        (evidence/"Docker_Containers.png",
         "Evidencia local 1. Docker Desktop: API y dashboard funcionando."),
        (evidence/"Dashboard_Piloto.png",
         "Evidencia local 2. Interfaz real de 12 máquinas, alertas y riesgo a 72 horas.")
    ]
    present=[p.is_file() for p,_ in requested]
    if any(present) and not all(present):
        raise FileNotFoundError(
          "Para completar evidencias locales, subir AMBAS capturas PNG: "
          "Docker_Containers.png y Dashboard_Piloto.png."
        )
    if all(present):
        page(st)
        sub(st,"13. Evidencias visuales auténticas de ejecución local")
        para_add(st,"Las siguientes imágenes provienen de la aplicación ejecutada "
            "por el estudiante en Docker Desktop Windows. Se conservan en "
            "el repositorio como archivos originales sin modificación de contenido. "
            "La verificación automática de GitHub no sustituye estas pruebas.")
        for filename,label in requested:
            header=filename.read_bytes()[:8]
            if header!=bytes.fromhex("89504e470d0a1a0a"):
                raise ValueError("Captura local no es un PNG: "+str(filename))
            width,height=ImageReader(str(filename)).getSize()
            if width<760 or height<400:
                raise ValueError("Captura demasiado pequeña: "+str(filename))
            fig(st,filename,label,maxh=8.2*cm)
        swagger=evidence/"Swagger_API.png"
        if swagger.is_file():
            page(st)
            sub(st,"14. Evidencia adicional del contrato OpenAPI")
            fig(st,swagger,"Evidencia local 3. Swagger /docs y los endpoints funcionales.",
                maxh=16.0*cm)
    return st

def main():
    manual_pdf=DOCS/"Manual_Despliegue_Nube_FaseII.pdf"
    validation_pdf=DOCS/"Documento_Validacion_Pruebas_FaseII.pdf"
    build(manual_pdf,manual())
    build(validation_pdf,validation())
    return manual_pdf,validation_pdf

if __name__=="__main__":
    main()
