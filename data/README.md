# Procedencia temporal sintética

El generador `src/simulation.py` produce una flota sintética de 60 máquinas durante 540 días, lecturas cada 6 horas. La etiqueta se calcula de eventos de falla *futuros*, a 12 lecturas de horizonte (72 horas). Los últimos 12 registros de cada serie quedan **censurados**, no se etiquetan falsamente como negativos. El archivo completo se publica como artefacto del workflow de GitHub Actions por tamaño; en Git se versiona una muestra y manifiesto con SHA256. **Estos datos no proceden de sensores industriales reales.**
