"""LCB recommendations from a fixed selected model and paper-bootstrap committee."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

import active_learning as al
from regression_models import build_model


def bootstrap_indices(groups, rng):
    unique = np.unique(groups)
    return np.concatenate([np.flatnonzero(groups == group) for group in rng.choice(unique, len(unique), replace=True)])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', default='data/curated_corrosion.csv')
    p.add_argument('--candidates', required=True)
    p.add_argument('--config', default='outputs/model_selection/final_config.json')
    p.add_argument('--output', default='outputs/advanced_batch')
    p.add_argument('--committee', type=int, default=5)
    p.add_argument('--batch-size', type=int, default=5)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--beta', type=float, default=1.)
    p.add_argument('--vae-epochs', type=int, default=150)
    p.add_argument('--strategy', choices=['uncertainty', 'lcb', 'random'], default='lcb')
    args = p.parse_args()
    if args.committee < 3 or args.batch_size < 1 or args.vae_epochs < 1 or not np.isfinite(args.beta) or args.beta < 0:
        p.error('Require committee>=3, batch-size>=1, vae-epochs>=1 and finite beta>=0.')
    d, c = al.load(args.data), al.load(args.candidates)
    if c.empty or set(c.record_id) & set(d.record_id):
        p.error('Candidate pool must be nonempty with IDs disjoint from measured data.')
    if al.TARGET in c and c[al.TARGET].notna().any():
        p.error('Candidate targets must be absent or blank.')
    if d.source_paper_id.isna().any() or d.source_paper_id.nunique() < 3:
        p.error('At least three nonmissing paper groups required for bootstrap committee.')
    x, nums, cats = al.features(d, process=True)
    cx, _, _ = al.features(c, process=True)
    fingerprints = pd.util.hash_pandas_object(x.round(10), index=False)
    cf = pd.util.hash_pandas_object(cx.round(10), index=False)
    keep = ~cf.isin(fingerprints) & ~cf.duplicated()
    excluded = int((~keep).sum())
    c, cx = c.loc[keep].copy(), cx.loc[keep].copy()
    if c.empty:
        p.error('No novel candidate conditions remain after duplicate removal.')
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    y = al.labels(d)
    rng = np.random.default_rng(args.seed)
    predictions = []
    with threadpool_limits(limits=1):
        for member in range(args.committee):
            ids = bootstrap_indices(d.source_paper_id.to_numpy(), rng)
            model = build_model(config, args.seed + member, args.vae_epochs)
            model.fit(x.iloc[ids], y[ids])
            predictions.append(model.predict(cx))
    values = np.asarray(predictions)
    if not np.isfinite(values).all():
        raise ValueError('Non-finite committee prediction.')
    mu, sigma = values.mean(0), values.std(0, ddof=1)
    c['pred_log10_icorr'] = mu
    c['committee_std_log10'] = sigma
    c['pred_icorr_geometric_A_cm2'] = 10 ** mu
    c['lcb_log10'] = mu - args.beta * sigma
    c['n_numeric_outside_training_range'] = sum(((cx[col] < x[col].min()) | (cx[col] > x[col].max())).astype(int) for col in nums)
    c['n_numeric_without_training_support'] = sum((cx[col].notna() & x[col].isna().all()).astype(int) for col in nums)
    c['n_unseen_categories'] = sum((~cx[col].isin(x[col].unique())).astype(int) for col in cats)
    take = al.select(mu, sigma, len(c), args.strategy, args.beta, rng)
    c = c.iloc[take].copy()
    c.insert(0, 'rank', range(1, len(c) + 1))
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    c.to_csv(out / 'ranked_candidates.csv', index=False, encoding='utf-8-sig')
    c.head(args.batch_size).to_csv(out / 'next_batch.csv', index=False, encoding='utf-8-sig')
    metadata = vars(args) | {'config': config, 'n_excluded_duplicates': excluded, 'uncertainty': 'sample std of paper-bootstrap model predictions; uncalibrated', 'sha256': {name: hashlib.sha256(Path(path).read_bytes()).hexdigest() for name, path in [('training', args.data), ('candidates', args.candidates), ('config', args.config)]}}
    (out / 'run.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(f'Eligible candidates: {len(c)}; excluded repeats: {excluded}; next batch: {min(len(c), args.batch_size)}')


if __name__ == '__main__':
    main()
