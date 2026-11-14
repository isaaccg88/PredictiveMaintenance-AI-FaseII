"""Validador independiente: CI debe FALLAR si las evidencias no prueban respuesta."""
import json,sys
from pathlib import Path
from .simulator import HERE

def main():
    a=json.loads((HERE/'evidence/incidents.json').read_text())
    b=json.loads((HERE/'results/evaluation_v2.json').read_text())
    assert b['model']['horizon_hours']==72 and b['model']['machines_holdout']==12
    assert b['metrics']['test_pilot']['failure_events_evaluable']>=20
    assert b['metrics']['test_pilot']['precision']>0
    assert a['checks']['rules_configured']>=5
    inc=a['incidents']
    assert len(inc)>=2
    latency=inc[0]
    assert latency['during']['latency_breached']
    assert not latency['baseline']['latency_breached']
    assert not latency['after']['latency_breached']
    assert latency['runbook']['status']=='RESOLVED'
    for row in inc:
        assert row['runbook']['status']=='RESOLVED'
        assert row['runbook']['verification_checks']
        assert all(row['runbook']['verification_checks'].values())
    assert inc[1]['during_psi']>.2 and inc[1]['after_psi']<.2
    assert inc[1]['quarantine']['operational_predictions_from_shifted_rows']==0
    actions=[e['action'] for e in a['alerts']]
    assert actions.count('EMITTED')>=2 and actions.count('SUPPRESSED_DUPLICATE')>=1
    assert actions.count('RESOLVED')>=2
    print('ACTIVIDAD8 VERIFICATION: PASS')
if __name__=='__main__':main()
