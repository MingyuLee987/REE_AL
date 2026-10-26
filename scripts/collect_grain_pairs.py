"""Reviewed pair construction from four additional papers. No automatic training merge."""
import json
import re
import sys
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from collect_grain_size import ROOT, OUT, DATA, ARCHIVE, key, norm, save_json

PAPERS={
 '10.1186/s40712-025-00240-9':{
  'material':'X65 pipeline steel','environment':'5 wt% NaCl + 0.5 wt% CH3COOH + 1 wt% H2SO4 + 3 g/L NH4SCN; pH 1.3',
  'samples':{'8 µm':'875s1 / 8 µm sample','11.5 µm':'1000s1 / 11.5 µm sample','13 µm':'1075s1 / 13 µm sample','19 µm':'1150s1 / 19 µm sample'},
  'note':'Table 2 annealed grain sizes matched to Table 3 measured Tafel currents. As-received and independently annealed passivation-validation samples excluded because no matching measured current table was recovered.'},
 '10.3390/ma12091455':{
  'material':'35CrMoV steel','environment':'3.5 wt% NaCl; 2400 s OCP stabilization; Tafel scan rate 0.5 mV/s',
  'samples':{'expanded_df459359f9c426e0':'35CrMoV steel, 850 °C deformation, 0.01 s−1','expanded_c9eb08ee7301769b':'35CrMoV steel, 1050 °C deformation, 0.01 s−1','expanded_754cd3792007527e':'35CrMoV steel, 850 °C deformation, 10 s−1'},
  'note':'Deformation temperature AND strain rate both matched. Unreported intermediate grain sizes were not interpolated.'},
 '10.3390/ma15248780':{
  'material':'Super austenitic stainless steel','environment':'Aerated 3.5% (0.6 M) NaCl; ambient conditions; 1 h OCP; LPR 0.125 mV/s or CPDP 0.5 mV/s',
  'samples':{'T30':'T30','T60':'T60','T120':'T120 / AT12','AT11':'AT11','AT13':'AT13'},
  'note':'LPR and CPDP-Tafel currents remain separate methods, not independent samples. AT12 repeats T120 material/heat treatment and is excluded from the pair set to avoid double counting.'},
 '10.1038/s41598-026-65428-1':{
  'material':'HFIHS-sintered 316L stainless steel','environment':'3.5 wt% NaCl; polarization after 72 h exposure',
  'samples':{'1000':'316L stainless steel, HFIHS at 1000 °C','1050':'316L stainless steel, HFIHS at 1050 °C','1100':'316L stainless steel, HFIHS at 1100 °C','1150':'316L stainless steel, HFIHS at 1150 °C'},
  'note':'Mean metallographic grain size matched by sintering temperature to Table 4 Tafel data. Porosity/densification also vary, so this is not an isolated grain-size intervention.'}
}

def main():
 sys.stdout.reconfigure(encoding='utf-8')
 candidates=pd.read_csv(ROOT/'data/literature/icorr_candidates.csv',float_precision='round_trip')
 inventory=pd.read_csv(ROOT/'data/literature/fulltext_inventory.csv')
 pairs=[];evidence=[]
 for doi,rule in PAPERS.items():
  extracted=json.loads((OUT/'llm'/f'{key(doi)}.json').read_text(encoding='utf-8'))['records']
  grains={r['sample_label']:r for r in extracted}
  source=ARCHIVE/inventory.loc[inventory.doi.eq(doi),'source_xml'].iloc[0]
  root=ET.parse(source).getroot()
  tables={int(re.search(r'(\d+)\s*$',norm(''.join(t.find('label').itertext())))[1]):t for t in root.iter('table-wrap') if t.find('label') is not None}
  p=json.loads((OUT/'papers'/f'{key(doi)}.json').read_text(encoding='utf-8'))
  methods=[b for b in p['blocks'] if re.search(r'NaCl|electrolyte|electrochemical|solution',b['text'],re.I) and b.get('section','').lower().find('intro')<0]
  for _,c in candidates[candidates.source_paper_id.eq(doi)].iterrows():
   grain_label=rule['samples'].get(c.record_id,rule['samples'].get(str(c.row_label)))
   if not grain_label:continue
   g=grains[grain_label]
   assert g['quote_verified'] and g['is_current_experiment'] and g['grain_size_value_reported']>0
   assert g['unit'] in ('μm','µm','um')
   table_number=int(re.search(r'_t(\d+)$',c.table_id)[1]);table=tables[table_number]
   reported=str(c.icorr_reported);raw_table=norm(''.join(table.itertext()))
   # Independent source-table check of the reported numeric target and original unit header.
   assert reported in raw_table
   assert re.search(r'[iIjJ].?corr',raw_table,re.I)
   assert np.isclose(float(reported)*float(c.unit_factor_to_A_cm2),float(c.icorr_A_cm2),rtol=1e-12,atol=0)
   assert float(c.unit_factor_to_A_cm2)==(1.0 if doi=='10.1038/s41598-026-65428-1' else 1e-6)
   source_grain_blocks=p['blocks'];assert any(norm(g['evidence_quote']) in b['text'] for b in source_grain_blocks)
   sample_id=doi+'|'+grain_label
   method='LPR' if 'LPR' in c.caption else 'Tafel_polarization'
   row={
    'record_id':'grain_pair_'+c.record_id,'source_paper_id':doi,'source_url':'https://doi.org/'+doi,
    'sample_id':sample_id,'sample_label':grain_label,'material':rule['material'],
    'grain_size_um':g['grain_size_value_reported'],'grain_definition':g['grain_definition'],
    'grain_method':g['measurement_method'],'grain_statistic':g['statistic'],
    'grain_evidence_quote':g['evidence_quote'],'grain_evidence_location':g['evidence_location'],
    'icorr_A_cm2':c.icorr_A_cm2,'icorr_reported':reported,'icorr_original_header':c.target_header,
    'icorr_unit_factor_to_A_cm2':c.unit_factor_to_A_cm2,'icorr_method':method,
    'icorr_table':f'Table {table_number}','icorr_source_record_id':c.record_id,
    'icorr_source_row':c.row_cells,'environment':rule['environment'],'RE_status':'not_reported_not_assigned_zero',
    'review_status':'source_table_and_sample_checked','admission_status':'separate_pair_dataset_not_merged_into_training',
    'review_note':rule['note'],'original_xml':str(source.resolve())
   }
   pairs.append(row)
  evidence.append({'doi':doi,'review_note':rule['note'],'tables':{str(n):norm(''.join(t.itertext())) for n,t in tables.items()},'environment_and_methods_blocks':methods})
 d=pd.DataFrame(pairs)
 assert d.record_id.is_unique and (d.icorr_A_cm2>0).all()
 assert len(d)==21 and d.sample_id.nunique()==16 and d.source_paper_id.nunique()==4
 d.to_csv(DATA/'additional_grain_icorr_pairs.csv',index=False,encoding='utf-8-sig')
 save_json(OUT/'additional_pair_source_evidence.json',evidence)
 summary={'paired_measurements':len(d),'distinct_material_conditions':d.sample_id.nunique(),'papers':d.source_paper_id.nunique(),'method_counts':d.icorr_method.value_counts().to_dict(),'duplicates_policy':'LPR/Tafel separated; AT12 repeat of T120 excluded','not_merged_into_training':True,'grain_values_not_imputed':True}
 save_json(DATA/'additional_pairs_summary.json',summary)
 queue=pd.read_csv(DATA/'external_paper_queue.csv')
 queue.loc[queue.source_paper_id.isin(PAPERS),'admission_status']='grain_icorr_pairs_checked_in_separate_dataset_composition_not_admitted'
 queue.to_csv(DATA/'external_paper_queue.csv',index=False,encoding='utf-8-sig')
 print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
