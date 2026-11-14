"""Dashboard Streamlit: flota, métricas V2, SLO e incidentes verificados."""
import json,os
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
from actividad8.simulator import HERE
st.set_page_config(page_title='Predictive Maintenance AI · Observabilidad',layout='wide')
st.title('🏭 Predictive Maintenance AI | Actividad 8')
st.warning('Piloto académico 100% sintético. Los sensores y las fallas NO son industriales. No iniciar mantenimiento físico automáticamente.')
base=json.loads((HERE/'results/evaluation_v2.json').read_text())
perf=base['metrics']['test_pilot']
c1,c2,c3,c4=st.columns(4)
c1.metric('Precision V2 · piloto',f"{perf['precision']:.1%}")
c2.metric('Recall por ventana',f"{perf['recall']:.1%}")
c3.metric('ROC-AUC',f"{perf['roc_auc']:.3f}")
c4.metric('Recall por evento',f"{perf['event_recall']:.1%}")
st.caption(f"{perf['failure_events_evaluable']} eventos evaluables · {perf['samples']} ventanas · {perf['positives']} positivas. No comparable directamente con V1 por distinto generador.")
st.subheader('Servicio HTTP')
url=os.getenv('ACT8_API','http://127.0.0.1:8008')
try:
    r=requests.get(url+'/metrics',timeout=4);r.raise_for_status();live=r.json()
    st.success('API conectada · peticiones medidas')
    a,b=st.columns(2);a.metric('Solicitudes recientes',live['total']);b.metric('Latencia p95',f"{live['p95_ms'] or 0:.1f} ms")
    st.dataframe(pd.DataFrame(live['measurements'][:40]),use_container_width=True)
except Exception:st.info('API sin conexión; las evidencias históricas permanecen disponibles.')
path=HERE/'evidence/incidents.json'
if path.exists():
    e=json.loads(path.read_text())
    st.subheader('Incidentes, antes/durante/después')
    for incident in e['incidents']:
        with st.expander(incident['incident_id']+' · '+incident['name'],expanded=True):
            st.json(incident)
    st.subheader('Alertas y supresión')
    st.dataframe(pd.DataFrame(e['alerts']),use_container_width=True)
else: st.info('Ejecuta el laboratorio para generar el reporte de incidentes.')
st.subheader('Objetivos SLO y versiones de modelo')
st.json(base['model'])
st.caption('Solicitudes reales HTTP en el laboratorio; eventos y entradas sintéticas; aprobación humana para cambios en producción.')
