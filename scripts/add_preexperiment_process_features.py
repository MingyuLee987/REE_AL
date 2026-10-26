"""Add source-supported, controllable process features without changing labels."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data/al_curated_20261023'
NUM = '''solution_temperature_C solution_time_min aging_temperature_C aging_time_min annealing_temperature_C annealing_time_min billet_reheat_temperature_C billet_reheat_time_min rolling_start_temperature_C rolling_finish_temperature_C rolling_pass_count rolling_final_thickness_mm accelerated_cooling_end_temperature_C deformation_temperature_C deformation_strain_rate_s_1 sintering_temperature_C sintering_time_min sintering_pressure_MPa sintering_heating_rate_C_min welding_voltage_V welding_current_A welding_speed_mm_min welding_heat_input_kJ_mm'''.split()
CAT = '''manufacturing_route_cat solution_cooling_cat aging_cooling_cat annealing_cooling_cat rolling_cooling_cat heat_treatment_atmosphere_cat'''.split()

def main():
    d = pd.read_csv(DEST/'al_labeled_prepared_review.csv', float_precision='round_trip')
    original = d.copy()
    for c in NUM: d[c] = float('nan')
    for c in CAT: d[c] = ''
    provenance = pd.read_csv(DEST/'source_and_proxy_provenance.csv').fillna('')
    logs = []
    for i, r in d.iterrows():
        p, sample = r.source_paper_id, str(r.source_sample_id)
        values = {}
        if p == '10.3390/met13010066': values = dict(manufacturing_route_cat='ultra_thin_cast_strip_rolling')
        elif p == '10.1002/srin.202400576': values = dict(manufacturing_route_cat='hot_rolling')
        elif p == '10.3390/ma19122685':
            values = dict(manufacturing_route_cat='controlled_hot_rolling', billet_reheat_temperature_C=1200, billet_reheat_time_min=120, rolling_start_temperature_C=1000, rolling_finish_temperature_C=880, rolling_pass_count=6, rolling_final_thickness_mm=14, accelerated_cooling_end_temperature_C=440, rolling_cooling_cat='water_cooling_then_air_cooling')
        elif p in ['10.1007/s10853-025-11514-0','10.1016/j.isci.2025.113319']:
            values = dict(manufacturing_route_cat='TIG_welding')
            if p == '10.1016/j.isci.2025.113319': values.update(welding_voltage_V=12, welding_current_A=90, welding_speed_mm_min=80, welding_heat_input_kJ_mm=.57)
        elif p == '10.1186/s40712-025-00240-9':
            values = dict(manufacturing_route_cat='annealing', annealing_temperature_C=r.heat_treatment_temperature_C, annealing_time_min=r.heat_treatment_time_min, annealing_cooling_cat='furnace_cooling')
        elif p == '10.3390/ma12091455':
            values = dict(manufacturing_route_cat='hot_deformation', deformation_temperature_C=1050 if '1050' in sample else 850, deformation_strain_rate_s_1=.01 if '0.01' in sample else 10)
        elif p == '10.3390/ma15248780':
            values = dict(manufacturing_route_cat='solution_treatment_then_aging', solution_temperature_C=r.heat_treatment_temperature_C, solution_time_min=r.heat_treatment_time_min, solution_cooling_cat='water_quench', aging_temperature_C=900, aging_time_min=30, aging_cooling_cat='air_cooling')
        elif p == '10.3390/ma18081823':
            values = dict(manufacturing_route_cat='solution_treatment_then_aging', solution_temperature_C=1040, solution_time_min=60, solution_cooling_cat='water_quench', aging_temperature_C=r.heat_treatment_temperature_C, aging_time_min=r.heat_treatment_time_min, heat_treatment_atmosphere_cat='vacuum')
        elif p == '10.1038/s41598-026-65428-1':
            values = dict(manufacturing_route_cat='HFIHS_sintering', sintering_temperature_C=r.heat_treatment_temperature_C, sintering_time_min=r.heat_treatment_time_min, sintering_pressure_MPa=40, sintering_heating_rate_C_min=150)
        elif p == '10.3390/ma18122722':
            values = dict(manufacturing_route_cat='HIP_sintering', sintering_temperature_C=1300, sintering_time_min=120, sintering_pressure_MPa=100)
        evidence = provenance.loc[provenance.record_id.eq(r.record_id) & provenance.field.isin(['sample_process_cat','heat_treatment_temperature_C','heat_treatment_time_min']), ['field','evidence','location','note']].to_dict('records')
        for c, v in values.items():
            d.loc[i,c] = v
            logs.append(dict(record_id=r.record_id, source_paper_id=p, feature=c, value=v, source_url=r.source_url, evidence=json.dumps(evidence,ensure_ascii=False), source_process_description=str(r.sample_process_cat), method='manual_stage_mapping_of_reviewed_source_conditions', note='Rolling temperatures/thickness approximate; 35CrMoV results use 1050 C despite methods inconsistency; see original review.'))
    pd.testing.assert_frame_equal(d[original.columns],original)
    d.to_csv(DEST/'al_labeled_with_process_features.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(logs).to_csv(DEST/'process_feature_provenance.csv',index=False,encoding='utf-8-sig')
    report = pd.DataFrame([dict(feature=c, populated=int(d[c].replace('',pd.NA).notna().sum()), missing_pct=round(d[c].replace('',pd.NA).isna().mean()*100,2)) for c in NUM+CAT])
    report.to_csv(DEST/'process_feature_missingness.csv',index=False,encoding='utf-8-sig')
    composition = 'C Si Mn P S Cr Ni Mo Cu N RE_ppm RE_element_cat'.split()
    conditions = 'electrolyte_condition_cat temperature_C temperature_condition_cat pH exposure_h scan_rate_mV_s ocp_stabilization_min'.split()
    schema = dict(numeric_process_features=NUM,categorical_process_features=CAT, candidate_predictor_columns=composition+conditions+NUM+CAT,target='log10(icorr_A_cm2)',group='source_paper_id',excluded_postmanufacture_features=['grain_size_um','grain_size_ASTM_number','matrix_phase_group'],excluded_ambiguous_legacy_process_columns=['sample_process_cat','heat_treatment_temperature_C','heat_treatment_time_min'],policies=['Unknown and inapplicable numeric values remain blank; do not replace with zero or donor-paper process conditions.','Route-specific numeric parameters require route-aware preprocessing. Blank alone does not distinguish unreported from inapplicable.','No grain or phase completeness requirement. Prior core_complete flags describe the old grain-aware review and are not selection criteria for this feature set.','Composition remains review-time filled; fit composition imputers within each paper-group training split.','RE_ppm and elemental composition may be measured residual/assayed chemistry. For prospective design, use separately verified nominal recipe inputs or an explicit recipe-to-assay model.','Only target_verified rows are eligible as checked labels. This file has not trained or modified the existing model.','Manufacturing route comes from reviewed source descriptions. Generic route names do not establish absence of earlier process stages.'])
    (DEST/'preexperiment_feature_schema.json').write_text(json.dumps(schema,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(rows=len(d),new_features=len(NUM+CAT),rows_with_route=int(d.manufacturing_route_cat.ne('').sum()),rows_with_any_numeric_process=int(d[NUM].notna().any(axis=1).sum()),verified_target_rows=int(d.target_verified.sum()),original_columns_unchanged=True),indent=2))
    print(report.to_string(index=False))

if __name__ == '__main__': main()
