"""Panel operativo de la Actividad 8.

Separa indicadores de desempeño sintético (offline), observabilidad de la API
local y evidencias HISTÓRICAS de incidentes generadas en el laboratorio.
"""
from __future__ import annotations

import json
import os

import pandas as pd
import altair as alt
import requests
import streamlit as st

from actividad8.simulator import HERE

API = os.getenv("ACT8_API", "http://127.0.0.1:8008").rstrip("/")
st.set_page_config(
    page_title="Predictive Maintenance AI | Actividad 8",
    page_icon="🏭",
    layout="wide",
)
st.title("🏭 Predictive Maintenance AI | Actividad 8")
st.caption("Centro de observabilidad, calidad predictiva y respuesta a incidentes")
st.warning(
    "Piloto académico con máquinas, datos y fallas 100% sintéticos. "
    "No conecta maquinaria industrial ni autoriza mantenimiento automático."
)


def read_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def number(value, digits=2, suffix=""):
    return "Sin datos" if value is None else f"{value:,.{digits}f}{suffix}"


def api_get(route, timeout=4):
    response = requests.get(API + route, timeout=timeout)
    response.raise_for_status()
    return response.json()


def section_metric(label, value, caption=None):
    st.metric(label, value)
    if caption:
        st.caption(caption)


def plot_incident_stages(stages, values, title, threshold):
    """Orden temporal explícito y umbral para no confundir antes/durante/después."""
    chart_data = pd.DataFrame({"Momento": stages, "Valor": values})
    bars = alt.Chart(chart_data).mark_bar(size=95).encode(
        x=alt.X("Momento:N", sort=stages, title=None,
                axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Valor:Q", title=title, scale=alt.Scale(zero=True)),
        tooltip=[
            alt.Tooltip("Momento:N"),
            alt.Tooltip("Valor:Q", format=".3f"),
        ],
    )
    target = alt.Chart(pd.DataFrame({"Objetivo": [threshold]})).mark_rule(
        strokeDash=[6, 4], color="#cc4a3f", strokeWidth=2
    ).encode(y="Objetivo:Q")
    st.altair_chart((bars + target).properties(height=290), use_container_width=True)
    st.caption(f"Línea roja discontinua: límite de alerta ({threshold:g}).")


data = read_json(HERE / "results" / "evaluation_v2.json") or {}
evaluation = data.get("metrics", {}).get("test_pilot", {})
evidence = read_json(HERE / "evidence" / "incidents.json")
summary = read_json(HERE / "evidence" / "summary.json") or {}

try:
    live = api_get("/metrics")
    connected = True
except requests.RequestException:
    live = {}
    connected = False

main, live_tab, slos_tab, incidents_tab, audit_tab = st.tabs([
    "📊 Resumen", "📡 Monitoreo HTTP", "🚨 Alertas y SLO",
    "🛠️ Incidentes y runbooks", "🧪 Evidencia y trazabilidad"
])

with main:
    st.subheader("Desempeño del modelo V2 · evaluación offline")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        section_metric("Precision", number(
            evaluation.get("precision", 0) * 100, 1, "%"))
    with c2:
        section_metric("Recall por ventana", number(
            evaluation.get("recall", 0) * 100, 1, "%"))
    with c3:
        section_metric("ROC-AUC", number(evaluation.get("roc_auc"), 3))
    with c4:
        section_metric("Recall por evento", number(
            evaluation.get("event_recall", 0) * 100, 1, "%"))
    st.caption(
        f"{evaluation.get('failure_events_evaluable', 0)} fallas evaluables · "
        f"{evaluation.get('samples', 0):,} ventanas · "
        f"{evaluation.get('positives', 0):,} positivas. "
        "Modelo V2 medido sobre un generador sintético diferente al de Fase II: "
        "las cifras V1 y V2 NO son directamente comparables."
    )
    st.divider()
    a, b, c = st.columns(3)
    with a:
        st.metric("Estado de la API local", "Conectada" if connected else "Sin conexión")
    with b:
        st.metric("Solicitudes /predict registradas", live.get("total", 0) if connected else "—")
    with c:
        latency = live.get("p95_ms") if connected else None
        st.metric("Latencia p95 · local", "Sin muestras" if latency is None else number(latency, 1, " ms"))
    st.caption(
        "Servicio HTTP: mediciones de esta instancia local, máximo 500 solicitudes /predict. "
        "El historial de incidentes mostrado en otras pestañas es del laboratorio y no "
        "representa alertas activas del servicio local."
    )
    st.subheader("Probar el piloto de 12 máquinas")
    st.caption("Las lecturas corresponden a snapshots sintéticos; cada prueba genera un registro HTTP y de inferencia.")
    machine = st.selectbox(
        "Selecciona una máquina del piloto",
        [f"PM-{i:03d}" for i in range(49, 61)],
        index=0,
    )
    if st.button("Ejecutar predicción a 72 h", type="primary", disabled=not connected):
        try:
            response = requests.post(API + "/predict", json={"machine_id": machine}, timeout=10)
            response.raise_for_status()
            st.session_state["last_prediction"] = response.json()
            st.rerun()
        except requests.RequestException as exc:
            st.error(f"No se completó la solicitud: {exc}")
    result = st.session_state.get("last_prediction")
    if result:
        st.success("Predicción sintética registrada en FastAPI y SQLite.")
        x, y, z = st.columns(3)
        with x:
            st.metric("Máquina", result.get("machine_id", "—"))
        with y:
            st.metric("Riesgo de falla a 72 h", number(
                result.get("probability_72h", 0) * 100, 1, "%"))
        with z:
            st.metric("Nivel de riesgo", result.get("risk_level", "—"))
        st.caption(
            "Decisión de mantenimiento: revisión humana. "
            f"Traza HTTP: {result.get('trace_id', '—')} · "
            f"Registro SQLite: {result.get('record_id', '—')}"
        )

with live_tab:
    st.subheader("Observabilidad HTTP · instancia local")
    if not connected:
        st.error("La API no está disponible. Verifica el contenedor antes de interpretar el panel.")
    else:
        rows = live.get("measurements", [])
        st.caption(
            "Datos vivos obtenidos de GET /metrics, sobre solicitudes POST /predict. "
            "No son los resultados históricos del laboratorio."
        )
        if not rows:
            st.info("Aún no hay predicciones registradas. Usa la pestaña Resumen para generar una.")
        else:
            df = pd.DataFrame(rows)
            df["duration_ms"] = pd.to_numeric(df["duration_ms"], errors="coerce")
            df["at_utc"] = pd.to_datetime(df["at_utc"], utc=True, errors="coerce")
            df = df.sort_values("at_utc")
            st.line_chart(df.set_index("at_utc")["duration_ms"], y_label="Duración (ms)")
            good = df["status"].between(200, 299)
            failed = df["status"] >= 500
            timely = good & (df["duration_ms"] <= 500)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Solicitudes elegibles", len(df))
            c2.metric("Disponibilidad observada", number((~failed).mean() * 100, 1, "%"))
            c3.metric("Oportunidad ≤500 ms", number(timely.mean() * 100, 1, "%"))
            c4.metric("Errores HTTP 5xx", int(failed.sum()))
            if len(df) < 10:
                st.info("Muestra insuficiente para evaluar SLO operativos: se requieren al menos 10 solicitudes.")
            else:
                allowed = len(df) * 0.01
                spend = failed.sum() / allowed * 100
                late_spend = (~timely).sum() / allowed * 100
                st.caption(
                    f"SLO disponibilidad y oportunidad: ≥99% en esta ventana. "
                    f"Presupuesto: {allowed:.2f} fallos equivalentes. "
                    f"Consumo por 5xx: {spend:.1f}% · "
                    f"consumo por respuestas no oportunas: {late_spend:.1f}%. "
                    "El porcentaje puede superar el 100% cuando se incumple el objetivo."
                )
            columns = ["at_utc", "status", "duration_ms", "trace_id"]
            st.dataframe(df[columns].sort_values("at_utc", ascending=False),
                         use_container_width=True, hide_index=True)
            st.caption(
                "Cada trace_id permite relacionar la solicitud con los registros "
                "de inferencia y persistencia en SQLite."
            )

with slos_tab:
    st.subheader("Seis reglas inteligentes configuradas")
    if not evidence:
        st.info("No se encontró evidencia de laboratorio para mostrar las reglas.")
    else:
        rules = evidence.get("rules", {})
        checked = evidence.get("checks", {}).get("evaluated_rules", {})
        table = []
        names = {
            "availability": "Disponibilidad",
            "http_5xx": "Errores HTTP 5xx",
            "latency": "Latencia / oportunidad",
            "cpu": "CPU",
            "drift": "Data drift",
            "quality": "Calidad del modelo",
        }
        for code, rule in rules.items():
            outcome = checked.get(code, {})
            table.append({
                "Indicador": names.get(code, code),
                "Severidad": rule.get("severity", "—"),
                "Regla / umbral": rule.get("condition", "—"),
                "Runbook": rule.get("runbook", "—"),
                "Evaluación final del laboratorio": outcome.get("status", "NO EVALUADO"),
            })
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
        st.caption(
            "El estado de la última columna procede de una ejecución HISTÓRICA del "
            "laboratorio. No es un monitor 24/7 ni representa alertas activas."
        )
        slo = evidence.get("slo", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("SLO disponibilidad", number(slo.get("availability", 0) * 100, 0, "%"))
        c2.metric("SLO oportunidad", number(slo.get("timely", 0) * 100, 0, "%"))
        c3.metric("Umbral PSI", number(slo.get("drift_psi"), 2))
        st.caption(
            "CPU en la evidencia original se midió en el ejecutor del laboratorio, "
            "NO en el contenedor de la API. Las métricas de calidad requieren "
            "etiquetas sintéticas maduras; no se calculan de predicciones sin resultado."
        )
        st.subheader("Historial de notificaciones del laboratorio")
        alerts = evidence.get("alerts", [])
        emitted = sum(x.get("action") == "EMITTED" for x in alerts)
        suppressed = sum(x.get("action") == "SUPPRESSED_DUPLICATE" for x in alerts)
        recovered = sum(x.get("action") == "RESOLVED" for x in alerts)
        a, b, c = st.columns(3)
        a.metric("Emitidas", emitted)
        b.metric("Duplicados suprimidos", suppressed)
        c.metric("Resoluciones", recovered)
        st.dataframe(pd.DataFrame([{
            "Momento UTC": x.get("at_utc", ""),
            "Regla": x.get("rule", ""),
            "Prioridad": x.get("severity", ""),
            "Evento": x.get("action", ""),
        } for x in alerts]), use_container_width=True, hide_index=True)

with incidents_tab:
    st.subheader("Incidentes controlados · evidencia histórica reproducible")
    st.caption(
        "Las siguientes mediciones fueron generadas por el laboratorio sintético, "
        "NO por las solicitudes de la sesión local del navegador."
    )
    if not evidence:
        st.info("No hay incidents.json. Ejecuta el laboratorio reproducible para generar evidencia.")
    else:
        for incident in evidence.get("incidents", []):
            identifier = incident.get("incident_id", "")
            rb = incident.get("runbook", {})
            if identifier == "INC-01":
                st.markdown("#### INC-01 · Degradación de latencia HTTP")
                stages = ["Antes", "Durante", "Después"]
                values = [
                    incident.get("baseline", {}).get("p95_ms", 0),
                    incident.get("during", {}).get("p95_ms", 0),
                    incident.get("after", {}).get("p95_ms", 0),
                ]
                c1, c2, c3 = st.columns(3)
                for slot, stage, value in zip([c1, c2, c3], stages, values):
                    slot.metric("p95 " + stage.lower(), number(value, 1, " ms"))
                plot_incident_stages(
                    stages, values, "Latencia p95 (ms)",
                    evidence.get("slo", {}).get("max_latency_ms", 500),
                )
                st.caption(
                    "Umbral de referencia: 500 ms. Se retiró la demora de prueba y "
                    "se midieron nuevas solicitudes HTTP en dos ventanas sanas."
                )
            elif identifier == "INC-02":
                st.markdown("#### INC-02 · Cambio de distribución de sensores")
                stages = ["Antes", "Durante", "Después"]
                values = [
                    incident.get("baseline_psi", 0),
                    incident.get("during_psi", 0),
                    incident.get("after_psi", 0),
                ]
                c1, c2, c3 = st.columns(3)
                for slot, stage, value in zip([c1, c2, c3], stages, values):
                    slot.metric("PSI " + stage.lower(), number(value, 3))
                plot_incident_stages(
                    stages, values, "PSI",
                    evidence.get("slo", {}).get("drift_psi", 0.20),
                )
                st.caption(
                    "Umbral PSI >0.20. Se aisló el lote sintético alterado y se "
                    "repitió la evaluación con una muestra restaurada."
                )
            st.write(
                f"**Runbook:** {rb.get('runbook', '—')} · "
                f"**Resultado:** {rb.get('status', '—')}"
            )
            validations = rb.get("verification_checks", {})
            with st.expander("Comprobaciones de cierre y detalle técnico"):
                st.dataframe(pd.DataFrame([
                    {"Verificación": key.replace("_", " "), "Superada": "Sí" if passed else "No"}
                    for key, passed in validations.items()
                ]), hide_index=True, use_container_width=True)
                st.json(incident)
            st.divider()

with audit_tab:
    st.subheader("Trazabilidad de la entrega")
    if evidence:
        st.metric("Incidentes simulados", len(evidence.get("incidents", [])))
        st.metric("Runbooks verificados", "Sí" if summary.get("both_runbooks_verified") else "Pendiente")
        st.caption(
            f"Ejecución original del laboratorio: {evidence.get('start_utc', 'sin fecha')} "
            f"→ {evidence.get('end_utc', 'sin fecha')}"
        )
    st.markdown(
        "**Código y explicaciones:** "
        "[Repositorio Actividad 8](https://github.com/isaaccg88/"
        "PredictiveMaintenance-AI-FaseII/tree/actividad8-v2-observabilidad)  \\n"
        "**Ejecuciones verificables:** "
        "[GitHub Actions](https://github.com/isaaccg88/"
        "PredictiveMaintenance-AI-FaseII/actions)"
    )
    st.caption(
        "Los incidentes, el modelo y las métricas offline corresponden a "
        "un experimento académico sintético versionado. La API local utiliza "
        "registros persistidos en SQLite."
    )
