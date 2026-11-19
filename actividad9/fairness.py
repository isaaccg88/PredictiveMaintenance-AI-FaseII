"""Auditoría de desempeño por tipo de máquina con datos sintéticos holdout.

Fairness OPERACIONAL: igualdad de oportunidad (TPR) y FPR entre tipos A/B/C.
No hay atributos de personas ni se infieren grupos demográficos.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import joblib
from sklearn.metrics import confusion_matrix,roc_auc_score,average_precision_score
from actividad8.simulator import generate, split, FEATURES, HERE as A8

OUT=Path(__file__).resolve().parent/"evidence"

def div(x,y):
    return None if y==0 else float(x/y)

def calculate(y,p,threshold):
    pred=(p>=threshold).astype(int)
    tn,fp,fn,tp=[int(z) for z in confusion_matrix(y,pred,labels=[0,1]).ravel()]
    return {
      "n":int(len(y)),"positive":int(np.sum(y)), "negative":int(len(y)-np.sum(y)),
      "tp":tp,"fp":fp,"fn":fn,"tn":tn,
      "precision":div(tp,tp+fp),"recall_tpr":div(tp,tp+fn),
      "fpr":div(fp,fp+tn),"fnr":div(fn,tp+fn),
      "predicted_positive_rate":float(pred.mean()),
      "roc_auc":float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,
      "average_precision":float(average_precision_score(y,p)) if np.sum(y)>0 else None
    }

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    model_file=A8/"artifacts"/"model_v2.joblib"
    md=json.loads((A8/"artifacts"/"metadata_v2.json").read_text())
    if not model_file.exists(): raise FileNotFoundError("Ejecutar entrenamiento V2 primero")
    model=joblib.load(model_file)
    test=split(generate())["test_pilot"]
    if set(test.machine_type)!=set("ABC"): raise AssertionError("Tipos incompletos")
    th=float(md["threshold"])
    groups={}
    for g,subset in test.groupby("machine_type"):
        y=subset.failure_next_72h.astype(int).to_numpy()
        p=model.predict_proba(subset[FEATURES])[:,1]
        groups[g]={**calculate(y,p,th),"machines":int(subset.machine_id.nunique())}
    def gap(key):
        valid=[x[key] for x in groups.values() if x[key] is not None]
        return round(max(valid)-min(valid),6) if len(valid)==3 else None
    worst=min([x["recall_tpr"] for x in groups.values() if x["recall_tpr"] is not None])
    out={"status":"MEASURED_ON_SYNTHETIC_HOLDOUT",
      "model":"RandomForest V2 72h","synthetic":True,
      "threshold":th,"grouping_feature":"machine_type","groups":groups,
      "gaps":{"equal_opportunity_tpr_gap":gap("recall_tpr"),
              "false_positive_rate_gap":gap("fpr"),
              "precision_gap":gap("precision")},
      "tpr_floor":worst,
      "policy_proposal":{"tpr_gap_review_threshold":0.10,
         "minimum_positive_samples_per_group":30,
         "gate":"REVIEW_BY_HUMAN_NOT_AUTOMATIC_CERTIFICATION"},
      "methodology":"Machine-type audit (A/B/C) on 12 held-out machines, 4 machines per type. A technical slice analysis; NOT demographic or legal protected-class fairness.",
      "caveats":["No real human personal or protected traits in data.",
        "Only four pilot machines of each type; within-group observations are temporally correlated.",
        "Performance gaps may reflect synthetic generator mechanisms, not discrimination.",
        "Confidence intervals require machine-level bootstrap / external validation before deployment.",
        "Group gap values are descriptive, not proof of fairness or safety."]
    }
    (OUT/"fairness_machine_types.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    lines=["# Fairness operacional en tres tipos de máquina",
      "","**Dato 100% sintético. No es fairness demográfica.**",
      "", "| Tipo | Máquinas | Ventanas | Positivas | TPR/Recall | FPR | Precision | ROC-AUC |",
      "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for g,x in groups.items():
        fmt=lambda v:"N/D" if v is None else f"{v:.3f}"
        lines.append(f"| {g} | {x['machines']} | {x['n']} | {x['positive']} | {fmt(x['recall_tpr'])} | {fmt(x['fpr'])} | {fmt(x['precision'])} | {fmt(x['roc_auc'])} |")
    lines+=["",f"**Brecha TPR entre tipos:** {gap('recall_tpr'):.3f} (máximo − mínimo).",
    f"**Brecha FPR entre tipos:** {gap('fpr'):.3f} (máximo − mínimo).",
    "","**Interpretación:** la equidad operacional aquí evalúa paridad de detección por tipo de equipo. No prueba ausencia de sesgo en máquinas industriales reales.",
    "Los cuatro equipos por subgrupo limitan inferencia estadística; requieren más unidades independientes y etiquetas maduras.",
    "Se propone revisión técnica si la brecha TPR >0.10; este umbral es una política propuesta, no una norma legal.",
    ""]
    (OUT/"fairness_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"groups":{k:{"TPR":v["recall_tpr"],"FPR":v["fpr"],"n":v["n"]} for k,v in groups.items()}, "gaps":out["gaps"]},indent=2))
    return out

if __name__=="__main__":main()
