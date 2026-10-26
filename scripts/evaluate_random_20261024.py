"""Random holdout main evaluation; fold-local preprocessing only."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np,pandas as pd
from sklearn.model_selection import train_test_split,KFold
from corrosion_ml.data import training_data,labels,score,NUM,PROCESS_NUM,CAT,PROCESS_CAT
from corrosion_ml.model import fitted
OUT=ROOT/'results/random_protocol_20261024';OUT.mkdir(parents=True,exist_ok=True)
raw=pd.read_csv(ROOT/'data/al_expanded_20261024/expanded_source_only.csv',float_precision='round_trip')
verified=raw.target_verified.fillna(False).astype(bool)
eligible=raw[verified & raw.icorr_A_cm2.gt(0)].copy().reset_index(drop=True)
thermal=eligible[eligible.checked_heat_label_available.fillna(False).astype(bool)].copy().reset_index(drop=True)
def prepare(d):
 d=d.copy().reset_index(drop=True)
 for c in NUM+PROCESS_NUM:
  if c not in d:d[c]=np.nan
 for c in CAT+PROCESS_CAT:
  if c not in d:d[c]='missing'
  d[c]=d[c].fillna('missing')
 for c in 'P S'.split():
  if c+'_upper_bound' in d:d[c+'_upper_bound_wt_pct']=d[c+'_upper_bound']
 return d
metrics=[];predictions=[];splits=[]
def run(d,cohort,method,tr,te,fold=0):
 d=prepare(d);y=labels(d);model,_=fitted(d.iloc[tr],y[tr],n_members=2,seed=42)
 predicted=model.predict(d.iloc[te].drop(columns=['icorr_A_cm2']))
 row=dict(cohort=cohort,method=method,fold=fold,n_total=len(d),n_train=len(tr),n_test=len(te),n_papers=int(d.source_paper_id.nunique()),**score(y[te],predicted));metrics.append(row)
 for i,p in zip(te,predicted):predictions.append(dict(cohort=cohort,method=method,fold=fold,record_id=d.record_id.iloc[i],source_paper_id=d.source_paper_id.iloc[i],observed_log10=y[i],predicted_log10=p,observed_A_cm2=10**y[i],predicted_A_cm2=10**p))
 for role,idx in [('train',tr),('test',te)]:
  for i in idx:splits.append(dict(cohort=cohort,method=method,fold=fold,role=role,record_id=d.record_id.iloc[i]))
 assert set(model.named_steps['composition'].pool_.record_id).issubset(set(d.iloc[tr].record_id))
 print(json.dumps(row),flush=True)
for name,d in [('operating_279',training_data()),('expanded_verified',eligible),('expanded_thermal_verified',thermal)]:
 tr,te=train_test_split(np.arange(len(d)),test_size=.2,shuffle=True,random_state=42)
 run(d,name,'random_holdout_80_20',tr,te)
for fold,(tr,te) in enumerate(KFold(5,shuffle=True,random_state=42).split(eligible),1):run(eligible,'expanded_verified','random_5fold',tr,te,fold)
m=pd.DataFrame(metrics);p=pd.DataFrame(predictions)
m.to_csv(OUT/'metrics.csv',index=False);p.to_csv(OUT/'predictions.csv',index=False);pd.DataFrame(splits).to_csv(OUT/'splits.csv',index=False)
cv=m[m.method.eq('random_5fold')];oof=p[p.method.eq('random_5fold')]
summary=dict(main_split='train_test_split(test_size=0.2, shuffle=True, random_state=42)',main_evaluation=m[m.method.eq('random_holdout_80_20')].to_dict('records'),cv_mean_r2=float(cv.r2_log10.mean()),cv_sd_r2=float(cv.r2_log10.std()),cv_pooled=score(oof.observed_log10,oof.predicted_log10),expanded_rows=len(raw),expanded_verified_rows=len(eligible),expanded_thermal_verified_rows=len(thermal),excluded_unverified=len(raw)-len(eligible),hyperparameter_search_performed=False,production_model_modified=False,primary_target='log10(icorr / A cm^-2)',bootstrap_members_for_evaluation=2)
(OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
