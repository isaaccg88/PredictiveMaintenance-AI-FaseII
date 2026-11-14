"""Evaluación V2 reproducible sin contaminación de datos de prueba.

Threshold seleccionado exclusivamente en validación; prueba temporal y piloto
no se usan para elegir modelo, features ni umbral. Dataset totalmente sintético.
"""
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (average_precision_score, roc_auc_score, precision_score,
                             recall_score, f1_score, fbeta_score, confusion_matrix)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from .simulator import generate,split,FEATURES,SEED,HORIZON,HERE

ART=HERE/'artifacts';RES=HERE/'results'
def metrics(y,prob,th):
    y=np.asarray(y,dtype=int); pred=(np.asarray(prob)>=th).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {"samples":len(y),"positives":int(y.sum()),"prevalence":float(y.mean()),
        "threshold":float(th),"precision":float(precision_score(y,pred,zero_division=0)),
        "recall":float(recall_score(y,pred,zero_division=0)),
        "f1":float(f1_score(y,pred,zero_division=0)),
        "f2":float(fbeta_score(y,pred,beta=2,zero_division=0)),
        "roc_auc":float(roc_auc_score(y,prob)),
        "average_precision":float(average_precision_score(y,prob)),
        "tp":int(tp),"fp":int(fp),"fn":int(fn),"tn":int(tn)}
def event_recall(df,partition,prob,th):
    s=partition[['machine_id','timestamp','failure_next_72h']].copy()
    s['alert']=np.asarray(prob)>=th
    found=0; total=0; leads=[]
    for mid,g in s.groupby('machine_id'):
        start=g.timestamp.min()+pd.Timedelta(hours=72)
        end=g.timestamp.max()
        events=df.loc[(df.machine_id==mid)&(df.failure_event==1)&
                     (df.timestamp>=start)&(df.timestamp<=end),'timestamp']
        alarms=pd.DatetimeIndex(g.loc[g.alert,'timestamp'])
        for ev in events:
            total+=1
            previous=alarms[(alarms>=ev-pd.Timedelta(hours=72))&(alarms<ev)]
            if len(previous):
                found+=1;leads.append((ev-previous.min()).total_seconds()/3600)
    false_windows=int(((s.failure_next_72h==0)&s.alert).sum())
    return {"failure_events_evaluable":total,"failure_events_detected":found,
       "event_recall":found/total if total else None,
       "mean_first_alert_lead_hours":float(np.mean(leads)) if leads else None,
       "false_positive_windows":false_windows,
       "false_windows_per_machine_week":float(false_windows/(len(s)/28)),
       "note":"False alarm count is per six-hour window, not deduplicated episodes"}

def main(track_mlflow=False):
    ART.mkdir(parents=True,exist_ok=True);RES.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter();df=generate();part=split(df)
    num=[x for x in FEATURES if x!='machine_type']
    pre=ColumnTransformer([('num',SimpleImputer(strategy='median'),num),
                           ('cat',OneHotEncoder(handle_unknown='ignore'),['machine_type'])])
    model=Pipeline([('prepare',pre),('model',RandomForestClassifier(
        n_estimators=130,max_depth=12,min_samples_leaf=7,max_features='sqrt',
        class_weight='balanced_subsample',random_state=SEED,n_jobs=2))])
    model.fit(part['train'][FEATURES],part['train'].failure_next_72h.astype(int))
    val=part['validation']; vy=val.failure_next_72h.astype(int).values
    vp=model.predict_proba(val[FEATURES])[:,1]
    candidates=[metrics(vy,vp,round(float(t),3)) for t in np.arange(.05,.951,.01)]
    eligible=[r for r in candidates if r['precision']>=.35]
    choice=max(eligible or candidates,key=lambda x:(x['f2'],x['precision'],x['recall']))
    th=choice['threshold']; result={'validation':choice}
    for name in ['test_temporal','test_pilot']:
        z=part[name]; y=z.failure_next_72h.astype(int).values
        p=model.predict_proba(z[FEATURES])[:,1]
        result[name]={**metrics(y,p,th),**event_recall(df,z,p,th)}
    snapshot=[]
    pilot_ids={f'PM-{i:03d}' for i in range(49,61)}
    for mid,g in df[df.machine_id.isin(pilot_ids)].groupby('machine_id'):
        last=g[g.status=='operating'].iloc[-1]
        snapshot.append({'machine_id':mid,'timestamp':last.timestamp.isoformat(),
                         **{k:str(last[k]) if k=='machine_type' else float(last[k]) for k in FEATURES}})
    joblib.dump(model,ART/'model_v2.joblib',compress=3)
    (ART/'pilot_v2.json').write_text(json.dumps({'synthetic':True,'machines':snapshot},indent=2)+'\n')
    metadata={'model':'RandomForest','seed':SEED,'horizon_hours':72,
        'interval_hours':6,'features':FEATURES,'threshold':th,
        'threshold_source':'validation_only','machines_train':48,'machines_holdout':12,
        'synthetic':True,'model_sha256':hashlib.sha256((ART/'model_v2.joblib').read_bytes()).hexdigest()}
    (ART/'metadata_v2.json').write_text(json.dumps(metadata,indent=2)+'\n')
    # Public report must distinguish cross-dataset change from model gain.
    report={'status':'measured_on_synthetic_v2','generator_version':2,
      'baseline_faseii_reported_on_v1_pilot':{'precision':.1636363636,'recall':.375,
          'f1':.2278481013,'roc_auc':.8621312152,'average_precision':.2416871022,
          'event_recall':8/11,'events':11},
      'not_directly_comparable':True,'seed':SEED,'rows':len(df),
      'failure_events_total':int(df.failure_event.sum()),
      'splits':{k:{'rows':len(v),'positives':int(v.failure_next_72h.sum())} for k,v in part.items()},
      'model':metadata,'metrics':result,'elapsed_seconds':round(time.perf_counter()-start,2)}
    (RES/'evaluation_v2.json').write_text(json.dumps(report,indent=2)+'\n')
    (RES/'baseline_sensors.json').write_text(json.dumps({
       'temperature_c':part['test_pilot'].temperature_c.tolist()[:2000],
       'vibration_mm_s':part['test_pilot'].vibration_mm_s.tolist()[:2000]},indent=2)+'\n')
    if track_mlflow:
        import mlflow
        mlflow.set_tracking_uri((HERE/'mlruns').resolve().as_uri())
        mlflow.set_experiment('PredictiveMaintenanceAI_Actividad8_V2')
        with mlflow.start_run(run_name='synthetic_v2_72h'):
            mlflow.log_params({'seed':SEED,'horizon_hours':72,'holdout_machines':12,'threshold':th})
            for group,vals in result.items():
                for metric in ['precision','recall','f1','roc_auc','average_precision']:
                    mlflow.log_metric(f'{group}_{metric}',vals[metric])
            mlflow.log_artifact(str(RES/'evaluation_v2.json'))
            mlflow.log_artifact(str(ART/'metadata_v2.json'))
            (RES/'mlflow_run.json').write_text(json.dumps({'run_id':mlflow.active_run().info.run_id,
                'experiment':'PredictiveMaintenanceAI_Actividad8_V2'},indent=2)+'\n')
    print(json.dumps({'threshold':th,'test_pilot':result['test_pilot'],
                       'events_all':report['failure_events_total']},indent=2))
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mlflow',action='store_true');args=p.parse_args()
    main(track_mlflow=args.mlflow)
