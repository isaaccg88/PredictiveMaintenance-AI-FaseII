# Evidencias de ejecución local — Docker Desktop (Windows 11)

Esta carpeta guarda **capturas reales**, tomadas por el estudiante desde su computadora, de la aplicación Docker ya descargada de GitHub. Las capturas NO se deben fabricar ni recrear con imágenes genéricas.

## Capturas solicitadas

1. **`Docker_Containers.png`** — Docker Desktop, pestaña Containers, con los dos servicios de `predictive-maintenance-faseii` en ejecución; idealmente API healthy y web running.
2. **`Dashboard_Piloto.png`** — navegador abierto en `http://localhost:8501`, mostrando el tablero Predictive Maintenance AI, las doce máquinas simuladas y los indicadores de riesgo a 72 horas.
3. **`Swagger_API.png`** (opcional) — navegador `http://localhost:8000/docs` mostrando los endpoints de FastAPI.

Guardar con Windows+Shift+S y subir mediante **GitHub > docs/local_evidence > Add file > Upload files**. Las dos primeras son obligatorias para la página de evidencia local; la tercera es opcional.

**Automatización:** al subir los dos PNG, el workflow [Fase II - Manual cloud y validación PDF](../../.github/workflows/publish-docs.yml) regenerará el documento de validación, incorporando las capturas originales y conservando sus rutas para auditoría. Si solo hay una captura, fallará intencionalmente hasta completar las dos.

## Comandos de preparación y prueba

```powershell
docker compose up --build -d --wait
docker compose ps
```

Para revisar información visual:
- Dashboard: `http://localhost:8501`
- Contrato API: `http://localhost:8000/docs`
- Salud API: `http://localhost:8000/health`
- Historial SQLite: `http://localhost:8000/predictions`

Se ha verificado la aplicación previamente en Docker real de GitHub Actions; estas imágenes sirven específicamente para demostrar la **ejecución local** de la Fase II.
