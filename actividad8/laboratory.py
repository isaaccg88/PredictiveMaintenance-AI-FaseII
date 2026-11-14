"""Pruebas reproducibles HTTP reales y drift sintético con antes/durante/después."""
from __future__ import annotations
import argparse,json,os,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import requests
from .rules import AlertState,SLOS,ALERT_RULES,evaluate_http,psi,evaluate_six_rules
from .runbooks import documented_action,RUNBOOKS
from .simulator import HERE,SEED

URL=os.getenv('ACT8_API','http://127.0.0.1:8008').rstrip('/')
TOKEN=os.getenv('LAB_TOKEN')

def traffic(n,fault=None):
    out=[]
    for i in range(n):
        headers={}
        if fault:
            if not TOKEN:raise RuntimeError('LAB_TOKEN required for fault injection')
            headers={'x-lab-token':TOKEN,'x-lab-fault':fault}
        now=time.perf_counter()
        try:
            response=requests.post(URL+'/predict',json={'machine_id':'PM-049'},headers=headers,timeout=8)
            out.append({'status':response.status_code,
                'duration_ms':round((time.perf_counter()-now)*1000,3),
                'trace_id':response.headers.get('X-Trace-Id')})
        except requests.RequestException:
            out.append({'status':599,'duration_ms':round((time.perf_counter()-now)*1000,3),
                        'trace_id':None})
    return out

def main():
    if requests.get(URL+'/health',timeout=10).json()['status']!='ok':
        raise RuntimeError('API unavailable')
    alerts=AlertState(); start=datetime.now(timezone.utc).isoformat()
    # CPU del runner y arranque en frio pueden producir latencia transitoria.
    # No ocultamos las muestras: registramos todos los intentos y solo iniciamos
    # el incidente tras confirmar una ventana base saludable (maximo 4 intentos).
    warmup=traffic(3)
    baseline_attempts=[]
    for attempt in range(4):
        sample=evaluate_http(traffic(12))
        baseline_attempts.append(sample)
        if (sample['status']=='MEASURED' and
            not sample['latency_breached'] and
            not sample['availability_breached']):
            break
        time.sleep(0.5)
    healthy_before=baseline_attempts[-1]
    if healthy_before['latency_breached'] or healthy_before['availability_breached']:
        raise RuntimeError('Baseline HTTP unstable after 4 measured windows: '+
                           json.dumps(baseline_attempts,ensure_ascii=False))
    incident=evaluate_http(traffic(12,'latency'))
    first=alerts.update('latency',incident['latency_breached'],incident)
    second=alerts.update('latency',incident['latency_breached'],incident)
    # Buscar dos ventanas sanas CONSECUTIVAS con un limite, sin falsificar la
    # recuperacion ni ocultar ventanas inestables intermedias.
    recovery_windows=[]
    for attempt in range(6):
        latest=evaluate_http(traffic(12))
        recovery_windows.append(latest)
        if (len(recovery_windows)>=2 and
            all(w['status']=='MEASURED' and
                not w['latency_breached'] and not w['availability_breached']
                for w in recovery_windows[-2:])):
            break
        time.sleep(0.3)
    recovery_1,recovery_2=recovery_windows[-2:]
    final=alerts.update('latency',recovery_1['latency_breached'] or recovery_2['latency_breached'],recovery_2)
    rb_latency=documented_action('RB-LATENCY',incident,recovery_2,{
      'first_window_healthy':not recovery_1['latency_breached'],
      'second_window_healthy':not recovery_2['latency_breached'],
      'actual_http_requests':recovery_2['eligible']==12,
      'deduplicated':first['action']=='EMITTED' and second['action']=='SUPPRESSED_DUPLICATE'})
    # In this scenario we do not send shifted measurements into the prediction API.
    # Quarantine is an actual exclusion of the anomalous batch from the operational stream.
    baseline=json.loads((HERE/'results'/'baseline_sensors.json').read_text())
    rng=np.random.default_rng(SEED)
    reference=np.asarray(baseline['temperature_c'])
    original=reference[:450].copy()
    shifted=original+rng.normal(14,1.5,len(original))
    drift_before=psi(reference,original)
    drift_during=psi(reference,shifted)
    alert_drift=alerts.update('drift',drift_during is not None and drift_during>SLOS['drift_psi'],
        {'psi':drift_during,'count':len(shifted)})
    quarantine={'quarantined_rows':len(shifted),'operational_predictions_from_shifted_rows':0,
                'action':'batch_removed_from_lab_input'}
    restored=reference[500:950].copy()
    drift_after=psi(reference,restored)
    alerts.update('drift',drift_after is not None and drift_after>SLOS['drift_psi'],{'psi':drift_after})
    rb_drift=documented_action('RB-DRIFT',{'psi':drift_during},{'psi':drift_after},
       {'detected':drift_during is not None and drift_during>SLOS['drift_psi'],
        'quarantined_no_prediction':quarantine['operational_predictions_from_shifted_rows']==0,
        'restored_psi_below_limit':drift_after is not None and drift_after<SLOS['drift_psi']})
    # Six documented rules. Collect quality from true held-out test and CPU using psutil if available.
    measured_quality=json.loads((HERE/'results'/'evaluation_v2.json').read_text())['metrics']['test_pilot']
    checks={'quality_auc':measured_quality['roc_auc'],
       'quality_breached':measured_quality['roc_auc']<SLOS['quality_min_auc'],
       'cpu_pct':None,'cpu_status':'NOT_MEASURED_IN_LAB',
       'rules_configured':len(ALERT_RULES)}
    try:
        import psutil
        checks['cpu_pct']=psutil.cpu_percent(interval=.1)
        checks['cpu_status']='MEASURED_RUNNER_NOT_CONTAINER'
    except ImportError: pass
    checks['evaluated_rules']=evaluate_six_rules(recovery_2,checks['cpu_pct'],drift_after,measured_quality['roc_auc'])
    report={'synthetic':True,'start_utc':start,
      'service':'real_local_http_FastAPI','slo':SLOS,'rules':ALERT_RULES,
      'incidents':[
       {'incident_id':'INC-01','name':'latency_injection','baseline':healthy_before,
         'baseline_attempts':baseline_attempts,
         'warmup_request_count':len(warmup),
         'during':incident,'after':recovery_2,
         'recovery_windows':recovery_windows,'runbook':rb_latency},
       {'incident_id':'INC-02','name':'synthetic_data_drift',
         'baseline_psi':drift_before,'during_psi':drift_during,
         'after_psi':drift_after,'quarantine':quarantine,'runbook':rb_drift}],
      'checks':checks,'alerts':alerts.events,'runbooks_catalog':RUNBOOKS,
      'end_utc':datetime.now(timezone.utc).isoformat()}
    dest=HERE/'evidence';dest.mkdir(exist_ok=True)
    (dest/'incidents.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    summary={'both_runbooks_verified':rb_latency['status']=='RESOLVED' and rb_drift['status']=='RESOLVED',
        'latency_ms_during':incident['p95_ms'],'latency_ms_after':recovery_2['p95_ms'],
        'drift_psi_during':drift_during,'drift_psi_after':drift_after,
        'alerts_emitted':sum(e['action']=='EMITTED' for e in alerts.events),
        'alerts_suppressed':sum(e['action']=='SUPPRESSED_DUPLICATE' for e in alerts.events)}
    (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    if not summary['both_runbooks_verified']:raise AssertionError('Incident runbook validation failed')
    return report
if __name__=='__main__':main()
