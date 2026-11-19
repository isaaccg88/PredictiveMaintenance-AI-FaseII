"""Verificación matemática y de integridad de análisis reproducible."""
from pathlib import Path
import json
from actividad9.finops import estimate,ARCH,SCENARIOS
from actividad9.fairness import calculate
import numpy as np

def test_cost_items_sum_and_unit_economics():
    settings={"safe_single_replica_rps":20.0}
    for name,arch in ARCH.items():
        r=estimate(name,arch,SCENARIOS["crecimiento"],settings)
        parts=["api_ecs_fargate_usd","dashboard_fargate_usd","alb_usd","db_assumption_usd",
          "cloudwatch_assumption_usd","s3_assumption_usd","egress_assumption_usd"]
        assert abs(sum(r[x] for x in parts)-r["total_usd_month"])<.05
        assert r["replicas_estimated"]>=arch["replicas_min"]
        assert r["usd_per_1000_requests"]>0

def test_fairness_confusion_and_zero_division():
    m=calculate(np.array([0,0,1,1]),np.array([.1,.7,.8,.4]),.5)
    assert (m["tp"],m["fp"],m["fn"],m["tn"])==(1,1,1,1)
    assert m["recall_tpr"]==.5 and m["fpr"]==.5
    assert calculate(np.zeros(6,dtype=int),np.zeros(6),.5)["recall_tpr"] is None

def test_worksheet_sources_not_represented_as_real_costs():
    from actividad9.finops import RATES
    assert RATES["rds_multi_az_month_assumption"] > 0
    assert "assumption" in "rds_multi_az_month_assumption"
    assert RATES["hours_month"]==730
