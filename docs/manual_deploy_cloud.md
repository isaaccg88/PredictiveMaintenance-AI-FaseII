# Manual de despliegue local y preparación para la nube — Fase II

**Ámbito:** entorno académico simulado; no garantiza mantenimiento predictivo industrial real. Fecha de documentación: 26 de octubre de 2026.

## 1. Componentes
- **Frontend:** Streamlit, puerto 8501. En Docker llama al backend por la red interna `http://api:8000`.
- **Backend:** FastAPI, puerto 8000, contrato OpenAPI en `/docs`.
- **Modelo:** `artifacts/risk72h_model.joblib` (RandomForest creado con datos SINTÉTICOS).
- **Datos piloto:** `artifacts/pilot_snapshot.json`, exactamente doce máquinas PM-049 a PM-060 nunca incluidas en el ajuste del modelo.
- **Persistencia:** SQLite `/state/predictions.sqlite`, protegida mediante volumen nombrado Docker `prediction_state`.
- **Orquestación:** `compose.yaml` y `docker/Dockerfile.{api,web}`.

## 2. Precondiciones del anfitrión (Windows 11)
1. Docker Desktop con WSL 2 y el motor Docker **Engine running**.
2. Ejecutar correctamente `docker run --rm hello-world` y `docker compose version`.
3. Conexión a Internet para la primera descarga de imágenes Python y dependencias.
4. Puertos locales **8000 y 8501** libres; red local y volumen persistente.
5. No instalar Python en Windows para ejecutar los contenedores: Python se instala dentro de imágenes.
6. GitHub Desktop o Git para clonar el repositorio.

## 3. Despliegue local reproducible
```powershell
git clone https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII.git
cd PredictiveMaintenance-AI-FaseII
docker compose up --build -d --wait
docker compose ps
```

**Nota:** los artefactos ML se publican automáticamente **tras superar** el workflow de entrenamiento y Docker. Si el modelo todavía no existe, el build de API fallará como control intencional. Para generar manualmente el modelo (con Python 3.11, en otro entorno) utilizar `pip install -r requirements-train.txt; python -m src.train`.

Acceso:
- Dashboard: http://localhost:8501
- Swagger/OpenAPI: http://localhost:8000/docs
- Salud: http://localhost:8000/health
- Listado: http://localhost:8000/machines
- Solicitud de evaluación `POST /predict`: `{"machine_id":"PM-049"}`.
- Historial: http://localhost:8000/predictions

Comandos de revisión:
```powershell
docker compose logs --no-color api
docker compose logs --no-color web
docker compose ps
docker compose down
```

`docker compose down` **conserva** el volumen de SQLite. Evitar `docker compose down -v` si se desea conservar el historial de predicciones.

## 4. Construcción y conexión de contenedores
Los Dockerfiles crean dos imágenes Python 3.11 independientes; cada una instala las dependencias necesarias con versiones fijadas. `compose.yaml` conecta los servicios en la red interna predeterminada, inicia web solo después de que la API esté saludable, expone los puertos **únicamente a 127.0.0.1** y persiste SQLite en un volumen Docker. No se necesitan claves privadas ni credenciales externas en la versión académica.

## 5. Estrategia de despliegue cloud (NO ejecutada)
Esta documentación **prepara** el despliegue, no declara que exista una aplicación pública ni compromete gastos.

**Alternativa PaaS:** plataformas que permiten aplicaciones Docker, por ejemplo Azure Container Apps, Google Cloud Run o AWS App Runner. Se deberán publicar dos servicios (API y dashboard), configurar sus rutas de red internas/HTTPS y variables de entorno. La API debe tener almacenamiento persistente o migrar a un servicio administrado de base de datos.

Pasos conceptuales: 1) versionar un tag inmutable del código; 2) construir imagen OCI para cada servicio; 3) publicar en un registro de contenedores; 4) elegir plataforma y región; 5) provisionar persistencia y secretos administrados; 6) configurar variables `API_URL`, `DB_PATH`, `MODEL_PATH`; 7) limitar exposición de endpoints, autenticar usuarios, TLS y rate limiting; 8) ejecutar smoke tests; 9) monitorizar logs, métricas, costo y latencia; 10) definir rollback a tags previos.

**No migrar SQLite a escala multiinstancia sin adaptar la concurrencia.** Preferir PostgreSQL administrado antes de desplegar múltiples réplicas. Evitar imágenes con secretos embebidos y validar licencias, acceso, segregación, privacidad y RBAC. En producción, contar con telemetría de equipos reales, validación prospectiva, seguimiento de drift y supervisión humana.

## 6. Guía de solución de fallas
- `docker compose ps` muestra API unhealthy: inspeccionar `docker compose logs api`; comprobar presencia del modelo y JSON de piloto.
- Puerto 8000 u 8501 ocupado: cerrar el otro servicio o cambiar **solo el puerto del anfitrión**.
- UI no alcanza API: dentro de la red Docker debe llamarse `http://api:8000`, no `http://localhost:8000`.
- SQLite no persiste: revisar definición del volumen y ruta `/state/predictions.sqlite`.
- Docker no arranca en Windows: verificar Docker Desktop Engine running, WSL y Virtual Machine Platform.
- No aparecen 12 máquinas: el pipeline debe publicar `pilot_snapshot.json` con PM-049 a PM-060.
- Envío de sensores inválidos: la API devuelve HTTP 422; una máquina fuera del piloto recibe 404.

## 7. Registro de uso de IA
ChatGPT apoyó arquitectura, creación de simulador, desarrollo de API, dashboard, Dockerfiles, pruebas y documentación. Los resultados se auditan mediante código ejecutable y GitHub Actions, no mediante capturas fabricadas.

## 8. Evidencia
- Ejecuciones automatizadas: https://github.com/isaaccg88/PredictiveMaintenance-AI-FaseII/actions
- Reportes y modelos: carpeta `results/` y `artifacts/` (una vez completada la ejecución).
- Los pasos locales deberán acompañarse de capturas auténticas del Docker Desktop y del dashboard, incorporadas al repositorio.
