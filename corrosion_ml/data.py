"""Input schema and pre-statistical-imputation training data."""
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.model_selection import KFold,GroupKFold
from sklearn.metrics import r2_score,mean_absolute_error,mean_squared_error
from .paths import ROOT,DATA
BASE=ROOT
TARGET = 'icorr_A_cm2'
NUM = 'C Si Mn P S Cr Ni Mo Cu N RE_ppm temperature_C pH exposure_h scan_rate_mV_s'.split()
CAT = ['RE_element_cat', 'electrolyte_condition_cat', 'steel_family']
PHASE = [f'{p}_fraction_pct' for p in ['austenite', 'ferrite', 'martensite', 'bainite', 'pearlite']]
PROCESS_NUM = ['heat_treatment_temperature_C', 'heat_treatment_time_min',
               'ocp_stabilization_min', 'pH_lower_bound',
               'P_upper_bound_wt_pct', 'S_upper_bound_wt_pct']
PROCESS_CAT = ['sample_process_cat', 'sample_region_cat', 'temperature_condition_cat']

def load(path, sheet='ENRICHED_DATA'):
    d = pd.read_csv(path, float_precision='round_trip') if Path(path).suffix.lower() == '.csv' else pd.read_excel(path, sheet_name=sheet)
    if 'record_id' not in d or d.record_id.isna().any() or d.record_id.duplicated().any():
        raise ValueError('record_id must be present, nonempty and unique.')
    return d.reset_index(drop=True)

def features(d, phase=False, process=False):
    nums = NUM + (PHASE if phase else []) + (PROCESS_NUM if process else [])
    cats = CAT + (['matrix_phase_group'] if phase else []) + (PROCESS_CAT if process else [])
    missing = set(nums + cats) - set(d.columns)
    if missing:
        raise ValueError(f'Missing feature columns: {sorted(missing)}')
    x = d[nums + cats].copy()
    for c in nums:
        original = x[c]
        x[c] = pd.to_numeric(original, errors='coerce')
        if (original.notna() & x[c].isna()).any() or np.isinf(x[c]).any():
            raise ValueError(f'Invalid numeric value in {c}')
    for c in cats:
        x[c] = x[c].fillna('missing').astype(str)
    return x, nums, cats

def labels(d):
    y = pd.to_numeric(d[TARGET], errors='coerce').to_numpy(float)
    if not (np.isfinite(y) & (y > 0)).all():
        raise ValueError('Training/simulation targets must all be finite and > 0; resolve missing labels first.')
    return np.log10(y)

def score(y,p):
    raw=10.**np.asarray(y);rp=10.**np.asarray(p)
    return dict(r2_log10=float(r2_score(y,p)),rmse_log10=float(np.sqrt(mean_squared_error(y,p))),mae_log10=float(mean_absolute_error(y,p)),r2_raw=float(r2_score(raw,rp)))

def training_data():
    d=load(DATA/'training.csv')
    features(d,process=True);labels(d)
    required=['source_paper_id']+['donor_'+c for c in 'C Si Mn P S Cr Ni Mo Cu N'.split()]
    if any(c not in d for c in required):raise ValueError('Prepared training file is missing donor provenance columns')
    return d

def validation_splits(d,n_splits=5,split='random'):
    if split=='random':return KFold(n_splits,shuffle=True,random_state=42).split(d)
    if split=='paper':return GroupKFold(n_splits).split(d,groups=d.source_paper_id)
    raise ValueError('Unknown split mode')
