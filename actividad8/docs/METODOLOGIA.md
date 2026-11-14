# Metodología, trazabilidad y límites del modelo V2

## Origen

Se preserva Fase II en `main`. La rama `actividad8-v2-observabilidad` contiene un nuevo generador sintético, nuevas evaluaciones y un laboratorio de observabilidad en FastAPI. No se afirma validez pronóstica en plantas reales.

## Generación

- 60 máquinas (48 para entrenamiento/validación/prueba temporal y 12 excluidas de ajuste).
- 2,160 lecturas por máquina (cada seis horas), objetivo `failure_next_72h`.
- Falla dentro de `t+6` hasta `t+72 h`; el evento en `t` no es futuro. Últimas 12 observaciones censuradas.
- Diferentes modos de falla: desgaste, térmica, vibración y eventos imprevistos. Las señales precursoras imperfectas se simulan antes de algunas fallas, no en todas. Hay falsas anomalías sin evento.
- El simulador programa eventos latentes y genera sensores correlacionados con el deterioro; **esto vuelve el escenario V2 más predecible que V1**. Ninguna variable de entrada revela explícitamente la cuenta regresiva ni contiene el evento futuro. Este mecanismo sintético no debe interpretarse como relación industrial validada.

## Separación y selección

- Cortes temporales con purga de 12 pasos de seis horas.
- Entrenamiento con 48 máquinas; piloto PM-049 a PM-060 completamente excluido del ajuste.
- Imputación y codificación ajustadas dentro del `Pipeline` exclusivamente a entrenamiento.
- Umbral seleccionado solamente en validación maximizando F2 entre umbrales que alcanzan al menos 35% de precision; no se utiliza la partición de prueba ni el piloto para elegir el umbral.
- Es importante distinguir recall por ventana de recall por episodio/evento y falsos positivos en ventanas frente a avisos deduplicados.

## Comparabilidad y gobernanza

V1 y V2 provienen de **generadores diferentes**. Sus métricas no constituyen una evaluación controlada de mejora de un algoritmo sobre un dataset común. Las mejoras en precision, recall y AUC reflejan en buena medida las nuevas relaciones estadístico-sintéticas; un modelo no garantiza ese desempeño sobre otros procesos.

El propósito de la Actividad 8 es monitorear la **operación del servicio de IA**: tiempos HTTP, errores, trazas de inferencia/SQLite, distribución de sensores y calidad cuando existen etiquetas maduras. Las alertas de riesgo de falla física permanecen separadas de los incidentes del software. La promoción de modelos y cualquier mantenimiento físico requiere revisión humana.

## Registros temporales

Los timestamps de telemetría son de un reloj **simulado**, no tiempo actual. Las solicitudes HTTP y runbooks usan UTC real. Nunca mezclar ambos en medidas de frescura.

## Reproducibilidad

`python -m actividad8.train_v2 --mlflow` genera artefactos, métricas y MLflow. `python -m actividad8.laboratory` ejecuta fallas controladas contra una API local. `python -m actividad8.verify` rechaza resultados sin evidencia de dos respuestas verificadas.
