"""Streamlit dashboard of 12 simulated pilot machines; FastAPI owns inference."""
import os
import requests
import pandas as pd
import streamlit as st
from time_display import format_request_local, format_simulated_utc

API=os.getenv("API_URL","http://localhost:8000").rstrip("/")
st.set_page_config(page_title="Predictive Maintenance AI | 72h",page_icon="🏭",
                   layout="wide",initial_sidebar_state="expanded")
st.title("🏭 Predictive Maintenance AI")
st.caption("Fase II · Piloto de 12 máquinas simuladas · horizonte: próximas 72 horas · actualización cada 6 horas SIMULADAS")
st.warning("PROTOTIPO ACADÉMICO: máquinas, sensores, fallas y resultados son 100% sintéticos. "
           "Las alertas requieren verificación humana. No se ha demostrado efectividad industrial.")
def call(method,endpoint,**kwargs):
    try:
        r=requests.request(method,f"{API}{endpoint}",timeout=20,**kwargs)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        st.error(f"Falla de comunicación con el backend: {str(e)[:250]}")
        st.stop()

health=call("GET","/health")
info=call("GET","/model/info")
if health["status"]!="ok":
    st.error("Backend no disponible")
    st.stop()

with st.sidebar:
    st.header("Control del piloto")
    st.metric("Horizonte",f"{info['horizon_hours']} h")
    st.metric("Umbral de alerta validado",f"{info['threshold']:.2f}")
    st.caption("Los niveles MEDIO/ALTO son reglas demostrativas; el umbral ALTO se seleccionó en validación.")
    st.info("El sistema ayuda a priorizar revisiones. Nunca ordena mantenimientos automáticamente.")
    st.caption(f"Modelo: {info['model_kind']} · semilla {info['seed']}")

machines=call("GET","/machines")
df=pd.DataFrame(machines)
high=int((df.risk_level=="ALTO").sum())
medium=int((df.risk_level=="MEDIO").sum())
low=int((df.risk_level=="BAJO").sum())
a,b,c,d=st.columns(4)
a.metric("Máquinas piloto",len(df));b.metric("Riesgo alto",high)
c.metric("Riesgo medio",medium);d.metric("Riesgo bajo",low)
tab1,tab2,tab3=st.tabs(["Flota y riesgos","Evaluación por máquina","Historial y evidencia"])
with tab1:
    view=df[["machine_id","risk_level","probability_72h","temperature_c",
             "vibration_mm_s","wear_index","timestamp_simulated"]].copy()
    view["timestamp_simulated"]=view["timestamp_simulated"].map(format_simulated_utc)
    view.columns=["Máquina","Riesgo","Probabilidad 72h","Temp °C",
                  "Vibración mm/s","Desgaste","Fecha simulada UTC"]
    st.dataframe(view.sort_values("Probabilidad 72h",ascending=False),
                 use_container_width=True,hide_index=True)
    st.subheader("Probabilidad estimada de falla en 72 horas")
    st.bar_chart(df.set_index("machine_id")["probability_72h"])
    st.caption("Cada probabilidad se genera mediante el modelo sobre una lectura SIMULADA."
               " No corresponde a equipos reales ni indica una fecha exacta de avería.")
with tab2:
    mid=st.selectbox("Selecciona una máquina",[x["machine_id"] for x in machines])
    payload=call("GET",f"/telemetry/{mid}")
    telemetry=payload["machine"]
    st.write(f"Última lectura SIMULADA (UTC): **{format_simulated_utc(telemetry['timestamp'])}**")
    col1,col2,col3=st.columns(3)
    col1.metric("Temperatura",f"{telemetry['temperature_c']:.1f} °C")
    col2.metric("Vibración",f"{telemetry['vibration_mm_s']:.2f} mm/s")
    col3.metric("Desgaste",f"{telemetry['wear_index']:.2f}")
    st.subheader("Escenario académico: modificar sensores")
    with st.form("prediction_form"):
        whatif=st.checkbox("Evaluar escenario hipotético con cambios manuales")
        temperature=st.slider("Temperatura °C",0.0,140.0,
                              float(min(140,max(0,telemetry["temperature_c"]))),.5)
        vibration=st.slider("Vibración mm/s",0.0,12.0,
                            float(min(12,max(0,telemetry["vibration_mm_s"]))),.05)
        wear=st.slider("Desgaste (0 a 1)",0.0,1.0,
                       float(telemetry["wear_index"]),.01)
        submit=st.form_submit_button("Evaluar riesgo de falla a 72 horas",type="primary")
    if submit:
        overrides=({"temperature_c":temperature,"vibration_mm_s":vibration,
                    "wear_index":wear} if whatif else None)
        result=call("POST","/predict",json={"machine_id":mid,"overrides":overrides})
        st.metric("Riesgo calculado",f"{result['probability_72h']:.1%}")
        if result["alert"]:
            st.error(f"Alerta {result['risk_level']}: revisar condiciones y planificar inspección humana.")
        else:
            st.success(f"Nivel {result['risk_level']}; continuar monitoreo, sin garantía de ausencia de falla.")
        st.caption(f"Predicción #{result['record_id']} persistida en SQLite. "
                   "Un escenario manual no equivale a una nueva medición real.")
with tab3:
    hist=call("GET","/predictions?limit=100")
    if hist:
        history_view=pd.DataFrame(hist)
        history_view["requested_at_utc"]=history_view["requested_at_utc"].map(format_request_local)
        history_view["observed_simulated_at"]=history_view["observed_simulated_at"].map(format_simulated_utc)
        history_view=history_view.rename(columns={
            "id":"Registro",
            "machine_id":"Máquina",
            "observed_simulated_at":"Lectura SIMULADA (UTC)",
            "requested_at_utc":"Solicitud real (CDMX)",
            "probability_72h":"Probabilidad 72h",
            "risk_level":"Riesgo",
            "alert":"Alerta",
            "source":"Origen",
        })
        st.dataframe(history_view,hide_index=True,use_container_width=True)
    else:
        st.info("Aún no hay inferencias guardadas. Evalúa una máquina para generar la primera.")
    st.markdown("**API integrada:** [Swagger/OpenAPI](http://localhost:8000/docs) · "
                "**Repositorio:** [Fase II](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII)")
    st.caption("La lectura de sensores corresponde a tiempo SIMULADO (UTC). "
               "La solicitud real se muestra en hora de Ciudad de México "
               "(America/Mexico_City); la API y SQLite conservan el valor UTC original.")
