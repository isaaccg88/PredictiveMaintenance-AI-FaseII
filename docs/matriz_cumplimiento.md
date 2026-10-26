# Matriz de cumplimiento — Fase II · Semana 8

**Proyecto:** Predictive Maintenance AI (predicción a 72 horas sobre máquinas sintéticas). **Entrega acordada:** URL del repositorio sin ZIP; mantener ambos PDF.

Esta es una auditoría técnica de los requisitos visibles y los cuatro criterios generales (25 puntos cada uno). No es una calificación oficial; las evidencias faltantes se señalan sin simularlas.

| Criterio evaluado | Evidencia verificable en GitHub | Estado |
|---|---|---|
| 1. Contenerización y ejecución local (25 pt) | Dockerfiles API y web, `compose.yaml`, workflow Docker real en Actions con ambos servicios healthy | **Cumple: CI y ejecución local Docker verificada con capturas; falta adjuntar evidencia al repositorio** |
| 2. Integración frontend/backend (25 pt) | Streamlit consulta API por HTTP, FastAPI con /health /machines /predict /predictions, SQLite con volumen | **Cumple funcionalmente: frontend y API validados localmente; faltan evidencias versionadas** |
| 3. Validación funcional y extremos (25 pt) | Unit tests temporal 72h; HTTP integración real, persistencia, 404/422, pruebas de modelo y métricas | **Pruebas de integración PASS y casos 404/422 comprobados; sensibilidad what-if con limitación detectada y documentada** |
| 4. Documentación y repositorio (25 pt) | README completo, PDF nube, PDF validación, manifiesto, arquitectura, scripts, GitHub Actions | **Documentación existente y diagnóstico de sensibilidad incorporado; falta añadir capturas de ejecución local** |

## Verificación por instrucción
| Instrucción | Ruta |
|---|---|
| Código fuente completo | `src/`, `app/`, `tests/` |
| Dockerfile funcional | `docker/Dockerfile.api`, `docker/Dockerfile.web` |
| Archivos de configuración | `compose.yaml`, `requirements-*.txt`, `.dockerignore` |
| Integración API/endpoints | `app/api.py`, `tests/integration.py`, Swagger |
| Imagen correctamente construida | Logs de workflow `validate-deploy.yml` en Actions |
| Ejecución local comprobable | **Validado con capturas en la conversación; pendiente guardar en GitHub**: `docs/local_evidence/Docker_Containers.png` |
| Manual paso a paso para nube | `docs/Manual_Despliegue_Nube_FaseII.pdf` |
| Requisitos y estrategia PaaS | `docs/manual_deploy_cloud.md` y manual PDF |
| Documentación con IA | Declaración en README y manual |
| Documento de pruebas en PDF | `docs/Documento_Validacion_Pruebas_FaseII.pdf` |
| Pruebas de extremos | `tests/integration.py`, HTTP 404/422 |
| Evidencia frontend operativo | **Validado con capturas en la conversación; pendiente guardar en GitHub**: `docs/local_evidence/Dashboard_Piloto.png` |

## Calidad científica y limitaciones
- Horizonte implementado en código: eventos de falla en (t,t+72h] etiquetados según 12 mediciones posteriores.
- Datos temporales sintéticos, no industriales. La probabilidad no demuestra anticipación en maquinaria real.
- Total sintético: 129,600 lecturas de 60 máquinas; 318 fallas simuladas.
- F1 test temporal 0.2670; F1 de máquinas no vistas 0.2278, precisión del piloto 16.36%. No se sobreinterpreta ROC-AUC.
- Sensibilidad what-if: temperatura/vibración presentaron respuestas no monótonas; desgaste fue no decreciente en el barrido de PM-049. Véase `docs/diagnostico_sensibilidad_PM049.md`. No se demuestra interpretación causal ni comportamiento en equipos reales.
- Event recall del piloto 8/11; número pequeño de eventos. Mantener interpretación prudente.
- No se afirma haber desplegado en PaaS; se documenta estrategia y no se contratan servicios.

## Evidencia de reproducibilidad
Consultar [Actions](https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions) para los tests y artefactos, incluyendo el CSV sintético completo y el registro de Docker Compose; las métricas tienen respaldo en `results/evaluation.json` y `results/model_metrics.csv`.

**Próxima acción del estudiante:** guardar y subir capturas reales de Windows (Docker, dashboard, integración PASS, casos 404/422 y sensibilidad), para que el repositorio y los PDF incluyan evidencia local auténtica. La prueba de sensibilidad no modifica SQLite y no requiere volver a entrenar el modelo para la Fase II.
