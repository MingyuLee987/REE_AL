"""Select just the existing temperature/time pair as process predictors."""
import json
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[1] / 'data/al_curated_20261023'
d = pd.read_csv(root / 'al_labeled_prepared_review.csv', float_precision='round_trip')
process = ['heat_treatment_temperature_C', 'heat_treatment_time_min']
composition = 'C Si Mn P S Cr Ni Mo Cu N RE_ppm RE_element_cat'.split()
conditions = 'electrolyte_condition_cat temperature_C temperature_condition_cat pH exposure_h scan_rate_mV_s ocp_stabilization_min'.split()
predictors = composition + conditions + process
metadata = ['record_id', 'source_paper_id', 'source_sample_id', 'source_url', 'target_verified', 'target_review_status', 'composition_uses_assumptions']
result = d[metadata + predictors + ['icorr_A_cm2']].copy()
result.to_csv(root / 'al_labeled_heat_treatment_only.csv', index=False, encoding='utf-8-sig')
pd.testing.assert_frame_equal(result, d[result.columns])
schema = dict(predictor_columns=predictors, numeric_process_features=process,
    categorical_process_features=[], target='log10(icorr_A_cm2)', group='source_paper_id',
    metadata_not_predictors=metadata,
    notes=['Only heat-treatment temperature and hold time are selected as process features.',
           'The original single temperature/time pair is preserved: solutionizing for ma15248780, aging for ma18081823, annealing, billet reheating or sintering for other sources. A single pair does not encode complete multi-stage history.',
           'Do not use grain size, phase, manufacturing route, cooling, rolling or welding parameters as predictors.',
           'Unknown process values remain missing. Composition imputation must be fitted within paper-group training splits.',
           'Only target_verified rows have checked targets. This change does not retrain the model.'])
(root / 'heat_treatment_only_feature_schema.json').write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(rows=len(result),process_features=process,complete_temperature_time_pairs=int(result[process].notna().all(axis=1).sum()),missing_pairs=int(result[process].isna().any(axis=1).sum()),all_selected_values_preserved=True),indent=2))
