"""Apply explicitly reviewed, source-linked corrections without modifying XLSX."""
from pathlib import Path
import hashlib
import json
import re

import numpy as np
import pandas as pd

from active_learning import DEFAULT

ROOT = Path('audit')
DATA = Path('data')

# Review scopes are deliberately narrower than 'paper/data fully verified'.
REVIEWS = {
    '10.1038/s41598-024-67799-9': ('methods_and_composition_body_targets', 'Methods; Table 1; polarization discussion', 'mA/cm2', 'C2=3.35 in discussion versus 6.350 in conclusions; retain source conflict. C1 is a graph estimate, not a tabulated measurement.'),
    '10.1038/s41529-025-00682-8': ('methods_composition_and_three_target_checks', 'Methods; Table 1; conclusions; Figures 6/8/10', 'A/cm2', '60 targets are principally figure-derived; only three day-8 values crosschecked against body. pH is >14, scan rate not found in inspected methods.'),
    '10.1007/s10853-025-11514-0': ('methods_composition_and_five_tabulated_targets', 'Methods; Tables 1 and 4; Figure 9', 'uA/cm2', 'Five Table 4 targets agree after conversion. Five day-0 targets remain figure-derived. Table 1 is base-alloy composition, not measured weld-zone chemistry.'),
    '10.1007/s11663-025-03817-z': ('methods_composition_and_all_targets', 'Experimental; Tables I and IV', '1e-7 A/cm2', '18 stored targets match Table IV. Heat-treatment temperature/time are separate from corrosion test temperature. Scan rate, pH and one-hour exposure not found in inspected methods.'),
    '10.1007/s11663-026-04267-x': ('methods_composition_and_body_targets', 'Sections 2 and 3.4; Table I; Figure 10', 'A/cm2', 'Two targets and total Ce+La composition agree. OCP duration and pH not quantified in inspected methods.'),
    '10.1007/s42243-025-01553-x': ('methods_and_all_targets', 'Section 2; Figure 6; Table 4', 'uA/cm2', 'Four targets agree. RE ppm is CC-stage value from Figure 6 discussion; Table 2 composition belongs to LF-stage samples, retained with stage caveat.'),
    '10.1007/s11665-015-1651-6': ('methods_composition_and_all_target_numbers', 'Corrosion Tests; Tables 1 and 5-7', 'printed Amp/cm (ambiguous)', '15 target numbers agree, but table unit is printed Amp/cm rather than A/cm2; exposed area is 1 cm2. Do not silently declare dimensional verification. Room temperature is not exact 25 C.'),
    '10.1134/s2070205124702265': ('methods_composition_and_all_targets', 'Section 2; Tables 1-2', 'A/cm2', 'Two targets agree. 30 min OCP monitoring is reported; 36 h weight-loss exposure must not be assigned to polarization.'),
    '10.1134/s2070205125700261': ('methods_composition_and_all_targets', 'Section 2; Tables 1 and 3', 'A/cm2', 'Two targets agree. OCP monitored for 400 s; salt-spray durations are separate experiments.'),
    '10.1007/s11003-015-9767-2': ('methods_and_figure_provenance', 'Experimental; Figure 2 caption', 'uA/cm2', 'Fe-Nb-B-Dy/Tb amorphous alloys, not conventional steels. Values digitized from cycle curves; source caption specifies nine cycles, body mentions ten.'),
    '10.3390/ma17184467': ('methods_composition_and_all_targets', 'Section 2; Tables 1-2', 'A/cm2', 'Five stored targets match zero-added-La-solution rows. pH=4.7 and one-hour exposure not found in inspected electrochemical methods; OCP is 30 min.'),
    '10.3390/ma18010069': ('methods_composition_and_all_targets', 'Methods; Tables 2 and 4', 'A/cm2', 'Three targets agree. Scan 0.167 mV/s agrees. Exact 22 C, pH=7, one-hour exposure not found in inspected methods.'),
    '10.3390/ma19122685': ('methods_composition_and_all_targets', 'Methods; Tables 1-2', '1e-6 A/cm2', 'Three targets agree. P and S are upper limits, not measured exact values. Room temperature; pH=7.1 and one-hour exposure not found in inspected methods.'),
    '10.3390/ma12203359': ('methods_composition_and_all_targets', 'Section 2.2.1; Tables 1-2', '1e-5 A/cm2', 'Three targets agree. 25+-1 C and scan 0.333 mV/s reported. OCP duration and pH not reported in inspected method.'),
    '10.3390/ma14123254': ('methods_composition_and_all_targets', 'Methods; Tables 1 and 4', 'mA/cm2', 'Three targets agree after conversion. No RE-alloying series; heat treatment varies. pH, exposure and 1 mV/s scan not found in inspected method.'),
    '10.3390/ma14040929': ('methods_and_all_targets', 'Methods; Table 1', 'uA/cm2', 'Three targets agree after conversion. Fe-based metallic glass, not conventional steel. OCP 30 min; exact pH=0 and 25 C are assumptions.'),
    '10.3390/ma16020876': ('methods_composition_and_all_targets', 'Methods; Tables 1 and 4', 'printed A cm2 (unit typo)', 'Two target numbers agree; text/table have formatting inconsistencies. Combined Al+Ca+Zr+Ti+RE=0.04 wt% cannot specify RE ppm.'),
    '10.3390/ma15228269': ('methods_and_figure_provenance', 'Methods; Figure 6', 'figure-derived current', 'Six targets lack a numeric icorr table. Caption has 0/0.1/1/3.5 wt% chloride conditions. Do not infer icorr from EIS resistance table.'),
    '10.1038/s41598-018-23273-x': ('methods_composition_and_figure_provenance', 'Methods; Tables 1-2; polarization figure', 'figure-derived current', 'Five stored currents are not tabulated; Table 2 reports potentials only. Require digitization uncertainty; do not treat as exact measured fit values.'),
    '10.1016/j.isci.2025.113319': ('methods_and_figure_provenance', 'STAR Methods; electrochemical measurements', 'figure-derived current', 'Ten stored targets are digitized, not tabulated. HAZ and 12-day seawater exposure are reported. pH=8.1 not found in inspected electrochemical methods.'),
}


def build(source=DEFAULT):
    ROOT.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    original = pd.read_excel(source, sheet_name='ENRICHED_DATA')
    d = original.copy()
    changes = []
    for c in ['heat_treatment_temperature_C', 'heat_treatment_time_min', 'ocp_stabilization_min', 'pH_lower_bound', 'P_upper_bound_wt_pct', 'S_upper_bound_wt_pct']:
        d[c] = np.nan
    for c in ['sample_process_cat', 'sample_region_cat', 'temperature_condition_cat']:
        d[c] = pd.Series(np.nan, index=d.index, dtype=object)
    d['target_review_status'] = 'not_verified'
    d['paper_review_scope'] = 'not_reviewed'
    d['review_source_url'] = ''

    def patch(mask, col, value, doi, locator, reason):
        url = 'https://doi.org/' + doi
        for i in d.index[mask]:
            old = d.at[i, col]
            same = (pd.isna(old) and pd.isna(value)) or (pd.notna(old) and pd.notna(value) and old == value)
            if same:
                continue
            changes.append(dict(record_id=d.at[i, 'record_id'], source_paper_id=doi, column=col, old_value=old, new_value=value, source_url=url, locator=locator, reason=reason))
            d.at[i, col] = value

    def apply(doi, updates, locator, reason, mask=None):
        mask = d.source_paper_id.eq(doi) if mask is None else (d.source_paper_id.eq(doi) & mask)
        for col, val in updates.items():
            patch(mask, col, val, doi, locator, reason)

    for doi, (scope, locator, unit, note) in REVIEWS.items():
        m = d.source_paper_id.eq(doi)
        d.loc[m, 'paper_review_scope'] = scope
        d.loc[m, 'review_source_url'] = 'https://doi.org/' + doi
        if 'all_targets' in scope:
            d.loc[m, 'target_review_status'] = 'table_numbers_and_units_checked'
        elif 'figure_provenance' in scope:
            d.loc[m, 'target_review_status'] = 'figure_values_not_redigitized'
        else:
            d.loc[m, 'target_review_status'] = 'partially_checked_see_paper_review'
    d.loc[d.source_paper_id.eq('10.1007/s11665-015-1651-6'), 'target_review_status'] = 'numbers_match_unit_ambiguous'
    d.loc[d.source_paper_id.eq('10.3390/ma16020876'), 'target_review_status'] = 'numbers_match_printed_unit_typo'
    m = d.source_paper_id.eq('10.1007/s10853-025-11514-0')
    d.loc[m & d.source_sample_id.str.contains('Table4'), 'target_review_status'] = 'table_numbers_and_units_checked'
    d.loc[m & d.source_sample_id.str.contains('Fig9a'), 'target_review_status'] = 'figure_values_not_redigitized'
    m = d.source_paper_id.eq('10.1038/s41598-024-67799-9')
    d.loc[m & d.source_sample_id.isin(['C0', 'C3']), 'target_review_status'] = 'body_number_and_unit_checked'
    d.loc[m & d.source_sample_id.eq('C2'), 'target_review_status'] = 'source_internal_numeric_conflict'
    d.loc[m & d.source_sample_id.eq('C1'), 'target_review_status'] = 'figure_values_not_redigitized'
    m = d.source_paper_id.eq('10.1038/s41529-025-00682-8')
    d.loc[m, 'target_review_status'] = 'figure_values_not_redigitized'
    d.loc[m & d.source_sample_id.isin(['0La_25C_8d', '0.5La_50C_8d', '0.5La_75C_8d']), 'target_review_status'] = 'body_number_and_unit_checked'
    d.loc[d.source_paper_id.eq('10.1007/s11663-026-04267-x'), 'target_review_status'] = 'body_number_and_unit_checked'

    # C1 belongs to the same 960-hour rusted-sample series as C0/C2/C3.
    doi = '10.1038/s41598-024-67799-9'
    apply(doi, {'exposure_h': 960., 'pH': 7.05, 'electrolyte_condition_cat': 'NaCl_3.5wtpct'}, 'Immersion experiments and electrochemical measurements', 'Same 960 h immersion and solution for all four samples', d.source_sample_id.eq('C1'))
    apply(doi, {'ocp_stabilization_min': 60., 'sample_region_cat': 'rusted_surface'}, 'Electrochemical measurements', 'OCP monitoring of rusted samples is 1 h; not the total immersion time')

    doi = '10.1038/s41529-025-00682-8'
    apply(doi, {'pH': np.nan, 'pH_lower_bound': 14., 'scan_rate_mV_s': np.nan}, 'Methods / Electrochemical testing', 'Source reports pH >14; exact pH and polarization scan rate not found in inspected method')
    apply(doi, {'heat_treatment_temperature_C': 1200., 'heat_treatment_time_min': 60., 'sample_process_cat': 'solution_treated_water_quenched', 'sample_region_cat': 'base_metal'}, 'Methods / Experimental materials', 'Solution treatment at 1200 C for 1 h followed by water cooling')

    doi = '10.1007/s10853-025-11514-0'
    for sample, nitrogen in [('0La', .19), ('0.5La', .21), ('1.0La', .19), ('1.5La', .21), ('2.0La', .19)]:
        apply(doi, {'N': nitrogen}, 'Table 1', 'Reported base-alloy nitrogen; not weld-zone EDS chemistry', d.source_sample_id.str.startswith(sample + '_'))
    apply(doi, {'sample_process_cat': 'TIG_welded', 'sample_region_cat': 'weld_joint'}, 'Materials and methods / welding procedure', 'Welded joint with dissimilar Q235 component and ER-NiCrMo-3 filler; bulk composition alone is incomplete')
    apply(doi, {'pH': np.nan}, 'Methods / Electrochemical testing', 'Exact pH=8.1 not found in inspected natural-seawater test description')

    doi = '10.1007/s11663-025-03817-z'
    apply(doi, {'pH': np.nan, 'exposure_h': np.nan, 'scan_rate_mV_s': np.nan}, 'Experimental / Experimentation and Analysis', 'OCP until stable is reported, but no quantified duration, pH or polarization scan rate in inspected method')
    for i in d.index[d.source_paper_id.eq(doi)]:
        sample = d.at[i, 'source_sample_id']
        m = re.fullmatch(r'S[02]_(\d+)C_(\d+)min', sample)
        updates = {'sample_process_cat': 'untreated'}
        if m:
            updates = {'heat_treatment_temperature_C': float(m[1]), 'heat_treatment_time_min': float(m[2]), 'sample_process_cat': 'solution_treated_water_quenched'}
        apply(doi, updates, 'Table IV and Experimental', 'Source-defined sample condition; heat temperature must not replace corrosion test temperature', d.index == i)

    for doi, minutes in [('10.1134/s2070205124702265', 30.), ('10.1134/s2070205125700261', 400. / 60.)]:
        apply(doi, {'pH': np.nan, 'exposure_h': np.nan, 'ocp_stabilization_min': minutes}, 'Section 2 / electrochemical methods', 'Quantified OCP stabilization is separate from prior corrosion exposure; pH not reported')

    doi = '10.1007/s11663-026-04267-x'
    apply(doi, {'pH': np.nan, 'exposure_h': np.nan}, 'Section 2.3 / electrochemical method', 'OCP stabilization without numeric duration; exact pH not reported')

    doi = '10.1007/s42243-025-01553-x'
    apply(doi, {'pH': np.nan, 'ocp_stabilization_min': 60., 'sample_process_cat': 'continuous_cast'}, 'Section 2 / electrochemical method', '3600 s OCP monitoring reported; pH not reported. Existing exposure_h=1 is retained with OCP interpretation caveat')

    doi = '10.1007/s11665-015-1651-6'
    apply(doi, {'pH': np.nan, 'scan_rate_mV_s': np.nan, 'temperature_C': np.nan, 'temperature_condition_cat': 'room_temperature', 'sample_process_cat': 'forged'}, 'Experimental / Corrosion Tests', 'Room temperature reported; exact 25 C, pH=0.3 and 0.5 mV/s not found in inspected method')

    doi = '10.3390/ma17184467'
    apply(doi, {'pH': np.nan, 'exposure_h': np.nan, 'temperature_C': np.nan, 'temperature_condition_cat': 'room_temperature', 'ocp_stabilization_min': 30.}, 'Methods / electrochemical tests', 'Room temperature and 30 min OCP reported; exact pH and one-hour prior immersion not reported')
    doi = '10.3390/ma18010069'
    apply(doi, {'pH': np.nan, 'exposure_h': np.nan, 'temperature_C': np.nan}, 'Methods / electrochemical test', 'Exact 22 C, pH=7 and one-hour prior immersion not found in inspected method')
    doi = '10.3390/ma19122685'
    apply(doi, {'P': np.nan, 'S': np.nan, 'P_upper_bound_wt_pct': .005, 'S_upper_bound_wt_pct': .008, 'pH': np.nan, 'exposure_h': np.nan, 'temperature_C': np.nan, 'temperature_condition_cat': 'room_temperature'}, 'Table 1; electrochemical methods', 'P<=0.005 and S<=0.008 are censored limits; exact pH/duration not reported and temperature is qualitative')
    doi = '10.3390/ma12203359'
    apply(doi, {'pH': np.nan, 'exposure_h': np.nan}, 'Section 2.2.1', '25+-1 C and scan rate reported; exact pH and prior one-hour exposure not found')
    doi = '10.3390/ma14123254'
    apply(doi, {'pH': np.nan, 'exposure_h': np.nan, 'scan_rate_mV_s': np.nan}, 'Methods / potentiodynamic tests', 'Numeric pH, scan rate and one-hour exposure not found in inspected method')
    for suffix, process in [('normalizing', 'normalized'), ('quenching', 'quenched'), ('quenching_high_temperature_tempering', 'quenched_tempered')]:
        apply(doi, {'sample_process_cat': process}, 'Table 4', 'Distinct controlled heat-treatment conditions', d.source_sample_id.eq(doi + '_' + suffix))
    doi = '10.3390/ma14040929'
    apply(doi, {'pH': np.nan, 'temperature_C': np.nan, 'exposure_h': np.nan, 'temperature_condition_cat': 'room_temperature', 'ocp_stabilization_min': 30.}, 'Methods / electrochemical tests', '30 min OCP and room temperature reported; exact pH=0, 25 C and one-hour exposure are not reported')
    doi = '10.3390/ma16020876'
    apply(doi, {'pH': np.nan, 'temperature_C': np.nan, 'exposure_h': np.nan, 'temperature_condition_cat': 'room_temperature', 'electrolyte_condition_cat': 'NaCl_3.5wtpct'}, 'Methods / electrochemical tests', 'Room temperature and 3.5 wt% NaCl reported; exact pH and immersion duration not reported')
    for sample, region in [('Base metal', 'base_metal'), ('CGHAZ', 'coarse_grained_HAZ')]:
        apply(doi, {'sample_region_cat': region}, 'Table 4', 'Measured region differs despite shared bulk composition', d.source_sample_id.eq(sample))
    doi = '10.1016/j.isci.2025.113319'
    apply(doi, {'pH': np.nan, 'ocp_stabilization_min': 1000. / 60., 'sample_process_cat': 'TIG_welded', 'sample_region_cat': 'HAZ'}, 'STAR Methods / electrochemical measurements', '1000 s OCP and HAZ measurement reported; exact pH=8.1 not found')

    # Never alter a corrosion target on the basis of plausibility or model residuals.
    pd.testing.assert_series_equal(d.icorr_A_cm2, original.icorr_A_cm2)
    d.to_csv(DATA / 'curated_corrosion.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(changes).to_csv(ROOT / 'changes.csv', index=False, encoding='utf-8-sig')
    rows = []
    for doi, group in original.groupby('source_paper_id', sort=False):
        review = REVIEWS.get(doi)
        rows.append(dict(source_paper_id=doi, n_records=len(group), review_status=review[0] if review else 'full_text_not_reviewed', locator=review[1] if review else '', source_unit=review[2] if review else '', note=review[3] if review else 'No corrections applied on the basis of uninspected full text.', source_url='https://doi.org/' + doi if doi.startswith('10.') else str(group.phase_source_url.iloc[0])))
    pd.DataFrame(rows).to_csv(ROOT / 'paper_review.csv', index=False, encoding='utf-8-sig')
    manifest = dict(source=str(source), sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(), records=len(d), reviewed_papers=len(REVIEWS), reviewed_records=int(d.source_paper_id.isin(REVIEWS).sum()), changed_cells=len(changes), changed_records=len(set(c['record_id'] for c in changes)), targets_changed=0, review_date='2026-10-22')
    (ROOT / 'curation_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))
    return d


if __name__ == '__main__':
    build()
