# CHANGELOG — Predictive Maintenance AI Fase II

## 2026-10-26 — Primera entrega técnica reproducible
- Instalación y validación de Docker Desktop en Windows 11 (WSL2, Engine running, hello-world y Compose v5.6.1), evidencias de ejecución a incorporar desde PC del estudiante.
- Generador original de datos temporales **100% sintéticos**: 60 máquinas × 2,160 instantes = 129,600 lecturas, intervalo de 6h, 318 fallas simuladas y mantenimiento/reparación.
- Etiqueta real de pronóstico dentro del simulador: falla futura en t+6 a t+72 horas; fallas presentes/paro fuera del ajuste; censura correcta de las 12 últimas ventanas.
- Particiones temporales con purga de 72h, grupo de 12 máquinas excluidas del entrenamiento, modelo Random Forest y umbral fijado en validación.
- Se publicaron métricas reales del simulador y pruebas de eventos con anticipación, sin afirmar validez industrial.
- Se implementaron FastAPI, contratos OpenAPI, Streamlit, SQLite persistente, Dockerfiles y Compose.
- Las pruebas integradas con Docker real y HTTP en GitHub Actions quedaron aprobadas; se verificaron errores 404/422 y lectura/escritura SQLite.
- Dos reportes PDF automáticos, inspeccionados: **Manual_Despliegue_Nube_FaseII.pdf** (5 páginas) y **Documento_Validacion_Pruebas_FaseII.pdf** (5 páginas).
- Se automatizó la incorporación opcional de capturas **auténticas de Windows** al documento de validación; aún deben capturarse localmente.
- Declaración de apoyo de ChatGPT en README, sin atribuirle mediciones no ejecutadas.

## Pendiente para cierre
1. Clonar desde GitHub Desktop en la PC del estudiante y ejecutar `docker compose up --build -d --wait`.
2. Verificar navegador en puertos 8501/8000, realizar una inferencia y comprobar historial.
3. Subir capturas auténticas `Docker_Containers.png` y `Dashboard_Piloto.png`.
4. Comprobar regeneración del documento PDF con las capturas y auditoría de rúbrica.
5. Entregar **únicamente URL de este repositorio**, no ZIP.

**Limitación central:** el valor del modelo se validó solo dentro de un simulador programado de degradación. Se requiere validación industrial prospectiva para usos de producción.
