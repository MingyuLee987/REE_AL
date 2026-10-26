"""Direct source audit and deterministic recovery after API credits were exhausted.

Only the explicitly enumerated, inspected primary tables below are accepted.
This is not an API review and is labelled separately in every exported record.
"""
import copy,json,re
from pathlib import Path
import numpy as np
import pandas as pd
from collect_grain_size import ROOT,key,norm,save_json,request
from expand_heat_treatment_data import OUT
from collect_heat_round4_ce import TableRows

METHOD='direct_primary_table_and_protocol_review'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def attr(field,value,quote,location,unit='',text=''):
 return dict(field=field,value=value,text=text,unit=unit,basis='reported',lower=None,upper=None,quote=quote,location=location,quote_verified=True)
def finish(doi,records,inp,reason):
 path=OUT/'extractions'/f'{key(doi)}.json'
 if path.exists():save_json(ROOT/'outputs/heat_expansion_round4_manual_20261023'/f'{key(doi)}_before.json',read(path))
 cmap={c['record_id']:c for c in inp['candidates']};reviews=[]
 for r in records:
  assert r['candidate_id'] in cmap
  assert np.isclose(r['target_value_A_cm2'],cmap[r['candidate_id']]['icorr_A_cm2'],rtol=1e-12,atol=0)
  assert any(norm(r['target_quote']) in norm(b['text']) for b in inp['source_blocks'])
  r.update(candidate_exists=True,target_quote_verified=True)
  for a in r['attributes']:
   assert any(norm(a['quote']) in norm(b['text']) for b in inp['source_blocks']),(doi,a)
   a['quote_verified']=True
  reviews.append(dict(candidate_id=r['candidate_id'],decision='accept',reason=reason,invalid_attribute_indices=[],thermal_history_incomplete=True,protocol_ambiguity=False))
 save_json(path,dict(doi=doi,title=inp['title'],records=records,review_method=METHOD,retry_partial_failure=False,exclusion_note='Recovered/verified directly from primary sources; API credit balance exhausted.'))
 save_json(OUT/'inputs'/path.name,inp)
 save_json(OUT/'reviews'/path.name,dict(doi=doi,reviews=reviews,local_checks=[],review_method=METHOD,reviewer='Codex direct primary-source audit',audit_note=reason))
 print(doi,len(records))

def nanofluid():
 doi='10.1155/ijco/5531986';path=OUT/'inputs'/f'{key(doi)}.json';inp=read(path);ex=read(OUT/'extractions'/path.name)
 base=ex['records'][0];common=[copy.deepcopy(a) for a in base['attributes'] if a['field'] in ['C','Si','Mn','P','S','scan_rate_mV_s','ocp_stabilization_min']]
 bb={b['location']:b['text'] for b in inp['source_blocks']}
 # Values read from PDF pages 7 and 8, Icorr column headed A/cm2.
 values={
  (False,'Tap water'):[8.0799e-6,7.6291e-6,4.4398e-6,6.1892e-6],
  (False,'Nano-CuO'):[5.367e-6,3.54e-6,4.815e-6,8.298e-6],
  (False,'Nano-Al2O3'):[1.543e-5,6.5239e-6,7.658e-6,9.2515e-6],
  (False,'Nano-Al2O3 + T'):[6.6492e-6,1.2605e-5,7.253e-6,8.2179e-6],
  (False,'Nano-CuO + T'):[2.936e-6,7.8241e-6,8.292e-6,3.257e-6],
  (True,'Tap water'):[5.846e-5,.000119,.000307,.000631],
  (True,'Nano-CuO'):[5.216e-5,9.06e-5,.000248,.0009355],
  (True,'Nano-Al2O3'):[5.462e-5,.000159,.000144,.000476],
  (True,'Nano-Al2O3 + T'):[5.613e-5,.0001516,.0003767,.000604],
  (True,'Nano-CuO + T'):[5.67e-5,.000159,.000171,.000486]}
 records=[]
 for c in inp['candidates']:
  label=c['row_label'];sample=label.split(';')[0];co2='CO2' in label;temp=int(re.findall(r'(25|35|45|55)',label)[-1]);value=values[co2,sample][[25,35,45,55].index(temp)]
  assert np.isclose(value,c['icorr_A_cm2'],rtol=1e-12,atol=0)
  tempered='+ T' in sample;thermal=next(b for b in inp['source_blocks'] if b['location'].startswith('page3_') and b['text'].startswith(sample+' ') and ('900' in b['text']))
  caption='page8_block7' if co2 else 'page7_block5'
  attrs=copy.deepcopy(common)+[
   attr('heat_treatment_temperature_C',350 if tempered else 900,thermal['text'],thermal['location'],'°C'),
   attr('heat_treatment_time_min',30 if tempered else 60,thermal['text'],thermal['location'],'min'),
   attr('temperature_C',temp,c['row_cells'],c['table_id'],'°C'),
   attr('electrolyte_condition_cat',None,bb[caption],caption,text='CO2-saturated 3.5% NaCl' if co2 else '3.5% NaCl without CO2 saturation'),
   attr('pH',3.9 if co2 else 6.5,'The pH value after bubbling the CO2 was 3.9, whereas it was 6.5 before the bubbling.','page5_block10')]
  records.append(dict(candidate_id=c['record_id'],sample_label=label,steel_family='carbon_low_alloy_steel',target_matches_primary_table=True,target_value_A_cm2=value,target_quote=c['row_cells'],target_location=c['table_id']+'; PDF page '+('8' if co2 else '7')+'; Icorr A/cm2',heat_stage='tempering' if tempered else 'austenitizing',heat_history_note='Table 2: '+thermal['text']+'. Cooling medium: '+sample+'. Different quenching media are recorded in metadata but are not model predictors. Reported Table 6 Icorr is retained even where the adjacent corrosion-rate column is inconsistent; no rate-derived correction.',attributes=attrs))
 finish(doi,records,inp,'Directly inspected rendered PDF pages 7–8, Tables 5–6: Icorr is A/cm2, not Ecorr or corrosion rate. Matched five heat-treated conditions × four test temperatures × two electrolytes. Untreated controls excluded. Table 2 establishes final hold; Table 1 bulk composition; Section 2.8 pH/scan/OCP. No independent API-review claim.')

def ce():
 doi='10.1007/s11663-025-03817-z';folder=ROOT/'outputs/heat_expansion_round4_ce_20261023';paper=read(folder/'sources'/f'{key(doi)}.json')
 url='https://link.springer.com/article/'+doi+'/tables/1';s,raw=request(url,timeout=40);assert s==200
 path=folder/'table1.html';path.write_bytes(raw);parser=TableRows();parser.feed(re.search(r'<table[\s\S]*?</table>',raw.decode()).group(0))
 table=[' | '.join(t for _,t in row) for row in parser.rows];block=dict(location='publisher_Table_I',section='Table I',text='Table I. Bulk chemical composition, wt.%.\n'+'\n'.join(table),source_path=str(path),source_url=url);paper['blocks'].append(block)
 headers=[t for _,t in parser.rows[0]];comp={}
 for row in parser.rows[1:]:
  vals=[t for _,t in row]
  if vals[0] not in ['S0','S2']:continue
  comp[vals[0]]={h.replace('.',''):float(v) for h,v in zip(headers[1:],vals[1:]) if re.fullmatch(r'[0-9.]+',v)}
 assert comp['S2']['Ce']==.0095 and comp['S0']['Ce']==0
 candidates=pd.read_csv(OUT/'round4_ce_candidates.csv').to_dict('records');old=read(folder/'previous_extractions.json')['records'][0]
 protocol=[copy.deepcopy(a) for a in old['attributes'] if a['field'] in ['temperature_C','electrolyte_condition_cat']]
 inp=dict(doi=doi,title=paper['title'],candidates=candidates,source_blocks=paper['blocks']);records=[]
 for c in candidates:
  cells=[x.strip() for x in c['row_cells'].split('|')];temp=int(cells[0]);sample=cells[1];hold=int(cells[2]);assert np.isclose(float(cells[4])*1e-7,c['icorr_A_cm2'],rtol=1e-12,atol=0)
  q=next(t for t in table if t.startswith(sample+' |'))
  attrs=[attr(h,v,q,'publisher_Table_I','wt.%') for h,v in comp[sample].items() if h!='Fe']
  attrs += [attr('RE_ppm',comp[sample]['Ce']*10000,q,'publisher_Table_I','ppm',text='Ce wt.% × 10000'),attr('RE_element_cat',None,q,'publisher_Table_I',text='Ce'),attr('heat_treatment_temperature_C',temp,c['row_cells'],'publisher_table_IV_rowspan_expanded','°C'),attr('heat_treatment_time_min',hold,c['row_cells'],'publisher_table_IV_rowspan_expanded','min')]+copy.deepcopy(protocol)
  records.append(dict(candidate_id=c['record_id'],sample_label=c['row_label'],steel_family='stainless_steel',target_matches_primary_table=True,target_value_A_cm2=c['icorr_A_cm2'],target_quote=c['row_cells'],target_location='Publisher Table IV, HTML rowspan-expanded row; Icorr ×10^-7 A/cm2',heat_stage='solution heat treatment',heat_history_note='Publisher Table IV explicitly assigns sample S0/S2 to each temperature group using HTML rowspan. Positive-duration solution treatments followed by water quenching. S2 measured Ce = 0.0095 wt.% = 95 ppm; zero-duration repeated controls omitted.',attributes=attrs))
 finish(doi,records,inp,'Direct publisher Tables I and IV: HTML rowspan establishes S0/S2 sample mapping; temperature and time belong to the same solution-treatment row. The Icorr multiplier is 10^-7 A/cm2. S2 bulk Ce 0.0095 wt.% converted to 95 ppm. No curve digitization, no API-review claim.')

def existing_verified():
 for doi,expected in [('10.3390/ma14133759',[1.54e-7,9.82e-8,1.02e-8,4.41e-8,4.82e-8,1.21e-7,1.74e-6,2.32e-6,2.49e-6,5.17e-8,1.13e-7,1.88e-7,2.52e-7,4.61e-7,1.27e-6,1.70e-7]),('10.3934/matersci.2023004',[40.02e-6,24.43e-6,18.65e-6,9.443e-6,5.498e-6,3.770e-6])]:
  path=OUT/'extractions'/f'{key(doi)}.json';ex=read(path);inp=read(OUT/'inputs'/path.name)
  assert len(ex['records'])==len(expected) and np.allclose([r['target_value_A_cm2'] for r in ex['records']],expected,rtol=1e-12,atol=0)
  for r in ex['records']:
   r['attributes']=[a for a in r['attributes'] if a['quote_verified']]
  reason='Direct source audit: '+('Tables 3–6 explicitly give Icorr in A/cm2; Table 1 bulk mass composition; protocol p17 specifies 1050 C/30 min, SZT 17 h, and two tempering cycles of 2 h each. Record time is the final individual hold, not the summed cycle duration. Repeated references in Tables 4–6 deduplicated.' if 'ma141' in doi else 'Table 4 explicitly gives Tafel Icorr in microA/cm2; converted by 1e-6. Six sample rows C10/C60/C360 × FeNiCrMo-3/4 checked. Table 1 bulk composition and final 200 C/1 h temper confirmed; earlier cryogenic duration retained only in metadata.')
  finish(doi,ex['records'],inp,reason)

def la_conversion():
 doi='10.1038/s41529-025-00682-8';path=OUT/'extractions'/f'{key(doi)}.json';ex=read(path)
 for r in ex['records']:
  r['attributes']=[a for a in r['attributes'] if a['field'] not in ['RE_ppm','RE_element_cat']]
  la=next(a for a in r['attributes'] if a['field']=='La');assert la['unit']=='wt.%' and la['value'] in [0,.49]
  for field,value,text,unit in [('RE_ppm',la['value']*10000,'Measured bulk La wt.% multiplied by 10000','ppm'),('RE_element_cat',None,'La','')]:
   a=copy.deepcopy(la);a.update(field=field,value=value,text=text,unit=unit,manual_correction_note='Direct deterministic conversion of reviewed bulk La assay, not the nominal 0.5 wt.% label.');r['attributes'].append(a)
 ex['review_method']='independent_API_review_with_direct_La_unit_conversion';save_json(path,ex)
 rp=OUT/'reviews'/path.name;review=read(rp);review['review_method']=ex['review_method'];review['direct_conversion_note']='La 0.49 wt.% = 4900 ppm; reported La 0.00 wt.% = 0 ppm. Converted directly after API audit.';save_json(rp,review)

if __name__=='__main__':nanofluid();ce();existing_verified();la_conversion()
