# Evidencias visuales — Actividad 8

> **Origen:** capturas de la ejecución local en Windows, aportadas el 14/11/2026. El sistema, los datos de máquinas y las fallas son **sintéticos**. Las capturas representan el dashboard del laboratorio y no demuestran un servicio cloud 24/7.

## Incidente INC-01 — Latencia HTTP

![INC-01: latencia p95, antes 35.9 ms, durante 689.2 ms, después 37.2 ms, umbral 500 ms](../evidence/screenshots/INC-01_latencia_antes_durante_despues.png)

La captura presenta correctamente la secuencia **Antes → Durante → Después**, con línea discontinua de SLO en **500 ms**. Las cifras precisas y las verificaciones del runbook `RB-LATENCY` se encuentran en [`incidents.json`](../evidence/incidents.json).

## Incidente INC-02 — Data drift

![INC-02: PSI antes 0.071, durante 10.361, después 0.056, umbral 0.20](../evidence/screenshots/INC-02_drift_antes_durante_despues.png)

La gráfica muestra el cambio de distribución inducido y la vuelta a una muestra restaurada, con umbral PSI **0.20**. El runbook documentado es `RB-DRIFT` y su estado se verifica en [`incidents.json`](../evidence/incidents.json).

## Trazabilidad y límites

- Las imágenes son capturas auténticas del dashboard de Streamlit después de la corrección de los ejes. No son visualizaciones reconstruidas para aparentar resultados.
- Los valores son los de la ejecución original del laboratorio registrada en el repositorio; las ejecuciones repetidas pueden variar mínimamente según entorno.
- El código fuente está en [`dashboard.py`](../dashboard.py), el generador de incidentes en [`laboratory.py`](../laboratory.py) y la verificación automática en [`verify.py`](../verify.py).
- Los dos incidentes fueron controlados y sintéticos; el runbook no ejecuta mantenimiento industrial.

## Archivos y huellas de integridad

| Imagen | SHA-256 |
|---|---|
| `INC-01_latencia_antes_durante_despues.png` | `a07f956225868d15143ab0228a66bda17baf623f51188bc2d18f12fb6693c9c5` |
| `INC-02_drift_antes_durante_despues.png` | `c55b5f897356485aeaf0cccbbd9b838f98de2df37b05f3d12d0dcca8c03a2314` |
