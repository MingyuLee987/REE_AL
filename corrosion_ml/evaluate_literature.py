"""Fixed SVR evaluation; preprocessing fit on training folds only."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split,KFold,GroupKFold
from sklearn.metrics import r2_score,mean_absolute_error,mean_squared_error
from .data import NUM,PROCESS_NUM,CAT,PROCESS_CAT,labels
from .model import fitted
from .paths import ROOT,MODEL

OUT=ROOT/'results/literature_evaluation_20261026'
def metrics(y,p):
    e=np.abs(np.asarray(y)-np.asarray(p))
    return dict(n=len(y),r2_log10=float(r2_score(y,p)),mae_log10=float(mean_absolute_error(y,p)),
        rmse_log10=float(np.sqrt(mean_squared_error(y,p))),geometric_mean_fold_error=float(10**e.mean()),
        fraction_within_factor2=float(np.mean(e<=np.log10(2))),r2_raw=float(r2_score(10**np.asarray(y),10**np.asarray(p))))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=ROOT/'data/verified_377.csv'
    d=pd.read_csv(source,float_precision='round_trip')
    assert len(d)==377 and d.record_id.is_unique and d.source_paper_id.notna().all()
    assert d.target_verified.all()
    for c in NUM+PROCESS_NUM:
        if c not in d:d[c]=np.nan
    for c in CAT+PROCESS_CAT:
        if c not in d:d[c]='missing'
        d[c]=d[c].fillna('missing')
    for c in ['P','S']:
        if c+'_upper_bound' in d:d[c+'_upper_bound_wt_pct']=d[c+'_upper_bound']
    # Restore original element values where source donor fields exist.
    for c in 'C Si Mn P S Cr Ni Mo Cu N'.split():
        if 'donor_'+c in d:d[c]=d['donor_'+c]
        d['original_missing_'+c]=d[c].isna().astype(int)
    y=labels(d);before=hashlib.sha256(MODEL.read_bytes()).hexdigest()
    rows=[];preds=[];splits=[]
    tr,te=train_test_split(np.arange(len(d)),test_size=.2,random_state=42)
    jobs=[('random_holdout',0,tr,te)]
    for method,splitter in [('random_5fold',KFold(5,shuffle=True,random_state=42)),('paper_5fold',GroupKFold(5))]:
        jobs += [(method,i,tr,te) for i,(tr,te) in enumerate(splitter.split(d,groups=d.source_paper_id),1)]
    for method,fold,tr,te in jobs:
        train=d.iloc[tr].drop(columns=['icorr_A_cm2']);test=d.iloc[te].drop(columns=['icorr_A_cm2'])
        model,_=fitted(train,y[tr],n_members=2,seed=42)
        p=model.predict(test);baseline=np.full(len(te),np.median(y[tr]))
        overlap=len(set(train.source_paper_id)&set(test.source_paper_id))
        if method=='paper_5fold':assert overlap==0
        assert set(model.named_steps['composition'].pool_.record_id)<=set(train.record_id)
        for name,values in [('SVR',p),('training_median',baseline)]:
            row=dict(method=method,fold=fold,model=name,n_train=len(tr),n_test=len(te),overlapping_papers=overlap,**metrics(y[te],values));rows.append(row)
            r=d.iloc[te][['record_id','source_paper_id','RE_ppm','RE_element_cat']].copy()
            r['method']=method;r['fold']=fold;r['model']=name;r['observed_log10']=y[te];r['predicted_log10']=values
            r['observed_A_cm2']=10**y[te];r['predicted_A_cm2']=10**values
            r['absolute_fold_error']=10**np.abs(y[te]-values);preds.append(r)
        for role,idx in [('train',tr),('test',te)]:
            for i in idx:splits.append(dict(method=method,fold=fold,role=role,record_id=d.record_id.iloc[i],source_paper_id=d.source_paper_id.iloc[i]))
        print(method,fold,json.dumps(rows[-2]),flush=True)
    m=pd.DataFrame(rows);p=pd.concat(preds,ignore_index=True)
    m.to_csv(OUT/'fold_metrics.csv',index=False);p.to_csv(OUT/'predictions.csv',index=False);pd.DataFrame(splits).to_csv(OUT/'splits.csv',index=False)
    pooled=[]
    for (method,name),g in p.groupby(['method','model']):
        if method!='random_holdout':assert len(g)==len(d) and g.record_id.is_unique
        for group,part in [('all',g),('RE_positive',g[g.RE_ppm.gt(0)])]:
            if len(part)>=2:pooled.append(dict(method=method,model=name,subgroup=group,**metrics(part.observed_log10,part.predicted_log10)))
    pooled=pd.DataFrame(pooled);pooled.to_csv(OUT/'metrics.csv',index=False)
    d[NUM+PROCESS_NUM].isna().mean().rename('missing_fraction').to_csv(OUT/'input_missingness.csv')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,method in zip(axes,['random_holdout','random_5fold','paper_5fold']):
        g=p[(p.method==method)&p.model.eq('SVR')];ax.scatter(g.observed_log10,g.predicted_log10,s=13,alpha=.6)
        bounds=[min(g.observed_log10.min(),g.predicted_log10.min())-.2,max(g.observed_log10.max(),g.predicted_log10.max())+.2]
        ax.plot(bounds,bounds,'k--',lw=1);ax.set(xlim=bounds,ylim=bounds,xlabel='Observed log10(icorr / A cm^-2)',ylabel='Predicted log10(icorr / A cm^-2)',title=method)
        ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'prediction_comparison.png',dpi=180);plt.close(fig)
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==before
    summary=dict(rows=len(d),papers=int(d.source_paper_id.nunique()),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),production_model_sha256=before,production_model_changed=False,
        protocol='Fixed RBF SVR C=10 epsilon=0.15 gamma=scale; no model tuning; fold-local imputation, encoding and scaling; seed42',
        uncertainty_evaluation=False,bootstrap_members=2,note='Central SVR predictions do not depend on bootstrap member count. Historical data and settings are already examined; not a new blind validation.',results=pooled.to_dict('records'))
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(pooled.to_string(index=False),flush=True)

if __name__=='__main__':main()
