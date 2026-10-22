"""Compare fixed model/data variants on identical paper holdouts; no tuning."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit

import active_learning as al


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original', default=al.DEFAULT)
    p.add_argument('--curated', default='data/curated_corrosion.csv')
    p.add_argument('--output', default='outputs/curation_benchmark')
    p.add_argument('--seeds', type=int, nargs='+', default=[42, 43, 44])
    args = p.parse_args()
    original, curated = al.load(args.original), al.load(args.curated)
    if set(original.record_id) != set(curated.record_id):
        raise ValueError('Original and curated IDs must match exactly.')
    curated = curated.set_index('record_id').loc[original.record_id].reset_index()
    if not original.source_paper_id.equals(curated.source_paper_id):
        raise ValueError('Paper groups changed; fixed-split comparison would be invalid.')
    y = al.labels(original)
    if not np.array_equal(y, al.labels(curated)):
        raise ValueError('This comparison expects identical targets.')
    rows, predictions, splits = [], [], []
    variants = [('original', original, False), ('curated_base', curated, False), ('curated_process', curated, True)]
    for seed in args.seeds:
        train, test = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=seed).split(original, groups=original.source_paper_id))
        # Reproduce the random acquisition strategy's 40 + 8*5 records.
        known = np.random.default_rng(seed).choice(train, 40, replace=False).tolist()
        pool = [i for i in train if i not in known]
        rng = np.random.default_rng(seed)
        for _ in range(8):
            chosen = [pool[i] for i in rng.permutation(len(pool))[:5]]
            known.extend(chosen)
            pool = [i for i in pool if i not in chosen]
        for i in range(len(original)):
            splits.append(dict(seed=seed, record_id=original.record_id.iloc[i], source_paper_id=original.source_paper_id.iloc[i], partition='test' if i in test else 'train', in_80=i in known))
        for budget, train_ids in [('random80', known), ('full_train', train)]:
            for name, data, process in variants:
                x, nums, cats = al.features(data, process=process)
                pre, model = al.fit(x.iloc[train_ids], y[train_ids], nums, cats, seed)
                pred, _ = al.predict(pre, model, x.iloc[test])
                rows.append(dict(seed=seed, budget=budget, variant=name, n_train=len(train_ids), n_test=len(test), mae_log10=mean_absolute_error(y[test], pred), rmse_log10=float(np.sqrt(mean_squared_error(y[test], pred))), r2_log10=r2_score(y[test], pred)))
                for i, value in zip(test, pred):
                    predictions.append(dict(seed=seed, budget=budget, variant=name, record_id=original.record_id.iloc[i], source_paper_id=original.source_paper_id.iloc[i], observed_log10=y[i], predicted_log10=value, absolute_error_log10=abs(y[i]-value)))
            baseline = DummyRegressor(strategy='mean').fit(np.zeros((len(train_ids), 1)), y[train_ids])
            pred = baseline.predict(np.zeros((len(test), 1)))
            rows.append(dict(seed=seed, budget=budget, variant='train_mean', n_train=len(train_ids), n_test=len(test), mae_log10=mean_absolute_error(y[test], pred), rmse_log10=float(np.sqrt(mean_squared_error(y[test], pred))), r2_log10=r2_score(y[test], pred)))
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    metrics = pd.DataFrame(rows)
    metrics.to_csv(out / 'metrics.csv', index=False)
    summary = metrics.groupby(['budget', 'variant'])[['mae_log10', 'rmse_log10', 'r2_log10']].agg(['mean', 'std'])
    summary.to_csv(out / 'summary.csv')
    pd.DataFrame(splits).to_csv(out / 'splits.csv', index=False)
    pred = pd.DataFrame(predictions)
    pred.to_csv(out / 'predictions.csv', index=False)
    pred.groupby(['seed', 'budget', 'variant', 'source_paper_id']).absolute_error_log10.agg(['size', 'mean', 'max']).to_csv(out / 'per_paper_errors.csv')
    manifest = vars(args) | {'sha256': {name: hashlib.sha256(Path(path).read_bytes()).hexdigest() for name, path in [('original', args.original), ('curated', args.curated)]}, 'model': 'fixed RF; no model selection or holdout-driven tuning'}
    (out / 'run.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(summary.round(4).to_string())


if __name__ == '__main__':
    main()
