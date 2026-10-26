"""Nested comparison of SHAP, Lasso, mutual information and tree selectors."""
import json,hashlib
import numpy as np
import pandas as pd
import joblib,shap
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import Lasso
from sklearn.feature_selection import mutual_info_regression
from sklearn.model_selection import KFold
from .select_features import prepare,encode,indices,fit_svr,KS
from .evaluate_literature import metrics
from .paths import ROOT,MODEL

OUT=ROOT/'results/selector_comparison_20261026'
METHODS=['tree_importance','tree_SHAP','Lasso','mutual_information']

def rankings(z,y):
    eligible=np.flatnonzero(np.var(z,axis=0)>1e-12)
    tree=ExtraTreesRegressor(n_estimators=200,min_samples_leaf=2,max_features=1.,random_state=42,n_jobs=2).fit(z,y)
    # These SHAP values explain the training-only tree selector, not the downstream SVR.
    explainer=shap.TreeExplainer(tree,feature_perturbation='tree_path_dependent')
    sv=np.asarray(explainer.shap_values(z,check_additivity=True))
    scores={'tree_importance':tree.feature_importances_,'tree_SHAP':np.mean(np.abs(sv),axis=0)}
    # A fixed alpha provides a regularized linear ranking; subset size is tuned inside CV.
    linear=Lasso(alpha=.01,max_iter=50000,tol=1e-5).fit(z,y)
    scores['Lasso']=np.abs(linear.coef_)
    mi=np.zeros(z.shape[1]);disc=np.array([len(np.unique(z[:,j]))<=2 for j in eligible])
    mi[eligible]=mutual_info_regression(z[:,eligible],y,discrete_features=disc,random_state=42)
    scores['mutual_information']=mi
    orders={}
    for name,score in scores.items():
        valid=eligible[score[eligible]>1e-12]
        orders[name]=valid[np.argsort(-score[valid],kind='stable')]
        if not len(valid):raise ValueError('No nonzero features: '+name)
    return orders,scores,sv

def choices(d,y,stage):
    records=[]
    for fold,(tr,va) in enumerate(KFold(3,shuffle=True,random_state=71).split(d),1):
        z,v,*_=encode(d.iloc[tr],d.iloc[va]);orders,_,_=rankings(z,y[tr])
        full=fit_svr(z,y[tr]).predict(v)
        for name in METHODS:
            for k in KS:
                ix=indices(orders[name],k,z.shape[1])
                p=full if k=='all' else fit_svr(z[:,ix],y[tr]).predict(v[:,ix])
                records.append(dict(stage=stage,inner_fold=fold,method=name,k=str(k),n_features=len(ix),mae=float(np.mean(np.abs(y[va]-p)))))
        print(stage,'inner',fold,'done',flush=True)
    means=pd.DataFrame(records).groupby(['method','k']).mae.mean()
    best={name:min(KS,key=lambda k:means[name,str(k)]) for name in METHODS}
    chosen=min(METHODS,key=lambda name:means[name,str(best[name])])
    return best,chosen,records

def main():
    OUT.mkdir(parents=True,exist_ok=True);d,y=prepare();before=hashlib.sha256(MODEL.read_bytes()).hexdigest()
    predictions=[];folds=[];inner=[];selected=[]
    for fold,(tr,te) in enumerate(KFold(5,shuffle=True,random_state=42).split(d),1):
        best,chosen,rec=choices(d.iloc[tr],y[tr],f'outer_{fold}');inner+=rec
        z,v,*rest=encode(d.iloc[tr],d.iloc[te]);orders,scores,_=rankings(z,y[tr]);pre=rest[-1];names=pre.get_feature_names_out()
        configs={'full':('full',np.arange(z.shape[1]))}
        for name in METHODS:configs[name]=(name,indices(orders[name],best[name],z.shape[1]))
        configs['inner_selected_method']=(chosen,configs[chosen][1])
        cache={}
        for label,(method,ix) in configs.items():
            key=tuple(ix)
            if key not in cache:cache[key]=fit_svr(z[:,ix],y[tr]).predict(v[:,ix])
            p=cache[key]
            folds.append(dict(fold=fold,method=label,selector=method,k='all' if method=='full' else str(best[method]),n_features=len(ix),**metrics(y[te],p)))
            for j,i in enumerate(te):predictions.append(dict(fold=fold,method=label,record_id=d.record_id.iloc[i],source_paper_id=d.source_paper_id.iloc[i],observed_log10=y[i],predicted_log10=p[j]))
            if label in METHODS:
                for j in ix:selected.append(dict(fold=fold,method=label,feature=names[j],score=float(scores[method][j])))
        print('OUTER',fold,'choices',best,'automatic',chosen,flush=True)
    p=pd.DataFrame(predictions);f=pd.DataFrame(folds);results=[]
    for name,g in p.groupby('method'):
        assert len(g)==377 and g.record_id.is_unique
        ff=f[f.method.eq(name)]
        results.append(dict(method=name,min_features=int(ff.n_features.min()),max_features=int(ff.n_features.max()),mean_fold_r2=float(ff.r2_log10.mean()),sd_fold_r2=float(ff.r2_log10.std()),**metrics(g.observed_log10,g.predicted_log10)))
    p.to_csv(OUT/'predictions.csv',index=False);f.to_csv(OUT/'fold_metrics.csv',index=False)
    pd.DataFrame(results).to_csv(OUT/'metrics.csv',index=False)
    s=pd.DataFrame(selected);s.to_csv(OUT/'selected_features_by_fold.csv',index=False)
    s.groupby(['method','feature']).agg(selected_folds=('fold','nunique'),mean_score=('score','mean')).to_csv(OUT/'selection_stability.csv')
    best,chosen,rec=choices(d,y,'final_development');inner+=rec
    z,_,donor,feat,pre=encode(d,d.iloc[:1]);orders,scores,sv=rankings(z,y);names=pre.get_feature_names_out()
    for name in METHODS:
        ix=indices(orders[name],best[name],z.shape[1])
        pd.DataFrame(dict(feature=names[ix],score=scores[name][ix])).sort_values('score',ascending=False).to_csv(OUT/(name+'_final_features.csv'),index=False)
    ix=indices(orders[chosen],best[chosen],z.shape[1]);svr=fit_svr(z[:,ix],y)
    bundle=dict(donor=donor,features=feat,preprocessor=pre,selected_indices=ix,model=svr,selector=chosen,training_ids=list(d.record_id))
    joblib.dump(bundle,OUT/'candidate_model.joblib')
    check=joblib.load(OUT/'candidate_model.joblib');q=check['preprocessor'].transform(check['features'].transform(check['donor'].transform(d.iloc[:3])))
    np.testing.assert_allclose(check['model'].predict(q[:,check['selected_indices']]),svr.predict(z[:3,ix]))
    pd.DataFrame(inner).to_csv(OUT/'inner_cv_selection.csv',index=False)
    # SHAP plots: training development data only, descriptive rather than independent validation.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    shap.summary_plot(sv,z,feature_names=names,max_display=15,show=False)
    plt.title('Tree selector SHAP - full development data');plt.tight_layout();plt.savefig(OUT/'tree_SHAP_summary.png',dpi=160,bbox_inches='tight');plt.close()
    imp=scores['tree_SHAP'];top=np.argsort(imp)[-15:]
    fig,ax=plt.subplots(figsize=(10,6));ax.barh(names[top],imp[top]);ax.set_xlabel('Mean absolute TreeSHAP value (log10 icorr)');ax.set_title('SHAP ranking of tree selector, not SVR');fig.tight_layout();fig.savefig(OUT/'tree_SHAP_importance.png',dpi=160);plt.close(fig)
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==before
    report=dict(protocol='Outer random 5-fold seed42, inner random 3-fold seed71; train-only ranking and preprocessing; k chosen by inner MAE; fixed downstream SVR',methods=METHODS,k=KS,shap_version=shap.__version__,shap_model='ExtraTrees selector, NOT SVR',results=results,final_method=chosen,final_k=str(best[chosen]),final_features=len(ix),production_model_changed=False,warning='Development comparison on previously examined data. Random split can share source papers. Comparing outer scores to choose a winner is exploratory; inner_selected_method is the nested automatic method-selection procedure.')
    (OUT/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
