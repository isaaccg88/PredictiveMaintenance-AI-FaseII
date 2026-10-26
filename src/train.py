"""Train a 72-hour risk model; all measurements and outcomes are SYNTHETIC."""
from __future__ import annotations
import json
import time
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (average_precision_score, roc_auc_score,
    precision_recall_curve, roc_curve, confusion_matrix, f1_score,
    fbeta_score, precision_score, recall_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from .simulation import (generate,chronological_split,persist_data,
                         ROOT,ARTIFACTS,RESULTS,FEATURES,HORIZON,STEPS,SEED)

def score(y,p,threshold):
    y=np.asarray(y,dtype=int); p=np.asarray(p,dtype=float)
    z=(p>=threshold).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,z,labels=[0,1]).ravel()
    return {"threshold":round(float(threshold),4),
        "precision":float(precision_score(y,z,zero_division=0)),
        "recall":float(recall_score(y,z,zero_division=0)),
        "f1":float(f1_score(y,z,zero_division=0)),
        "f2":float(fbeta_score(y,z,beta=2,zero_division=0)),
        "roc_auc":float(roc_auc_score(y,p)),
        "average_precision":float(average_precision_score(y,p)),
        "tn":int(tn),"fp":int(fp),"fn":int(fn),"tp":int(tp),
        "positives":int(y.sum()),"samples":len(y)}
def threshold_search(y,p):
    rows=[score(y,p,v) for v in np.round(np.arange(.05,.851,.01),2)]
    eligible=[x for x in rows if x["precision"]>=.20]
    selected=max(eligible or rows,key=lambda r:(r["f2"],r["recall"],r["precision"]))
    return selected,pd.DataFrame(rows),bool(eligible)

def event_metrics(df,p,threshold):
    """Event recall and lead time on a complete test interval.

    An event counts if its preceding 12 measurements contain an alarm
    before the event. False-alert rate: negative labelled alert rows / week.
    The synthetic timebase is fixed at one observation every 6h.
    """
    temp=df[["machine_id","timestamp","failure_next_72h"]].copy()
    temp["alert"]=np.asarray(p)>=threshold
    event_flags={}
    for machine_id,m in temp.groupby("machine_id"):
        event_flags[machine_id]={x:i for i,x in enumerate(m.timestamp)}
    # Metrics of labelled windows, not "event" recall, are provided here.
    # True event recall is calculated against the complete event log outside.
    false_alert=int(((temp.failure_next_72h==0)&temp.alert).sum())
    machine_weeks=len(temp)/(4*7)
    return {"false_alerts_per_machine_week":float(false_alert/machine_weeks),
            "false_positive_alert_windows":false_alert,
            "alert_windows":int(temp.alert.sum()),
            "metric_level":"six-hour prediction windows, not distinct alarm episodes"}

def event_lead_time(full,partition,p,threshold):
    """Recall of distinct synthetic failures using alarms in prior 72h."""
    a=partition[["machine_id","timestamp"]].copy()
    a["alert"]=np.asarray(p)>=threshold
    starts=partition.groupby("machine_id").timestamp.min().to_dict()
    stops=partition.groupby("machine_id").timestamp.max().to_dict()
    flagged=a.loc[a.alert]
    per_machine={k:pd.DatetimeIndex(v.timestamp) for k,v in flagged.groupby("machine_id")}
    outcomes=[]
    for machine_id,start in starts.items():
        events=full.loc[
            (full.machine_id==machine_id)&(full.failure_event==1)&
            (full.timestamp>=start+pd.Timedelta(hours=72))&
            (full.timestamp<=stops[machine_id]),"timestamp"
        ]
        alarms=per_machine.get(machine_id,pd.DatetimeIndex([],tz="UTC"))
        for event_time in events:
            prior=alarms[(alarms>=event_time-pd.Timedelta(hours=72))&
                          (alarms<event_time)]
            outcomes.append({"machine_id":machine_id,
                             "event_timestamp":str(event_time),
                             "detected":len(prior)>0,
                             "lead_time_hours":float((event_time-prior.min()).total_seconds()/3600)
                                               if len(prior) else None})
    observed=pd.DataFrame(outcomes)
    return ({
        "failure_events_evaluable":len(observed),
        "failure_events_detected":int(observed.detected.sum()) if len(observed) else 0,
        "event_recall":float(observed.detected.mean()) if len(observed) else None,
        "mean_first_alert_lead_time_hours":float(observed.loc[observed.detected,"lead_time_hours"].mean())
                 if len(observed) and observed.detected.any() else None
    },observed)

def main():
    start=time.perf_counter()
    full=generate()
    parts=chronological_split(full)
    meta=persist_data(full,parts)
    ARTIFACTS.mkdir(parents=True,exist_ok=True)
    fig=RESULTS/"figures";fig.mkdir(parents=True,exist_ok=True)
    tr,va,te,pilot=[parts[k] for k in ("train","validation","test_temporal","test_unseen_machines")]
    xtrain=tr[FEATURES];ytrain=tr.failure_next_72h.astype(int).to_numpy()
    yval=va.failure_next_72h.astype(int).to_numpy()
    preprocessing=ColumnTransformer([
        ("numeric",SimpleImputer(strategy="median"),
         [f for f in FEATURES if f!="machine_type"]),
        ("categorical",OneHotEncoder(handle_unknown="ignore"),["machine_type"])
    ])
    pipe=Pipeline([("preprocess",preprocessing),
                   ("model",RandomForestClassifier(
                       n_estimators=110,max_depth=11,min_samples_leaf=9,
                       max_features="sqrt",class_weight="balanced_subsample",
                       random_state=SEED,n_jobs=2))])
    pipe.fit(xtrain,ytrain)
    pv=pipe.predict_proba(va[FEATURES])[:,1]
    chosen,grid,feasible=threshold_search(yval,pv)
    threshold=chosen["threshold"]
    baseline=DummyClassifier(strategy="prior")
    baseline.fit(xtrain,ytrain)
    grid.to_csv(RESULTS/"threshold_validation.csv",index=False)
    outputs={"validation":chosen}
    records=[]
    for name,data in [("test_temporal",te),("test_unseen_machines",pilot)]:
        y=data.failure_next_72h.astype(int).to_numpy()
        pred=pipe.predict_proba(data[FEATURES])[:,1]
        outputs[name]=score(y,pred,threshold)
        outputs[name].update(event_metrics(data,pred,threshold))
        bm=baseline.predict_proba(data[FEATURES])[:,1]
        outputs[name]["baseline_average_precision"]=float(average_precision_score(y,bm))
        outputs[name]["prevalence"]=float(y.mean())
        em,ev=event_lead_time(full,data,pred,threshold)
        outputs[name].update(em)
        ev.to_csv(RESULTS/f"failure_events_{name}.csv",index=False)
        prediction=data[["timestamp","machine_id","failure_next_72h"]].copy()
        prediction["probability_72h"]=pred
        prediction["risk_alert"]=(pred>=threshold).astype(int)
        prediction.to_csv(RESULTS/f"predictions_{name}.csv",index=False)
        precision,recall,_=precision_recall_curve(y,pred)
        fpr,tpr,_=roc_curve(y,pred)
        plt.figure(figsize=(7,4));plt.plot(recall,precision,label="Modelo RF")
        plt.axhline(y.mean(),ls="--",label="Prevalencia / baseline")
        plt.xlabel("Recall");plt.ylabel("Precision")
        plt.title(f"Precision–Recall | {name} (sintético)")
        plt.legend();plt.tight_layout()
        plt.savefig(fig/f"pr_{name}.png",dpi=160);plt.close()
        records.append({"partition":name,**outputs[name]})
        print(name,{"n":len(y),"positive":int(y.sum()),"F1":outputs[name]["f1"],
                    "AP":outputs[name]["average_precision"],"event_recall":outputs[name]["event_recall"]})
    pd.DataFrame(records).to_csv(RESULTS/"model_metrics.csv",index=False)
    # Latest simulated reading of 12 holdout machines: operational demo.
    snapshots=[]
    for mid,g in full.loc[full.machine_id.isin(pilot.machine_id.unique())].groupby("machine_id"):
        last=g.loc[g.status=="operating"].iloc[-1]
        d={k:(str(last[k]) if k in ("timestamp","machine_id","machine_type") else
              float(last[k])) for k in ["timestamp","machine_id"]+FEATURES}
        snapshots.append(d)
    assert len(snapshots)==12
    (ARTIFACTS/"pilot_snapshot.json").write_text(
        json.dumps({"synthetic":True,"data_timestamp_label":"SIMULATED UTC",
             "machines":snapshots},ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    joblib.dump(pipe,ARTIFACTS/"risk72h_model.joblib",compress=3)
    model_meta={"horizon_hours":72,"frequency_hours":6,
        "model_kind":"RandomForestClassifier","source":"100% synthetic scenario",
        "seed":SEED,"features":FEATURES,"threshold":threshold,
        "threshold_selected_on":"validation",
        "minimum_precision_validation_feasible":feasible,
        "dataset_sha256":meta["sha256_csv"],
        "pilot_unseen_machines":12,"training_machines":48}
    (ARTIFACTS/"model_metadata.json").write_text(
        json.dumps(model_meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    importances=pipe.named_steps["model"].feature_importances_
    encoded=pipe.named_steps["preprocess"].get_feature_names_out()
    pd.DataFrame({"feature":encoded,"importance":importances}).sort_values(
        "importance",ascending=False).to_csv(RESULTS/"feature_importance.csv",index=False)
    result={"provenance":"entirely synthetic simulated industrial scenario",
            "72h_target_definition":"at least one event in next 12 readings, excluding t",
            "training_machines":48,"pilot_machines":12,"periods_are_chronological":True,
            "window_purge_steps":12,"threshold_validation":chosen,
            "metrics":outputs,"elapsed_seconds":round(time.perf_counter()-start,2),
            "caution":"Metrics are only meaningful within this synthetic generator; no industrial validation"}
    (RESULTS/"evaluation.json").write_text(json.dumps(
        result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assert all(outputs[n]["samples"]>1000 for n in ("test_temporal","test_unseen_machines"))
    print("TRAINING COMPLETE; threshold",threshold,"records",len(full),"model",ARTIFACTS/"risk72h_model.joblib")
    return result

if __name__=="__main__":
    main()
