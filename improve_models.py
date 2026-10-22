"""Train-only grouped model selection, followed by fixed paper-holdout evaluation."""
import argparse
import hashlib
import json
import importlib.metadata
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from threadpoolctl import threadpool_limits

import active_learning as al
from regression_models import build_model, configurations


def choose_config(x, y, groups, configs, seed, folds=3, vae_epochs=150):
    """Does not accept external test inputs/labels; all preprocessing is fold-local."""
    if pd.Series(groups).isna().any() or len(set(groups)) < folds:
        raise ValueError('Need nonmissing paper groups and at least one group per CV fold.')
    cv = list(GroupKFold(n_splits=folds).split(x, y, groups))
    results = []
    for config_id, config in enumerate(configs):
        oof = np.full(len(y), np.nan)
        for fit_ids, valid_ids in cv:
            model = build_model(config, seed, vae_epochs)
            model.fit(x.iloc[fit_ids], y[fit_ids])
            oof[valid_ids] = model.predict(x.iloc[valid_ids])
        if not np.isfinite(oof).all():
            raise ValueError(f'Non-finite out-of-fold predictions: {config}')
        error = pd.DataFrame({'paper': groups, 'ae': abs(y - oof)})
        results.append(dict(config_id=config_id, model=config['model'], features=config['features'], params=json.dumps(config['params'], sort_keys=True), cv_rmse_log10=float(np.sqrt(mean_squared_error(y, oof))), cv_mae_log10=mean_absolute_error(y, oof), cv_paper_macro_mae_log10=error.groupby('paper').ae.mean().mean()))
    results = pd.DataFrame(results)
    best = int(results.sort_values(['cv_rmse_log10', 'config_id']).iloc[0].config_id)
    return best, results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', default='data/curated_corrosion.csv')
    p.add_argument('--output', default='outputs/model_selection')
    p.add_argument('--seeds', nargs='+', type=int, default=[42, 43, 44])
    p.add_argument('--folds', type=int, default=3)
    p.add_argument('--include-vae', action='store_true')
    p.add_argument('--vae-epochs', type=int, default=150)
    p.add_argument('--fit-final', action='store_true', help='Also select/refit on all provided rows, after evaluation.')
    args = p.parse_args()
    if args.folds < 2 or args.vae_epochs < 1:
        p.error('folds>=2 and vae-epochs>=1 required')
    d = al.load(args.data)
    x, _, _ = al.features(d, process=True)
    y = al.labels(d)
    if d.source_paper_id.isna().any() or d.source_paper_id.nunique() < args.folds + 2:
        p.error('Insufficient or missing source_paper_id groups')
    groups = d.source_paper_id.to_numpy()
    configs = configurations(args.include_vae)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    # Freeze the whole search space before observing any new holdout result.
    (out / 'search_space.json').write_text(json.dumps(configs, indent=2), encoding='utf-8')
    metrics, predictions, cv_records, splits, selections = [], [], [], [], []
    with threadpool_limits(limits=1):
        for seed in args.seeds:
            train, test = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=seed).split(x, y, groups))
            xt = x.iloc[train].reset_index(drop=True)
            yt, gt = y[train], groups[train]
            print(f'seed={seed}: selecting {len(configs)} configurations using training papers only...', flush=True)
            best, cv = choose_config(xt, yt, gt, configs, seed, args.folds, args.vae_epochs)
            cv_records.extend(cv.assign(seed=seed).to_dict('records'))
            chosen = {'selected_by_inner_cv': best}
            for family, table in cv.groupby('model'):
                chosen['family_' + family] = int(table.sort_values(['cv_rmse_log10', 'config_id']).iloc[0].config_id)
            baseline = {'model': 'random_forest', 'features': 'basic', 'params': {'min_samples_leaf': 2}}
            choices = [(name, configs[i], i) for name, i in chosen.items()] + [('fixed_previous_rf', baseline, -1)]
            selections.append(dict(seed=seed, selected_config=configs[best], inner_cv_rmse=float(cv.loc[best, 'cv_rmse_log10'])))
            # Only now evaluate each preregistered family winner on external holdout.
            fitted = {}
            for name, config, config_id in choices:
                key = json.dumps(config, sort_keys=True)
                if key not in fitted:
                    model = build_model(config, seed, args.vae_epochs)
                    model.fit(xt, yt)
                    fitted[key] = (model, model.predict(x.iloc[test]))
                model, pred = fitted[key]
                metrics.append(dict(seed=seed, evaluation=name, model=config['model'], features=config['features'], config_id=config_id, n_train=len(train), n_test=len(test), test_r2_log10=r2_score(y[test], pred), test_rmse_log10=float(np.sqrt(mean_squared_error(y[test], pred))), test_mae_log10=mean_absolute_error(y[test], pred)))
                for i, value in zip(test, pred):
                    predictions.append(dict(seed=seed, evaluation=name, record_id=d.record_id.iloc[i], source_paper_id=groups[i], observed_log10=y[i], predicted_log10=value))
                if name == 'selected_by_inner_cv':
                    joblib.dump(model, out / f'model_seed{seed}.joblib')
            inner = list(GroupKFold(args.folds).split(xt, yt, gt))
            for fold, (fit_ids, valid_ids) in enumerate(inner):
                assert not set(gt[fit_ids]) & set(gt[valid_ids])
                for local, global_id in enumerate(train):
                    splits.append(dict(seed=seed, record_id=d.record_id.iloc[global_id], source_paper_id=groups[global_id], fold=fold, partition='inner_valid' if local in valid_ids else 'inner_train'))
            for i in test:
                splits.append(dict(seed=seed, record_id=d.record_id.iloc[i], source_paper_id=groups[i], fold=-1, partition='outer_test'))
            print(f'seed={seed}: training-CV winner={configs[best]}', flush=True)
        if args.fit_final:
            best, cv = choose_config(x, y, groups, configs, args.seeds[0], args.folds, args.vae_epochs)
            cv.to_csv(out / 'final_training_cv.csv', index=False)
            model = build_model(configs[best], args.seeds[0], args.vae_epochs).fit(x, y)
            joblib.dump(model, out / 'final_model.joblib')
            (out / 'final_config.json').write_text(json.dumps(configs[best], indent=2), encoding='utf-8')
    pd.DataFrame(cv_records).to_csv(out / 'training_cv.csv', index=False)
    frame = pd.DataFrame(metrics)
    frame.to_csv(out / 'metrics.csv', index=False)
    pd.DataFrame(predictions).to_csv(out / 'predictions.csv', index=False)
    pd.DataFrame(splits).to_csv(out / 'splits.csv', index=False)
    summary = frame.groupby('evaluation')[['test_r2_log10', 'test_rmse_log10', 'test_mae_log10']].agg(['mean', 'std'])
    summary.to_csv(out / 'summary.csv')
    versions = {name: importlib.metadata.version(name) for name in ['numpy', 'pandas', 'scikit-learn', 'joblib'] + (['torch'] if args.include_vae else [])}
    metadata = vars(args) | {'sha256': hashlib.sha256(Path(args.data).read_bytes()).hexdigest(), 'selection_objective': 'pooled inner OOF log10 RMSE', 'selections': selections, 'holdouts_reused_from_prior_reports': True, 'versions': versions, 'python': platform.python_version()}
    (out / 'run.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(summary.round(4).to_string())


if __name__ == '__main__':
    main()
