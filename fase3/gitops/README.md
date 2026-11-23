# GitOps — estado deseado de dos versiones de modelo

El pipeline de Fase III materializa el estado declarativo `desired-state.json` después de construir **dos modelos diferentes**, comprobar sus SHA-256, evaluar sus indicadores, desplegar ambos contenedores y registrar un rollback comprobado por solicitudes HTTP reales.

La versión `stable` contiene Random Forest de 130 árboles y la versión `candidate` contiene 135 árboles entrenados con `warm_start` sobre la misma partición. La candidata puede promoverse solo cuando pasa controles offline y smoke. Una degradación intencional de latencia del servicio candidato permite demostrar que el router vuelve al **SHA del modelo estable anterior** y recupera predicciones válidas.

El estado final se conserva en Git como evidencia. La reconciliación ocurre dentro de un runner efímero; no se afirma que exista un operador externo monitorizando Git de forma continua, una infraestructura de producción o un despliegue multizona.

[Leer arquitectura y evidencias verificables](../../README.md#4-gitopscd-despliegue-promoción-incidente-y-recuperación).
