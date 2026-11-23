"""API del laboratorio Fase III: middleware de degradación intencional SOLO en CI.

Un flag local dentro del volumen candidate genera latencia extra de forma
controlada. No expone endpoint para activar la falla ni modifica el modelo.
"""
from __future__ import annotations
import asyncio, os
from pathlib import Path
from fastapi import Request
from actividad8.service import app

FLAG=os.getenv("F3_DEGRADATION_FLAG","")
@app.middleware("http")
async def controlled_candidate_delay(request:Request, call_next):
    if request.url.path=="/predict" and FLAG and Path(FLAG).is_file():
        # No aceptar delays arbitrarios de usuarios externos o contenido del flag.
        await asyncio.sleep(0.70)
    return await call_next(request)
