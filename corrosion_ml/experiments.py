"""Frozen-model prospective predictions and external experimental validation."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import joblib,numpy as np,pandas as pd
from sklearn.metrics import r2_score
from . import data as al
from .paths import ROOT,DATA,MODEL

BASE=ROOT
PHASES=al.PHASE+['other_fraction_pct']
META=['condition_id','replicate_id','batch_id','phase_method','phase_fraction_basis','phase_note']

def make_template(path):
    path=Path(path)
    if path.exists():raise FileExistsError('Template destination already exists; choose a new path')
    path.parent.mkdir(parents=True,exist_ok=True)
    columns=['record_id']+META+al.NUM+al.PROCESS_NUM+al.CAT+al.PROCESS_CAT+PHASES+[al.TARGET]
    pd.DataFrame(columns=columns).to_csv(path,index=False,encoding='utf-8-sig')
    print(f'Created blank template: {path}')

def validate_phases(d):
    x=pd.DataFrame(index=d.index)
    for col in PHASES:
        original=d[col] if col in d else pd.Series(np.nan,index=d.index)
        values=pd.to_numeric(original,errors='coerce')
        if (original.notna()&values.isna()).any() or ((values<0)|(values>100)|np.isinf(values)).any():
            raise ValueError(f'{col}: use numeric percentages from 0 to 100; unknown stays blank')
        x[col]=values
    sums=x.sum(axis=1,min_count=1)
    # Allow a stated 1 percentage-point rounding margin; never rescale values.
    if sums.gt(101).any():raise ValueError('Phase fractions sum above 101%; check overlapping definitions and units')
    return x,sums

def predict_without_target(bundle,d):
    x,_,_=al.features(d,process=True)
    inputs=d.drop(columns=[al.TARGET],errors='ignore').copy();inputs[x.columns]=x
    pred=np.asarray(bundle.predict(inputs),dtype=float)
    if not np.isfinite(pred).all():raise ValueError('Nonfinite model predictions')
    return pred

def metrics(observed_log10,predicted_log10):
    y=np.asarray(observed_log10,float);p=np.asarray(predicted_log10,float)
    if len(y)==0 or not np.isfinite(y).all() or not np.isfinite(p).all():raise ValueError('Finite nonempty measurements required')
    err=p-y;raw=10.**y;rp=10.**p
    def r2(a,b):return float(r2_score(a,b)) if len(a)>=2 and np.ptp(a)>0 else None
    return dict(n=len(y),r2_log10=r2(y,p),r2_A_cm2=r2(raw,rp),rmse_log10=float(np.sqrt(np.mean(err**2))),mae_log10=float(np.mean(abs(err))),mae_A_cm2=float(np.mean(abs(rp-raw))),geometric_mean_fold_error=float(10.**np.mean(abs(err))),median_fold_error=float(np.median(10.**abs(err))),fraction_within_factor2=float(np.mean(abs(err)<=np.log10(2))),r2_note='Null if fewer than 2 records or constant observed values; small or narrow-range experiments give unstable R2')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make-template',metavar='PATH');parser.add_argument('--data')
    parser.add_argument('--sheet',help='XLSX sheet name; default is first sheet')
    parser.add_argument('--predict-only',action='store_true')
    parser.add_argument('--expected-model-sha256',help='Optional hash from the prior frozen prediction run')
    parser.add_argument('--output',default=str(BASE/'results/experiments'))
    args=parser.parse_args()
    if args.make_template:make_template(args.make_template);return
    if not args.data:parser.error('--data or --make-template is required')
    path=Path(args.data);d=al.load(path,sheet=args.sheet if args.sheet else 0)
    if d.empty:raise ValueError('Fill the template with actual experiment rows first')
    known=al.load(DATA/'training.csv')
    if set(d.record_id)&set(known.record_id):raise ValueError('External experiment record_id overlaps training IDs; use genuine new experiment IDs')
    phase_values,phase_sum=validate_phases(d)
    model_path=MODEL
    model_hash=hashlib.sha256(model_path.read_bytes()).hexdigest()
    if args.expected_model_sha256 and model_hash!=args.expected_model_sha256:raise ValueError('Model hash differs from frozen prediction run')
    bundle=joblib.load(model_path);p=predict_without_target(bundle,d)
    feature_columns=list(bundle.named_steps['preprocessor'].feature_names_in_)
    used_phase=sorted(set(feature_columns)&set(PHASES))
    result=d.copy();result[phase_values.columns]=phase_values
    result['phase_sum_reported_pct']=phase_sum
    result['phase_fractions_used_by_model']=bool(used_phase)
    result['pred_log10_icorr']=p;result['pred_icorr_geometric_A_cm2']=10.**p
    unseen={}
    for col in al.CAT+al.PROCESS_CAT:
        if col=='electrolyte_condition_cat':continue  # This string is parsed into environment descriptors.
        new=set(d[col].dropna().astype(str))-set(known[col].dropna().astype(str))
        if new:unseen[col]=sorted(new)
    summary=dict(evaluation='frozen external experiment validation; no fit/retraining in this command',mode='predict_only' if args.predict_only else 'evaluate',model_path=str(model_path),model_sha256=model_hash,input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),timestamp_utc=datetime.now(timezone.utc).isoformat(),phase_features_used=used_phase,phase_note='Current environment SVR does not use recorded phase fractions',phase_sum_rounding_tolerance_pct_points=1,n_records=len(d),unseen_categorical_values=unseen)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    if (out/'predictions.csv').exists() or (out/'metrics.json').exists():raise FileExistsError('Use a new output directory to preserve earlier predictions and evaluation records')
    if not args.predict_only:
        if al.TARGET not in d:raise ValueError('Evaluation needs measured icorr_A_cm2')
        y=al.labels(d);result['observed_log10_icorr']=y
        result['signed_log10_error']=p-y;result['absolute_fold_error']=10.**abs(p-y)
        result['within_factor2']=abs(p-y)<=np.log10(2)
        summary['replicate_level']=metrics(y,p)
        if 'condition_id' in d and d.condition_id.notna().all():
            grouped=result.groupby('condition_id',sort=False).agg(n_replicates=('record_id','size'),observed_log10_icorr=('observed_log10_icorr','mean'),pred_log10_icorr=('pred_log10_icorr','mean')).reset_index()
            grouped['observed_icorr_geometric_A_cm2']=10.**grouped.observed_log10_icorr
            grouped['pred_icorr_geometric_A_cm2']=10.**grouped.pred_log10_icorr
            grouped.to_csv(out/'condition_predictions.csv',index=False,encoding='utf-8-sig')
            summary['condition_level']=metrics(grouped.observed_log10_icorr,grouped.pred_log10_icorr)
            summary['aggregation']='Mean log10 within condition, equivalent to geometric mean in A/cm2; replicates are not independent conditions'
        else:summary['condition_level_note']='Provide a nonmissing condition_id for every row to aggregate replicates'
    result.to_csv(out/'predictions.csv',index=False,encoding='utf-8-sig')
    (out/'metrics.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=True,allow_nan=False))

if __name__=='__main__':main()
