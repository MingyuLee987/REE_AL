"""Preserve composition reporting forms and evaluate a revised development DB."""
import os,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd,joblib,shap
from sklearn.model_selection import KFold,GroupKFold
from sklearn.feature_selection import VarianceThreshold
from sklearn.svm import SVR
from sklearn.ensemble import ExtraTreesRegressor
from .select_features import prepare,encode
from .features import CorrosionFeatures
from .model import make_pre
from .evaluate_literature import metrics
from .paths import ROOT,MODEL

DATA=ROOT/'data/composition_revised_20261026'
OUT=ROOT/'results/composition_revised_20261026'
CORE='C Si Mn P S Cr Ni Mo Cu N'.split()
EXTRA='Nb Ti V Al W Co B Sn Sb Ce La Y O'.split()
ELEMENTS=CORE+EXTRA
CONFIGS=[('legacy',10,'all'),('structured',1,'all'),('structured',10,'all'),('structured',100,'all'),('structured',10,40),('structured',10,80)]

def build():
    DATA.mkdir(parents=True,exist_ok=True)
    src=ROOT/'data/verified_377.csv';d=pd.read_csv(src,float_precision='round_trip');original=d.copy()
    old=(Path(os.environ['REE_RECOVERY_PATH'])/'al_labeled_raw.csv') if os.environ.get('REE_RECOVERY_PATH') else DATA/'recovered_source_rows.csv'
    raw=pd.read_csv(old,float_precision='round_trip');raw=raw[raw.record_id.isin(d.record_id)]
    # Keep a small evidence snapshot; do not restore unrelated archived folders.
    raw.to_csv(DATA/'recovered_source_rows.csv',index=False,encoding='utf-8-sig')
    by=raw.set_index('record_id');logs=[];conflicts=[]
    extra={}
    for e in ELEMENTS:
        for suffix in ['value_wt_pct','lower_wt_pct','upper_wt_pct']:extra[f'{e}_{suffix}']=np.nan
        extra[e+'_reporting_type']='unreported'
        extra[e+'_basis']='unreported'
        extra[e+'_evidence']=''
    d=pd.concat([d,pd.DataFrame(extra,index=d.index)],axis=1)
    for i,r in d.iterrows():
        oldrow=by.loc[r.record_id] if r.record_id in by.index else None
        if oldrow is not None:assert oldrow.source_paper_id==r.source_paper_id
        for e in ELEMENTS:
            value=r.get(e,np.nan);lo=np.nan;hi=r.get(e+'_upper_bound',np.nan)
            evidence='verified_377.csv';basis=str(r.composition_input_basis) if pd.notna(value) else 'unreported'
            if e=='W' and pd.notna(r.get('additional_element_W_wt_pct',np.nan)):
                value=r.additional_element_W_wt_pct;basis='reported_additional_element';evidence='verified_377.additional_element_W_wt_pct'
            if oldrow is not None:
                ov=oldrow.get(e,np.nan);ol=oldrow.get(e+'_lower_bound',np.nan);oh=oldrow.get(e+'_upper_bound',np.nan)
                if pd.isna(value) and pd.notna(ov):
                    value=ov;basis=str(oldrow.get('composition_input_basis','recovered_source_row_basis_unresolved'));evidence='recovered_source_rows.csv'
                    logs.append(dict(record_id=r.record_id,element=e,field='value_wt_pct',value=value,source='recovered_source_rows.csv'))
                elif pd.notna(value) and pd.notna(ov) and not np.isclose(value,ov,rtol=1e-8,atol=1e-12):
                    conflicts.append(dict(record_id=r.record_id,element=e,current=value,recovered=ov,decision='keep_current_no_overwrite'))
                if pd.notna(ol):lo=ol
                if pd.isna(hi) and pd.notna(oh):
                    hi=oh;logs.append(dict(record_id=r.record_id,element=e,field='upper_wt_pct',value=hi,source='recovered_source_rows.csv'))
            # Only an unambiguous single-RE label permits conversion to that element.
            if e in ['Ce','La','Y'] and pd.isna(value) and str(r.RE_element_cat).strip()==e and pd.notna(r.RE_ppm):
                value=r.RE_ppm/10000;basis=str(r.RE_content_basis);evidence='single_RE_label_and_total_ppm_divided_by_10000'
                logs.append(dict(record_id=r.record_id,element=e,field='value_wt_pct',value=value,source=evidence))
            if pd.notna(value) and (value<0 or value>100):raise ValueError('Invalid wt percent')
            if pd.notna(lo) and pd.notna(hi) and lo>hi:raise ValueError('Invalid interval')
            kind='point' if pd.notna(value) else ('interval' if pd.notna(lo) and pd.notna(hi) else ('upper_bound' if pd.notna(hi) else ('lower_bound' if pd.notna(lo) else 'unreported')))
            if pd.notna(lo) or pd.notna(hi):
                if basis=='unreported':basis='reported_bound_origin_not_fully_classified'
            d.loc[i,[e+'_value_wt_pct',e+'_lower_wt_pct',e+'_upper_wt_pct',e+'_reporting_type',e+'_basis',e+'_evidence']]=[value,lo,hi,kind,basis,evidence if kind!='unreported' else '']
    # Legacy derived flags are retained only as namespaced metadata, never predictors.
    for c in ['composition_uses_assumptions','composition_statistically_filled_count','pH_is_estimated','pH_donor_papers','pH_reference_min','pH_reference_max']:
        if c in d:d=d.rename(columns={c:'legacy_'+c})
    np.testing.assert_array_equal(d.icorr_A_cm2,original.icorr_A_cm2)
    assert list(d.record_id)==list(original.record_id)
    d.to_csv(DATA/'database_377.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(logs).to_csv(DATA/'recovery_log.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(conflicts,columns=['record_id','element','current','recovered','decision']).to_csv(DATA/'conflicts.csv',index=False)
    coverage=[]
    for e in ELEMENTS:
        coverage.append(dict(element=e,point=int(d[e+'_value_wt_pct'].notna().sum()),lower=int(d[e+'_lower_wt_pct'].notna().sum()),upper=int(d[e+'_upper_wt_pct'].notna().sum())))
    pd.DataFrame(coverage).to_csv(DATA/'composition_coverage.csv',index=False)
    (DATA/'schema.json').write_text(json.dumps(dict(elements=ELEMENTS,unit='wt.%',targets_unchanged=True,no_target_imputation=True,no_midpoint_assumed=True,no_zero_for_unreported=True,basis_note='A point is a reported scalar, not necessarily a measured bulk assay; basis preserved when known, otherwise unresolved.',bound_note='Only reported endpoints stored; upper-only does not create a fabricated zero lower endpoint.',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest()),indent=2),encoding='utf-8')
    print('DATABASE',len(d),'recoveries',len(logs),'conflicts',len(conflicts),flush=True)
    return d

def structured(d):
    f=CorrosionFeatures().transform(d)
    drop=CORE+[f'original_missing_{e}' for e in CORE]+['P_upper_bound_wt_pct','S_upper_bound_wt_pct']
    f=f.drop(columns=[c for c in drop if c in f])
    extra={}
    for e in ELEMENTS:
        value=d[e+'_value_wt_pct'];lo=d[e+'_lower_wt_pct'];hi=d[e+'_upper_wt_pct']
        extra[e+'_reported_value']=value
        # Encoding endpoints for exact points is a deterministic transform, not new source evidence.
        extra[e+'_lower_endpoint']=lo.combine_first(value)
        extra[e+'_upper_endpoint']=hi.combine_first(value)
        extra[e+'_reporting_type']=d[e+'_reporting_type'].fillna('unreported').astype(str)
    return pd.concat([f,pd.DataFrame(extra,index=d.index)],axis=1)

def enc(train,test,kind):
    if kind=='legacy':
        z,v,donor,feat,pre=encode(train,test)
        return z,v,dict(kind=kind,donor=donor,features=feat,preprocessor=pre)
    a=structured(train);b=structured(test);pre=make_pre(a);z=pre.fit_transform(a);v=pre.transform(b)
    vt=VarianceThreshold(1e-12);z=vt.fit_transform(z);v=vt.transform(v)
    return z,v,dict(kind=kind,preprocessor=pre,variance=vt)

def rank(z,y):
    tree=ExtraTreesRegressor(n_estimators=150,min_samples_leaf=2,n_jobs=2,random_state=42).fit(z,y)
    values=shap.TreeExplainer(tree).shap_values(z,check_additivity=True)
    return np.argsort(-np.mean(np.abs(values),axis=0),kind='stable')

def predict_config(z,v,y,c,k,order):
    ix=np.arange(z.shape[1]) if k=='all' else order[:min(k,z.shape[1])]
    model=SVR(C=c,epsilon=.15,gamma='scale').fit(z[:,ix],y)
    return model.predict(v[:,ix]),model,ix

def inner_choice(d,y,tag,grouped=False):
    records=[]
    cv=GroupKFold(3) if grouped else KFold(3,shuffle=True,random_state=71)
    splits=cv.split(d,groups=d.source_paper_id) if grouped else cv.split(d)
    for fold,(tr,va) in enumerate(splits,1):
        cache={}
        for kind in ['legacy','structured']:
            z,v,bundle=enc(d.iloc[tr],d.iloc[va],kind);order=rank(z,y[tr]) if kind=='structured' else None
            cache[kind]=(z,v,order)
        for ci,(kind,c,k) in enumerate(CONFIGS):
            z,v,order=cache[kind];p,_,ix=predict_config(z,v,y[tr],c,k,order)
            records.append(dict(stage=tag,inner_fold=fold,config=ci,kind=kind,C=c,k=str(k),n_features=len(ix),mae=float(np.mean(np.abs(y[va]-p)))))
    means=pd.DataFrame(records).groupby('config').mae.mean();best=int(means.idxmin())
    print(tag,'chosen',best,CONFIGS[best],flush=True)
    return best,records

def main():
    OUT.mkdir(parents=True,exist_ok=True);rev=build();base,y=prepare()
    newcols=[c for c in rev if any(c.startswith(e+'_') for e in ELEMENTS)]
    d=base.copy()
    for c in newcols:d[c]=rev[c].to_numpy()
    before=hashlib.sha256(MODEL.read_bytes()).hexdigest();predictions=[];folds=[];inners=[]
    for protocol,cv in [('random_5fold',KFold(5,shuffle=True,random_state=42)),('paper_5fold',GroupKFold(5))]:
        splits=cv.split(d,groups=d.source_paper_id) if protocol=='paper_5fold' else cv.split(d)
        for fold,(tr,te) in enumerate(splits,1):
            if protocol=='paper_5fold':assert set(d.source_paper_id.iloc[tr]).isdisjoint(set(d.source_paper_id.iloc[te]))
            best,rec=inner_choice(d.iloc[tr],y[tr],f'{protocol}_{fold}',protocol=='paper_5fold');inners+=rec
            cache={}
            for label,ci in [('legacy',0),('structured_fixed',2),('inner_selected',best)]:
                kind,c,k=CONFIGS[ci]
                if kind not in cache:
                    z,v,bundle=enc(d.iloc[tr],d.iloc[te],kind);cache[kind]=(z,v,rank(z,y[tr]) if kind=='structured' else None)
                z,v,order=cache[kind];p,_,ix=predict_config(z,v,y[tr],c,k,order)
                folds.append(dict(protocol=protocol,fold=fold,model=label,config=ci,n_features=len(ix),**metrics(y[te],p)))
                for j,i in enumerate(te):predictions.append(dict(protocol=protocol,fold=fold,model=label,record_id=d.record_id.iloc[i],source_paper_id=d.source_paper_id.iloc[i],observed_log10=y[i],predicted_log10=p[j]))
            print('DONE',protocol,fold,flush=True)
    p=pd.DataFrame(predictions);f=pd.DataFrame(folds);rows=[]
    for (protocol,label),g in p.groupby(['protocol','model']):
        assert len(g)==377 and g.record_id.is_unique
        ff=f[(f.protocol==protocol)&(f.model==label)]
        rows.append(dict(protocol=protocol,model=label,min_features=int(ff.n_features.min()),max_features=int(ff.n_features.max()),mean_fold_r2=float(ff.r2_log10.mean()),**metrics(g.observed_log10,g.predicted_log10)))
    p.to_csv(OUT/'predictions.csv',index=False);f.to_csv(OUT/'fold_metrics.csv',index=False);pd.DataFrame(rows).to_csv(OUT/'metrics.csv',index=False)
    best,rec=inner_choice(d,y,'final_random_development');inners+=rec
    kind,c,k=CONFIGS[best];z,v,bundle=enc(d,d.iloc[:3],kind);order=rank(z,y) if kind=='structured' else None
    pp,model,ix=predict_config(z,v,y,c,k,order);bundle.update(model=model,indices=ix,config=CONFIGS[best],training_ids=list(d.record_id))
    joblib.dump(bundle,OUT/'candidate_model.joblib')
    names=bundle['preprocessor'].get_feature_names_out()
    if kind=='structured':names=names[bundle['variance'].get_support()]
    pd.DataFrame(dict(feature=names[ix])).to_csv(OUT/'final_features.csv',index=False)
    pd.DataFrame(inners).to_csv(OUT/'inner_cv.csv',index=False)
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==before
    summary=dict(configs=CONFIGS,results=rows,final_config=CONFIGS[best],final_features=len(ix),production_model_changed=False,interpretation='Bounds representation is project-specific engineering, not a published recipe. Previously examined development data; not blind validation. Both reporting pattern and domain shift can affect results.')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
