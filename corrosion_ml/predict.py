"""Predict with the single saved SVR/AL model."""
import argparse
from pathlib import Path
import joblib,numpy as np
from . import data
from .paths import MODEL,RESULTS

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',required=True);p.add_argument('--sheet')
    p.add_argument('--output',default=str(RESULTS/'predictions.csv'))
    args=p.parse_args();d=data.load(args.data,sheet=args.sheet if args.sheet else 0)
    if d.empty:raise ValueError('Fill the candidate template first')
    x,_,_=data.features(d,process=True)
    inputs=d.drop(columns=[data.TARGET],errors='ignore').copy();inputs[x.columns]=x
    model=joblib.load(MODEL);prediction=model.predict(inputs)
    if not np.isfinite(prediction).all():raise ValueError('Nonfinite predictions')
    z=model[:-1].transform(inputs)
    d['pred_log10_icorr']=prediction;d['pred_icorr_geometric_A_cm2']=10.**prediction
    d['bootstrap_std_log10']=model.named_steps['model'].uncertainty(z)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    d.to_csv(out,index=False,encoding='utf-8-sig');print(f'Saved {len(d)} predictions: {out}')

if __name__=='__main__':main()
