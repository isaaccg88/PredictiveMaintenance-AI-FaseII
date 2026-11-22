"""Secciones adicionales de análisis crítico para reporte técnico de maestría."""
from __future__ import annotations
from pathlib import Path
from reportlab.platypus import PageBreak, Image, Spacer
from reportlab.lib.units import cm

def extra_sections(fairness,costs,bench,evaluation,P,H,table,diagram_path):
    s=[PageBreak(),H("APÉNDICE A. Análisis detallado de arquitectura",1),
       P("Los diagramas y escenarios siguientes son propuestas documentadas. Solo el modelo, la API, las mediciones HTTP, la instrumentación y los experimentos sintéticos han sido ejecutados."),
       Image(str(diagram_path),width=17*cm,height=7.6*cm),
       P("Figura A1. Arquitectura actual en Docker local frente al diseño AWS de alta disponibilidad. El rediseño requiere cambios de persistencia, red, identidad, observabilidad y despliegue; no se consigue simplemente añadiendo instancias."),
       H("A.1 Cuellos de botella y mitigaciones",2),
       table(["Componente","Situación actual comprobada","Medida propuesta / dependencia"],[
          ["API de inferencia","Un proceso/contendor por entorno local","Escalar replicas sin estado, healthcheck y pruebas de capacidad"],
          ["Base de datos","SQLite en un volumen local persistente","Migrar a RDS Multi-AZ antes de replicar API; probar concurrencia y migraciones"],
          ["Distribución de carga","Sin ALB, sin zonas de disponibilidad","Balanceo, TLS, 2 zonas, circuit breaking y límites de ingreso"],
          ["MLOps","Modelo versionado y MLflow en CI efímero","Artifact store S3/KMS, registro persistente y aprobación de promoción"],
          ["Observabilidad","HTTP, logs JSONL, trace_id, dashboard","Centralizar métricas, alertas, log retention, on-call y dashboards SLA"],
          ["Gobierno","Humano decide mantenimiento","Políticas de acceso, segregación de funciones, model cards y auditoría"],
       ]),
       H("A.2 Escalabilidad vertical versus horizontal",2),
       P("Vertical: incrementar recursos por tarea puede mejorar inferencia paralela, pero no protege de un fallo de AZ ni elimina limitaciones de base de datos. El benchmark actual no impuso límites CPU/RAM, por lo que NO prueba ganancias verticales."),
       P("Horizontal: agregar réplicas detiene la dependencia de una sola API, pero exige sesiones sin estado, SQL externo, idempotencia, estrategias de canary y distribución real de peticiones. Dos procesos Linux comparten CPU en Actions: ilustran un mecanismo, no cuantifican la elasticidad cloud."),
       P("Decisión arquitectónica: separar inferencia crítica del dashboard administrativo, migrar persistencia, establecer mínimo de dos réplicas por resiliencia y validar tamaños CPU/memoria usando carga representativa antes de seleccionar x86 o ARM."),
       H("A.3 SLA, disponibilidad y recuperación",2),
       P("Objetivos aspiracionales de staging: éxito HTTP >=99%, oportunidad >=99% con latencia <=500ms, 2 zonas de disponibilidad, rollback supervisado y evidencia de failover. No existe SLA contractual ni RTO/RPO probado porque no hay entorno AWS en producción. Se propone definir RTO <=60 minutos y RPO <=15 minutos como hipótesis a validar con ensayos de recuperación y respaldo."),
       PageBreak(),H("APÉNDICE B. Evaluación técnica de rendimiento",1),
       P("Las tablas preservan las 60 solicitudes de cada ventana de carga. El p95 es percentil de respuesta; la oportunidad es el porcentaje de HTTP 2xx en <=500 ms. Para afirmar un SLO de 99% ambos indicadores y el conjunto de respuestas deben ser observados."),
       table(["API","Clientes","N","p50 ms","p95 ms","p99 ms","RPS","Oportunas"],[
        [label,str(x["concurrency"]),str(x["samples"]),
        f"{x['p50_ms']:.1f}",f"{x['p95_ms']:.1f}",f"{x['p99_ms']:.1f}",
        f"{x['throughput_rps']:.1f}",f"{x.get('timely_ratio',0)*100:.1f}%"]
        for label,k in (("1 instancia","single"),("2 instancias","dual"))
        for x in bench[k]["levels"]
       ]),
       H("B.1 Interpretación de los resultados",2),
       Image(str(Path(__file__).resolve().parent/"evidence"/"fig_02_latencia_p95.png"),width=16*cm,height=8.5*cm),
       P("Figura B1. Curva p95: la medición de latencia se compara con el umbral diagnóstico de 500 ms; el umbral aislado no sustituye la comprobación del SLI de oportunidad de 99%."),
       Image(str(Path(__file__).resolve().parent/"evidence"/"fig_03_throughput.png"),width=16*cm,height=8.5*cm),
       P("Figura B2. Throughput: la prueba muestra tasas observadas con uno y dos servidores en el mismo runner, no escalado horizontal real en AWS.")]
    single={x["concurrency"]:x for x in bench["single"]["levels"]}
    dual={x["concurrency"]:x for x in bench["dual"]["levels"]}
    a=single[4];b=dual[4];hi1=single[16];hi2=dual[16]
    s+=[
       P(f"Concurrencia 4: la segunda instancia pasa de {a['throughput_rps']:.2f} a {b['throughput_rps']:.2f} RPS; incremento relativo {(b['throughput_rps']/a['throughput_rps']-1)*100:.1f}%. El p95 cambia de {a['p95_ms']:.1f} a {b['p95_ms']:.1f} ms. No se concluye escalado lineal."),
       P(f"Concurrencia 16: con una API el p95 sube a {hi1['p95_ms']:.1f} ms, incumpliendo el umbral diagnóstico de 500 ms; con dos endpoints se observó {hi2['p95_ms']:.1f} ms. Sin embargo, el resultado dual a concurrencia 8 puede ser peor que a 16 por interferencia y variabilidad del runner: la prueba requiere replicaciones y análisis de intervalos antes de establecer un SLA."),
       H("B.2 Reglas de capacidad y advertencias",2),
       P("La estimación de réplicas se basa en la máxima tasa de una sola instancia que pasó simultáneamente disponibilidad >=99%, oportunidad >=99% y p95 <=500ms. Se añade un factor de pico y una utilización objetivo para reserva. La capacidad ARM se aproxima proporcionalmente a vCPU, una hipótesis a comprobar en instancias ARM reales."),
       P("Métricas de memoria y CPU se recogen del proceso Linux del runner, no de un contenedor Fargate con cgroups ni de un clúster cloud. No se ha probado el throughput sostenido a escala de 60 millones de solicitudes mensuales ni una distribución horaria real."),
       H("B.3 Controles de rendimiento propuestos",2),
       table(["Indicador","Baseline de laboratorio","Objetivo propuesto","Acción ante incumplimiento"],[
         ["Disponibilidad","100% de HTTP 200 en las ventanas medidas","99% de éxito","Comprobar dependencia DB, salud de tareas y rutas"],
         ["Oportunidad","Depende de la concurrencia; ver tabla B","99% <=500 ms","Reducir carga, revisar autoscaling y dependencia DB"],
         ["p95 inferencia HTTP",f"{single[4]['p95_ms']:.1f} ms a concurrencia 4","<=500ms","Reperfilar modelo y límites CPU/RAM"],
         ["Throughput",f"{single[4]['throughput_rps']:.1f} RPS (1), {dual[4]['throughput_rps']:.1f} RPS (2)","Medir capacidad al 50% utilización","Tasar por 1,000 inferencias exitosas"],
       ]),
       PageBreak(),H("APÉNDICE C. FinOps: modelo económico y sensibilidad",1),
       P("Región y moneda: us-east-1, USD. La base computacional utiliza Fargate Linux x86 y ARM y ALB como referencias públicas. Los demás servicios se tratan como supuestos parametrizados. Los escenarios comparten 730 horas por mes y 1 LCU base de ALB no medida."),
       table(["Volumen","Arquitectura","Réplicas","USD/mes","USD/1000"],[
        [x["scenario"],x["architecture_name"],str(x["replicas_estimated"]),
         f"{x['total_usd_month']:.2f}",f"{x['usd_per_1000_requests']:.5f}"]
        for x in costs["estimates"]]),
       H("C.1 Descomposición de costo para 10 millones de solicitudes",2),
       Image(str(Path(__file__).resolve().parent/"evidence"/"fig_04_costos_finops.png"),width=16*cm,height=8.5*cm),
       P("Figura C1. Nueve estimaciones tarifarias: se muestran tres volúmenes y tres arquitecturas; comparar HA x86 frente a HA ARM dimensionada no aísla el efecto del procesador y excluye costos de red y operación.")]
    for x in [y for y in costs["estimates"] if y["scenario"]=="crecimiento"]:
        s.append(P(f"{x['architecture_name']}: API Fargate USD {x['api_ecs_fargate_usd']:.2f}; dashboard {x['dashboard_fargate_usd']:.2f}; ALB {x['alb_usd']:.2f}; DB hipotética {x['db_assumption_usd']:.2f}; monitoreo {x['cloudwatch_assumption_usd']:.2f}; almacenamiento {x['s3_assumption_usd']:.2f}; egreso {x['egress_assumption_usd']:.2f}. Total = USD {x['total_usd_month']:.2f}."))
    s+=[
      H("C.2 Economía unitaria y decisiones",2),
      P("La elección de arquitectura no se debe basar en el mínimo USD/mes bruto: cloud_naive elimina redundancia y puede incumplir el objetivo de continuidad. La comparación de optimización económica responsable es HA x86 vs HA ARM, sujeto a confirmar capacidades, comportamiento bajo fallo y costos de soporte."),
      P("Pruebas de sensibilidad propuestas antes del presupuesto: (a) RDS y backup +50%; (b) duplicar egreso y logs; (c) picos x2 frente a supuesto; (d) 2 zonas con costos de transferencia interzona; (e) arquitectura con NAT y WAF. Las tablas actuales NO incluyen estos gastos, por lo que un comité no debe tratar sus totales como cotización vinculante."),
      P("Gestión FinOps: (Inform) etiquetar por ambiente/proyecto/centro de costos y emitir reporte USD/1000 predicciones; (Optimize) dimensionar tareas y revisar ARM, clases DB y cargas; (Operate) revisión semanal, presupuestos y alerta de sobrecosto, aprobación de compromisos y ajustes de SLA."),
      PageBreak(),H("APÉNDICE D. Fairness y gobernanza responsable",1),
      P("El concepto de fairness de esta actividad se refiere a equidad operacional del algoritmo respecto al tipo de máquina A, B y C. No hay personas, datos sensibles, atributos protegidos ni grupos demográficos en el dataset sintético; no se deben extrapolar estos resultados a decisiones laborales."),
      table(["Grupo","Máquinas","Positivas","TP","FN","FP","TN","TPR","FPR"],[
        [g,str(x["machines"]),str(x["positive"]),str(x["tp"]),str(x["fn"]),str(x["fp"]),str(x["tn"]),
         f"{x['recall_tpr']*100:.1f}%",f"{x['fpr']*100:.1f}%"] for g,x in fairness["groups"].items()
      ]),
      H("D.1 Brechas y precisión estadística",2),
      Image(str(Path(__file__).resolve().parent/"evidence"/"fig_05_fairness_tpr.png"),width=16*cm,height=8.5*cm),
      P("Figura D1. TPR por tipo de equipo: los intervalos bootstrap por máquina se superponen ampliamente, por lo que las diferencias descriptivas no permiten acreditar paridad fuera de esta muestra sintética."),
      P(f"Brecha de recall/TPR = {fairness['gaps']['equal_opportunity_tpr_gap']*100:.2f} puntos porcentuales. Brecha FPR = {fairness['gaps']['false_positive_rate_gap']*100:.2f} puntos porcentuales. La política de revisión propuesta usa 10 puntos porcentuales para TPR, sin convertirlo en criterio de certificación."),
    ]
    for g,x in fairness["groups"].items():
        ci=x.get("tpr_cluster_bootstrap_95ci")
        if ci:
            s.append(P(f"Tipo {g}: recall {x['recall_tpr']*100:.1f}%, intervalo descriptivo bootstrap por 4 máquinas [{ci[0]*100:.1f}%, {ci[1]*100:.1f}%]. Se recomputa por clúster máquina, no tomando ventanas temporales como individuos independientes."))
    s +=[
      P("La muestra solo incluye 4 máquinas por tipo; el bootstrap por tan pocos clústeres puede tener cobertura inestable. No hay datos externos de un sitio industrial, por lo que la auditoría es diagnóstica y no establece ausencia de sesgo ni garantía de seguridad."),
      H("D.2 Controles NIST AI RMF e ISO/IEC 42001",2),
      table(["Función / ámbito","Aplicación en este proyecto","Evidencia / brecha"],[
         ["GOVERN","Definir responsable de calidad, datos, seguridad y excepción","Política y RACI propuestos, sin adopción corporativa"],
         ["MAP","Identificar riesgo de falla falsa/omitida, datos, costos y contexto","Matriz de riesgos y caso sintético"],
         ["MEASURE","Evaluar ROC-AUC, TPR/FPR por tipo, PSI, latencia, costos","Scripts reproducibles, muestra acotada"],
         ["MANAGE","Canary, rollback, registro de incidentes y revisión humana","Procedimientos propuestos, cloud no desplegado"],
         ["ISO 42001","Sistema de gestión, proceso de mejora y control documental","Marco de referencia, NO certificación"],
      ]),
      H("D.3 Marco legal y privacidad",2),
      P("La LFPDPPP de México es relevante si una futura solución ingiere información de operadores, turnos o identificadores ligados a trabajadores. Deben evaluarse finalidades, legitimación, transferencias, conservación, acceso y seguridad con asesoría jurídica antes de pasar a datos reales. Con sensores simulados sin personal identificable, la entrega no demuestra cumplimiento de una organización real."),
      PageBreak(),H("APÉNDICE E. Roadmap y decisiones de gobierno",1),
      table(["Hito","Responsable A/R","Evidencia requerida","Riesgo mitigado"],[
         ["Baseline y carga","SRE / Product Owner","p95/p99, throughput, éxito y errores de CI","Dimensionamiento"],
         ["Datos y privacidad","Security + Legal","Inventario, minimización y controles IAM","Exposición o uso indebido"],
         ["Migrar SQLite","Backend lead","Pruebas concurrentes y esquema RDS","Inconsistencia entre réplicas"],
         ["Staging multizona","SRE + FinOps","Fallo de AZ, costo revisado y recuperación","Disponibilidad y presupuesto"],
         ["Validar fairness","ML Lead","Muestras por sitio/tipo y revisión de TPR/FPR","Riesgos de omisión"],
         ["Canary/rollback","SRE + ML Lead","Aprobación, criterios y trazas de versión","Degradación silenciosa"],
         ["Operación supervisada","Product Owner","SLA reales, costos, incidentes y auditorías","Escalado sin control"],
      ]),
      H("E.1 Puertas de no-go y evidencia mínima",2),
      P("No-go si: no se cumple 99% de oportunidad y disponibilidad bajo carga/ambiente relevante, el costo total supera presupuesto aprobado, no hay responsable humano de alertas, faltan controles de privacidad cuando apliquen, ni se ha probado restauración y rollback del sistema completo. Al completar mitigaciones, el responsable de negocio valida riesgo residual por escrito."),
      H("E.2 Riesgos residuales",2),
      P("El mayor límite de inferencia es el generador sintético V2: el modelo reconoce relaciones diseñadas y puede fallar bajo nuevos regímenes reales de sensores. El modelo de costos presupone precios/instancias de us-east-1 y omite partidas potencialmente relevantes; su riesgo es subestimar TCO. El benchmark local comparte CPU y red, por lo que no es una prueba de escalado real."),
      H("E.3 Conclusiones ejecutables",2),
      P("Se recomienda un piloto de staging de duración limitada y presupuesto acotado, no un despliegue productivo inmediato. La primera aprobación debe exigir una arquitectura sin estado, persistencia externa, métricas reales en contenedor, presupuesto AWS Calculator, ensayo de fallo de AZ y revisión de fairness sobre máquinas suficientes. Cualquier afirmación de ROI/HA debe depender de datos observados."),
      H("Bibliografía principal",2),
      P("AWS Fargate https://aws.amazon.com/fargate/pricing/ · AWS ELB https://aws.amazon.com/elasticloadbalancing/pricing/ · AWS RDS https://aws.amazon.com/rds/postgresql/pricing/ · FinOps https://www.finops.org/framework/phases/"),
      P("NIST AI RMF https://airc.nist.gov/airmf-resources/airmf/5-sec-core/ · ISO/IEC 42001 https://www.iso.org/standard/42001 · LFPDPPP https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf")
    ]
    return s
