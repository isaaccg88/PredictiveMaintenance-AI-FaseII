# Predictive Maintenance AI — Fase II: Ejecución

**Módulo 2 / Semana 8 · Proyecto académico simulado de manufactura mexicana.**

> **Estado:** implementación en curso. El horizonte de 72 horas se entrenará sobre eventos sintéticos con cronología explícita; NO se atribuyen esas capacidades al dataset AI4I 2020 de actividades anteriores. Todas las métricas se publicarán después de ejecutar el experimento.

## Objetivo

Estimación cada 6 horas del riesgo de que una máquina en funcionamiento presente una falla **dentro de las próximas 72 horas**, en un piloto simulado de 12 máquinas de una flota ficticia de 60. Los técnicos conservan la decisión de mantenimiento. No es un sistema productivo validado con maquinaria real.

## Arquitectura

`Streamlit (8501)` → `FastAPI (8000)` → `RandomForest a 72 h + SQLite`; Docker Compose administra ambos servicios y la persistencia local.

## Procedencia

Actividades precursoras: [Actividad 4](https://github.com/isaaccg88/PredictiveMaintenance-AI-Activity4) y [Actividad 5](https://github.com/isaaccg88/PredictiveMaintenance-AI-Activity5). La segunda entrena un clasificador de falla en el instante. **La Fase II entrena otro modelo para un objetivo temporal diferente.**

## Reproducir

El workflow de GitHub Actions genera el dataset temporal sintético (semilla fija), verifica fuga de información, entrena el clasificador, exporta sus métricas y prueba el contenedor completo. Una vez publicados los artefactos:

```powershell
docker compose up --build -d
docker compose ps
```

Dashboard: http://localhost:8501 · Documentación API: http://localhost:8000/docs

**Entrega:** URL de este repositorio con código, Docker, manual PDF y documento de pruebas PDF. No ZIP, según acuerdo del proyecto.

## Limitaciones

Datos **100% sintéticos**, generados con una función de degradación que induce patrones previos a fallas. Los resultados son una validación del simulador y del pipeline, NO una estimación confiable de eficacia en una planta real. El pronóstico es probabilidad de *alguna* falla dentro de 72 h, no predicción de una hora exacta.
