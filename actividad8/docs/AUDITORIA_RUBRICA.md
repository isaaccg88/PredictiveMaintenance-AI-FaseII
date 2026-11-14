# Auditoría académica de cierre — Actividad 8

**Materia:** Implementación de Soluciones de Inteligencia Artificial · Módulo 3, Semana 10  
**Caso:** Predictive Maintenance AI, predicción de falla sintética a 72 horas.  
**Fecha de revisión:** 14 de noviembre de 2026.  
**Referencia:** cuatro criterios de la rúbrica (25 puntos cada uno). La puntuación real corresponde al profesor; este documento no es una calificación oficial.

## Dictamen

**Entrega académica implementada y demostrable bajo los límites declarados.** La ejecución de CI más reciente debe consultarse en [GitHub Actions](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/workflows/actividad8.yml). El propósito es demostrar un piloto reproducible de observabilidad y respuesta, no declarar operación industrial ni servicio cloud 24/7.

## Matriz requisito → implementación → evidencia → límite

| Criterio / requisito | Implementación verificable | Evidencia consultable | Límite honesto |
|---|---|---|---|
| **1. Monitorización y observabilidad (25 pts)** | [`service.py`](../service.py) instrumenta /predict, almacena HTTP en SQLite, logs JSONL con `trace_id` y eventos correlacionados `http.request`, `model.infer`, `sqlite.commit` | [Dashboard](../dashboard.py), ejecución local /metrics y /history, [métricas offline](../results/evaluation_v2.json), artefacto de CI con `runtime/events.jsonl` | Trazas correlacionadas, **no** tracing distribuido OpenTelemetry. Las métricas de calidad son offline y necesitan etiquetas maduras |
| Seguimiento con MLflow | [`train_v2.py`](../train_v2.py) registra 4 parámetros, 15 métricas, 2 artefactos | [Exportación inspeccionada](MLFLOW_EVIDENCIA.md); [auditor `mlflow_audit.py`](../mlflow_audit.py); artefacto descargable de [Actions](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/runs/43649432772) | Tracking store efímero; no hay UI MLflow alojada de forma permanente |
| Detección de drift | [`rules.py`](../rules.py) calcula PSI con muestra mínima de 100; [`laboratory.py`](../laboratory.py) altera telemetría sintética y evalúa el cambio | [INC-02](../evidence/screenshots/INC-02_drift_antes_durante_despues.png), [registro JSON](../evidence/incidents.json) | Se demuestra para temperatura mediante lote controlado, no drift continuo de todas las características |
| **2. Alertas inteligentes (25 pts)** | Seis reglas con severidad P1/P2, condición y runbook en [`rules.py`](../rules.py), motor de deduplicación `AlertState` | [Informe de incidentes](../evidence/incidents.json), [pruebas](../test_activity8.py) y pestaña Alertas y SLO | **Seis reglas configuradas y evaluables; solo dos alertas provocadas** en el laboratorio (latencia y drift) |
| SLO y error budget | Disponibilidad y oportunidad ≥99%; latencia umbral 500 ms; presupuesto de error calculado según tamaño de la ventana | [README](../../README.md), [`rules.py`](../rules.py), [INC-01](../evidence/screenshots/INC-01_latencia_antes_durante_despues.png) | Ventana de 12 solicitudes: didáctica, no una base SRE industrial. Consumo puede exceder 100% |
| **3. Simulación de dos incidentes (25 pts)** | Fallas controladas de latencia HTTP y shift de temperatura; pasos antes/durante/después | [Capturas autenticadas](EVIDENCIAS_VISUALES.md), [incidents.json](../evidence/incidents.json), [summary.json](../evidence/summary.json) | La inyección HTTP solo opera en laboratorio; el lote con drift no alimenta el servicio productivo |
| Ejecución de runbooks | `RB-LATENCY` retira demora y repite mediciones; `RB-DRIFT` aísla lote y restaura fuente validada | [Procedimientos](RUNBOOKS.md), [`runbooks.py`](../runbooks.py), [`laboratory.py`](../laboratory.py) | Respuestas del laboratorio, **no** reinicios de infraestructura, rollback real de modelo ni mantenimiento físico |
| **4. Respuesta automatizada (25 pts)** | Detección, emisión/supresión de alertas, ejecución limitada de recuperación, verificación y decisión `RESOLVED`/`ESCALATE` | [Validador `verify.py`](../verify.py), [workflow](../../.github/workflows/actividad8.yml), [GitHub Actions](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/workflows/actividad8.yml) | Sin despliegue permanente; no hay auto-reentrenamiento ni auto-promoción. Ante incumplimiento se registra escalamiento y falla CI |

## Evidencia cuantitativa principal (referencia local)

**Modelo V2** en 12 máquinas piloto no vistas durante el entrenamiento: precision 72.38%, recall por ventana 78.28%, ROC-AUC 0.9655 y recall por evento 31/35 (88.57%). Se trata de datos **sintéticos** construidos con mecanismos más predecibles que en V1; esas diferencias no son una comparación experimental controlada del modelo.

**INC-01 latencia:** p95 antes 35.9 ms; durante 689.2 ms; después 37.2 ms (objetivo ≤500 ms).  
**INC-02 drift:** PSI antes 0.071; durante 10.361; después 0.056 (límite ≤0.20).  
**Control de alertas:** dos emitidas, una duplicada suprimida, dos cerradas. La ejecución de CI puede mostrar tiempos distintos, ya que mide peticiones HTTP reales en su entorno.

## Comprobaciones técnicas de reproducibilidad

1. [`test_activity8.py`](../test_activity8.py) comprueba etiquetado futuro a 72 h, censura, alertas, PSI y los seis predicados.
2. [`train_v2.py`](../train_v2.py) regenera los datos sintéticos, entrena con partición separada y registra MLflow.
3. [`mlflow_audit.py`](../mlflow_audit.py) coteja experimentalmente el tracking store con el reporte del mismo run.
4. [`laboratory.py`](../laboratory.py) mide HTTP real e inyecta escenarios controlados; también registra los reintentos de calentamiento si los necesita.
5. [`verify.py`](../verify.py) exige los dos runbooks resueltos con comprobaciones, dos alertas y deduplicación.
6. El workflow verifica además que Streamlit **renderice sin excepciones**; no basta un healthcheck.

## Hallazgos y riesgos residuales

- **Prioridad alta antes de implementación industrial:** convertir reglas basadas en ventanas pequeñas en SLO con volumen y periodos representativos, habilitar métricas y trazas centralizadas, monitoreo continuo, alarmas con ciclo de vida persistente y on-call.
- **ML:** validar drift en más variables, asegurar etiquetas reales maduras, evaluar calibración y costo de falsas alarmas por episodio, no solo por ventana. No usar el ROC-AUC sintético como garantía de desempeño fuera del generador.
- **CPU:** la medición de la evidencia es del ejecutor de GitHub Actions, no del contenedor de la API; esta regla demuestra lógica pero no monitorización de capacidad industrial.
- **Gobernanza:** rollback y reentrenamiento solo están **documentados como procedimientos de escalamiento**; no se declara una implementación de despliegue/reversión de modelos.
- **Formato:** el README es el documento principal de la entrega en GitHub. La plataforma originalmente indicó ZIP y documentos; la autorización verbal del profesor sobre entregar solo por GitHub prevalecerá únicamente si efectivamente la acepta para esta actividad. Mantener el repositorio exportable.

## Enlaces de entrega

- [README principal](../../README.md)
- [Documento de metodología](METODOLOGIA.md)
- [MLflow: evidencia de registro](MLFLOW_EVIDENCIA.md)
- [Runbooks](RUNBOOKS.md)
- [Capturas verificadas](EVIDENCIAS_VISUALES.md)
- [Ejecuciones automatizadas](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/workflows/actividad8.yml)

**Resultado de auditoría:** preparado para revisión del profesor como piloto académico, **con limitaciones explícitas**. No es certificación de nivel de servicio en producción ni garantiza una nota.
