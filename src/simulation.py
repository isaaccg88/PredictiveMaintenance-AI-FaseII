"""Simulador reproducible de sensores y eventos de fallas: escenario ACADÉMICO, no industrial.

Cada registro representa una medición espaciada seis horas. La etiqueta se
construye de eventos FUTUROS, nunca del sensor/evento del instante actual.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
GENERATED=ROOT/"data/generated"
ARTIFACTS=ROOT/"artifacts"
RESULTS=ROOT/"results"
SEED=202608
STEPS=2160  # 540 días x cuatro lecturas / día
MACHINES=60
HORIZON=12 # 12 x 6 horas
FREQUENCY_HOURS=6
NUMERIC=[
    "temperature_c","vibration_mm_s","pressure_bar","rpm","torque_nm",
    "wear_index","load_pct","hours_since_service","temperature_avg_24h",
    "vibration_avg_24h","wear_delta_72h"
]
FEATURES=NUMERIC+["machine_type"]
FIELDS=["timestamp","machine_id","machine_type","status","failure_event"]+NUMERIC+["failure_next_72h"]

def _sigmoid(z:float)->float:
    return 1.0/(1.0+np.exp(-np.clip(z,-30,30)))

def generate(seed:int=SEED,steps:int=STEPS,machines:int=MACHINES)->pd.DataFrame:
    rng=np.random.default_rng(seed)
    t0=pd.Timestamp("2025-01-01 00:00:00",tz="UTC")
    rows=[]
    for mi in range(1,machines+1):
        machine_id=f"PM-{mi:03d}"
        machine_type=["A","B","C"][(mi-1)%3]
        vulnerability=float(rng.uniform(.8,1.3))
        base_temp=float(rng.normal(53,2))
        wear=float(rng.uniform(.09,.16))
        last_service=0
        downtime=0
        last_temp=[]
        last_vib=[]
        last_wear=[]
        for step in range(steps):
            when=t0+pd.Timedelta(hours=step*FREQUENCY_HOURS)
            if downtime:
                # During repairs the machine is unavailable for prediction.
                rows.append({
                    "timestamp":when,"machine_id":machine_id,"machine_type":machine_type,
                    "status":"down","failure_event":0,
                    "temperature_c":np.nan,"vibration_mm_s":np.nan,
                    "pressure_bar":np.nan,"rpm":np.nan,"torque_nm":np.nan,
                    "wear_index":wear,"load_pct":0.,"hours_since_service":step*6-last_service*6,
                    "temperature_avg_24h":np.nan,"vibration_avg_24h":np.nan,
                    "wear_delta_72h":np.nan
                })
                downtime-=1
                if not downtime:
                    wear=float(rng.uniform(.06,.16))
                    last_service=step+1
                    last_temp=[];last_vib=[];last_wear=[]
                continue
            load=float(np.clip(rng.normal(.66,.14),.22,.98))
            wear=float(np.clip(wear+(0.0008+0.0007*load)*vulnerability+
                         rng.normal(0,.00017),0,1.0))
            temp=float(base_temp+24*wear+4*load+rng.normal(0,1.45))
            vib=float(max(.05,.27+2.45*wear**2+.17*load+rng.normal(0,.19)))
            pressure=float(max(1.,3.8-.67*wear+.12*load+rng.normal(0,.10)))
            rpm=float(1460+75*load-54*wear+rng.normal(0,23))
            torque=float(48+75*load+25*wear+rng.normal(0,8))
            last_temp.append(temp);last_vib.append(vib);last_wear.append(wear)
            temperature_avg=float(np.mean(last_temp[-4:]))
            vibration_avg=float(np.mean(last_vib[-4:]))
            wear_delta=float(wear-last_wear[-13]) if len(last_wear)>12 else 0.
            # Probabilistic hazard increases with degradation, but contains
            # irreducible randomness and occasional spontaneous events.
            hazard=float(np.clip(.00025+.08*_sigmoid((wear-.74)*16)*
                               (.7+.45*load)*vulnerability,.0001,.11))
            fail=int(rng.random()<hazard)
            rows.append({
                "timestamp":when,"machine_id":machine_id,"machine_type":machine_type,
                "status":"failure" if fail else "operating","failure_event":fail,
                "temperature_c":round(temp,4),"vibration_mm_s":round(vib,4),
                "pressure_bar":round(pressure,4),"rpm":round(rpm,4),
                "torque_nm":round(torque,4),"wear_index":round(wear,6),
                "load_pct":round(load,6),
                "hours_since_service":max(0,(step-last_service)*6),
                "temperature_avg_24h":round(temperature_avg,4),
                "vibration_avg_24h":round(vibration_avg,4),
                "wear_delta_72h":round(wear_delta,6)
            })
            if fail:
                downtime=int(rng.integers(2,6))
        assert len(rows)==mi*steps
    frame=pd.DataFrame.from_records(rows)
    # A label for step t looks at [t+1, ..., t+12]. An event at t does
    # not leak into the target at t; we exclude event/down records in training.
    frames=[]
    for _,group in frame.groupby("machine_id",sort=False):
        event=group.failure_event.to_numpy(dtype=np.int8)
        label=np.zeros(len(group),dtype=np.int8)
        for delta in range(1,HORIZON+1):
            label[:-delta]|=event[delta:]
        series=pd.Series(label,index=group.index,dtype="float64")
        series.iloc[-HORIZON:]=np.nan  # unknown future = censored
        frames.append(series)
    frame["failure_next_72h"]=pd.concat(frames).sort_index().values
    return frame

def chronological_split(df:pd.DataFrame)->dict[str,pd.DataFrame]:
    """Machine-OOD pilot + strictly chronological in-distribution splits.

    The purge ensures no positive label references future events in the next
    partition. The 12 pilot machines are never seen during training/validation.
    """
    step=df.groupby("machine_id",sort=False).cumcount()
    cutoff1=int(STEPS*.65)
    cutoff2=int(STEPS*.80)
    machine_number=df.machine_id.str[-3:].astype(int)
    observable=(df.status=="operating")&df.failure_next_72h.notna()
    familiar=machine_number<=48
    cuts={
        "train":familiar&(step<cutoff1-HORIZON),
        "validation":familiar&(step>=cutoff1)&(step<cutoff2-HORIZON),
        "test_temporal":familiar&(step>=cutoff2)&(step<STEPS-HORIZON),
        "test_unseen_machines":(~familiar)&(step>=cutoff2)&(step<STEPS-HORIZON)
    }
    result={k:df.loc[mask&observable].copy() for k,mask in cuts.items()}
    # Future labels of train cannot cross cutoff1; same for validation/cutoff2.
    assert result["train"].timestamp.max()<result["validation"].timestamp.min()
    assert result["validation"].timestamp.max()<result["test_temporal"].timestamp.min()
    assert not (set(result["train"].machine_id)&set(result["test_unseen_machines"].machine_id))
    assert set(result["test_unseen_machines"].machine_id)=={f"PM-{i:03d}" for i in range(49,61)}
    return result

def persist_data(df:pd.DataFrame,subsets:dict[str,pd.DataFrame])->dict:
    GENERATED.mkdir(parents=True,exist_ok=True)
    RESULTS.mkdir(parents=True,exist_ok=True)
    # Full dataset lives in GitHub Actions as an artifact, not a huge Git blob.
    full=GENERATED/"synthetic_machine_telemetry.csv"
    df.to_csv(full,index=False)
    metadata={
        "synthetic":True,"not_real_industrial_data":True,
        "simulation":"wear-dependent stochastic failure hazard, maintenance and downtime",
        "seed":SEED,"machines":MACHINES,"pilot_machines":12,
        "steps_per_machine":STEPS,"measurement_interval_hours":FREQUENCY_HOURS,
        "horizon_hours":72,"horizon_steps":HORIZON,"rows":len(df),
        "failure_events":int(df.failure_event.sum()),
        "positive_observable_records":int((df.failure_next_72h==1).sum()),
        "sha256_csv":hashlib.sha256(full.read_bytes()).hexdigest(),
        "splits":{k:{"rows":len(v),"positives":int(v.failure_next_72h.sum())}
                  for k,v in subsets.items()},
        "model_features":FEATURES,
        "training_policy":"only operating states, future labels censored, 12-step temporal purge",
        "generalization_policy":"12 pilot machines completely excluded from model fitting",
        "known_limitations":[
            "Artificial wear process intentionally correlates with simulated events.",
            "Predictive metrics on synthetic data do not demonstrate industrial effectiveness.",
            "Labels within 72h of the series end are censored, never assumed negative.",
            "Train/validation/test are temporal and the pilot set uses unseen machines."
        ]
    }
    (RESULTS/"dataset_manifest.json").write_text(
        json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    # Small traceable illustrative sample for reviewing features without 20MB clone.
    df.loc[df.machine_id.isin(["PM-001","PM-049"])].head(300).to_csv(
        GENERATED/"telemetry_sample.csv",index=False
    )
    return metadata

if __name__=="__main__":
    df=generate()
    groups=chronological_split(df)
    info=persist_data(df,groups)
    print(json.dumps({k:info[k] for k in ("rows","failure_events","splits")},
                     ensure_ascii=False,indent=2))
