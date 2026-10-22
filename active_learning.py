"""Pool-based active learning for the REE corrosion workbook (CSV outputs)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET = 'icorr_A_cm2'
NUM = 'C Si Mn P S Cr Ni Mo Cu N RE_ppm temperature_C pH exposure_h scan_rate_mV_s'.split()
CAT = ['RE_element_cat', 'electrolyte_condition_cat', 'steel_family']
PHASE = [f'{p}_fraction_pct' for p in ['austenite', 'ferrite', 'martensite', 'bainite', 'pearlite']]
DEFAULT = 'rare_earth_steel_single_sheet_sources.xlsx'


def load(path, sheet='ENRICHED_DATA'):
    d = pd.read_csv(path) if Path(path).suffix.lower() == '.csv' else pd.read_excel(path, sheet_name=sheet)
    if 'record_id' not in d or d.record_id.isna().any() or d.record_id.duplicated().any():
        raise ValueError('record_id must be present, nonempty and unique.')
    return d.reset_index(drop=True)


def features(d, phase=False):
    nums = NUM + (PHASE if phase else [])
    cats = CAT + (['matrix_phase_group'] if phase else [])
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


def fit(x, y, nums, cats, seed):
    pre = ColumnTransformer([
        ('num', make_pipeline(SimpleImputer(strategy='median', add_indicator=True, keep_empty_features=True), StandardScaler()), nums),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cats),
    ])
    z = pre.fit_transform(x)
    model = RandomForestRegressor(n_estimators=150, min_samples_leaf=2, max_features=0.8, random_state=seed, n_jobs=-1)
    model.fit(z, y)
    return pre, model


def predict(pre, model, x):
    z = pre.transform(x)
    p = np.array([tree.predict(z) for tree in model.estimators_])
    return p.mean(axis=0), p.std(axis=0)


def select(mu, sigma, n, strategy, beta, rng):
    if strategy == 'random':
        return rng.permutation(len(mu))[:n]
    # Lower corrosion is better. LCB minimizes mu-beta*sigma.
    score = sigma if strategy == 'uncertainty' else -mu + beta * sigma
    return np.argsort(-score, kind='stable')[:n]


def simulate(d, args, out):
    if 'source_paper_id' not in d or d.source_paper_id.isna().any() or d.source_paper_id.nunique() < 2:
        raise ValueError('Simulation needs at least two nonmissing source_paper_id groups.')
    x, nums, cats = features(d, args.with_phase)
    y = labels(d)
    rows, queries, splits = [], [], []
    for seed in args.seeds:
        train, test = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(x, groups=d.source_paper_id))
        if args.initial >= len(train) or len(test) < 2:
            raise ValueError('Initial size must be smaller than training pool; test requires >=2 rows.')
        initial = np.random.default_rng(seed).choice(train, args.initial, replace=False).tolist()
        for i in range(len(d)):
            splits.append(dict(seed=seed, record_id=d.record_id.iloc[i], source_paper_id=d.source_paper_id.iloc[i], partition='test' if i in test else ('initial' if i in initial else 'pool')))
        for strategy in ['random', 'uncertainty', 'lcb']:
            known = initial.copy()
            pool = [i for i in train if i not in known]
            rng = np.random.default_rng(seed)
            for step in range(args.rounds + 1):
                pre, model = fit(x.iloc[known], y[known], nums, cats, seed)
                pred, _ = predict(pre, model, x.iloc[test])
                rows.append(dict(seed=seed, strategy=strategy, round=step, n_labeled=len(known), mae_log10=mean_absolute_error(y[test], pred), rmse_log10=float(np.sqrt(mean_squared_error(y[test], pred))), r2_log10=r2_score(y[test], pred)))
                if step == args.rounds or not pool:
                    break
                mu, sigma = predict(pre, model, x.iloc[pool])
                take = select(mu, sigma, min(args.batch_size, len(pool)), strategy, args.beta, rng)
                chosen = [pool[i] for i in take]
                for i in chosen:
                    queries.append(dict(seed=seed, strategy=strategy, round=step + 1, record_id=d.record_id.iloc[i]))
                known.extend(chosen)
                pool = [i for i in pool if i not in chosen]
    pd.DataFrame(rows).to_csv(out / 'learning_curves.csv', index=False)
    pd.DataFrame(queries).to_csv(out / 'queries.csv', index=False)
    pd.DataFrame(splits).to_csv(out / 'splits.csv', index=False)
    pd.DataFrame(rows).groupby(['strategy', 'n_labeled'])[['mae_log10', 'rmse_log10', 'r2_log10']].agg(['mean', 'std']).to_csv(out / 'summary.csv')


def recommend(d, args, out):
    c = load(args.candidates, args.sheet)
    if c.empty:
        raise ValueError('Candidate pool is empty.')
    if set(c.record_id) & set(d.record_id):
        raise ValueError('Candidate record_id overlaps training records.')
    if TARGET in c and c[TARGET].notna().any():
        raise ValueError('Candidates must have blank targets (unmeasured experiments).')
    x, nums, cats = features(d, args.with_phase)
    cx, _, _ = features(c, args.with_phase)
    # Reject repeats of measured conditions and collapse identical candidate inputs.
    # Normalize serialization roundoff (CSV vs XLSX) for condition comparison.
    fingerprints = pd.util.hash_pandas_object(x.round(10), index=False)
    cf = pd.util.hash_pandas_object(cx.round(10), index=False)
    keep = ~cf.isin(fingerprints) & ~cf.duplicated()
    c, cx = c.loc[keep].copy(), cx.loc[keep]
    if c.empty:
        raise ValueError('No new unique candidate conditions remain.')
    pre, model = fit(x, labels(d), nums, cats, args.seeds[0])
    mu, sigma = predict(pre, model, cx)
    c['pred_log10_icorr'] = mu
    c['tree_std_log10'] = sigma
    c['pred_icorr_geometric_A_cm2'] = 10 ** mu
    c['lcb_log10'] = mu - args.beta * sigma
    take = select(mu, sigma, len(c), args.strategy, args.beta, np.random.default_rng(args.seeds[0]))
    c = c.iloc[take].copy()
    c.insert(0, 'rank', range(1, len(c) + 1))
    c.to_csv(out / 'ranked_candidates.csv', index=False, encoding='utf-8-sig')
    c.head(args.batch_size).to_csv(out / 'next_batch.csv', index=False, encoding='utf-8-sig')
    print(f'Eligible candidates: {len(c)}; excluded duplicate/measured conditions: {int((~keep).sum())}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['simulate', 'recommend'])
    p.add_argument('--data', default=DEFAULT)
    p.add_argument('--sheet', default='ENRICHED_DATA')
    p.add_argument('--output', default='outputs/al')
    p.add_argument('--seeds', type=int, nargs='+', default=[42, 43, 44])
    p.add_argument('--initial', type=int, default=40)
    p.add_argument('--rounds', type=int, default=8)
    p.add_argument('--batch-size', type=int, default=5)
    p.add_argument('--beta', type=float, default=1.0)
    p.add_argument('--with-phase', action='store_true')
    p.add_argument('--candidates')
    p.add_argument('--strategy', choices=['random', 'uncertainty', 'lcb'], default='uncertainty')
    args = p.parse_args()
    if args.initial < 2 or args.rounds < 0 or args.batch_size < 1 or not np.isfinite(args.beta) or args.beta < 0:
        p.error('Require initial>=2, rounds>=0, batch-size>=1, finite beta>=0.')
    if args.mode == 'recommend' and not args.candidates:
        p.error('recommend requires --candidates')
    d = load(args.data, args.sheet)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (simulate if args.mode == 'simulate' else recommend)(d, args, out)
    metadata = vars(args) | {'n_records': len(d), 'target': 'log10(icorr_A_cm2)', 'data_sha256': __import__('hashlib').sha256(Path(args.data).read_bytes()).hexdigest()}
    (out / 'run.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Results: {out.resolve()}')


if __name__ == '__main__':
    main()
