"""API observada real: Random Forest V2, métricas HTTP, logs JSON y trazas correlacionadas.

LAB_MODE habilita inyección temporal SOLO en loopback y con LAB_TOKEN; por defecto
se deshabilita. Ninguna ruta dispara mantenimiento físico automático.
"""
from __future__ import annotations
import json, os, sqlite3, time, uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from .simulator import HERE

ART=HERE/'artifacts'; RUNTIME=Path(os.getenv('ACT8_RUNTIME',str(HERE/'runtime')))
STATE={}
def utc(): return datetime.now(timezone.utc).isoformat()
def log(**entry):
    RUNTIME.mkdir(parents=True,exist_ok=True)
    with (RUNTIME/'events.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'at_utc':utc(),**entry},ensure_ascii=False)+'\n')
def conn():
    c=sqlite3.connect(str(RUNTIME/'events.sqlite'),timeout=20)
    c.row_factory=sqlite3.Row
    return c
@asynccontextmanager
async def lifespan(app:FastAPI):
    STATE['model']=joblib.load(ART/'model_v2.joblib')
    STATE['metadata']=json.loads((ART/'metadata_v2.json').read_text())
    snap=json.loads((ART/'pilot_v2.json').read_text())
    STATE['machines']={x['machine_id']:x for x in snap['machines']}
    if len(STATE['machines'])!=12 or STATE['metadata']['horizon_hours']!=72:
        raise RuntimeError('Metadata/pilot incompatible')
    RUNTIME.mkdir(parents=True,exist_ok=True)
    with conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS request_metrics(id INTEGER PRIMARY KEY,
          at_utc TEXT, trace_id TEXT, route TEXT, status INTEGER, duration_ms REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS inference_history(id INTEGER PRIMARY KEY,
          at_utc TEXT, trace_id TEXT, machine_id TEXT, probability REAL, risk_level TEXT,
          observed_simulated_utc TEXT, source TEXT, inputs_json TEXT)''')
        c.commit()
    yield
    STATE.clear()
app=FastAPI(title='Predictive Maintenance AI - Observabilidad A8',
    description='Prototipo académico sintético; predicción de fallas a 72h',
    version='2.0.0',lifespan=lifespan)

@app.middleware('http')
async def instrument(request:Request,call_next):
    started=time.perf_counter()
    trace_id=str(uuid.uuid4())
    request.state.trace_id=trace_id
    lab_enabled=os.getenv('LAB_MODE','0')=='1' and bool(os.getenv('LAB_TOKEN'))
    loopback=request.client and request.client.host in ('127.0.0.1','::1','testclient')
    authorized=lab_enabled and loopback and request.headers.get('x-lab-token')==os.getenv('LAB_TOKEN')
    fault=request.headers.get('x-lab-fault') if authorized else None
    try:
        if request.url.path=='/predict' and fault=='latency':
            import asyncio
            await asyncio.sleep(.65)
        if request.url.path=='/predict' and fault=='unavailable':
            response=JSONResponse(status_code=503,content={'detail':'synthetic failure injection'})
        else: response=await call_next(request)
    except Exception as ex:
        log(level='ERROR',event='request.exception',trace_id=trace_id,error=type(ex).__name__)
        response=JSONResponse(status_code=500,content={'detail':'Internal server error'})
    duration=round((time.perf_counter()-started)*1000,3)
    response.headers['X-Trace-Id']=trace_id
    with conn() as c:
        c.execute('INSERT INTO request_metrics(at_utc,trace_id,route,status,duration_ms) VALUES(?,?,?,?,?)',
            (utc(),trace_id,request.url.path,response.status_code,duration))
        c.commit()
    log(level='INFO',event='http.request',trace_id=trace_id,route=request.url.path,
        status=response.status_code,duration_ms=duration,lab_fault=fault or 'none')
    return response

class Overrides(BaseModel):
    model_config=ConfigDict(extra='forbid')
    temperature_c:float|None=Field(default=None,ge=-20,le=200)
    vibration_mm_s:float|None=Field(default=None,ge=0,le=80)
    pressure_bar:float|None=Field(default=None,ge=0,le=50)
    rpm:float|None=Field(default=None,ge=0,le=12000)
    torque_nm:float|None=Field(default=None,ge=0,le=2000)
    wear_index:float|None=Field(default=None,ge=0,le=1)
    load_pct:float|None=Field(default=None,ge=0,le=1)
    hours_since_service:float|None=Field(default=None,ge=0,le=100000)
    temperature_avg_24h:float|None=Field(default=None,ge=-20,le=200)
    vibration_avg_24h:float|None=Field(default=None,ge=0,le=80)
    wear_delta_72h:float|None=Field(default=None,ge=-1,le=1)
class Prediction(BaseModel):
    model_config=ConfigDict(extra='forbid')
    machine_id:str=Field(pattern=r'^PM-\d{3}$')
    overrides:Overrides|None=None

@app.get('/health')
def health():
    with conn() as c: c.execute('SELECT 1').fetchone()
    return {'status':'ok','synthetic':True,'model_loaded':True,'horizon_hours':72}
@app.get('/model/info')
def model_info(): return STATE['metadata']
@app.get('/machines')
def machines():
    return [{'machine_id':mid,'timestamp_simulated_utc':v['timestamp']} for mid,v in sorted(STATE['machines'].items())]
@app.post('/predict')
def predict(body:Prediction,request:Request):
    m=STATE['machines'].get(body.machine_id)
    if m is None: raise HTTPException(status_code=404,detail='Unknown pilot machine')
    vals={k:m[k] for k in STATE['metadata']['features']}
    if body.overrides: vals.update(body.overrides.model_dump(exclude_none=True))
    trace_id=request.state.trace_id
    t0=time.perf_counter()
    p=float(STATE['model'].predict_proba(pd.DataFrame([vals]))[0,1])
    log(level='INFO',event='model.infer',trace_id=trace_id,
        duration_ms=round((time.perf_counter()-t0)*1000,3))
    threshold=float(STATE['metadata']['threshold'])
    level='ALTO' if p>=threshold else ('MEDIO' if p>=threshold*.5 else 'BAJO')
    with conn() as c:
        cur=c.execute('''INSERT INTO inference_history(at_utc,trace_id,machine_id,
          probability,risk_level,observed_simulated_utc,source,inputs_json)
          VALUES(?,?,?,?,?,?,?,?)''',(utc(),trace_id,body.machine_id,p,level,m['timestamp'],
            'synthetic_whatif' if body.overrides else 'synthetic_snapshot',json.dumps(vals)))
        c.commit()
        record_id=cur.lastrowid
    log(level='INFO',event='sqlite.commit',trace_id=trace_id,record_id=record_id)
    return {'trace_id':trace_id,'record_id':record_id,'machine_id':body.machine_id,
         'probability_72h':round(p,6),'risk_level':level,'alert':p>=threshold,
         'horizon_hours':72,'synthetic':True,'observed_simulated_utc':m['timestamp'],
         'action':'human_review_required_if_alert'}
@app.get('/metrics')
def recent_metrics():
    with conn() as c:
        rows=c.execute("SELECT status,duration_ms,at_utc,trace_id FROM request_metrics WHERE route='/predict' ORDER BY id DESC LIMIT 500").fetchall()
    data=[dict(r) for r in rows]
    return {'total':len(data),'errors_5xx':sum(x['status']>=500 for x in data),
        'p95_ms':float(pd.Series([x['duration_ms'] for x in data]).quantile(.95)) if data else None,
        'measurements':data,'source':'measured_http_requests'}
@app.get('/history')
def history():
    with conn() as c:
        rows=c.execute('SELECT id,at_utc,machine_id,probability,risk_level,trace_id FROM inference_history ORDER BY id DESC LIMIT 100').fetchall()
    return [dict(r) for r in rows]
