"""Isolate recovered-element and bound additions from other preprocessing changes."""
import json,hashlib
import numpy as np,pandas as pd,joblib
from sklearn.model_selection import KFold,GroupKFold
from .select_features import prepare,fit_svr
from .composition import CompositionDonorImputer
from .features import CorrosionFeatures
from .model import make_pre
from .revise_database import ELEMENTS,EXTRA,DATA,OUT
from .evaluate_literature import metrics
from .paths import MODEL

def desc(d,donor):
    f=CorrosionFeatures().transform(donor.transform(d));extra={}
    for e in EXTRA:extra[e+'_reported_wt_pct']=d[e+'_value_wt_pct']
    for e in ELEMENTS:
        if e in ['P','S']:continue # Existing upper bounds already enter the legacy pipeline.
        extra[e+'_reported_upper_wt_pct']=d[e+'_upper_wt_pct']
        extra[e+'_reported_lower_wt_pct']=d[e+'_lower_wt_pct']
    return pd.concat([f,pd.DataFrame(extra,index=d.index)],axis=1)

def main():
    d,y=prepare();rev=pd.read_csv(DATA/'database_377.csv',float_precision='round_trip')
    for e in ELEMENTS:
        for suffix in ['value_wt_pct','upper_wt_pct','lower_wt_pct']:d[e+'_'+suffix]=rev[e+'_'+suffix].to_numpy()
    before=hashlib.sha256(MODEL.read_bytes()).hexdigest();preds=[];folds=[]
    for protocol,cv in [('random_5fold',KFold(5,shuffle=True,random_state=42)),('paper_5fold',GroupKFold(5))]:
        splits=cv.split(d,groups=d.source_paper_id) if protocol=='paper_5fold' else cv.split(d)
        for fold,(tr,te) in enumerate(splits,1):
            donor=CompositionDonorImputer().fit(d.iloc[tr]);a=desc(d.iloc[tr],donor);b=desc(d.iloc[te],donor)
            pre=make_pre(a);z=pre.fit_transform(a);v=pre.transform(b);svr=fit_svr(z,y[tr]);p=svr.predict(v)
            folds.append(dict(protocol=protocol,fold=fold,n_features=z.shape[1],**metrics(y[te],p)))
            for j,i in enumerate(te):preds.append(dict(protocol=protocol,fold=fold,record_id=d.record_id.iloc[i],source_paper_id=d.source_paper_id.iloc[i],observed_log10=y[i],predicted_log10=p[j]))
            print(protocol,fold,'done',flush=True)
    p=pd.DataFrame(preds);rows=[]
    for name,g in p.groupby('protocol'):
        assert len(g)==377 and g.record_id.is_unique
        rows.append(dict(protocol=name,model='legacy_plus_recovered',**metrics(g.observed_log10,g.predicted_log10)))
    p.to_csv(OUT/'augmented_predictions.csv',index=False);pd.DataFrame(folds).to_csv(OUT/'augmented_fold_metrics.csv',index=False);pd.DataFrame(rows).to_csv(OUT/'augmented_metrics.csv',index=False)
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==before
    print(json.dumps(rows,indent=2),flush=True)

if __name__=='__main__':main()
