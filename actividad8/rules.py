"""Definiciones de alertas inteligentes, presupuestos y deduplicación."""
from __future__ import annotations
from dataclasses import dataclass,field
from datetime import datetime,timezone
import numpy as np

SLOS={'availability':.99,'timely':.99,'max_latency_ms':500,
      'cpu_pct':85,'drift_psi':.20,'quality_min_auc':.75}
ALERT_RULES={
 'availability':{'severity':'P1','condition':'available / eligible < 99%', 'runbook':'RB-AVAIL'},
 'http_5xx':{'severity':'P1','condition':'5xx > 1% of eligible', 'runbook':'RB-AVAIL'},
 'latency':{'severity':'P2','condition':'timely / eligible < 99%', 'runbook':'RB-LATENCY'},
 'cpu':{'severity':'P2','condition':'CPU average > 85%', 'runbook':'RB-CAPACITY'},
 'drift':{'severity':'P2','condition':'PSI > 0.2 and sample >=100', 'runbook':'RB-DRIFT'},
 'quality':{'severity':'P2','condition':'AUC < 0.75 with mature labels', 'runbook':'RB-QUALITY'}}

def evaluate_http(samples):
    n=len(samples)
    if n<10: return {'status':'INSUFFICIENT_DATA','eligible':n}
    failures=sum(s['status']>=500 for s in samples)
    timely=sum(200<=s['status']<300 and s['duration_ms']<=SLOS['max_latency_ms'] for s in samples)
    lat=[s['duration_ms'] for s in samples]
    permitted=n*(1-SLOS['availability'])
    latency_bad=n-timely
    return {'status':'MEASURED','eligible':n,'failures_5xx':failures,
      'availability':(n-failures)/n,'timely_ratio':timely/n,
      'p95_ms':float(np.percentile(lat,95)),'error_budget':permitted,
      'availability_budget_spent_pct':100*failures/permitted,
      'latency_budget_spent_pct':100*latency_bad/permitted,
      'availability_breached':failures>permitted,
      'latency_breached':latency_bad>permitted}

def psi(reference,actual,bins=10):
    x=np.asarray(reference,dtype=float);y=np.asarray(actual,dtype=float)
    x=x[np.isfinite(x)];y=y[np.isfinite(y)]
    if len(x)<100 or len(y)<100: return None
    edges=np.unique(np.quantile(x,np.linspace(0,1,bins+1)))
    if len(edges)<3: return None
    edges[0]=-np.inf;edges[-1]=np.inf
    a=np.histogram(x,bins=edges)[0]/len(x)
    b=np.histogram(y,bins=edges)[0]/len(y)
    a=np.clip(a,1e-5,1);b=np.clip(b,1e-5,1)
    return float(np.sum((b-a)*np.log(b/a)))

@dataclass
class AlertState:
    state:dict=field(default_factory=dict)
    events:list=field(default_factory=list)
    def update(self,code,breach,details=None):
        old=self.state.get(code,'RESOLVED')
        if breach and old!='ACTIVE':
            self.state[code]='ACTIVE'; action='EMITTED'
        elif breach: action='SUPPRESSED_DUPLICATE'
        elif old=='ACTIVE':
            self.state[code]='RESOLVED'; action='RESOLVED'
        else: action='NO_ALERT'
        record={'at_utc':datetime.now(timezone.utc).isoformat(),'rule':code,
                'action':action,'severity':ALERT_RULES[code]['severity'],
                'details':details or {}}
        self.events.append(record)
        return record

def evaluate_six_rules(http=None,cpu_pct=None,drift_psi=None,quality_auc=None):
    """Six executable detection rules. None means evidence insufficient, never healthy by assumption."""
    values={key:None for key in ALERT_RULES}
    if http and http.get('status')=='MEASURED':
        values['availability']=bool(http['availability_breached'])
        values['http_5xx']=bool(http['failures_5xx']/http['eligible']>.01)
        values['latency']=bool(http['latency_breached'])
    if cpu_pct is not None: values['cpu']=bool(cpu_pct>SLOS['cpu_pct'])
    if drift_psi is not None: values['drift']=bool(drift_psi>SLOS['drift_psi'])
    if quality_auc is not None: values['quality']=bool(quality_auc<SLOS['quality_min_auc'])
    return {name:{'breach':breach,'status':'NOT_EVALUATED' if breach is None else
                ('BREACH' if breach else 'OK'),'severity':ALERT_RULES[name]['severity'],
                'runbook':ALERT_RULES[name]['runbook']} for name,breach in values.items()}
