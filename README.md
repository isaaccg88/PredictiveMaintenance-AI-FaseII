# Predictive Maintenance AI — Fase II: Ejecución

**Master en Inteligencia Artificial · Módulo 2 / Semana 8 · Proyecto académico**

**Estado verificado:** modelo temporal de 72 horas entrenado; los dos contenedores Docker fueron construidos y ejecutados realmente en GitHub Actions; FastAPI, Streamlit y SQLite aprobaron pruebas de integración. Los dos documentos PDF solicitados están publicados. 

> **AVISO DE TRANSPARENCIA:** la empresa, las 60 máquinas, sus mediciones y las fallas son **100% sintéticas**. Se demuestra la implementación y evaluación de un modelo que predice si sucederá una falla dentro de las siguientes 72 horas **en un simulador**, no validez pronóstica industrial real, ni conocimiento exacto de cuándo fallará una máquina.

## 1. Continuidad con Fase I y actividades previas

Este repositorio materializa el piloto de 12 máquinas ficticias de una empresa manufacturera mexicana planteado en Fase I. La evaluación ocurre cada 6 horas simuladas y el horizonte del clasificador es de **72 horas**. Los técnicos conservan la decisión de inspeccionar o intervenir.

Antecedentes: [Actividad 4, modelos preentrenados](https://github.com/isaaccg88/PredictiveMaintenance-AI-Activity4) y [Actividad 5, entrenamiento y MLflow](https://github.com/isaaccg88/PredictiveMaintenance-AI-Activity5). El AI4I 2020 de ambas actividades clasifica fallas por registro; **no sustenta una anticipación temporal de 72 horas**. Para Fase II se desarrolló un dataset temporal sintético nuevo, con eventos fechados, degradación y mantenimiento, y un modelo Random Forest entrenado específicamente sobre el objetivo futuro.

## 2. Arquitectura funcional

```text
Navegador Windows                  Red privada Docker Compose
http://localhost:8501        ┌───────────────────────────┐
         │                   │ Streamlit (web) :8501     │
         └──────────────────>│ Tablero de 12 máquinas    │
                             └──────────┬────────────────┘
                                        │ HTTP / JSON
                             ┌──────────▼────────────────┐
                             │ FastAPI (api) :8000       │
                             │ Validación con Pydantic   │
                             └──────────┬────────────────┘
                                  ┌─────┴─────────┐
                                  ▼               ▼
                            RandomForest      SQLite
                            riesgo 72h       historial
                                            volumen persistente
```

**Servicios Docker:** [compose.yaml](compose.yaml), [Dockerfile API](docker/Dockerfile.api) y [Dockerfile web](docker/Dockerfile.web). El backend se inicia primero y ofrece healthcheck; el frontend espera a que esté saludable.

## 3. Cómo se construyó la predicción temporal

[Simulador reproducible](src/simulation.py), semilla **202608**. Se generaron **129,600 lecturas** (60 máquinas × 2,160 instantes) espaciadas exactamente cada seis horas, **318 eventos de falla** distribuidos temporalmente, estados de parada/reparación y sensores con patrones de degradación probabilística.

Para cada registro de una máquina en funcionamiento, la variable `failure_next_72h` vale **1** si existe algún evento de falla durante los **12 registros siguientes**: `t+6, t+12, ..., t+72 horas`. Una falla en el instante actual no se contabiliza como anticipada, y las últimas 12 lecturas de cada máquina se **censuran** por falta de información futura. Las medias y variaciones de sensores solo usan valores históricos disponibles hasta `t`.

**Modelo:** [pipeline Random Forest](src/train.py) de scikit-learn, 12 características de sensores e historial. El umbral **0.64** se fijó exclusivamente sobre el conjunto de validación maximizando F2 sujeto a precisión >=20%. El modelo se serializó en [`artifacts/risk72h_model.joblib`](artifacts/risk72h_model.joblib), acompañado de [metadatos de features/umbral](artifacts/model_metadata.json), [lecturas del piloto](artifacts/pilot_snapshot.json) y [manifiesto SHA256](results/dataset_manifest.json).

Se aplicaron particiones temporales con purga de 12 lecturas entre conjuntos. Solo las máquinas PM-001 a PM-048 participaron en entrenamiento y validación. **Las 12 máquinas PM-049 a PM-060 permanecieron completamente excluidas del ajuste**, y representan el piloto experimental fuera de la muestra de máquinas, pero dentro del mismo simulador.

## 4. Resultados reales del dataset sintético

| Indicador | Test temporal | Piloto de 12 máquinas NO vistas |
|---|---:|---:|
| Registros evaluados | 19,906 | 4,991 |
| Prevalencia positiva | 3.26% | 2.89% |
| ROC-AUC | 0.8073 | 0.8621 |
| Average Precision | 0.2286 | 0.2417 |
| Precision | 20.83% | 16.36% |
| Recall por registro | 37.19% | 37.50% |
| F1 | 0.2670 | 0.2278 |
| Fallas con al menos una alerta dentro de 72 h | 30 de 54 (55.56%) | 8 de 11 (72.73%) |
| Anticipación media primera alerta | 61.6 h | 59.25 h |
| Ventanas con falsa alarma / máquina-semana | 1.29 | 1.55 |

**Interpretación crítica:** estos resultados verifican una capacidad de ranking dentro del simulador, pero el **F1 es bajo/modesto** y hay falsas alertas. El recall de eventos es diferente al recall por ventana; en el piloto se basa únicamente en **11 eventos**, por lo que es estadísticamente inestable. No deben extrapolarse a fábricas reales ni confundir un evento sintético detectado con mantenimiento que habría evitado el fallo.

Datos completos del experimento: [evaluación JSON](results/evaluation.json), [métricas CSV](results/model_metrics.csv), [curvas PR](results/figures), [test temporal](results/predictions_test_temporal.csv), [máquinas no vistas](results/predictions_test_unseen_machines.csv), [selección de umbral](results/threshold_validation.csv) y [importancia de variables](results/feature_importance.csv).

El dataset completo reproducible, de mayor tamaño, está en los **artefactos descargables de GitHub Actions**; no se versiona un CSV grande innecesario en Git. Se incluye una [muestra trazable de telemetría](data/generated/telemetry_sample.csv) y el código exacto que lo reconstruye.

## 5. Ejecutar la solución en Docker Desktop

Requisitos: Docker Desktop, WSL2 / motor de contenedores Linux y GitHub Desktop o Git. La prueba de instalación `docker run --rm hello-world` ya fue superada por el estudiante. **No hace falta instalar Python en Windows para ejecutar la aplicación.**

```powershell
git clone https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII.git
cd PredictiveMaintenance-AI-FaseII
docker compose up --build -d --wait
docker compose ps
```

- **Dashboard de las 12 máquinas:** http://localhost:8501
- **Swagger de FastAPI:** http://localhost:8000/docs
- **Salud del backend:** http://localhost:8000/health
- **Historial de predicciones:** http://localhost:8000/predictions

Con Docker Desktop abierto, selecciona una de las máquinas, evalúa el riesgo de falla en las próximas 72 horas y revisa la respuesta. Puedes probar modificaciones de sensores simuladas: se registran como **escenarios hipotéticos**, no como telemetría real.

Para detener sin perder SQLite: `docker compose down`. El volumen `prediction_state` conserva el historial. No ejecutar `down -v` si se quiere mantenerlo.

## 6. Endpoints, pruebas de integración y casos extremos

Código API: [app/api.py](app/api.py); frontend: [app/dashboard.py](app/dashboard.py). Contratos `GET /health`, `GET /model/info`, `GET /machines`, `GET /telemetry/{machine_id}`, `POST /predict`, `GET /predictions`.

[Pruebas unitarias](tests/test_temporal.py) reconstruyen la etiqueta futura a 72h y validan censura, separación cronológica, máquinas excluidas, métricas y umbral. [Prueba de integración Docker](tests/integration.py) ejecuta peticiones HTTP reales, verifica doce máquinas, inferencia y persistencia, escenario hipotético y rechazo de datos inválidos (HTTP 404 y 422). El frontend aprobó su healthcheck HTTP.

Automatización [GitHub Actions](.github/workflows/validate-deploy.yml): instala dependencias fijadas, regenera dataset, prueba el modelo, construye ambos contenedores, los levanta con Docker Compose y verifica integración. El workflow publica los resultados **solo después de superar todos los controles**.

## 7. Entregables académicos en el repositorio

| Entregable | Enlace |
|---|---|
| Código completo y Docker funcional | [app/](app/), [src/](src/), [docker/](docker/), [compose.yaml](compose.yaml) |
| Manual PDF de despliegue local y nube | [Manual_Despliegue_Nube_FaseII.pdf](docs/Manual_Despliegue_Nube_FaseII.pdf) |
| Documento PDF de validación y pruebas | [Documento_Validacion_Pruebas_FaseII.pdf](docs/Documento_Validacion_Pruebas_FaseII.pdf) |
| Manual técnico ampliado | [docs/manual_deploy_cloud.md](docs/manual_deploy_cloud.md) |
| Protocolo de pruebas y casos extremos | [docs/validation_and_tests.md](docs/validation_and_tests.md) |
| Ejecución CI y artefactos | [Actions](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions) |
| Evidencias auténticas de Docker Windows y dashboard | [docs/local_evidence/](docs/local_evidence/) — **pendientes de subir** |

**Formato de entrega:** exclusivamente URL del repositorio público GitHub, **sin ZIP**, según el acuerdo académico de este proyecto. Los dos PDF obligatorios permanecen dentro de GitHub.

## 8. Estrategia de despliegue en la nube

El manual incluye paso a paso, dependencias, Dockerfiles y comparación operativa con PaaS de contenedores. Para la nube se consideran registro OCI, HTTPS, variables de entorno, secretos, healthchecks, observabilidad y migración de SQLite a persistencia administrada para varias réplicas. **No se realizó despliegue cloud comercial ni se generaron cargos**.

## 9. Limitaciones y ética

El modelo aprende una degradación sintética programada, no una relación estimada sobre sensores reales. Las doce máquinas excluidas siguen procediendo del mismo generador. Las etiquetas se refieren a presencia de una falla durante una ventana futura y no determinan su momento exacto. Toda alerta requiere revisión humana; no se emiten órdenes automáticas de mantenimiento. La adopción real requeriría datos prospectivos, calibración, grupos industriales distintos, validación técnica y gestión de drift.

## 10. Declaración de uso de inteligencia artificial

| Herramienta | Finalidad | Control |
|---|---|---|
| ChatGPT de OpenAI | Diseño temporal, generación de datos sintéticos, código ML, API, frontend, Docker, pruebas, manuales y auditoría | Las métricas y verificaciones se ejecutan con código real, reproducible y visible en GitHub; el estudiante revisa la entrega final. |

**Origen de código y modelo:** desarrollo sintético nuevo de Fase II; referencias del flujo: [Actividad 4](https://github.com/isaaccg88/PredictiveMaintenance-AI-Activity4), [Actividad 5](https://github.com/isaaccg88/PredictiveMaintenance-AI-Activity5), documentaciones oficiales de [Docker](https://docs.docker.com), [FastAPI](https://fastapi.tiangolo.com) y [scikit-learn](https://scikit-learn.org).
