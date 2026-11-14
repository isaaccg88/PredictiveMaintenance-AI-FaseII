"""Generador V2: episodios de desgaste, fallas repentinas y falsas anomalías.

Los eventos de falla son sintéticos. Los sensores se construyen con señales
precursoras imperfectas; ninguna característica contiene el tiempo FUTURO de falla.
Se mantiene una etiqueta verdadera: falla en t+6,...,t+72 horas, nunca en t.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEED = 20261114
MACHINES = 60
STEPS = 2160
FREQ_H = 6
HORIZON = 12
FEATURES = ["temperature_c", "vibration_mm_s", "pressure_bar", "rpm",
            "torque_nm", "wear_index", "load_pct", "hours_since_service",
            "temperature_avg_24h", "vibration_avg_24h", "wear_delta_72h", "machine_type"]

def generate(seed=SEED, machines=MACHINES, steps=STEPS):
    rows = []
    t0 = pd.Timestamp("2025-01-01", tz="UTC")
    for mi in range(1, machines+1):
        rng = np.random.default_rng(seed+mi*1009)
        kind = ["A", "B", "C"][(mi-1)%3]
        shift = rng.normal(0, 1.9)
        wear = rng.uniform(.08, .16)
        last_service_step = 0
        cycle_start = 0
        # Duración de los ciclos es incierta; el clasificador nunca recibe este valor.
        planned_failure = int(rng.integers(100, 191))
        precursor_start = planned_failure-int(rng.integers(10, 24))
        failure_kind = str(rng.choice(["wear", "thermal", "vibration", "sudden"],
                                      p=[.34,.25,.26,.15]))
        downtime = 0
        temp_hist=[]; vib_hist=[]; wear_hist=[]
        false_alarms = set(int(z) for z in rng.integers(15, steps-15, size=steps//95))
        for step in range(steps):
            dt = t0+pd.Timedelta(hours=step*FREQ_H)
            if downtime>0:
                rows.append({"timestamp":dt,"machine_id":f"PM-{mi:03d}",
                    "machine_type":kind,"status":"down","failure_event":0,
                    "failure_type":"none", **{k:np.nan for k in FEATURES if k not in
                            ("machine_type","hours_since_service","wear_index","load_pct")},
                    "wear_index":wear,"load_pct":0.,
                    "hours_since_service":(step-last_service_step)*FREQ_H})
                downtime-=1
                if downtime==0:
                    wear=float(rng.uniform(.06,.17));last_service_step=step+1
                    cycle_start=step+1
                    planned_failure=cycle_start+int(rng.integers(100,191))
                    precursor_start=planned_failure-int(rng.integers(10,24))
                    failure_kind=str(rng.choice(["wear","thermal","vibration","sudden"],
                                          p=[.34,.25,.26,.15]))
                    temp_hist=[];vib_hist=[];wear_hist=[]
                continue
            load=float(np.clip(rng.normal(.64,.12),.21,.97))
            wear=float(np.clip(wear+.0013+.0007*load+rng.normal(0,.0002),0,.98))
            base_temp=51+shift+22*wear+5*load+rng.normal(0,1.9)
            base_vib=.3+2.05*wear**2+.2*load+rng.normal(0,.18)
            base_pressure=4.1-.72*wear+rng.normal(0,.13)
            # Solo algunos fallos muestran precursor; otros son repentinos.
            severity=0.0
            if failure_kind!='sudden' and precursor_start<=step<=planned_failure:
                onset=max(1,planned_failure-precursor_start)
                severity=float(np.clip(.3+1.1*(step-precursor_start)/onset,0,1.4))
            if any(0<=step-f<3 for f in false_alarms):
                severity+=float(rng.uniform(.2,.6)) # síntomas que NO causan fallo
            temp=base_temp+severity*(8 if failure_kind=='thermal' else 3.5)
            vib=base_vib+severity*(1.65 if failure_kind=='vibration' else .7)
            pressure=base_pressure-severity*.19
            rpm=1480+72*load-60*wear-severity*11+rng.normal(0,24)
            torque=50+68*load+20*wear+severity*8+rng.normal(0,7)
            temp_hist.append(temp);vib_hist.append(vib);wear_hist.append(wear)
            avg_temp=float(np.mean(temp_hist[-4:]))
            avg_vib=float(np.mean(vib_hist[-4:]))
            wear_delta=float(wear-wear_hist[-13]) if len(wear_hist)>12 else 0.
            fail=int(step==planned_failure)
            rows.append({"timestamp":dt,"machine_id":f"PM-{mi:03d}","machine_type":kind,
                "status":"failure" if fail else "operating","failure_event":fail,
                "failure_type":failure_kind if fail else "none",
                "temperature_c":round(temp,4),"vibration_mm_s":round(max(.03,vib),4),
                "pressure_bar":round(max(.2,pressure),4),"rpm":round(rpm,4),
                "torque_nm":round(torque,4),"wear_index":round(wear,6),
                "load_pct":round(load,6),"hours_since_service":(step-last_service_step)*FREQ_H,
                "temperature_avg_24h":round(avg_temp,4),
                "vibration_avg_24h":round(avg_vib,4),"wear_delta_72h":round(wear_delta,6)})
            if fail: downtime=int(rng.integers(2,5))
    df=pd.DataFrame.from_records(rows)
    df['failure_next_72h']=np.nan
    for _, g in df.groupby('machine_id',sort=False):
        events=g.failure_event.to_numpy(dtype=np.int8)
        label=np.zeros(len(g),dtype=np.int8)
        for ahead in range(1,HORIZON+1):
            label[:-ahead]|=events[ahead:]
        target=label.astype(float);target[-HORIZON:]=np.nan
        df.loc[g.index,'failure_next_72h']=target
    return df

def split(df):
    idx=df.groupby('machine_id',sort=False).cumcount()
    familiar=df.machine_id.str[-3:].astype(int)<=48
    ok=(df.status=='operating') & df.failure_next_72h.notna()
    a=int(STEPS*.65);b=int(STEPS*.80)
    masks={"train":familiar&(idx<a-HORIZON),
           "validation":familiar&(idx>=a)&(idx<b-HORIZON),
           "test_temporal":familiar&(idx>=b)&(idx<STEPS-HORIZON),
           "test_pilot":~familiar&(idx>=b)&(idx<STEPS-HORIZON)}
    out={k:df.loc[v&ok].copy() for k,v in masks.items()}
    assert set(out['test_pilot'].machine_id)=={f'PM-{i:03d}' for i in range(49,61)}
    assert out['train'].timestamp.max()<out['validation'].timestamp.min()
    assert out['validation'].timestamp.max()<out['test_temporal'].timestamp.min()
    return out

if __name__=='__main__':
    df=generate(); parts=split(df)
    print(json.dumps({"rows":len(df),"events":int(df.failure_event.sum()),
        "splits":{k:{"n":len(v),"positive":int(v.failure_next_72h.sum())} for k,v in parts.items()}},indent=2))
