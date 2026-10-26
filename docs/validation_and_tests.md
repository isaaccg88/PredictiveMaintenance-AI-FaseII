# Protocolo de validación y pruebas — Modelo predictivo a 72 h

## 1. Contexto
Piloto académico de 12 máquinas ficticias no vistas por el modelo, dentro de un universo simulado de 60. La generación no utiliza observaciones industriales reales. **Nunca afirmar precisión de producción o anticipación industrial demostrada.**

## 2. Definición de evento futuro
La etiqueta en (máquina m, instante t) es positiva si ocurre al menos un evento de falla durante las **12 lecturas posteriores** (t + 6 h a t + 72 h). La falla presente en t queda excluida y los instantes con máquina detenida se eliminan del entrenamiento. Los últimos 12 registros no disponen de futuro observado y se censuran (no se suponen negativos). El código construye el objetivo a partir de eventos sintéticos creados con degradación y ruido estocástico.

## 3. Particiones y prevención de fuga
- Generación determinista, semilla 202608; 60 máquinas x 2,160 lecturas cada una = 129,600 registros brutos.
- Modelado sobre máquinas M001 a M048. Se separa train hasta aproximadamente el 65% de la historia; validación hasta el 80%; test temporal posterior.
- Purga de 12 lecturas (~72 h) entre train y validación y entre validación y test para evitar que la etiqueta mire dentro de la partición siguiente.
- Máquinas PM-049 a PM-060 se excluyen **por completo** del ajuste y selección de umbral. Solo forman el piloto OOD de 12 equipos en periodo final.
- Las características de promedio 24 h y variación 72 h se calculan exclusivamente a partir de lecturas presentes o anteriores; no hay variables derivadas de futuras fallas.
- Umbral se selecciona con F2 en validación y restricción de precisión mínima del 20%, si se puede satisfacer. Test temporal y piloto OOD no se usan para seleccionar umbral.
- Se evalúan métricas por ventana de 6 h y por evento distinto de falla, incluyendo tasa de alertas falsas por máquina/semana y anticipación media.

## 4. Pruebas de ciencia de datos
| ID | Prueba | Criterio de aceptación |
|---|---|---|
| D01 | Cronología | Monótona por máquina y espaciada exactamente 6 horas |
| D02 | Horizonte | Etiqueta igual a existencia de evento futuro en t+1..t+12, nunca t |
| D03 | Censura | Últimas 12 lecturas de cada máquina con etiqueta ausente |
| D04 | Estado | Filas con máquina parada o en falla no entran al entrenamiento |
| D05 | Independencia OOD | PM-049..PM-060 nunca aparecen en train ni validación |
| D06 | Purga temporal | train precede val; val precede test; gap 12 pasos |
| D07 | Baseline | Probabilidad constante según prevalencia para comparar AP |
| D08 | Métricas | Precision, recall, F1/F2, ROC-AUC, AP y matriz de confusión |
| D09 | Anticipación | Eventos capturados usando alertas emitidas dentro de 72 horas anteriores, no del momento de falla |
| D10 | Persistencia | Artefacto model.joblib serializado y verificado con predicciones HTTP |

## 5. Pruebas del sistema integrado
| ID | Acción | Respuesta esperada |
|---|---|---|
| I01 | GET /health | 200; model_loaded true; database ok |
| I02 | GET /machines | Lista de exactamente doce máquinas piloto |
| I03 | POST /predict PM-049 | 200; probabilidad entre 0 y 1; horizonte 72; ID de registro |
| I04 | GET /predictions | Nuevo registro SQLite observable |
| I05 | POST /predict con sensores hipotéticos | 200; escenario distinguible de lectura simulada original |
| I06 | Máquina no perteneciente al piloto | HTTP 404 |
| I07 | Desgaste mayor que 1, temperatura bajo límite | HTTP 422 |
| I08 | Campo de entrada que no forma parte del contrato | HTTP 422 |
| I09 | GET http://localhost:8501/_stcore/health | HTTP 200 en frontend |
| I10 | Docker Compose | Dos servicios sanos en contenedores reales, volumen persistente |

## 6. Casos extremos adicionales de mantenimiento
- Vibración muy alta y desgaste 0.99: aceptar si está dentro de rangos declarados, sin prometer un resultado de probabilidad exacto.
- Máquina ausente: rechazar con 404, nunca inventar telemetría.
- Temperatura fuera de rango físico: rechazar con 422.
- Datos faltantes o estructura errónea: 422.
- Historial SQLite: verificar que reiniciar o detener contenedores sin eliminar el volumen no borra registros.

## 7. Evidencia mínima para documentación final
1. Salida del workflow exitoso y artefacto con CSV completo, manifiesto SHA256 y resultados.
2. `results/model_metrics.csv`, `results/evaluation.json`, PR curves y matrix de confusión.
3. Screenshot real de Docker Desktop con los contenedores de `docker compose ps` operando.
4. Screenshot real del dashboard y predicción de PM-049 a 72 horas.
5. Swagger `/docs` y datos persistidos `/predictions`.
6. Resumen verificable de casos extremos I06-I08.

## 8. Limitaciones y alcance de la interpretación
La generación de fallas se basa en una ecuación de desgaste definida por el equipo del proyecto. Un Random Forest puede aprender esa relación artificial; una alta métrica sobre test simulado **no equivale a efectividad fuera del simulador**. Necesitaríamos datos industriales reales, revisión operacional, distintas plantas, modelos de confiabilidad y validación prospectiva de alertas antes de desplegar para mantenimiento productivo.

## 9. Uso de IA
ChatGPT asistió en diseño del modelo temporal, implementación, pruebas, integración Docker/API/frontend y redacción. GitHub Actions ejecuta las pruebas; el estudiante verifica capturas locales auténticas.
