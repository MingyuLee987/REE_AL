"""Nested random CV for ExtraTrees-ranked feature selection with fixed SVR."""
import json,hashlib
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import KFold
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.svm import SVR
from .paths import ROOT,MODEL
from .data import NUM,PROCESS_NUM,CAT,PROCESS_CAT,labels
from .composition import CompositionDonorImputer
from .features import CorrosionFeatures
from .model import make_pre
from .evaluate_literature import metrics

OUT=ROOT/'results/feature_selection_20261026'
KS=[10,20,40,80,'all']

def prepare():
    d=pd.read_csv(ROOT/'data/verified_377.csv',float_precision='round_trip')
    for c in NUM+PROCESS_NUM:
        if c not in d:d[c]=np.nan
    for c in CAT+PROCESS_CAT:
        if c not in d:d[c]='missing'
        d[c]=d[c].fillna('missing')
    for c in ['P','S']:
        if c+'_upper_bound' in d:d[c+'_upper_bound_wt_pct']=d[c+'_upper_bound']
    for c in 'C Si Mn P S Cr Ni Mo Cu N'.split():
        d['original_missing_'+c]=d[c].isna().astype(int)
    return d.drop(columns=['icorr_A_cm2']),labels(d)

def encode(train,test):
    donor=CompositionDonorImputer().fit(train)
    feat=CorrosionFeatures();a=feat.fit_transform(donor.transform(train));b=feat.transform(donor.transform(test))
    pre=make_pre(a);z=pre.fit_transform(a);v=pre.transform(b)
    return z,v,donor,feat,pre

def ranking(z,y):
    r=ExtraTreesRegressor(n_estimators=200,min_samples_leaf=2,max_features=1.,random_state=42,n_jobs=2).fit(z,y)
    eligible=np.flatnonzero(np.var(z,axis=0)>1e-12)
    order=eligible[np.argsort(-r.feature_importances_[eligible],kind='stable')]
    return order,r.feature_importances_

def indices(order,k,n):return np.arange(n) if k=='all' else order[:min(k,len(order))]
def fit_svr(z,y):return SVR(C=10,epsilon=.15,gamma='scale').fit(z,y)

def choose(d,y,tag):
    records=[]
    for fold,(tr,va) in enumerate(KFold(3,shuffle=True,random_state=71).split(d),1):
        z,v,*_=encode(d.iloc[tr],d.iloc[va]);order,_=ranking(z,y[tr])
        for k in KS:
            ix=indices(order,k,z.shape[1]);p=fit_svr(z[:,ix],y[tr]).predict(v[:,ix])
            records.append(dict(stage=tag,inner_fold=fold,k=str(k),mae=float(np.mean(np.abs(y[va]-p)))))
    scores=pd.DataFrame(records).groupby('k').mae.mean()
    best=min(KS,key=lambda k:scores[str(k)])
    return best,records

def main():
    OUT.mkdir(parents=True,exist_ok=True);d,y=prepare();before=hashlib.sha256(MODEL.read_bytes()).hexdigest()
    predictions=[];folds=[];selected=[];inner=[]
    for fold,(tr,te) in enumerate(KFold(5,shuffle=True,random_state=42).split(d),1):
        train=d.iloc[tr];test=d.iloc[te]
        best,rec=choose(train,y[tr],f'outer_{fold}');inner+=rec
        z,v,donor,feat,pre=encode(train,test);order,importance=ranking(z,y[tr]);ix=indices(order,best,z.shape[1])
        for name,cols in [('full',np.arange(z.shape[1])),('selected',ix)]:
            p=fit_svr(z[:,cols],y[tr]).predict(v[:,cols])
            folds.append(dict(fold=fold,model=name,k_chosen=str(best),n_features=len(cols),**metrics(y[te],p)))
            for j,i in enumerate(te):predictions.append(dict(fold=fold,model=name,record_id=d.record_id.iloc[i],source_paper_id=d.source_paper_id.iloc[i],observed_log10=y[i],predicted_log10=p[j]))
        names=pre.get_feature_names_out()
        for i in ix:selected.append(dict(fold=fold,feature=names[i],importance=float(importance[i])))
        print('FOLD',fold,'chosen',best,'full',z.shape[1],'selected',len(ix),'R2',folds[-1]['r2_log10'],flush=True)
    p=pd.DataFrame(predictions);f=pd.DataFrame(folds)
    summary=[]
    for name,g in p.groupby('model'):
        assert len(g)==377 and g.record_id.is_unique
        sub=f[f.model.eq(name)]
        summary.append(dict(model=name,mean_fold_r2=float(sub.r2_log10.mean()),sd_fold_r2=float(sub.r2_log10.std()),**metrics(g.observed_log10,g.predicted_log10)))
    p.to_csv(OUT/'predictions.csv',index=False);f.to_csv(OUT/'fold_metrics.csv',index=False)
    pd.DataFrame(summary).to_csv(OUT/'metrics.csv',index=False)
    s=pd.DataFrame(selected);s.to_csv(OUT/'selected_features_by_fold.csv',index=False)
    s.groupby('feature').agg(selected_folds=('fold','nunique'),mean_importance=('importance','mean')).sort_values(['selected_folds','mean_importance'],ascending=False).to_csv(OUT/'feature_stability.csv')
    best,rec=choose(d,y,'final_development');inner+=rec
    z,_,donor,feat,pre=encode(d,d.iloc[:1]);order,importance=ranking(z,y);ix=indices(order,best,z.shape[1]);svr=fit_svr(z[:,ix],y)
    names=pre.get_feature_names_out()
    pd.DataFrame(dict(feature=names[ix],importance=importance[ix])).sort_values('importance',ascending=False).to_csv(OUT/'final_selected_features.csv',index=False)
    pd.DataFrame(inner).to_csv(OUT/'inner_cv_selection.csv',index=False)
    joblib.dump(dict(donor=donor,features=feat,preprocessor=pre,selected_indices=ix,model=svr,training_ids=list(d.record_id)),OUT/'candidate_model.joblib')
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==before
    report=dict(protocol='Outer random 5-fold seed42; inner random 3-fold seed71; ExtraTrees ranking; k selected by inner MAE; fixed SVR; fold-local preprocessing',candidate_k=KS,results=summary,final_k=str(best),final_encoded_features=len(ix),production_model_changed=False,warning='Development comparison, not fresh blind validation. Random folds may share source papers. Encoded features are not original experimental variables.')
    (OUT/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
