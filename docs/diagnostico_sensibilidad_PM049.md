# Diagnóstico de sensibilidad del modelo de falla a 72 horas — máquina PM-049

**Estado:** análisis ejecutado en Docker por el estudiante, 26 de octubre de 2026. **Datos:** 100 % sintéticos. **Modelo:** RandomForestClassifier, horizonte de 72 horas. **Archivo de prueba:** `tests/sensitivity_whatif.py`.

## Objetivo
Determinar cómo cambia la salida de un modelo de clasificación ante alteraciones hipotéticas de temperatura, vibración y desgaste de PM-049. La prueba usa el modelo serializado efectivamente desplegado y el `pilot_snapshot.json`. Invoca `predict_proba` **sin llamar al endpoint POST /predict ni insertar registros en SQLite**.

## Resultados de escenarios

| Escenario | Cambios respecto a la observación original | Probabilidad 72 h | Cambio (puntos porcentuales) | Clasificación |
|---|---|---:|---:|---|
| Original | Ninguno | 51.55 % | 0.00 | MEDIO |
| Temperatura alta | 110 °C | 46.35 % | −5.20 | MEDIO |
| Vibración alta | 8 mm/s | 46.00 % | −5.54 | MEDIO |
| Desgaste alto | 0.99 | 54.40 % | +2.85 | MEDIO |
| Tres sensores severos | 110 °C, 8 mm/s, 0.99 | 47.64 % | −3.91 | MEDIO |
| Primer escenario manual | 53.5 °C, 3.3 mm/s, 0.57 | 35.03 % | −16.52 | MEDIO |

**Nota:** valores presentados con dos decimales; el cálculo original opera con mayor precisión. Los descensos de las variables no equivalen a una mejora demostrada de condición real.

## Barridos univariables

Las otras 11 variables se conservaron sin modificar para aislar cambios en la entrada.

| Temperatura (°C) | Probabilidad |
|---:|---:|
| 50 | 44.91 % |
| 60 | 44.91 % |
| 70 | 51.92 % |
| 80 | 46.35 % |
| 90 | 46.35 % |
| 100 | 46.35 % |
| 110 | 46.35 % |

**Descensos al incrementar temperatura:** 1.

| Vibración (mm/s) | Probabilidad |
|---:|---:|
| 0.5 | 47.03 % |
| 1 | 50.24 % |
| 1.5 | 50.08 % |
| 2 | 46.00 % |
| 3 | 46.00 % |
| 4 | 46.00 % |
| 6 | 46.00 % |
| 8 | 46.00 % |

**Descensos al incrementar vibración:** 2.

| Índice de desgaste | Probabilidad |
|---:|---:|
| 0.40 | 16.42 % |
| 0.55 | 42.34 % |
| 0.65 | 51.42 % |
| 0.75 | 54.40 % |
| 0.85 | 54.40 % |
| 0.95 | 54.40 % |
| 0.99 | 54.40 % |

**Descensos al incrementar desgaste:** 0 en los puntos evaluados.

## Interpretación técnica y hallazgo

1. **La inferencia es funcional**, pero el Random Forest convencional no obliga a que la predicción sea monótona respecto a ninguna variable.
2. En `src/simulation.py`, los eventos sintéticos de falla se generan mediante una función de peligro vinculada principalmente a desgaste, carga y vulnerabilidad de cada equipo. Temperatura y vibración se correlacionan con desgaste en los datos generados, pero **no son causas directas en esa fórmula**.
3. El endpoint what-if de `app/api.py` sobrescribe los sensores manuales y conserva otras características. Por ejemplo, `temperature_avg_24h`, `vibration_avg_24h` y `wear_delta_72h` permanecen intactas. Por tanto, un salto brusco en lecturas instantáneas puede crear entradas sintéticamente incoherentes con su propia historia.
4. Los valores extremos pueden quedar fuera de la distribución de entrenamiento. Este diagnóstico no midió distancia a la distribución original ni cuantificó qué fracción de entradas es fuera de dominio, por lo que **no afirmamos que estos escenarios estén formalmente clasificados como OOD**.
5. Una caída de probabilidad ante el empeoramiento de un sensor **no debe presentarse como evidencia de reducción real de riesgo**, ni el resultado what-if como efecto causal.

## Decisión técnica para la Fase II

- **Conservar el modelo original para mantener trazabilidad** de las métricas, la definición de etiqueta y la evidencia académica existente.
- **No reentrenar únicamente para obtener una respuesta intuitiva**. Sería necesario formular un experimento nuevo con reglas de generación, cambios coherentes en características históricas, y nuevas métricas de prueba temporal y de máquinas no vistas.
- Mantener el dashboard como **demostración exploratoria**, con advertencia explícita sobre la interpretación what-if.
- Si se plantea una Fase III o una mejora del experimento, diseñar escenarios temporalmente consistentes, verificar representatividad de las entradas frente al entrenamiento y evaluar monotonicidad/estabilidad/calibración en conjunto, sin perder de vista falsos positivos y detección temprana.

## Conclusión

El módulo de simulación what-if supera pruebas de ejecución e integración, pero **no supera una validación de respuesta monótona para temperatura o vibración**. La clasificación y la probabilidad no demuestran capacidad industrial real. Este resultado se conserva como limitación técnica reproducible del piloto académico.

**Fuentes internas:** `src/simulation.py`, `app/api.py`, `artifacts/model_metadata.json`, `results/evaluation.json`, `results/feature_importance.csv`, `tests/sensitivity_whatif.py`. Los números anteriores proceden de la salida de PowerShell compartida por el estudiante; no se inventaron ejecuciones adicionales.
