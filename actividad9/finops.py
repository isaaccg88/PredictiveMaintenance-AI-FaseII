"""Modelo FinOps transparente para un despliegue AWS simulado (sin crear recursos).

Tarifas confirmadas: Fargate Linux x86/ARM us-east-1, ALB base y LCU.
RDS, almacenamiento, egreso y logs = HIPÓTESIS EDITABLES, no factura oficial.
"""
from __future__ import annotations
import json, csv, math, argparse
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/"evidence"
RATES={
  "region":"us-east-1","currency":"USD","hours_month":730,
  "fargate_x86_vcpu_hour":0.04048,"fargate_x86_gb_hour":0.004445,
  "fargate_arm_vcpu_hour":0.03238,"fargate_arm_gb_hour":0.00356,
  "alb_hour":0.0225,"alb_lcu_hour":0.008,
  "rds_single_az_month_assumption":45.0,"rds_multi_az_month_assumption":95.0,
  "log_ingest_gb_assumption":0.50,"s3_storage_gb_month_assumption":0.023,
  "egress_gb_assumption":0.09,
  "data_logs_gb_per_million_requests":0.4,
  "traffic_response_gb_per_million_requests":1.0,
  "storage_gb":10.0,
  "base_cloudwatch_other_month_assumption":7.0,
  "high_availability_cost_excludes_disaster_recovery":True,
}
SOURCE_URLS={
 "fargate":"https://aws.amazon.com/fargate/pricing/",
 "fargate_price_reference":"https://docs.aws.amazon.com/solutions/latest/prebid-server-deployment-on-aws/cost1.html",
 "alb":"https://aws.amazon.com/elasticloadbalancing/pricing/",
 "rds":"https://aws.amazon.com/rds/postgresql/pricing/",
}
ARCH={
 "cloud_naive":{"replicas_min":1,"api_vcpu":1,"api_gb":2,
                "dashboard_vcpu":.5,"dashboard_gb":1,
                "arch":"x86","rds":"single",
                "high_availability":False,"peak_target_utilization":.65},
 "ha_without_rightsizing":{"replicas_min":2,"api_vcpu":1,"api_gb":2,
                "dashboard_vcpu":.5,"dashboard_gb":1,
                "arch":"x86","rds":"multi",
                "high_availability":True,"peak_target_utilization":.50},
 "proposed_rightsized_arm":{"replicas_min":2,"api_vcpu":.5,"api_gb":1,
                "dashboard_vcpu":.5,"dashboard_gb":1,
                "arch":"arm","rds":"multi",
                "high_availability":True,"peak_target_utilization":.50},
}
SCENARIOS={
 "piloto":{"monthly_requests":500_000,"peak_factor":4.0},
 "crecimiento":{"monthly_requests":10_000_000,"peak_factor":6.0},
 "expansion":{"monthly_requests":60_000_000,"peak_factor":8.0},
}

def per_task_hour(vcpu,gb,arch):
    return vcpu*RATES[f"fargate_{arch}_vcpu_hour"]+gb*RATES[f"fargate_{arch}_gb_hour"]

def size_tasks(arch,traffic,bench):
    peak_rps=traffic["monthly_requests"]/RATES["hours_month"]/3600*traffic["peak_factor"]
    # Benchmark mide host Linux x86 con 1 vCPU NO limitado; estimación
    # orientativa y NO validación de rendimiento ARM / ECS.
    verified=bench.get("safe_single_replica_rps")
    if verified is None or verified<=0:
        return arch["replicas_min"],peak_rps,False
    assumed_capacity=verified * (arch["api_vcpu"]/1.0)
    tasks=max(arch["replicas_min"],math.ceil(peak_rps / max(assumed_capacity*arch["peak_target_utilization"],1e-9)))
    return min(tasks,100),peak_rps,True

def estimate(label,arch,traffic,bench):
    tasks,peak_rps,used_benchmark=size_tasks(arch,traffic,bench)
    hours=RATES["hours_month"]
    api=tasks*hours*per_task_hour(arch["api_vcpu"],arch["api_gb"],arch["arch"])
    dashboard=hours*per_task_hour(arch["dashboard_vcpu"],arch["dashboard_gb"],arch["arch"])
    # Aproximación 1 LCU base; no presume medición de dimensiones ALB.
    alb=hours*(RATES["alb_hour"]+RATES["alb_lcu_hour"])
    db=RATES["rds_multi_az_month_assumption"] if arch["rds"]=="multi" else RATES["rds_single_az_month_assumption"]
    million=traffic["monthly_requests"]/1_000_000
    logs=RATES["base_cloudwatch_other_month_assumption"]+million*RATES["data_logs_gb_per_million_requests"]*RATES["log_ingest_gb_assumption"]
    s3=RATES["storage_gb"]*RATES["s3_storage_gb_month_assumption"]
    egress=million*RATES["traffic_response_gb_per_million_requests"]*RATES["egress_gb_assumption"]
    comp={"api_ecs_fargate_usd":api,"dashboard_fargate_usd":dashboard,"alb_usd":alb,
      "db_assumption_usd":db,"cloudwatch_assumption_usd":logs,"s3_assumption_usd":s3,
      "egress_assumption_usd":egress}
    total=sum(comp.values())
    return {"scenario":label,"architecture":arch,"monthly_requests":traffic["monthly_requests"],
            "peak_rps_assumed":peak_rps,"replicas_estimated":tasks,
            "capacity_calibrated_from_local_benchmark":used_benchmark,
            "total_usd_month":round(total,2),
            "usd_per_1000_requests":round(total/traffic["monthly_requests"]*1000,5),
            **{k:round(v,2) for k,v in comp.items()},
            "limitations":"Illustrative forecast; ARM not benchmarked; ALB 1LCU assumption; excludes taxes, backup, NAT, WAF, networking, DR, support and operational personnel."}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/"load_benchmark.json"
    bench=json.loads(path.read_text()) if path.exists() else {}
    observed=bench.get("single",{}).get("levels",[])
    eligible=[x for x in observed if x.get("availability",0)>=.99 and x.get("p95_ms",float("inf"))<=500]
    # Solo cargas realmente medidas y exitosas; no extrapolar de escenarios inestables.
    safe=max((x["throughput_rps"] for x in eligible),default=None)
    settings={"safe_single_replica_rps":safe}
    rows=[estimate(name,arch,traffic,settings) for name,traffic in SCENARIOS.items()
           for arch_name,arch in ARCH.items()]
    for i,row in enumerate(rows):
        row["architecture_name"]=list(ARCH)[i%len(ARCH)]
    export={"method":"illustrative_us_east_1_usd","rates":RATES,"source_urls":SOURCE_URLS,
      "benchmark_reference_rps":safe,
      "requires_aws_pricing_calculator_before_approval":True,
      "scenario_definitions":SCENARIOS,
      "notes":["Not a real cloud deployment or bill.",
       "ARM pricing modeled, but compatibility/performance must be validated in ARM before choice.",
       "Architecture comparison changes HA, so cost savings within same HA class are fairer comparisons.",
       "Network NAT/VPC endpoints and WAF excluded; report shows exclusions explicitly."],
      "estimates":rows}
    (OUT/"finops_model.json").write_text(json.dumps(export,ensure_ascii=False,indent=2)+"\n")
    with (OUT/"cost_comparison.csv").open("w",newline="",encoding="utf-8") as f:
        fields=["scenario","architecture_name","monthly_requests","peak_rps_assumed",
                "replicas_estimated","capacity_calibrated_from_local_benchmark",
                "api_ecs_fargate_usd","dashboard_fargate_usd","alb_usd",
                "db_assumption_usd","cloudwatch_assumption_usd",
                "s3_assumption_usd","egress_assumption_usd",
                "total_usd_month","usd_per_1000_requests"]
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
    print(json.dumps({"cases":len(rows),"safe_single_replica_rps":safe,
     "monthly_usd":[{k:x[k] for k in ("scenario","architecture_name","total_usd_month")}
                    for x in rows]},indent=2))
    return export

if __name__=="__main__":main()
