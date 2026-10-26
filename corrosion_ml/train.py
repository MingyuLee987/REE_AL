"""Evaluate and refit only the selected environment SVR."""
import argparse,hashlib,json
import importlib.metadata
import joblib,numpy as np,pandas as pd
from .data import training_data,labels,score,validation_splits
from .model import fitted
from .paths import DATA,MODELS,MODEL,RESULTS

def save_model(bundle,evaluation=None):
    MODELS.mkdir(parents=True,exist_ok=True);joblib.dump(bundle,MODEL)
    info=dict(model='Environment SVR with bootstrap uncertainty',central=dict(C=10.,epsilon=.15,kernel='rbf',gamma='scale'),bootstrap_members=bundle.named_steps['model'].n_members,seed=bundle.named_steps['model'].seed,training_rows=len(bundle.training_record_ids_),uses_phase_fractions=False,model_sha256=hashlib.sha256(MODEL.read_bytes()).hexdigest(),training_sha256=hashlib.sha256((DATA/'training.csv').read_bytes()).hexdigest(),versions={n:importlib.metadata.version(n) for n in ['numpy','pandas','scikit-learn','joblib']})
    if evaluation is not None:info['evaluation']=evaluation
    (MODELS/'manifest.json').write_text(json.dumps(info,indent=2),encoding='utf-8')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evaluate-only',action='store_true');p.add_argument('--members',type=int,default=15)
    args=p.parse_args()
    if args.members<2:p.error('At least two bootstrap members required')
    d=training_data();y=labels(d);out=RESULTS/'training';out.mkdir(parents=True,exist_ok=True)
    rows=[];predictions=[];splits=[]
    for fold,(tr,te) in enumerate(validation_splits(d,5,'random'),1):
        pipeline,_=fitted(d.iloc[tr],y[tr],args.members,42)
        predicted=pipeline.predict(d.iloc[te].drop(columns=['icorr_A_cm2']))
        rows.append(dict(fold=fold,n_train=len(tr),n_test=len(te),**score(y[te],predicted)))
        for i,value in zip(te,predicted):predictions.append(dict(fold=fold,record_id=d.record_id.iloc[i],observed_log10=y[i],predicted_log10=value))
        for role,idx in [('train',tr),('test',te)]:
            for i in idx:splits.append(dict(fold=fold,role=role,record_id=d.record_id.iloc[i]))
        print(f'Fold {fold}/5 test R2(log10)={rows[-1]["r2_log10"]:.4f}',flush=True)
    frame=pd.DataFrame(rows);pred=pd.DataFrame(predictions)
    summary=dict(model='fixed environment SVR',split='random-row KFold(5, shuffle=True, random_state=42)',records=len(d),mean_r2_log10=float(frame.r2_log10.mean()),std_r2_log10=float(frame.r2_log10.std()),mean_rmse_log10=float(frame.rmse_log10.mean()),mean_mae_log10=float(frame.mae_log10.mean()),pooled_oof=score(pred.observed_log10,pred.predicted_log10))
    frame.to_csv(out/'metrics.csv',index=False);pred.to_csv(out/'predictions.csv',index=False);pd.DataFrame(splits).to_csv(out/'splits.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    if not args.evaluate_only:
        bundle,_=fitted(d,y,args.members,42);save_model(bundle,summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
