# Runbooks de Actividad 8 — Predictive Maintenance AI

**Alcance:** entorno académico con datos y fallas 100% sintéticos. El sistema no inicia intervenciones físicas. El propietario de la decisión de mantenimiento sigue siendo humano.

| ID | Condición | Prioridad | Responsable | Respuesta permitida | Cierre exigido |
|---|---|---|---|---|---|
| RB-LATENCY | SLO de respuestas oportunas <99% | P2 | SRE | Identificar el `trace_id` y retirar demora de laboratorio; repetir HTTP | Dos ventanas HTTP sanas, con p95 medido |
| RB-DRIFT | PSI >0.20 y n≥100 | P2 | Ing. ML | Poner en cuarentena lote sintético y restaurar lote validado | PSI de lote nuevo <0.20, sin emitir predicciones sobre lote en cuarentena |
| RB-AVAIL | Disponibilidad <99% o errores 5xx >1% | P1 | SRE | Retirar falla controlada, revisar `/health` y repetir `/predict` | Servicio y peticiones recuperados; evitar duplicados |
| RB-CAPACITY | CPU >85% persistente | P2 | SRE | Diagnóstico, escalamiento humano | Nueva medición bajo umbral o escalamiento documentado |
| RB-QUALITY | AUC <0.75 con etiquetas maduras | P2 | ML Lead | Validar etiquetas, estudiar drift y probar candidato | Solo promover con revisión humana y evaluación adecuada |

## INC-01 — Latencia elevada

1. Verificar `GET /health` y una muestra de peticiones HTTP reales de `/predict`.
2. Inyectar retraso SOLO con `LAB_MODE=1`, `LAB_TOKEN` y loopback; nunca exponer esto a Internet.
3. Calcular disponibilidad, latencia p95 y error budget a partir de tiempos medidos.
4. Emitir una alerta activa; ante repetición, suprimir duplicado sin esconder nuevas métricas.
5. El runbook retira el encabezado de prueba, hace nuevas peticiones y comprueba dos ventanas normales.
6. Si la latencia persiste, registrar `ESCALATE` en lugar de declarar éxito.

## INC-02 — Data drift

1. Calcular PSI sobre una referencia de sensores sintéticos históricos, con al menos 100 observaciones en ambas muestras.
2. Crear lote con temperatura perturbada, separado del flujo operativo normal.
3. Si PSI supera 0.20, emitir alerta, registrar el tamaño del lote y ponerlo en cuarentena.
4. No utilizar ese lote para inferencias operativas mientras se investiga.
5. Restaurar un lote sintético validado y calcular nuevamente PSI.
6. Solo cerrar cuando PSI vuelve a <0.20; de lo contrario escalar al responsable del modelo.

**Advertencia:** la recuperación por corrección de entradas no demuestra que un modelo reentrenado recupere desempeño en datos futuros. El cambio de versión debe pasar evaluación separada y aprobación humana.
