"""Train latest cohorts, then evaluate a previously selected unseen paper."""
import sys, json, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import joblib
from corrosion_ml.data import NUM, PROCESS_NUM, CAT, PROCESS_CAT, labels
from corrosion_ml.model import fitted
from corrosion_ml.experiments import metrics, predict_without_target

def prepare(d):
    d = d.copy().reset_index(drop=True)
    for c in NUM + PROCESS_NUM:
        if c not in d:
            d[c] = np.nan
    for c in CAT + PROCESS_CAT:
        if c not in d:
            d[c] = 'missing'
        d[c] = d[c].fillna('missing')
    for c in ['P', 'S']:
        if c + '_upper_bound' in d:
            d[c + '_upper_bound_wt_pct'] = d[c + '_upper_bound']
    return d

def main():
    out = ROOT / 'results/latest_external_20261024'
    out.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'data/al_expanded_20261024/expanded_source_only.csv'
    raw = pd.read_csv(source, float_precision='round_trip')
    eligible = raw[raw.target_verified.fillna(False).astype(bool) & raw.icorr_A_cm2.gt(0)].copy()
    thermal = eligible[eligible.checked_heat_label_available.fillna(False).astype(bool)].copy()
    external = pd.read_csv(ROOT / 'results/external_paper_20261024/source_inputs.csv')
    # Restore the source's steel-family label explicitly in case of encoding damage.
    external['steel_family'] = '스테인리스강'
    external = prepare(external)
    doi = '10.1016/j.prostr.2025.08.043'
    assert not raw.source_paper_id.astype(str).str.lower().str.contains(doi, regex=False).any()
    assert set(external.record_id).isdisjoint(set(raw.record_id))
    summary = dict(external_doi=doi, evaluation='Retrospective unseen-paper validation; not a prospective new experiment',
                   source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                   primary='Four 480 C aging conditions; AR secondary',
                   model_settings='Existing SVR C=10 epsilon=0.15 gamma=scale; no tuning using external outcomes',
                   missing_policy='Unreported values remain missing; preprocessing fitted on training corpus only',
                   external_used_in_fit=False, production_model_replaced=False, models={})
    results = []
    for name, cohort in [('expanded_verified_377', eligible), ('expanded_thermal_342', thermal)]:
        train = prepare(cohort)
        model, _ = fitted(train, labels(train), n_members=15, seed=42)
        assert doi not in model.named_steps['composition'].training_papers_
        pred = predict_without_target(model, external.drop(columns=['icorr_A_cm2']))
        result = external.copy()
        result['model'] = name
        result['observed_log10'] = np.log10(result.icorr_A_cm2)
        result['predicted_log10'] = pred
        result['predicted_A_cm2'] = 10. ** pred
        result['absolute_fold_error'] = 10. ** abs(pred - result.observed_log10)
        primary = result[result.evaluation_role.eq('primary_aged')]
        model_path = out / (name + '.joblib')
        joblib.dump(model, model_path)
        summary['models'][name] = dict(n_train=len(train), n_papers=int(train.source_paper_id.nunique()),
            primary=metrics(primary.observed_log10, primary.predicted_log10),
            secondary_all_five=metrics(result.observed_log10, result.predicted_log10),
            model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest())
        results.append(result)
        print(name, json.dumps(summary['models'][name]), flush=True)
        print(primary[['source_sample_id','icorr_A_cm2','predicted_A_cm2','absolute_fold_error']].to_string(index=False), flush=True)
    pd.concat(results, ignore_index=True).to_csv(out/'predictions.csv', index=False, encoding='utf-8-sig')
    (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
