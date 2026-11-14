# Diseño de alertamiento y respuesta automatizada — Actividad 8

**Ámbito:** laboratorio académico con FastAPI y datos sintéticos. No hay intervención sobre maquinaria, redes industriales, ni despliegue de modelos en nube.

## 1. Ciclo operativo implementado

1. **Medir:** cada `POST /predict` produce tiempo HTTP, código de respuesta, `trace_id`; FastAPI registra spans `model.infer` y `sqlite.commit` en JSONL y SQLite.
2. **Comparar con SLO:** el laboratorio toma ventanas medibles de al menos 10 solicitudes. Umbrales de oportunidad 99% y disponibilidad 99%; plazo objetivo ≤500 ms.
3. **Detectar:** [`rules.py`](../rules.py) configura seis predicados P1/P2. La demo genera incidencias efectivas de latencia y drift.
4. **Deduplicar:** `AlertState` emite una alerta en la transición normal→activa, suprime alertas idénticas mientras permanece activa y registra resolución al recuperarse.
5. **Responder:** [`laboratory.py`](../laboratory.py) retira la demora de prueba en el caso de latencia o aísla un lote alterado de telemetría en el caso de drift. Estas respuestas están limitadas al laboratorio.
6. **Verificar:** se ejecutan nuevas peticiones HTTP, dos ventanas saludables consecutivas y una nueva evaluación de PSI; [`runbooks.py`](../runbooks.py) produce `RESOLVED` únicamente con comprobaciones verdaderas.
7. **Bloquear un resultado incorrecto:** [`verify.py`](../verify.py) falla la corrida si faltan dos incidentes, si el runbook no resuelve o si no hay trazas de alertas y supresión.

Los [resultados en JSON](../evidence/incidents.json) y [capturas del dashboard](EVIDENCIAS_VISUALES.md) permiten comprobar las transiciones. El laboratorio no opera de manera continua cuando GitHub Actions termina.

## 2. Matriz de decisión: automático vs. supervisado

| Condición | Acción automática real | Acción supervisada / no implementada |
|---|---|---|
| Latencia anormal controlada | Detectar, alertar, suprimir duplicados, retirar el retraso inyectado, repetir medición y cerrar si se verifica | Escalar si hay problemas de red, CPU o almacenamiento reales |
| Data drift controlado | Calcular PSI, retirar el lote sintético alterado, restaurar lote validado y repetir cálculo | Investigar calidad de sensores, aprobar cambios de preprocesamiento |
| Error HTTP o indisponibilidad | Regla y runbook de diagnóstico configurados; pruebas unitarias de disparo | Reinicio de servicios real o despliegue de recuperación, sin demostración funcional |
| CPU elevada | Regla de umbral evaluable y runbook de capacidad | Escalamiento de recursos real, no implementado |
| Degradación supervisada del modelo | Regla de AUC mínimo configurada para conjuntos con etiquetas maduras | Reentrenamiento, promoción y rollback real; aprobación humana obligatoria |

**Reglas configuradas ≠ incidentes provocados.** En esta entrega se provocan y resuelven dos incidentes: latencia y drift. En las demás reglas se comprueba su lógica, no una secuencia de recuperación completa. La medición de CPU del laboratorio corresponde al ejecutor del workflow, no al contenedor del servicio.

## 3. Procedimiento gobernado de reentrenamiento (documentado, no ejecutado automáticamente)

**Disparador candidato:** AUC bajo 0.75 sobre muestras con etiquetas maduras y representativas, con revisión de drift, cobertura, fechas de observación y costos de falsas alertas.

1. Validar que las etiquetas se conocen y no se mezclan predicciones sin resultado con verdaderos eventos.
2. Investigar cambios de distribución y detectar datos incompletos/anómalos; poner lotes bajo cuarentena cuando sea necesario.
3. Preparar nuevo conjunto aprobado y registrar versión, procedencia, semillas, variables, ventana y criterios de aceptación.
4. Entrenar un **modelo candidato aislado** y registrarlo en MLflow. Mantener inalterada la versión activa.
5. Comparar con la versión estable utilizando un conjunto común de evaluación, sin usar el piloto de prueba para seleccionar el candidato.
6. Requerir aprobación del responsable de ML antes de promover la versión y supervisar SLO y métricas tras la promoción.

**La automatización implementada en Actividad 8 llega hasta la evaluación y documentación de una versión sintética, no a este flujo de promoción.** No afirmar que se ha recuperado precisión en producción por simplemente restaurar un lote.

## 4. Procedimiento gobernado de rollback (documentado, no ejecutado automáticamente)

**Disparador candidato:** un despliegue de modelo aprobado degrada significativamente SLO, compatibilidad de features, integridad o calidad frente a la versión estable.

1. Detener nuevas promociones y conservar trazas, versión activa, configuración, incidente, datos y esquema usados.
2. Identificar la última versión validada (modelo y preprocesamiento deben ser compatibles), con hash y métricas verificadas.
3. Realizar rollback **solo mediante canal autorizado** con aprobación humana en esta arquitectura conceptual.
4. Validar healthcheck, inferencia, contratos de API, coherencia de probabilidades y de persistencia SQLite.
5. Reabrir el incidente si la recuperación no se sostiene; documentar análisis causal y acciones preventivas.

El repositorio **no contiene una implementación operativa de rollback de una versión desplegada**. Esta sección responde a la exigencia de documentar mecanismos de recuperación, sin inventar su ejecución.

## 5. Cómo gestionar el error budget

Los presupuestos actuales son de demostración. Para una ventana de 12 solicitudes elegibles y SLO 99%, el presupuesto corresponde a 0.12 fallos equivalentes. Una sola solicitud incumplida agota y supera dicho presupuesto. Se documentan numerador, denominador y porcentaje consumido; no equivale a un sistema de alertas de burn-rate calibrado para un servicio con cientos de miles de solicitudes.

En una implantación real, definir ventanas de duración adecuada, condiciones sostenidas, niveles de alerta, seguimiento de consumo de presupuesto y notificación a responsables de guardia.

## 6. Evidencia

- [Reglas ejecutables](../rules.py)
- [Registro histórico de incidentes](../evidence/incidents.json)
- [Runbooks y comprobaciones](RUNBOOKS.md)
- [GitHub Actions](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions/workflows/actividad8.yml)
- [Auditoría de rúbrica](AUDITORIA_RUBRICA.md)
