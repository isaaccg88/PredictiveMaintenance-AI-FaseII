# 🏭 Predictive Maintenance AI | Proyecto Fase III — Resultados
### MLOps · GitOps · Despliegue continuo simulado · Observabilidad · Portfolio técnico-estratégico

[![Fase III CI/CD](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/workflows/fase3.yml/badge.svg?branch=proyecto-fase-iii)](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/workflows/fase3.yml)

**Universidad Tecmilenio · Gestión de Proyectos de Inteligencia Artificial · Módulo 3 / Semana 12**  
**Rama:** `proyecto-fase-iii` · **Proyecto:** Predictive Maintenance AI · **Caso:** manufacturera mexicana ficticia · **Horizonte del modelo:** 72 horas

> **Alcance comprobado:** sistema académico reproducible con máquinas, fallas y sensores **100% sintéticos**. El CI/CD ejecuta realmente entrenamiento, MLflow, validaciones y un despliegue Docker temporal en GitHub Actions. **No existe despliegue en una fábrica ni en AWS, servicio permanente o mantenimiento físico automático.** GitOps se demuestra mediante estado declarativo, enrutamiento en vivo y rollback en el runner; no constituye un controlador cloud persistente. Las decisiones de mantenimiento y promoción a un entorno real corresponden a personas autorizadas.

**Antecedentes técnicos:** [Prototipo Fase II](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/tree/main) · [Observabilidad e incidentes](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/tree/actividad8-v2-observabilidad) · [Escalabilidad, FinOps y gobernanza](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/tree/actividad9-escalabilidad-gobernanza). Cada etapa conserva sus artefactos y su trazabilidad de versiones.

---

## 1. Resumen ejecutivo y problema industrial

**Problema:** las fallas no previstas interrumpen la producción, incrementan correctivos y dificultan programar mantenimientos. Una alerta anticipada podría ayudar a priorizar inspecciones y decisiones humanas, pero una predicción sin control de versiones, monitoreo ni capacidad de recuperación puede convertirse en otra fuente de riesgo.

**Solución investigada:** un sistema de IA que estima la probabilidad de falla de cada máquina en las siguientes **72 horas**, registra predicciones, presenta riesgos al equipo de mantenimiento y vigila tanto su desempeño de clasificación como la operación del servicio. El alcance académico utiliza 60 máquinas sintéticas y reserva 12 máquinas para una evaluación independiente del ajuste.

**Contribución de Fase III:** cerrar el ciclo técnico demostrando una **línea automatizada de código/datos → entrenamiento → pruebas → MLflow → modelo con huella SHA-256 validada → despliegue de candidata → promoción → detección de fallo → rollback → recuperación auditada**.

| Indicador principal | Resultado comprobado | Interpretación y alcance |
|---|---:|---|
| ROC-AUC de piloto V2 | **0.9655** | Capacidad discriminativa en generador sintético V2; no generalización industrial |
| Precision del piloto | **72.38%** | De cada ventana marcada positiva, proporción verdaderamente positiva en el holdout |
| Recall por ventana | **78.28%** | Ventanas anteriores a falla detectadas; no equivale a recall por evento |
| Recall por evento | **88.57% (31/35)** | Fallas evaluables con al menos una alerta previa en el horizonte |
| Despliegue CI/CD | **2 jobs aprobados** | Modelo validado en MLflow y Docker ejecutado en un runner |
| Recuperación GitOps | **2 promociones y 1 rollback de modelo** | Dos hashes distintos; regresión de latencia medida y retorno a la versión anterior |
| Auditoría operacional Fase III | **Ver sección 5.3, sincronizada con CI/CD** | Muestra breve del API en CI; no acredita SLA 99% industrial |

**Decisión de producto:** el sistema emite estimaciones y recomendaciones de **revisión humana**; nunca detiene ni interviene equipos físicos por su cuenta.

---

## 2. Arquitectura: del prototipo a un ciclo CI/CD verificable

```mermaid
flowchart TB
  DEV["Commit en rama proyecto-fase-iii"] --> CI["GitHub Actions / Job CI"]
  CI --> TEST["Pruebas: etiquetas 72 h, alertas, FinOps, hash SHA-256 y GitOps"]
  TEST --> TRAIN["Generador V2 + Random Forest"]
  TRAIN --> MLF["MLflow: parámetros, 15 métricas, artefactos"]
  MLF --> GATE{"¿Supera gates y hash SHA-256?"}
  GATE -->|No| STOP["Publicación bloqueada"]
  GATE -->|Sí| ART["Release versionada + model.joblib + manifest"]
  ART --> CD["GitHub Actions / Job CD"]
  CD --> DOCKER["Docker Compose: stable, candidate, router, dashboard"]
  DOCKER --> HEALTH["Smoke /health, /model/info, /predict, SQLite"]
  HEALTH --> PROM{"¿Candidata aprobada?"}
  PROM -->|No| STOP
  PROM -->|Sí| SWITCH["Enrutador usa slot candidate"]
  SWITCH --> FAIL["Inyección controlada de demora solo en candidate"]
  FAIL --> HTTP["Regresión HTTP p95 > 500 ms observada"]
  HTTP --> BACK["GitOps revierte al hash del modelo stable"]
  BACK --> CHECK["Predicciones y persistencia recuperadas"]
  CHECK --> RESTORE["Corregir demora en candidate + nuevos smoke"]
  RESTORE --> FIN["Nueva promoción + estado deseado en Git"]
```

**Figura 1.** Flujo ejecutado de Fase III, no una arquitectura conceptual sin implementación. [Código CI/CD](.github/workflows/fase3.yml) · [Estado deseado publicado](fase3/gitops/desired-state.json) · [bitácora cronológica real](fase3/evidence/deployment_events.json).

### Componentes

| Capa | Implementación real | Función | Limitación |
|---|---|---|---|
| Datos sintéticos | [`actividad8/simulator.py`](actividad8/simulator.py) | Simular sensores, fallas, ventanas y etiquetas futuras | No representa fallas industriales reales |
| Modelado | [`train_v2.py`](actividad8/train_v2.py), scikit-learn | Entrenar Random Forest para 72 h y evaluar por particiones | V2 y V1 no se comparan sobre el mismo generador |
| Registro de experimentos | [MLflow](actividad8/mlflow_audit.py) 3.6 | Parámetros, 15 métricas, artefactos y auditoría | Tracking store creado en el runner |
| Release y gates | [`release.py`](fase3/release.py) | Verificar calidad, SHA-256 y alcance de publicación | Los umbrales son política académica configurable |
| Inferencia | [FastAPI](actividad8/service.py) + Docker | POST /predict, /health, /metrics, /history | Servicios temporales del runner |
| Datos de operación | SQLite por instancia, JSONL, trace_id | Persistencia y rastreabilidad HTTP/inferencia | Bases por instancia: no están replicadas ni son HA |
| Tráfico GitOps | [`router.py`](fase3/router.py) y [`gitops.py`](fase3/gitops.py) | Leer estado declarativo y cambiar slot en vivo | Conmutación push-driven en runner, no operador GitOps continuo |
| Dashboard | [Streamlit](actividad8/dashboard.py) | Resumen, HTTP, alertas, incidentes, trazabilidad | Sin IAM/TLS públicos ni operación permanente |

```mermaid
flowchart LR
  USER["Supervisor / Usuario de pruebas"] --> ROUTER["Router :8010"]
  ROUTER --> STABLE["FastAPI stable :8008"]
  ROUTER --> CAND["FastAPI candidate :8008"]
  STABLE --> SQLITE1[("SQLite stable")]
  CAND --> SQLITE2[("SQLite candidate")]
  DASH["Streamlit :8510"] --> ROUTER
  ROUTER --> DES["desired-state.json"]
  CI["GitHub Actions"] --> DES
```

**Figura 2.** Arquitectura del despliegue Docker. *Stable utiliza Random Forest con 130 árboles; candidate emplea una versión distinta de 135 árboles, cada una con SHA-256 propio y SQLite independiente.* El rollback recupera el modelo anterior mediante enrutamiento, pero **no** migra el historial SQLite ni prueba alta disponibilidad multizona.

### Puertos de demostración local

| Servicio | Endpoint | Protección de alcance |
|---|---|---|
| API stable | http://localhost:8008/health | Solo loopback |
| API candidate | http://localhost:8009/health | Solo loopback |
| Router GitOps | http://localhost:8010/health | Solo loopback |
| Dashboard Streamlit | http://localhost:8510 | Solo loopback |

El [Compose de Fase III](fase3/compose.yaml) inicia cuatro servicios. Para demostrar recuperación de **una versión distinta** se introduce intencionalmente latencia en la instancia candidate ya promovida. El router registra solicitudes HTTP 200 cuyo p95 supera 500 ms; el rollback se acepta únicamente con esos resultados y al restaurar el SHA estable. Esta degradación controlada **no representa una caída natural del desempeño predictivo**.

---

## 3. Implementación MLOps: datos, pruebas, MLflow y versionado

### 3.1 Dataset y estrategia de evaluación

El generador V2 crea **129,600 observaciones sintéticas** de 60 máquinas con intervalo de 6 horas. La etiqueta positiva se define cuando ocurre una falla en las siguientes 6–72 horas; las últimas 12 observaciones por máquina se censuran para no utilizar un horizonte futuro incompleto.

Se separan **48 máquinas** para ajuste/validación temporal y **12 máquinas (PM-049 a PM-060)** para evaluación del piloto. El umbral de clasificación **0.50** fue elegido sobre validación, sin optimizarlo contra el piloto. [Metodología detallada](actividad8/docs/METODOLOGIA.md).

### 3.2 Evidencia de desempeño del modelo

| Métrica | Validación | Prueba temporal | Piloto no visto |
|---|---:|---:|---:|
| Precision | 0.6882 | 0.7007 | **0.7238** |
| Recall | 0.8425 | 0.8303 | **0.7828** |
| F1-score | 0.7576 | 0.7600 | **0.7522** |
| ROC-AUC | 0.9760 | 0.9708 | **0.9655** |
| Average Precision | 0.8609 | 0.8530 | **0.8144** |

**Piloto:** TP=346, FP=132, FN=96, TN=4,322; 35 eventos evaluables y 31 detectados. El modelo produce falsas alarmas por ventana, por lo que los equipos requieren reglas de deduplicación y evaluación de impacto operativo. [Resultados originales](actividad8/results/evaluation_v2.json).

**Advertencia comparativa:** Fase II/V1 reportó precision 16.36% y ROC-AUC 0.8621 sobre otro generador. La mejoría numérica de V2 no prueba una mejora controlada de algoritmo: se cambió la distribución generadora. No se presume desempeño industrial.

### 3.3 Automatización y pruebas de integración

El job **continuous-integration** de [GitHub Actions](.github/workflows/fase3.yml) ejecuta:

1. Pruebas de etiquetas futuras, censura, detección de drift, seis reglas de alertas y supresión de duplicados.
2. Pruebas de costos/FinOps, gobernanza del release y transición de estados GitOps.
3. Entrenamiento reproducible V2, evaluación offline y registro de un run real en MLflow.
4. Comprobación cruzada de las **15 métricas MLflow** y sus artefactos contra la evaluación del mismo run.
5. Rechazo si el modelo/metadata no coincide en SHA-256, faltan el horizonte 72 h/holdout 12, o las métricas no alcanzan los límites definidos.
6. Creación de una candidata RF de 135 árboles mediante cinco árboles adicionales, con umbral fijo y evaluación documentada; su hash debe ser diferente del estable y superar los gates.
7. Publicación de **ambos** artefactos de modelo para el job CD. Las imágenes Docker reciben los binarios ya aprobados; no reentrenan dentro del contenedor.

### 3.4 Baseline de calidad y gates de promoción

| Indicador de release | Baseline piloto medido | Mínimo de promoción | Resultado |
|---|---:|---:|---|
| Precision | **0.723849** | ≥0.70 | PASS |
| Recall por ventana | **0.782805** | ≥0.75 | PASS |
| ROC-AUC | **0.965536** | ≥0.95 | PASS |
| Recall por evento | **0.885714** | ≥0.85 | PASS |
| Horizonte de predicción | **72 h** | Exactamente 72 h | PASS |
| Máquinas holdout | **12** | Exactamente 12 | PASS |
| Integridad de artefacto | SHA-256 calculado | Coincide con metadata/manifest | PASS |

**Integridad ≠ firma digital:** SHA-256 permite comprobar que el archivo no cambió respecto al manifest. **No se implementó una firma criptográfica autenticada con clave privada**, ni cadena de confianza de una registry. Esta distinción forma parte de la auditoría de seguridad.

**Criterio técnico:** estos límites son umbrales definidos para el experimento sintético, no normas regulatorias ni garantías industriales. El segundo modelo mantiene el mismo conjunto de entrenamiento y el mismo umbral fijado por validación, y cambia únicamente el número de árboles (130 → 135). La receta se define antes de revisar los resultados de la candidata. El [código de gating](fase3/release.py) hace fallar la ejecución si se degrada una métrica o se modifica el binario. Las [pruebas unitarias](fase3/test_phase3.py) verifican también que un release degradado o manipulado sea rechazado.

### 3.5 MLflow e integridad SHA-256 del artefacto

<!-- F3-RELEASE-START -->
<details>
<summary>Manifest de la última release validada</summary>

- **Versión:** `v2-849ad06d182b`
- **SHA-256 completo:** `849ad06d182b07d578d3adf0117543953fda063a47ef56e8e60be3d3dfb3b79f`
- **Experimento MLflow:** `PredictiveMaintenanceAI_Actividad8_V2`
- **Run MLflow de esta ejecución:** `3c61be3957d54d2783b0c4f789f3926d`
- **Commit origen:** `e719a5a14fd5436a53844ed3394b5febc9aab537`
- **Alcance:** `academic_staging_only` (autorización industrial = `false`)
- **GitHub Actions:** [ejecución #45218317927](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/runs/45218317927)

</details>

[JSON de release](fase3/evidence/release_manifest.json) · [MLflow auditado por el pipeline](actividad8/mlflow_audit.py) · [Evidencia operativa](fase3/evidence/operations_audit.json).
<!-- F3-RELEASE-END -->

La [evidencia de release](fase3/evidence/release_manifest.json) contiene el hash completo, seed, evaluación, gates, run MLflow y commit Git de origen. La coincidencia se verifica **antes** del despliegue. El modelo serializado se publica como artefacto temporal de Actions; **no** se incorpora su binario a Git sin necesidad.

![MLflow — entrenamiento y registro de runs](actividad8/evidence/screenshots/MLflow_experimento_runs.png)

**Figura 3.** Evidencia histórica real de la interfaz MLflow del laboratorio de la Actividad 8. Fase III realiza una nueva auditoría programática del tracking store en su propio CI; esta captura no se presenta como pantalla de la ejecución nueva.

[Ejecuciones de Fase III](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/workflows/fase3.yml) · [Auditoría MLflow reutilizada](actividad8/mlflow_audit.py).

---

## 4. GitOps/CD: despliegue, promoción, incidente y recuperación

### 4.1 ¿Cómo funciona?

El job **continuous-deployment** solo comienza después de la aprobación del CI. Descarga el modelo cualificado, verifica nuevamente su huella, crea estado deseado inicial `stable`, construye los cuatro contenedores y realiza peticiones HTTP reales contra la API y el router.

Se comprueban `/health`, `/model/info`, el conjunto de **12 máquinas**, **3 predicciones distintas**, sus `trace_id` y los registros persistidos en SQLite. Solo con estas comprobaciones aprobadas se autoriza cambiar la ruta a `candidate`.

El router lee [`desired-state.json`](fase3/gitops/desired-state.json), por lo que las transiciones de slots producen un cambio observable en el encabezado HTTP `X-Serving-Slot`. El estado final aprobado se conserva en Git junto con la bitácora y los resultados; **Git documenta y controla el estado del experimento, pero no hay un agente GitOps externo observando permanentemente el repositorio**.

### 4.2 Secuencia de promoción, degradación y rollback

| Etapa | Evidencia técnica | Verificación |
|---|---|---|
| Inicio | [Desired state](fase3/gitops/desired-state.json) | Stable activo con su versión y SHA |
| Candidata validada | [Smoke candidate](fase3/evidence/candidate_smoke.json) · [evaluación offline](fase3/evidence/candidate_evaluation.json) | RF 135 árboles, hash distinto, 3 predicciones SQLite |
| Primera promoción | [Router promovido](fase3/evidence/router_promoted.json) | Respuestas HTTP con SHA candidate |
| Incidente controlado | [Medición de regresión](fase3/evidence/router_degradation.json) | Solicitudes 2xx reales pero p95 >500 ms |
| Rollback de versión | [Router restaurado](fase3/evidence/router_restored.json) | Tres predicciones con SHA del modelo stable previo |
| Reparación y nueva promoción | [Router final](fase3/evidence/router_final.json) | Latencia restaurada y hash candidate |
| Auditoría de operaciones | [Eventos GitOps](fase3/evidence/deployment_events.json) · [métricas](fase3/evidence/operations_audit.json) | Dos promociones, un rollback entre binarios diferentes |

La [bitácora cronológica](fase3/evidence/deployment_events.json) contiene los hashes y tiempos UTC observados; las mediciones son del laboratorio temporal. La degradación se simula añadiendo 700 ms exclusivamente al servicio candidato **después de haber superado los controles previos**. Esta prueba ejercita una regla de SLO operacional y un rollback de versión, no evidencia degradación espontánea de precisión o seguridad industrial.

**Regla de reversión:** `p95 >500 ms` sobre al menos cinco solicitudes HTTP exitosas en candidata y correlación con su SHA. Tras el cambio, el smoke de restauración debe demostrar que el router entrega el **hash stable diferente**, recupera predicciones y registra sus trazas en SQLite. No se promueve una candidata que falle los controles offline.

### 4.3 Qué se automatizó y qué no

| Capacidad | Estado |
|---|---|
| CI ante push a la rama de Fase III | Automatizado |
| Entrenamiento, auditoría MLflow, versionado y gates | Automatizado |
| Despliegue Docker temporal de 2 API + router + dashboard | Ejecutado |
| Promoción y rollback entre **dos versiones de modelo** | Ejecutado: dos SHA-256 distintos y router verificado |
| Reversión ante degradación de latencia en candidata | Medida en HTTP; no representa degradación natural de ROC-AUC |
| Autoescalado/AWS, persistencia compartida, failover multizona | Solo diseño propuesto en Actividad 9 |
| Aprobaciones corporativas, seguridad IAM, operatividad 24/7 | Pendiente de un escenario industrial real |
| Mantenimiento físico automatizado | No permitido en el piloto |

**Decisión:** esta implementación prueba técnicamente una **entrega continua simulada** en entorno efímero. No debe denominarse producción ni GitOps reconciliado desde un cluster externo.

---

## 5. Operación del sistema, monitoreo y runbooks

### 5.1 Operación de la solución

| Operación | Endpoint/artefacto | Responsable propuesto |
|---|---|---|
| Comprobar salud, carga de modelo y horizonte | `GET /health` · `GET /model/info` | SRE |
| Consultar máquinas y solicitar predicción | `GET /machines` · `POST /predict` | Mantenimiento |
| Auditar latencia y solicitudes HTTP | `GET /metrics`; registros estructurados | SRE |
| Consultar inferencias persistidas | `GET /history`; SQLite | MLOps / SRE |
| Revisar características y métricas | MLflow + `evaluation_v2.json` | ML Lead |
| Investigar drift, incidentes y error budget | Dashboard y [A8](actividad8/evidence/incidents.json) | ML Lead / SRE |
| Aprobar cambios de release, gates y rollback | [CI/CD de Fase III](.github/workflows/fase3.yml) | ML Lead / Product Owner |
| Supervisar impacto económico | [FinOps de A9](actividad9/evidence/finops_model.json) | FinOps / Product Owner |

**Runbook de recuperación del despliegue:**

1. Comprobar release/hash, `/health` y el slot en `GET router:8010/health`.
2. Si candidata está disponible, ejecutar [smoke](fase3/smoke.py) y comparar trazas con `/history`; promocionar **únicamente** después de PASS.
3. Si el p95 supera 500 ms con candidata activa, registrar las muestras y el SHA con [degradation_probe.py](fase3/degradation_probe.py) y ejecutar [rollback](fase3/gitops.py) al modelo estable anterior.
4. Repetir tres predicciones y comprobar que los `trace_id` aparecen en SQLite. Cerrar la incidencia solo tras verificar servicio recuperado.
5. Corregir la regresión de la candidata, repetir pruebas HTTP y promoverla solo después de pasar los controles; conservar la [bitácora de versiones y eventos](fase3/evidence/deployment_events.json).
6. Si `stable` también falla, **escalar a SRE** y no declarar recuperación. Este laboratorio no prueba restauración de una base de datos común ni disaster recovery.

### 5.2 Monitoreo de referencia (baseline) y niveles de servicio

Se utiliza el histórico medido de la Actividad 8 para establecer **antes → incidente → después**. Son mediciones del laboratorio sintético y no benchmarks de AWS.

| Indicador | Baseline normal | Umbral/objetivo configurado | Incidente | Recuperación |
|---|---:|---|---:|---:|
| Disponibilidad HTTP | 100% | SLO ≥99% | 100% en falla de latencia A8 | 100% |
| Oportunidad HTTP 2xx ≤500 ms | 100% | SLO ≥99% | 0% en INC-01 | 100% |
| Latencia p95 | **35.89 ms** | Diagnóstico 500 ms; alerta por SLI | **689.22 ms** | 37.22 ms |
| Errores HTTP 5xx | 0% | Alerta >1% | 0% en INC-01 | 0% |
| PSI de temperatura | **0.071** | Alerta >0.20, N≥100 | **10.361** | 0.056 |
| Calidad ROC-AUC offline | **0.9655** | Alerta propuesta <0.75 con etiquetas maduras | No simulada | No evaluada |

El p95 no sustituye el SLI de oportunidad. Con 12 peticiones, un error consume más que todo el presupuesto de error del 1% de esa ventana; ello es **didáctico** y no un presupuesto mensual representativo. [Baseline detallado](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/blob/actividad8-v2-observabilidad/README.md#4-diseño-de-monitoreo-métricas-logs-y-trazas).

### 5.3 Auditoría operacional nueva de Fase III

<!-- F3-OPERATIONS-START -->
| Campo medido en última ejecución #45218317927 | Resultado |
|---|---:|
| Backend `/predict` registrado | **12 solicitudes** |
| Respuestas HTTP 5xx del backend | **0** |
| Disponibilidad backend de la muestra | **100.0%** |
| Oportunidad backend de la muestra | **100.0%** |
| Latencia p95 backend | **34.250 ms** |
| Caída observada desde router (fuera del contador backend) | **HTTP 502** |
| Transiciones verificadas | **2 promociones y 1 rollback** |
| Slot final | **`candidate`** |

Estas cifras proceden de [la misma ejecución aprobada](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/runs/45218317927); no son promedios de un servicio permanente. El error 502 se conserva en el [smoke del router](fase3/evidence/router_failure.json), por separado de `/metrics` del backend apagado.
<!-- F3-OPERATIONS-END -->

[JSON de auditoría](fase3/evidence/operations_audit.json) · [Regresión de latencia observada](fase3/evidence/router_degradation.json) · [Comprobación después del rollback](fase3/evidence/router_restored.json).

**Matiz estadístico:** las muestras de corta duración y un único runner no acreditan un SLA de 99% ni un tiempo de recuperación operativo. La demora se introdujo en el middleware candidato y se midió desde el router; las métricas del backend no capturan necesariamente el tiempo agregado por ese middleware. La supervisión industrial necesita SLIs medidos en el borde.

### 5.4 Logs y trazabilidad de una predicción

Cada `POST /predict` genera `trace_id`, duración, estatus, identificador de máquina, probabilidad y registro SQLite. Una solicitud puede seguirse mediante eventos `model.infer` → `sqlite.commit` → `http.request`. El dashboard no necesita acceder a contraseñas o datos personales para hacerlo en este caso sintético.

[Traza HTTP correlacionada preservada](actividad8/evidence/ejemplo_traza_real.json) · [Código de instrumentación](actividad8/service.py) · [Logs de contenedores del CD](fase3/evidence/containers.log).

![Dashboard — estado del modelo y API](actividad8/evidence/screenshots/Dashboard_resumen.png)

**Figura 4.** Interfaz real capturada en la Actividad 8 (vista ilustrativa del mismo stack). En Fase III el dashboard se vuelve a levantar automáticamente, pero la imagen no pretende ser una captura específica del último job de Fase III.

---

## 6. Auditoría y optimización del sistema

### 6.1 Resultado del incidente de latencia y data drift

![INC-01 — Latencia antes, durante y después](actividad8/evidence/screenshots/INC-01_latencia_antes_durante_despues.png)

**Figura 5.** La latencia p95 aumentó de **35.9 ms a 689.2 ms** al inyectar demora temporal y bajó a **37.2 ms** tras retirarla; el runbook RB-LATENCY exigió nuevas ventanas saludables antes de RESOLVED.

![INC-02 — PSI antes, durante y después](actividad8/evidence/screenshots/INC-02_drift_antes_durante_despues.png)

**Figura 6.** El PSI de temperatura evolucionó de **0.071 a 10.361 y posteriormente 0.056**. Aislar el lote sintético restableció una distribución estable: esto **no** demuestra por sí solo recuperación del ROC-AUC, que necesita etiquetas maduras.

### 6.2 Mejoras de capacidad observadas en la Actividad 9

La Actividad 9 comparó HTTP con una y dos API sobre **el mismo runner**, con 60 solicitudes por ventana, por lo que son resultados operativos de corta duración y no pruebas de alta disponibilidad cloud.

| Concurrencia 4 | Una API | Dos API | Interpretación |
|---|---:|---:|---|
| Throughput | 52.83 req/s | 95.56 req/s | **+80.9%** observado en esa corrida |
| p95 | 89.8 ms | 51.4 ms | Menor latencia en dos procesos para esa prueba |
| Respuestas oportunas | 100% | 100% | Muestra insuficiente para acreditar SLO 99% industrial |

![Throughput bajo carga](actividad9/evidence/fig_03_throughput.png)

**Figura 7.** La segunda API ofrece mayor capacidad en el host de ensayo; no supone una ganancia lineal ni prueba escalabilidad en ARM o en múltiples zonas. [Datos completos de benchmark](actividad9/evidence/load_benchmark.json).

### 6.3 Costos y optimización FinOps

En el escenario **hipotético de 10 millones de solicitudes mensuales**, el modelo FinOps propone:

| Arquitectura modelada | USD/mes | Condición |
|---|---:|---|
| Cloud básica x86 | **131.46** | Sin redundancia/HA |
| HA x86 sin right-sizing | **217.50** | 2 tareas API, supuesto Multi-AZ |
| HA ARM con right-sizing | **170.65** | 2 tareas API; compatibilidad y desempeño ARM pendientes |

La comparación de HA x86 contra HA ARM genera un ahorro **estimado** de **21.5%**, no realizado. El cálculo excluye componentes como NAT, WAF, respaldos, soporte y personal, y no demuestra que ARM cumpla el mismo SLO bajo carga real. [Fórmulas y supuestos](actividad9/finops.py) · [datos](actividad9/evidence/finops_model.json).

![Costos de las tres arquitecturas y tres escenarios](actividad9/evidence/fig_04_costos_finops.png)

**Figura 8.** Las curvas de costo muestran decisiones de infraestructura **propuestas**, no facturación real. La elección debe condicionarse a mediciones cloud con límites reales, seguridad y presupuesto aprobado.

### 6.4 Sesgos técnicos y vigilancia de desempeño entre equipos

| Tipo de máquina sintética | Recall | FPR | Máquinas distintas |
|---|---:|---:|---:|
| A | 72.54% | 3.01% | 4 |
| B | 80.13% | 2.59% | 4 |
| C | 81.94% | 3.29% | 4 |

La brecha TPR máxima es **9.41 puntos porcentuales**. Se recomputaron intervalos exploratorios bootstrap por máquina, pero únicamente cuatro máquinas por tipo impiden concluir paridad estadística industrial. No hay atributos personales/demográficos; esto es **fairness operacional por tipo de máquina**.

![Recall por tipo de máquina e incertidumbre](actividad9/evidence/fig_05_fairness_tpr.png)

**Figura 9.** El tipo A presenta menor recall descriptivo. La decisión propuesta es investigar la brecha con más equipos independientes y etiquetas maduras antes de autorizar cualquier uso industrial. [Auditoría reproducible](actividad9/evidence/fairness_machine_types.json).

### 6.5 Registro de acciones y próximas optimizaciones

| Decisión | Justificación cuantitativa | Acción realizada o recomendada |
|---|---|---|
| Mantener el modelo V2 evaluado | ROC-AUC 0.9655, recall por evento 88.57%, solo sintético | **Realizado:** release bajo gates, MLflow y SHA |
| Fortalecer respuesta a degradación del servicio | A8: p95 689 ms; F3: regresión de latencia controlada tras promover candidata | **Realizado:** runbooks, medición HTTP y rollback a la versión estable |
| Controlar data drift | PSI 10.361 frente al umbral 0.20 | **Realizado:** cuarentena y medición de recuperación sintética |
| Dimensionar y controlar costo cloud | HA ARM US$170.65 vs HA x86 US$217.50 hipotéticos | **Propuesto:** pruebas ARM y presupuesto AWS completo |
| Reducir brecha de recall por tipo | TPR gap 9.41 puntos, 4 máquinas/tipo | **Propuesto:** evaluación con más unidades independientes |
| Hacer verdaderamente resiliente el sistema | SQLite separada por réplica y una sola máquina de CI | **Pendiente industrial:** DB compartida, despliegue multi-AZ, seguridad IAM/TLS, observabilidad central |

---

## 7. Valor de negocio y viabilidad de la solución

### 7.1 Propuesta de valor

**Usuarios:** técnicos de mantenimiento, supervisores de planta, operaciones y responsables de TI/MLOps. El sistema prioriza inspecciones con información de riesgo a 72 horas y puede apoyar decisiones de programación; la decisión final permanece con el personal responsable.

**Cadena de impacto propuesta:**

```mermaid
flowchart LR
  S["Telemetría validada"] --> P["Riesgo de falla a 72h"]
  P --> I["Inspección humana priorizada"]
  I --> D["Programar acciones antes de paro"]
  D --> V["Posible reducción de paros/correctivos"]
  V --> KPI["Horas de paro evitadas y costo neto"]
```

Los primeros tres pasos tienen **componentes técnicos demostrados con datos sintéticos**; los dos últimos **requieren un piloto industrial** para validar causalidad e impacto económico.

### 7.2 Ejemplo financiero de sensibilidad, NO ahorro realizado

Para discutir valor de negocio se plantea un ejemplo **hipotético**: costo de paro = MXN **18,000 por hora** y costo marginal de intervención preventiva = MXN **12,000 por evento**. **No son costos extraídos de una planta ni resultados observados.**

| Horas de paro efectivamente evitadas | Beneficio bruto supuesto | Costo preventivo supuesto | Beneficio neto ilustrativo |
|---|---:|---:|---:|
| 2 h | MXN 36,000 | MXN 12,000 | **MXN 24,000** |
| 4 h | MXN 72,000 | MXN 12,000 | **MXN 60,000** |
| 6 h | MXN 108,000 | MXN 12,000 | **MXN 96,000** |

**Fórmula:** `beneficio_neto = horas_realmente_evitadas × costo_hora − costo_intervención − costos_de_falsas_alarmas − costo_operativo_de_la_IA`. La tabla omite los últimos dos términos para ejemplificar la sensibilidad, por lo que **no representa ROI calculado**. Para medir valor real se requieren datos de paros, costos de refacciones, inspecciones fallidas, fallas no detectadas y una comparación controlada antes/después.

### 7.3 Decisiones de producto y arquitectura justificadas

- **72 horas de horizonte:** permite explorar decisiones antes de una falla sin activar mantenimiento físico autónomo; las etiquetas se generan solo con futuros eventos sintéticos.
- **Modelo Random Forest con ingeniería de variables:** elegido por su capacidad de clasificación tabular; el piloto revela compromisos entre precision y recall.
- **FastAPI y Streamlit:** separación de inferencia e interfaz; APIs medidas y observables.
- **MLflow + GitHub Actions:** trazabilidad de parámetros, resultados y releases en un ejercicio reproducible.
- **SHA-256 + gates:** prevenir que el entorno de staging use un artefacto diferente al evaluado.
- **Dos binarios de modelo + router:** demostrar promoción, detección de regresión de latencia y recuperación de un hash anterior sin atribuir alta disponibilidad industrial.
- **FinOps y responsible AI:** el costo unitario, la calidad por grupos, la privacidad y los SLO deben evaluarse **conjuntamente**, no como métricas aisladas.

### 7.4 Riesgos estratégicos

| Riesgo | Consecuencia | Control/gate propuesto |
|---|---|---|
| Sobreajuste al generador sintético | Métricas optimistas fuera del laboratorio | Piloto con sensores reales y nuevas etiquetas |
| Falsos negativos/positivos | Paros no anticipados o inspecciones innecesarias | Costos por episodio, recall por evento y revisión humana |
| Drift en condiciones de operación | Degradación silenciosa | PSI, nuevas cohortes, quality gates con etiquetas maduras |
| Pérdida de datos/caída del backend | Trazabilidad incompleta | Migrar de SQLite local a DB robusta compartida |
| Errores en cambio de versión | Predicciones no disponibles | Canary, validaciones, enrutamiento reversible y rollback real de modelo |
| Gastos cloud subestimados | Proyecto financieramente inviable | AWS Calculator, presupuestos, alarmas y costo por inferencia |
| Datos personales en implantación futura | Riesgo legal/privacidad | Inventario de datos, minimización, controles IAM y revisión jurídica |

---

## 8. Gobernanza, auditoría y ciclo de vida responsable

**Gobernanza técnica:** modelo y dataset etiquetados como sintéticos; evidencia de evaluación segregada, huellas verificadas, permisos de GitHub Actions acotados por job, monitoreo separado de incidentes y bitácora inmutable a nivel de commits del repositorio (sujeta a permisos Git). Los archivos JSON contienen trazabilidad; no constituyen por sí solos un sistema de auditoría corporativo antifraude.

**Gobernanza humana:** el ML Lead aprueba validez y riesgos del modelo; SRE valida infraestructura/SLO; Product Owner decide presupuesto y aceptación operativa; Legal/Security evalúan la pertinencia de protección de datos. Ningún resultado sintético permite certificar cumplimiento de una fábrica.

**Marcos de orientación:** NIST AI RMF (GOVERN, MAP, MEASURE, MANAGE), ISO/IEC 42001 y, en caso de introducir información de trabajadores, la normativa mexicana de protección de datos personales aplicable. Son referencias para diseñar controles, no certificaciones obtenidas.

### Plan de transición posterior a la Fase III

| Etapa | Producto verificable | Criterio de avance |
|---|---|---|
| 0. CI/CD de staging | Dos releases de modelo, gates, canary, degradación y rollback de versión | **Ejecutado en Actions** |
| 1. Staging real controlado | Backend DB compartida, secretos, TLS, CI de seguridad, despliegue a nube | Revisión técnica y costos aprobados |
| 2. Datos industriales | Inventario de sensores, calidad, fallas etiquetadas y evaluación temporal externa | Calidad por sitio/tipo, riesgos aceptados |
| 3. Experimento operativo | Operadores comparan predicción con proceso convencional | Reducción de paros y falsas alarmas medible |
| 4. Producción supervisada | SLO mensual, MLOps completo, DR, alertas, roles y costos | Autorización empresarial, legal y operacional |

---

## 9. Evolución técnica y decisiones del proyecto

| Fase / actividad | Pregunta del negocio o tecnología | Lo construido o aprendido |
|---|---|---|
| **Fase I** | ¿Es pertinente abordar las fallas con IA? | Problema, alcance, usuarios, propuesta de valor y horizonte de 72 h |
| **Fase II** | ¿Puede operar un servicio de predicción integral? | Dataset/modelo sintético, FastAPI, persistencia, Docker, frontend y pruebas |
| **Actividad 8** | ¿Cómo sabemos si servicio y modelo se degradan? | Baseline, SLO, seis reglas, MLflow, PSI, dos incidentes con runbooks |
| **Actividad 9** | ¿Cómo crecer sin perder costo, fiabilidad y gobernanza? | Benchmark de carga, rediseño AWS simulado, FinOps, fairness A/B/C |
| **Fase III** | ¿Podemos construir, probar, liberar y recuperar versiones de modo controlado? | **CI/CD funcional** con RF 130/135, SHA-256, MLflow, Docker, regresión p95 controlada, rollback entre versiones y auditoría |

**Implicación para la adopción:** un buen valor de ROC-AUC no es suficiente para justificar una adopción industrial. La IA debe ser **reproducible, observable, económicamente evaluable, operable y gobernada**. Ese es el principal resultado de gestión del proyecto.

---

## 10. Reproducibilidad, código y evidencia

### Estructura principal de la Fase III

```text
.github/workflows/fase3.yml      # CI + CD GitOps simulado
fase3/
  release.py                    # gates de calidad e integridad del modelo
  model_versions.py             # stable RF130 + candidate RF135
  degradation_probe.py          # medición HTTP de regresión p95
  visualizations.py             # tres gráficas SVG con datos del run
  gitops.py                     # desired state / promote / rollback
  router.py                     # forwarding HTTP según slot
  smoke.py                      # salud, inferencia, modelo, SQLite
  ops_audit.py                  # auditoría de servicio y routing
  test_phase3.py                # pruebas de rechazo, hash, estado
  compose.yaml                  # 2 API + router + dashboard
  docker/                       # imágenes con artefacto ya evaluado
  gitops/desired-state.json     # estado declarativo final publicado
  evidence/                     # release, smokes, incidentes y auditoría
actividad8/                     # dataset, modelo, MLflow, observabilidad
actividad9/                     # costos, benchmarking y fairness
```

**Verificación y reproducibilidad:** el [workflow de Fase III](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/workflows/fase3.yml), elegir una ejecución completada y revisar ambos jobs y sus artefactos. Las evidencias principales también están versionadas en `fase3/evidence/` para no depender exclusivamente de la caducidad de artefactos de Actions.

### Reproducir en Windows (con Git, Python 3.11 y Docker Desktop)

```powershell
git clone --branch proyecto-fase-iii https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII.git PredictiveMaintenance-FaseIII
cd PredictiveMaintenance-FaseIII

python -m pip install -r actividad8/requirements.txt
python -m pytest actividad8/test_activity8.py actividad9/test_activity9.py fase3/test_phase3.py -q

python -m actividad8.train_v2 --mlflow
python -m actividad8.mlflow_audit
python -m fase3.release
python -m fase3.model_versions

python -m fase3.gitops init
docker compose -f fase3/compose.yaml up --build -d --wait
python -m fase3.smoke --url http://127.0.0.1:8008 --expected-model stable --out fase3/evidence/stable_local.json
python -m fase3.smoke --url http://127.0.0.1:8009 --expected-model candidate --out fase3/evidence/candidate_local.json
python -m fase3.gitops promote --validation fase3/evidence/candidate_local.json
python -m fase3.smoke --url http://127.0.0.1:8010 --expected-model candidate --expected-slot candidate --out fase3/evidence/router_local.json

# Al finalizar:
docker compose -f fase3/compose.yaml down
```

Para reproducir **el rollback de modelo**, tras la primera promoción en Docker se crea el flag local `/state/latency_degradation.flag` dentro de `api-candidate`, se ejecuta `fase3.degradation_probe` y luego `fase3.gitops rollback --failure fase3/evidence/router_degradation.json`. Se comprueba con `smoke --expected-model stable --expected-slot stable`. El flujo completo está automatizado en el [workflow CI/CD](.github/workflows/fase3.yml) y la inyección se limita al laboratorio sin conexión industrial.

### Trazabilidad de evidencias verificables

| Requisito | Evidencia específica |
|---|---|
| Fuente y tests de CI/CD | [Workflow](.github/workflows/fase3.yml) · [pruebas](fase3/test_phase3.py) |
| Modelo versionado y auditado | [Manifest](fase3/evidence/release_manifest.json) · [MLflow](actividad8/mlflow_audit.py) |
| Infraestructura declarativa | [Compose](fase3/compose.yaml) · [Desired state](fase3/gitops/desired-state.json) |
| Promoción, degradación y rollback de modelo | [Eventos](fase3/evidence/deployment_events.json) · [p95 observado](fase3/evidence/router_degradation.json) · [recuperación](fase3/evidence/router_restored.json) |
| Operación y métricas | [Auditoría F3](fase3/evidence/operations_audit.json) · [historial A8](actividad8/evidence/incidents.json) |
| Evidencia visual del dashboard | [Capturas A8](actividad8/docs/EVIDENCIAS_VISUALES.md) |
| MLflow de etapa previa | [Capturas MLflow A8](actividad8/docs/MLFLOW_EVIDENCIA.md) |
| Performance/FinOps/fairness | [Benchmark](actividad9/evidence/load_benchmark.json) · [Costos](actividad9/evidence/finops_model.json) · [Grupos A/B/C](actividad9/evidence/fairness_machine_types.json) |
| Ejecución auditada de Fase III | [Workflow de Fase III](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/workflows/fase3.yml) |

---

## 11. Evaluación crítica: fortalezas y limitaciones

**Fortalezas demostradas:** gates de calidad verificables, versionado por hash, MLflow auditado, dos slots ejecutándose en Docker, enrutamiento dinámico, predicciones persistidas y recuperación comprobada ante falla HTTP real, con un historial GitOps versionado. La arquitectura integra evidencia técnica y financiera de proyectos anteriores sin modificar sus ramas.

**Limitaciones materialmente importantes:**

1. Solo existen **datos sintéticos**, sin rendimiento validado en máquinas reales.
2. `stable` y `candidate` usan **modelos diferentes** y la reversión restaura el hash stable mediante el router. No reproduce una degradación espontánea del algoritmo: la regresión de latencia fue provocada para ensayar el mecanismo de recuperación.
3. El estado GitOps se genera y publica desde el job; **no** existe un agente externo que sondee Git continuamente ni un despliegue permanente de nube.
4. El runner se destruye al finalizar: los cuatro servicios dejan de estar disponibles, salvo su código/evidencias.
5. Cada API tiene **SQLite independiente**; las predicciones no se replican entre slots.
6. Las mediciones HTTP de corta duración no demuestran un SLA mensual. La latencia introducida por el middleware candidato se mide desde el router y no equivale al tiempo de inferencia registrado por el backend.
7. La estimación de costos de A9 no incluye TCO completo; la fairness de A9 se evaluó con cuatro máquinas por tipo.
8. La aplicación no implementa aún autenticación empresarial, gestión de secretos, auditoría centralizada, backups automáticos o pruebas de desastre de una infraestructura real.

**Conclusión técnica:** se alcanzó un entorno de **MLOps/GitOps académico ejecutable y reproducible**, con criterios de aceptación verificables. Se documenta una trayectoria razonable hacia la industria, pero no se afirma que la implementación sea ya una solución industrial certificada.

---

## 12. Conclusiones estratégicas

1. **Valor técnico:** el proyecto superó la etapa de entrenamiento aislado y demuestra un proceso controlado para generar y ejecutar versiones evaluadas de un modelo.
2. **Confiabilidad:** el laboratorio demuestra la recuperación de una versión previa del modelo ante una regresión de servicio. La siguiente dificultad industrial es mantener consistencia de datos y habilitar despliegue resiliente con estado compartido.
3. **Gobernanza:** el hash, la trazabilidad MLflow, los tests de etiquetas y gates hacen auditable qué se entrenó y qué se ejecutó. Sin aprobación y datos reales no constituyen un certificado de calidad.
4. **Costos y escalabilidad:** la arquitectura propuesta debe contrastar costo total con SLO real. Los escenarios FinOps son herramientas de decisión, no presupuestos confirmados.
5. **Decisión de negocio:** antes de operar en una planta, la siguiente inversión prioritaria debe enfocarse en calidad de datos industriales, seguridad, persistencia robusta, ensayos de falla y una prueba controlada de reducción neta de paros.

---

## Referencias técnicas

- [GitHub Actions — workflow y ejecuciones de Fase III](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/workflows/fase3.yml)
- [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/)
- [Google SRE — Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- [FinOps Framework](https://www.finops.org/framework/phases/)
- [NIST AI RMF](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [ISO/IEC 42001](https://www.iso.org/standard/42001)
- [Ley Federal de Protección de Datos Personales en Posesión de los Particulares — México](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf)

**Nota metodológica final:** las métricas, inferencias y decisiones descritas corresponden a un entorno sintético controlado; la adopción industrial requiere validación externa y supervisión humana.
