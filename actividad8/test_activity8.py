"""Pruebas deterministas de etiquetas, aislamiento, presupuesto y deduplicación."""
from actividad8.simulator import generate,split,HORIZON
from actividad8.rules import AlertState,evaluate_http,psi
import numpy as np

def test_label_future_and_censor():
    df=generate(machines=2,steps=160)
    for _,g in df.groupby('machine_id'):
        flags=g.failure_event.to_numpy()
        for i in range(len(g)-HORIZON):
            assert g.iloc[i].failure_next_72h==int(flags[i+1:i+HORIZON+1].any())
        assert g.failure_next_72h.tail(HORIZON).isna().all()

def test_alert_budget_and_no_duplicate():
    samples=[{'status':200,'duration_ms':30.} for _ in range(20)]
    assert not evaluate_http(samples)['latency_breached']
    bad=[{'status':200,'duration_ms':650.} for _ in range(20)]
    assert evaluate_http(bad)['latency_breached']
    engine=AlertState()
    assert engine.update('latency',True)['action']=='EMITTED'
    assert engine.update('latency',True)['action']=='SUPPRESSED_DUPLICATE'
    assert engine.update('latency',False)['action']=='RESOLVED'

def test_drift_psi():
    rng=np.random.default_rng(17);a=rng.normal(50,2,1000)
    assert psi(a,a)<.01
    assert psi(a,a+12)>.2

def test_six_rules_have_real_predicates():
    from actividad8.rules import evaluate_six_rules
    rows=[{'status':503,'duration_ms':700.} for _ in range(20)]
    decision=evaluate_six_rules(evaluate_http(rows),cpu_pct=92,drift_psi=2,quality_auc=.55)
    assert len(decision)==6
    assert all(x['status']=='BREACH' and x['breach'] for x in decision.values())
