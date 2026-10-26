"""Random-row active learning using the selected SVR model."""
import argparse,hashlib,json,time
from pathlib import Path
import joblib,numpy as np,pandas as pd
from . import data as al
from .data import training_data,score,validation_splits
from .composition import ELEMENTS
from .model import fitted,rank_batch,STRATEGIES
from .paths import ROOT,DATA,MODELS,RESULTS,MODEL
BASE=ROOT
FRACTIONS=[.25,.5,.75,1.]

def query(pipeline,known_z,known_ids,pool,count,strategy,rng):
    if al.TARGET in pool:raise ValueError('Pool outcomes must be hidden before acquisition')
    z=pipeline[:-1].transform(pool)
    sigma=pipeline.named_steps['model'].uncertainty(z)
    take=rank_batch(known_z,known_ids,z,pool.record_id,sigma,count,strategy,rng)
    assert len(take)==count and len(set(take))==count and set(take).issubset(set(pool.record_id))
    return take

def simulate(d,out,batch_size=10,n_members=15):
    started=time.time();y=al.labels(d);curves=[];queries=[];splits=[];predictions=[]
    for fold,(train,test) in enumerate(validation_splits(d,5,'random'),1):
        full=None;test_set=set(test);train_ids=set(d.record_id.iloc[train])
        for i in range(len(d)):splits.append(dict(fold=fold,record_id=d.record_id.iloc[i],partition='test' if i in test_set else 'train_pool'))
        budgets=[int(np.ceil(len(train)*f)) for f in FRACTIONS];budgets[-1]=len(train)
        for seed in [42,43]:
            initial=set(np.random.default_rng(seed).choice(train,budgets[0],replace=False))
            initial_fit=None
            for strategy in STRATEGIES:
                known=set(initial);rng=np.random.default_rng(seed);cached=None;cached_ids=None;round_id=0
                for stage,budget in enumerate(budgets):
                    while len(known)<budget:
                        idx=np.array(sorted(known));remaining=np.array([i for i in train if i not in known])
                        count=min(batch_size,budget-len(known))
                        if strategy=='random':chosen=list(rng.choice(remaining,count,replace=False))
                        else:
                            if cached_ids!=tuple(idx):cached=fitted(d.iloc[idx],y[idx],n_members,seed);cached_ids=tuple(idx)
                            pipeline,z=cached
                            assert set(pipeline.training_record_ids_).isdisjoint(d.record_id.iloc[test])
                            pool=d.iloc[remaining].drop(columns=[al.TARGET])
                            ids=query(pipeline,z,d.record_id.iloc[idx],pool,count,strategy,rng)
                            assert set(ids).issubset(train_ids)
                            lookup=dict(zip(d.record_id.iloc[remaining],remaining));chosen=[lookup[r] for r in ids]
                        assert not known.intersection(chosen) and set(chosen).isdisjoint(test_set)
                        round_id+=1
                        for i in chosen:queries.append(dict(fold=fold,seed=seed,strategy=strategy,round=round_id,reveal_at_stage=stage,record_id=d.record_id.iloc[i],n_labeled_before=len(known)))
                        known.update(chosen)
                    idx=np.array(sorted(known));assert len(idx)==budget
                    if stage==3 and full is not None:cached=full;cached_ids=tuple(idx)
                    elif stage==0 and initial_fit is not None:cached=initial_fit;cached_ids=tuple(idx)
                    elif cached_ids!=tuple(idx):cached=fitted(d.iloc[idx],y[idx],n_members,seed);cached_ids=tuple(idx)
                    if stage==0:initial_fit=cached
                    if stage==3:full=cached
                    pipeline,z=cached
                    p=pipeline.predict(d.iloc[test].drop(columns=[al.TARGET]))
                    curves.append(dict(fold=fold,seed=seed,strategy=strategy,stage=stage,fraction=FRACTIONS[stage],n_labeled=len(idx),n_test=len(test),**score(y[test],p)))
                    for i,value in zip(test,p):predictions.append(dict(fold=fold,seed=seed,strategy=strategy,stage=stage,record_id=d.record_id.iloc[i],observed_log10=y[i],predicted_log10=value))
                pd.DataFrame(curves).to_csv(out/'learning_curves.csv',index=False)
                print(f'Fold {fold}/5 seed {seed} {strategy}: done; elapsed {time.time()-started:.0f}s',flush=True)
    frame=pd.DataFrame(curves)
    for _,g in frame[frame.stage.eq(0)].groupby(['fold','seed']):assert np.ptp(g.r2_log10)<1e-12
    for _,g in frame[frame.stage.eq(3)].groupby('fold'):assert np.ptp(g.r2_log10)<1e-12
    for _,g in frame.groupby(['fold','seed','stage']):assert g.n_labeled.nunique()==1
    per_fold=frame.groupby(['strategy','stage','fold'])[['r2_log10','rmse_log10','mae_log10','n_labeled']].mean().reset_index()
    summary=per_fold.groupby(['strategy','stage']).agg(mean_r2=('r2_log10','mean'),std_r2=('r2_log10','std'),mean_rmse=('rmse_log10','mean'),mean_mae=('mae_log10','mean'),mean_labeled=('n_labeled','mean')).reset_index()
    summary['fraction']=summary.stage.map(dict(enumerate(FRACTIONS)));summary.to_csv(out/'summary.csv',index=False)
    pd.DataFrame(queries).to_csv(out/'queries.csv',index=False);pd.DataFrame(splits).to_csv(out/'splits.csv',index=False)
    pd.DataFrame(predictions).to_csv(out/'predictions.csv',index=False)
    paired=per_fold.pivot(index=['stage','fold'],columns='strategy',values='r2_log10')
    for strategy in ['uncertainty','diverse_uncertainty']:paired[strategy+'_minus_random']=paired[strategy]-paired['random']
    paired.to_csv(out/'paired_differences.csv')
    info=dict(records=len(d),papers=int(d.source_paper_id.nunique()),outer_split='KFold(5, shuffle=True, random_state=42), same as random_training',start_seeds=[42,43],fractions=FRACTIONS,batch_size=batch_size,bootstrap_members=n_members,model='environment + SVR(C=10, epsilon=0.15); central fit predicts, bootstrap committee selects',uncertainty='Bootstrap SVRs on fixed queried-train preprocessing; not a calibrated confidence interval or full imputation uncertainty',query_unit='individual observation, identical row costs at checkpoints',selection='Hidden pool outcomes removed; held-out test inputs and outcomes never used in acquisition; all preprocessing fitted only on revealed training rows',development='Model family previously selected using this development dataset; reused benchmark, not an independent external test. No test-score strategy tuning.',endpoint='Fixed environment SVR, not the 18-model nested selection score 0.7973',elapsed_seconds=time.time()-started,input_sha256=hashlib.sha256((DATA/'training.csv').read_bytes()).hexdigest())
    (out/'manifest.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    # Operational full-data committee; no training score reported as test performance.
    from .train import save_model
    bundle,_=fitted(d,y,n_members,42);save_model(bundle,info)
    print(summary.to_string(index=False),flush=True)

def recommend(d,args,out):
    c=al.load(args.candidates, sheet=0)
    if c.empty:raise ValueError('Candidate pool is empty')
    if al.TARGET in c and c[al.TARGET].notna().any():raise ValueError('Unmeasured candidate targets must be blank')
    if set(c.record_id)&set(d.record_id):raise ValueError('Candidate IDs overlap measured data')
    x,_,_=al.features(c,process=True);c[x.columns]=x
    if c[ELEMENTS].notna().sum(axis=1).lt(2).any():raise ValueError('At least two known core composition values required')
    known,_,_=al.features(d,process=True)
    hashes=pd.util.hash_pandas_object(x.round(10),index=False)
    keep=~hashes.isin(pd.util.hash_pandas_object(known.round(10),index=False))&~hashes.duplicated()
    c=c.loc[keep].reset_index(drop=True)
    if c.empty:raise ValueError('No new candidate conditions remain')
    pipeline,z=fitted(d,al.labels(d),args.members,42)
    take=query(pipeline,z,d.record_id,c.drop(columns=[al.TARGET],errors='ignore'),min(args.batch_size,len(c)),args.strategy,np.random.default_rng(42))
    pz=pipeline[:-1].transform(c)
    c['pred_log10_icorr']=pipeline.predict(c);c['pred_icorr_geometric_A_cm2']=10.**c.pred_log10_icorr
    c['bootstrap_std_log10']=pipeline.named_steps['model'].uncertainty(pz);c['selected']=c.record_id.isin(take)
    c.to_csv(out/'scored_candidates.csv',index=False,encoding='utf-8-sig')
    c.set_index('record_id').loc[take].reset_index().to_csv(out/'next_batch.csv',index=False,encoding='utf-8-sig')
    info=dict(strategy=args.strategy,batch_size=len(take),bootstrap_members=args.members,eligible_candidates=len(c),excluded_measured_or_duplicate=int((~keep).sum()),model='environment SVR',query_unit='individual unmeasured experiment',uncertainty='uncalibrated bootstrap disagreement',input_sha256=hashlib.sha256((DATA/'training.csv').read_bytes()).hexdigest())
    (out/'run.json').write_text(json.dumps(info,indent=2),encoding='utf-8');print(f'Selected {len(take)} experiments: {out}',flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['simulate','recommend'])
    p.add_argument('--batch-size',type=int,default=10);p.add_argument('--members',type=int,default=15)
    p.add_argument('--strategy',choices=STRATEGIES,default='diverse_uncertainty');p.add_argument('--candidates');p.add_argument('--output')
    args=p.parse_args()
    if args.batch_size<1 or args.members<2:p.error('Positive batch-size and at least two members required')
    if args.mode=='recommend' and not args.candidates:p.error('recommend requires --candidates')
    out=Path(args.output) if args.output else BASE/'results'/('active_learning' if args.mode=='simulate' else 'queries')
    out.mkdir(parents=True,exist_ok=True);d=training_data()
    if args.mode=='simulate':simulate(d,out,args.batch_size,args.members)
    else:recommend(d,args,out)

if __name__=='__main__':main()
