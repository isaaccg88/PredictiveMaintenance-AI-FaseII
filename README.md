# Predictive Maintenance AI · Actividad 8 — Observabilidad y gobernanza operativa

**Gestión de Proyectos de Inteligencia Artificial · Tecmilenio · Módulo 3 / Semana 10**  
**Repositorio de entrega:** rama `actividad8-v2-observabilidad` de [PredictiveMaintenance-AI-FaseII](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/tree/actividad8-v2-observabilidad).  
**Código original validado:** [Fase II, rama `main`](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/tree/main).

> **TRANSPARENCIA ACADÉMICA:** empresa, 60 máquinas, sensores, fallas y predicciones son sintéticos. Los escenarios de incidente están inyectados deliberadamente en el laboratorio. Esto NO implica evidencia de desempeño industrial real, detección de fallas reales ni despliegue cloud permanente. La decisión de mantenimiento es siempre humana.

## Resumen ejecutivo

Se amplió el piloto Predictive Maintenance AI con un generador sintético V2, modelo Random Forest de horizonte 72 h, API FastAPI instrumentada, bitácoras JSONL, trazas correlacionadas (`trace_id` entre HTTP, inferencia y SQLite), seis reglas de alertas, SLO/error budgets, detección de drift con PSI, dashboard Streamlit, dos incidentes medidos y runbooks cuya recuperación se verifica por nuevas mediciones. GitHub Actions puede reconstruir los resultados sin alterar la versión original.

## 1. Modelo y métricas

- `actividad8/simulator.py`: generador reproducible V2 con 60 máquinas y 853 eventos sintéticos en la ejecución de referencia.
- `actividad8/train_v2.py`: entrenamiento reproducible, separación cronológica y 12 máquinas piloto nunca usadas para ajuste.
- [Resultados medidos V2](actividad8/results/evaluation_v2.json) y [metodología/limitaciones](actividad8/docs/METODOLOGIA.md).

| Métrica | Fase II V1 (generador antiguo) | Actividad 8 V2 (generador nuevo) |
|---|---:|---:|
| Precision en piloto | 16.36% | 72.38% |
| Recall por ventana | 37.50% | 78.28% |
| F1 | 0.2278 | 0.7522 |
| ROC-AUC | 0.8621 | 0.9655 |
| Average Precision | 0.2417 | 0.8144 |
| Recall por evento | 8/11 (72.73%) | 31/35 (88.57%) |
| Falsas ventanas / máquina-semana | 1.55 | 0.75 |

**Nota metodológica crucial:** V1 y V2 tienen mecanismos generadores diferentes; las cifras muestran propiedades de dos laboratorios sintéticos, NO mejoras atribuibles a una comparación justa del mismo algoritmo sobre los mismos datos. No se optimizó con la partición de piloto.

## 2. Criterio 1 — Diseño de monitorización y observabilidad (25 pts)

| Señal | Captura | Objetivo operativo |
|---|---|---|
| Disponibilidad HTTP | `/predict`: estados 2xx/5xx y fallos de cliente | El servicio recibe y procesa solicitudes válidas |
| Latencia p95 | Duraciones reales de peticiones y spans `model.infer` | Entrega oportuna de predicciones |
| Logs estructurados | `actividad8/runtime/events.jsonl` en ejecución | Diagnosticar errores con tiempo UTC y `trace_id` |
| Trazas correlacionadas | eventos `http.request`, `model.infer`, `sqlite.commit` | Seguir inferencia y persistencia |
| Calidad supervisada | AUC, precision, recall, F1 por ventana | Reconocer degradación cuando se conocen etiquetas |
| Data drift | PSI sobre temperatura, referencia vs lote | Detectar desviación de distribución |
| Dashboard | `actividad8/dashboard.py` | Supervisar SLO, estado y episodios |

**Alcance de trazas:** son eventos correlacionados por `trace_id` mediante JSONL y SQLite; no se declara instrumentación OpenTelemetry ni trazas distribuidas completas. **Métricas y logs** se generan en el servicio, mientras que MLflow documenta experimentos de entrenamiento.

## 3. Criterio 2 — SLO, error budget y seis reglas de alerta (25 pts)

Los SLO iniciales de laboratorio son 99% de disponibilidad y 99% de solicitudes válidas exitosas en máximo 500 ms. Para una ventana de 12 solicitudes elegibles, presupuesto de error = 12×(1−0.99) = 0.12 fallos. Una petición fallida agota el presupuesto y lo supera; son ventanas **didácticas y pequeñas**, no un SLO industrial calibrado. Se muestran denominadores y ratio de consumo.

| Regla | Severidad | Umbral | Runbook |
|---|---|---|---|
| API indisponible | P1 | disponibilidad <99% | RB-AVAIL |
| HTTP 5xx | P1 | >1% errores elegibles | RB-AVAIL |
| Latencia elevada | P2 | solicitudes oportunas <99% / p95 de diagnóstico | RB-LATENCY |
| CPU elevada | P2 | CPU >85% sostenido | RB-CAPACITY |
| Data drift | P2 | PSI >0.20 y al menos 100 observaciones | RB-DRIFT |
| Calidad | P2 | AUC <0.75 con etiquetas maduras | RB-QUALITY |

Las seis reglas están configuradas; **no todas se provocan en esta demostración**. Se prueba deduplicación: `EMITTED` → `SUPPRESSED_DUPLICATE` → `RESOLVED` tras corrección. El presupuesto por ventana es un ejercicio de laboratorio y no sustituye ventanas largas de operación real.

Código: [reglas](actividad8/rules.py), [catálogo de runbooks](actividad8/runbooks.py).

## 4. Criterio 3 — Incidentes y runbooks ejecutados (25 pts)

| Caso | Antes | Durante | Después | Evidencia |
|---|---|---|---|---|
| INC-01 Latencia | Peticiones HTTP sanas | Retraso controlado de 650 ms en `/predict`, alerta | Retirar inyección, repetir HTTP y verificar dos ventanas sanas | [Incidentes JSON](actividad8/evidence/incidents.json) |
| INC-02 Drift | PSI de lote normal | Sensor sintético desplazado +14 °C y puesto en cuarentena | Restaurar lote limpio y comprobar PSI <0.20 | [Resumen](actividad8/evidence/summary.json) |

### Evidencias visuales verificadas

Las capturas de la ejecución local muestran el estado del dashboard corregido, con fases cronológicas y límites de alerta explícitos. Consulta la [documentación de evidencias visuales](actividad8/docs/EVIDENCIAS_VISUALES.md), que incluye procedencia, alcance y huellas de integridad.

**INC-01 — Latencia HTTP:** 35.9 → 689.2 → 37.2 ms (límite: 500 ms). [Abrir captura a tamaño completo](actividad8/evidence/screenshots/INC-01_latencia_antes_durante_despues.png).

![Evidencia visual INC-01: p95 antes, durante y después de la inyección controlada de latencia](actividad8/evidence/screenshots/INC-01_latencia_antes_durante_despues.png)

**INC-02 — Data drift:** PSI 0.071 → 10.361 → 0.056 (límite: 0.20). [Abrir captura a tamaño completo](actividad8/evidence/screenshots/INC-02_drift_antes_durante_despues.png).

![Evidencia visual INC-02: PSI antes, durante y después de la restauración del lote sintético](actividad8/evidence/screenshots/INC-02_drift_antes_durante_despues.png)

**Alcance:** las capturas proceden de la ejecución sintética local; no constituyen mediciones de maquinaria real ni certifican un servicio 24/7.

**Los resultados antes/durante/después son medidos por código**, salvo la intervención deliberadamente simulada. El runbook no finge reiniciar un servidor ni escalar contenedores cuando únicamente se elimina una falla del laboratorio. La cuarentena retira un lote sintético del flujo de entrada del laboratorio; no implica una cola industrial persistente.

Revisión: [runbooks explicados](actividad8/docs/RUNBOOKS.md), [motor de simulaciones](actividad8/laboratory.py), [verificador independiente](actividad8/verify.py).

## 5. Criterio 4 — Respuesta automatizada, evidencia y gobernanza (25 pts)

La lógica automatiza la medición, clasificación, supresión de duplicados, respuesta limitada a fallas del laboratorio, verificación con nuevas observaciones y reporte final. Si la recuperación no cumple los criterios, el verificador marca `ESCALATE` y la corrida falla. No se realizan despliegues de modelos nuevos sin aprobación humana.

- [Corridas de GitHub Actions](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/workflows/actividad8.yml) — ejecutar y comprobar el estado **PASS**; no afirmar éxito de CI hasta observar una corrida verde.
- [Workflow fuente](.github/workflows/actividad8.yml) — reentrena, registra MLflow, ejecuta pruebas, levanta FastAPI y Streamlit, inyecta incidentes, verifica resultados y publica un artefacto de evidencia.
- [Resultados reproducibles](actividad8/results/evaluation_v2.json) y [registro de incidentes](actividad8/evidence/incidents.json) — valores de una corrida local; las cifras de CI se regeneran y pueden diferir mínimamente por entorno.
- [MLflow](actividad8/train_v2.py) — corridas con parámetros, métricas y artefactos; los datos de tracking generados se guardan como artefacto de Actions y no como una base permanente compartida.

## 6. Ejecutar localmente (Windows)

Con GitHub Desktop o Git y Docker Desktop instalado:

```powershell
git clone --branch actividad8-v2-observabilidad https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII.git
cd PredictiveMaintenance-AI-FaseII
docker compose -f actividad8/compose.yaml up --build -d --wait
```

- **Dashboard:** http://localhost:8510
- **Swagger:** http://localhost:8008/docs
- **Healthcheck:** http://localhost:8008/health
- **Métricas HTTP:** http://localhost:8008/metrics

Para parar y conservar SQLite: `docker compose -f actividad8/compose.yaml down` (no usar `down -v` para conservar historial). La inyección de fallas queda **deshabilitada por defecto** en Docker de demostración. Para regenerar el experimento completo se usa el workflow de GitHub Actions, sin requisitos locales de Python.

## 7. Cómo se entrega

Este README es el **documento técnico principal** y enlaza toda la evidencia verificable. Repositorio accesible por URL, sin depender de un ZIP para lectura del código. Si la plataforma solicita estrictamente un ZIP, esta rama puede descargarse desde **Code → Download ZIP**. La autorización verbal de omitir PDFs debe confirmarse con el profesor, puesto que la instrucción escrita de la plataforma sigue mencionando esos formatos.

**Nota de distribución del modelo:** el `.joblib` se regenera desde código determinista en el build Docker y en GitHub Actions; no se versiona un binario potencialmente incompatible con otros entornos. Los artefactos de Actions incluyen el modelo regenerado.
