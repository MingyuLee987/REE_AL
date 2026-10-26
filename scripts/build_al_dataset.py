"""Curate a grain-aware labelled corrosion corpus using the supplied PDF's rules.

Review-time filled CSV is separate from source-only CSV. Fold imputation never
uses a held-out paper as a donor, and never receives corrosion targets.
"""
import hashlib
import json
import re
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from prepare_al_sources import OUT, seeds, ELEMENTS, NUMERIC, TEXT
from collect_grain_size import ROOT, key, save_json, norm

DEST=ROOT/'data/al_curated_20261023'
CORE='C Si Mn P S Cr Ni Mo Cu N'.split()
SOURCE_URL='https://www.electrochemsci.org/papers/vol10/100806187.pdf'

def impute_composition(query,reference):
 """Independent 3–5-paper elemental medians; frozen observed query; no target."""
 forbidden={'icorr_A_cm2','log10_icorr','pred_log10_icorr'}
 assert not (forbidden & set(query.columns)) and not(forbidden & set(reference.columns))
 result=query.copy();logs=[]
 scale=(reference[CORE].quantile(.75)-reference[CORE].quantile(.25)).replace(0,np.nan).fillna(1)
 for idx,row in query.iterrows():
  pool=reference.loc[reference.steel_family.eq(row.steel_family)&reference.source_paper_id.ne(row.source_paper_id)].copy()
  if pd.notna(row.Cr):pool=pool.loc[pool.Cr.isna()|pool.Cr.ge(10).eq(row.Cr>=10)]
  # Match the existing PDF-era rule: high-Ni queries require high-Ni donors.
  # For lower-Ni queries, continuous composition distance still penalizes Ni mismatch.
  if pd.notna(row.Ni) and row.Ni>=6:pool=pool.loc[pool.Ni.ge(6)]
  overlap=pool[CORE].notna()&row[CORE].notna();count=overlap.sum(axis=1)
  distances=((pool[CORE]-row[CORE])/scale).abs().where(overlap).mean(axis=1)
  pool=pool.assign(distance=distances).loc[count.ge(2)].sort_values(['distance','source_paper_id','record_id'],kind='stable')
  for element in CORE:
   if pd.notna(row[element]):continue
   donors=pool[pool[element].notna()].drop_duplicates('source_paper_id').head(5)
   if len(donors)<3:continue
   value=float(donors[element].median())
   upper=row.get(element+'_upper_bound',np.nan)
   if pd.notna(upper):value=min(value,float(upper)/2)
   result.loc[idx,element]=value
   mismatch=bool(pd.notna(row.Ni) and row.Ni<6 and donors.Ni.ge(6).any())
   logs.append({'record_id':row.record_id,'source_paper_id':row.source_paper_id,'element':element,'value':value,'unit':'wt.%','method':'cross_paper_similar_alloy_median','donor_papers':json.dumps(donors.source_paper_id.tolist()),'donor_record_ids':json.dumps(donors.record_id.tolist()),'reference_low':float(donors[element].min()),'reference_high':float(donors[element].max()),'n_donor_papers':len(donors),'donor_distances':json.dumps(donors.distance.tolist()),'low_Ni_query_has_high_Ni_donor':mismatch,'confidence':'estimate_not_measurement'})
 return result,logs

def readiness(d):
 comp=d[CORE].notna().all(axis=1)
 grain=d.grain_size_um.notna()|d.grain_size_ASTM_number.notna()
 temperature=d.temperature_C.notna()|d.temperature_condition_cat.fillna('').str.contains('room|ambient',case=False,regex=True)
 text=d[['electrolyte_condition_cat','sample_process_cat','matrix_phase_group']].fillna('').ne('').all(axis=1)
 core=comp&grain&temperature&text&d.scan_rate_mV_s.notna()&d.icorr_A_cm2.gt(0)&d.target_verified
 detailed=core&d.pH.notna()&d.exposure_h.notna()&d.ocp_stabilization_min.notna()
 return comp,core,detailed

def main():
 sys.stdout.reconfigure(encoding='utf-8');DEST.mkdir(parents=True,exist_ok=True)
 seed=seeds();baseline=pd.read_csv(ROOT/'data/provenance/curated_original.csv',float_precision='round_trip').set_index('record_id')
 legacy=pd.read_csv(ROOT/'data/training.csv',float_precision='round_trip')
 estimate_log=pd.read_csv(ROOT/'data/provenance/estimation_log.csv')
 d=pd.DataFrame({'record_id':seed.record_id,'source_paper_id':seed.source_paper_id,'source_sample_id':seed.source_sample_id,'icorr_A_cm2':seed.icorr_A_cm2,'seed_origin':seed.seed_origin})
 for c in set(NUMERIC+['Sb']):d[c]=np.nan
 for c in TEXT+['steel_family']:d[c]=''
 d['source_url']=d.source_paper_id.map(lambda s:SOURCE_URL if s.startswith('source:') else 'https://doi.org/'+s)
 d['grain_size_definition']=seed['grain_size_definition'].combine_first(seed.get('grain_definition',pd.Series(index=seed.index,dtype=object)))
 d['icorr_method']='Tafel_polarization'
 d['target_verified']=True;d['target_review_status']='source_table_and_units_checked';d['target_source_location']=''
 candidate_targets=pd.read_csv(ROOT/'data/literature/icorr_candidates.csv',float_precision='round_trip').set_index('record_id')
 for idx,row in seed.iterrows():
  if str(row.get('target_review_status',''))=='figure_values_not_redigitized':
   d.loc[idx,'target_verified']=False;d.loc[idx,'target_review_status']='legacy_figure_value_not_redigitized';d.loc[idx,'target_source_location']='Legacy figure extraction; requires independent redigitization'
  elif str(row.record_id).startswith('Vera'):
   d.loc[idx,'target_source_location']='PDF page 7, Table 2, Ic (A cm^-2) column'
  else:
   cid=str(row.get('icorr_source_record_id',''))
   if cid not in candidate_targets.index:cid=str(row.record_id).removeprefix('grain_pair_').removeprefix('AL_')
   if cid in candidate_targets.index:
    c=candidate_targets.loc[cid]
    assert np.isclose(float(c.icorr_A_cm2),float(row.icorr_A_cm2),rtol=1e-12,atol=0)
    d.loc[idx,'target_source_location']=str(c.caption)+'; sample '+str(c.row_label)+'; original header '+str(c.target_header)
   else:
    d.loc[idx,'target_source_location']={'10.3390/met13010066':'PDF Table 5, Icorr (mA/cm2); factor 1e-3','10.1002/srin.202400576':'PDF page 5, Table 4, Icorr (A cm^-2)','10.3390/ma19122685':'Primary XML Table 2, Icorr (A cm^-2)','10.1007/s10853-025-11514-0':'Publisher Table 4, Tafel current density'}.get(row.source_paper_id,'Previously source-checked table')
 provenance=[];conflicts=[];discarded=[]
 for i,r in d.iterrows():
  rid=r.record_id
  if rid in baseline.index:
   orig=baseline.loc[rid]
   for c in CORE:
    if pd.notna(orig[c]):
     d.loc[i,c]=orig[c];provenance.append({'record_id':rid,'source_paper_id':r.source_paper_id,'field':c,'value':orig[c],'method':'legacy_original_entry','evidence':'data/provenance/curated_original.csv; original entry, not statistical estimate'})
   d.loc[i,'steel_family']=orig.steel_family
  else:d.loc[i,'steel_family']='stainless_steel' if 'stainless' in str(seed.loc[i].get('material','')).lower() else 'carbon_low_alloy_steel'
  # These grain values were checked in the previous source review; never interpolate.
  for c in ['grain_size_um','grain_size_ASTM_number']:
   if c in seed and pd.notna(seed.loc[i,c]):
    d.loc[i,c]=seed.loc[i,c]
    provenance.append({'record_id':rid,'source_paper_id':r.source_paper_id,'field':c,'value':seed.loc[i,c],'method':'previous_source_checked_grain' if not rid.startswith('Vera') else 'source_pdf_ASTM_number','evidence':str(seed.loc[i].get('grain_size_source_location',seed.loc[i].get('grain_evidence_location','PDF page 4, Figure 1 description')))})
 # Normalize source families consistently with the existing reference corpus.
 d.steel_family=d.steel_family.replace({'stainless_steel':'스테인리스강','carbon_low_alloy_steel':'일반·합금강'})
 valid_ids=set(d.record_id)
 for p in (OUT/'extractions').glob('*.json'):
  extracted=json.loads(p.read_text(encoding='utf-8'))
  for r in extracted['records']:
   label=r['sample_label']
   if re.search(r'wet.?dry|cyclic.?immersion|flow.system',label,re.I):
    discarded.append({'doi':extracted['doi'],'sample_label':label,'reason':'Separate gravimetric/cyclic protocol must not be assigned to polarization targets'});continue
   for a in r['attributes']:
    if not a['quote_verified']:
     discarded.append({'doi':extracted['doi'],'sample_label':label,'field':a['field'],'reason':'Exact source quote not verified'});continue
    if a['field']=='exposure_h' and re.search('separate|corrosion.rate immersion',a['text']+' '+a['note'],re.I):continue
    if a['field']=='scan_rate_mV_s' and re.search(r'\bLPR\b|linear polarization resistance',a['text'],re.I):
     discarded.append({'doi':extracted['doi'],'field':a['field'],'reason':'LPR scan rate is not assigned to a Tafel target'});continue
    if a['field']=='exposure_h' and a['location'].endswith('f012'):
     discarded.append({'doi':extracted['doi'],'field':a['field'],'reason':'Post-corrosion SEM observation duration does not uniquely establish pre-Tafel exposure'});continue
    if a['field']=='ocp_stabilization_min' and re.search('criterion|observation period',a['text']+' '+a['note'],re.I):
     discarded.append({'doi':extracted['doi'],'field':a['field'],'reason':'Stability criterion is not explicit OCP stabilization duration'});continue
    field=a['field']
    for rid in r['record_ids']:
     assert rid in valid_ids
     idx=d.index[d.record_id.eq(rid)][0];assert d.loc[idx,'source_paper_id']==extracted['doi']
     if field in ELEMENTS and a['value'] is not None and a['unit'].lower().replace(' ','') not in ['wt.%','wt%','wt.%percent','mass%','weight%','%']:
      discarded.append({'doi':extracted['doi'],'field':field,'reason':'Composition unit not established as mass percent'});continue
     if a['basis'] in ['upper_bound','range']:
      if pd.notna(d.loc[idx,field]):
       conflicts.append({'record_id':rid,'field':field,'old':d.loc[idx,field],'source_recovered':'bounded_only; exact value unknown','resolution':'restore_missing_and_preserve_original_limit','source':a['location']})
      d.loc[idx,field]=np.nan
      for side in ['lower','upper']:
       if a[side] is not None:
        c=field+'_'+side+'_bound'
        if c not in d:d[c]=np.nan
        d.loc[idx,c]=a[side]
      provenance.append({'record_id':rid,'source_paper_id':extracted['doi'],'field':field,'value':None,'lower':a['lower'],'upper':a['upper'],'method':a['basis'],'evidence':a['evidence_quote'],'location':a['location']})
      continue
     value=a['value'] if field in NUMERIC else a['text']
     if value is None or value=='':continue
     old=d.loc[idx,field]
     if pd.notna(old) and old!='' and str(old)!=str(value):conflicts.append({'record_id':rid,'field':field,'old':old,'source_recovered':value,'resolution':'fresh_primary_source_selected','source':a['location']})
     d.loc[idx,field]=value
     provenance.append({'record_id':rid,'source_paper_id':extracted['doi'],'field':field,'value':value,'method':a['basis'],'evidence':a['evidence_quote'],'location':a['location'],'note':a['note']})
 # Direct phase evidence, not a phase-fraction estimate: gamma/σ/M23C6 in source Table 2.
 phase_mask=d.source_paper_id.eq('10.3390/ma15248780')
 d.loc[phase_mask,'matrix_phase_group']='gamma austenite matrix; sigma and M23C6 reported in SEM/EDS'
 d.loc[phase_mask,'exposure_h']=1.0
 for rid in d.loc[phase_mask,'record_id']:
  provenance.append({'record_id':rid,'source_paper_id':'10.3390/ma15248780','field':'matrix_phase_group','value':'gamma austenite matrix; sigma and M23C6','method':'reported_phase_table_reviewed','evidence':'Primary XML Table 2, gamma/sigma/M23C6 phase rows; no phase fractions inferred'})
  provenance.append({'record_id':rid,'source_paper_id':'10.3390/ma15248780','field':'exposure_h','value':1.0,'method':'reported_pretest_immersion_reviewed','evidence':'Primary XML p7: an immersion duration of 1 h for the system to attain steady-state condition during which OCP was measured before other electrochemical tests; this explicit pre-test immersion is separate from an inferred post-corrosion SEM duration'})
 # Major Sb is explicitly in the 0.4Sb alloy table; do not silently drop this alloying element.
 sbdoi='10.3390/ma19122685'
 for name,value in [('0RE',.42),('0.03LaCe',.40),('0.3LaCe',.40)]:
  mask=d.source_paper_id.eq(sbdoi)&d.source_sample_id.eq(name);d.loc[mask,'Sb']=value
  for rid in d.loc[mask,'record_id']:provenance.append({'record_id':rid,'source_paper_id':sbdoi,'field':'Sb','value':value,'method':'reported_table_checked','evidence':'Primary XML Table 1, Sb column, sample '+name})
 # The supplied PDF prioritizes documented grade proxies over cross-paper statistics.
 # Manufacturer 17-4PH / S17400 Mo maximum is 0.60 wt.%; this is NOT the tested heat's assay.
 mask=d.source_paper_id.eq('10.3390/ma18081823')&d.Mo.isna()
 d.loc[mask,'Mo']=0.30
 d['Mo_grade_upper_bound']=np.nan;d.loc[mask,'Mo_grade_upper_bound']=0.60
 for rid in d.loc[mask,'record_id']:
  provenance.append({'record_id':rid,'source_paper_id':'10.3390/ma18081823','field':'Mo','value':0.30,'method':'manufacturer_grade_limit_midpoint_proxy','evidence':'https://www.bohler-edelstahl.com/en/products/n700-2/ ; N700 / S17400 / 17-4PH, Mo max 0.60 wt.%; use U/2=0.30 as project assumption, not measured sample chemistry','confidence':'grade_proxy_not_sample_measurement'})
 # Restore only source/grade proxies explicitly documented in the PDF-era provenance.
 static_methods={'source_table_parent_alloy_proxy','source_table_assayed_parent_alloy','same_paper_base_alloy_proxy','manufacturer_typical_grade_proxy','grade_range_midpoint','paper_nominal_recipe','nominal_atomic_recipe_to_wt'}
 for r in estimate_log[estimate_log.method.isin(static_methods)&estimate_log.record_id.isin(valid_ids)].itertuples():
  if r.element not in d:continue
  idx=d.index[d.record_id.eq(r.record_id)][0]
  if pd.isna(d.loc[idx,r.element]):
   d.loc[idx,r.element]=r.value
   provenance.append({'record_id':r.record_id,'source_paper_id':r.source_paper_id,'field':r.element,'value':r.value,'method':'documented_'+r.method,'evidence':r.evidence,'confidence':'proxy_or_nominal_not_local_measurement'})
 # Explicit measured Ce+La values can be converted; unreported RE is never filled with zero.
 for idx,row in d.iterrows():
  if pd.isna(row.RE_ppm) and pd.notna(row.Ce) and pd.notna(row.La):
   d.loc[idx,'RE_ppm']=(row.Ce+row.La)*10000
   provenance.append({'record_id':row.record_id,'source_paper_id':row.source_paper_id,'field':'RE_ppm','value':d.loc[idx,'RE_ppm'],'method':'sum_reported_Ce_La_wt_percent_to_ppm','evidence':'1 wt.% = 10000 ppm; both components explicitly reported'})
 d['grain_metric']=np.where(d.grain_size_um.notna(),'reported_diameter_um',np.where(d.grain_size_ASTM_number.notna(),'ASTM_grain_size_number','missing'))
 d['condition_id']=d.source_paper_id+'|'+d.source_sample_id.str.replace(r'_(before|after)_immersion$|_weld_Table4$|_weld_Fig9a_0day$','',regex=True)
 # Exposure rows share original microstructure and must stay in the same source-paper group.
 d['source_group_id']=d.source_paper_id
 raw=d.copy();raw.to_csv(DEST/'al_labeled_raw.csv',index=False,encoding='utf-8-sig')
 prepared=raw.copy()
 for idx,row in raw.iterrows():
  for c in CORE:
   if pd.notna(row[c]):continue
   lo=row.get(c+'_lower_bound',np.nan);hi=row.get(c+'_upper_bound',np.nan)
   if pd.notna(hi):
    value=(float(lo)+float(hi))/2 if pd.notna(lo) else float(hi)/2
    prepared.loc[idx,c]=value
    provenance.append({'record_id':row.record_id,'source_paper_id':row.source_paper_id,'field':c,'value':value,'method':'reported_range_midpoint' if pd.notna(lo) else 'reported_upper_limit_U_over_2','evidence':'Explicit original bound retained in raw CSV; representative assumption, not measured concentration'})
 # Reference pool contains only original (pre-statistical-imputation) composition entries.
 ref=baseline.reset_index();ref=ref[ref.record_id.isin(legacy.record_id)][['record_id','source_paper_id','steel_family']+CORE]
 newref=prepared[['record_id','source_paper_id','steel_family']+CORE]
 reference=pd.concat([newref,ref],ignore_index=True).drop_duplicates('record_id',keep='first')
 reference=reference[reference[CORE].notna().sum(axis=1).ge(3)]
 reference.to_csv(DEST/'composition_reference_source_values.csv',index=False,encoding='utf-8-sig')
 query=prepared[['record_id','source_paper_id','steel_family']+CORE+[c for c in prepared if c.endswith('_upper_bound')]]
 filled,stats=impute_composition(query,reference)
 result=prepared.copy();result[CORE]=filled[CORE]
 for c in CORE:result['original_missing_'+c]=raw[c].isna().astype(int)
 result['composition_statistically_filled_count']=sum(prepared[c].isna()&result[c].notna() for c in CORE)
 result['composition_missing_count']=result[CORE].isna().sum(axis=1)
 result['composition_donor_domain_warning']=result.record_id.isin({r['record_id'] for r in stats if r['low_Ni_query_has_high_Ni_donor']})
 result['composition_uses_assumptions']=result.record_id.isin({r['record_id'] for r in provenance if any(s in r['method'] for s in ['proxy','nominal','midpoint','U_over_2'])}|{r['record_id'] for r in stats})
 composition_ok,core_ok,detail_ok=readiness(result)
 result['core_complete']=core_ok;result['detailed_protocol_complete']=detail_ok
 result['al_use']='labelled_pool_for_retrospective_AL_or_initial_fit'
 result['production_model_compatible']=False
 result['review_note']='Use raw source data and fit imputers within each training split. Review-time filled values are not independent-validation inputs.'
 result.to_csv(DEST/'al_labeled_prepared_review.csv',index=False,encoding='utf-8-sig')
 result[core_ok].to_csv(DEST/'al_core_complete.csv',index=False,encoding='utf-8-sig')
 result[detail_ok].to_csv(DEST/'al_detailed_protocol_complete.csv',index=False,encoding='utf-8-sig')
 _,raw_core_ok,_=readiness(raw)
 raw[raw_core_ok].to_csv(DEST/'al_source_only_core_complete.csv',index=False,encoding='utf-8-sig')
 ree_core=core_ok&result.RE_ppm.notna()&result.RE_element_cat.fillna('').ne('')
 result[ree_core].to_csv(DEST/'al_ree_core_complete.csv',index=False,encoding='utf-8-sig')
 result[~result.target_verified].to_csv(DEST/'quarantine_legacy_figure_targets.csv',index=False,encoding='utf-8-sig')
 pd.DataFrame(provenance).to_csv(DEST/'source_and_proxy_provenance.csv',index=False,encoding='utf-8-sig')
 pd.DataFrame(stats).to_csv(DEST/'composition_imputation_log.csv',index=False,encoding='utf-8-sig')
 pd.DataFrame(conflicts).to_csv(DEST/'source_conflicts.csv',index=False,encoding='utf-8-sig')
 pd.DataFrame(discarded).to_csv(DEST/'rejected_attributes.csv',index=False,encoding='utf-8-sig')
 fold_rows=[];fold_checks=[]
 for fold,(train_idx,test_idx) in enumerate(GroupKFold(5).split(prepared,groups=prepared.source_paper_id)):
  held=set(prepared.iloc[test_idx].source_paper_id)
  ref_train=reference[~reference.source_paper_id.isin(held)]
  foldfilled,logs=impute_composition(query,ref_train)
  for log in logs:assert not (set(json.loads(log['donor_papers']))&held)
  folddata=prepared.copy();folddata[CORE]=foldfilled[CORE]
  _,ready,_=readiness(folddata)
  for idx,row in prepared.iterrows():fold_rows.append({'record_id':row.record_id,'source_paper_id':row.source_paper_id,'fold':fold,'role':'test' if idx in set(test_idx) else 'train','core_complete_after_train_only_imputation':bool(ready.iloc[idx])})
  for log in logs:log['fold']=fold
  pd.DataFrame(logs).to_csv(DEST/f'composition_imputation_fold_{fold}.csv',index=False,encoding='utf-8-sig')
  fold_checks.append({'fold':fold,'train_rows':len(train_idx),'test_rows':len(test_idx),'train_core_complete':int(ready.iloc[train_idx].sum()),'test_core_complete':int(ready.iloc[test_idx].sum()),'held_out_papers':sorted(held),'held_out_paper_used_as_donor':False})
 pd.DataFrame(fold_rows).to_csv(DEST/'paper_group_folds.csv',index=False,encoding='utf-8-sig')
 missing=[]
 for c in CORE+['grain_size_um','grain_size_ASTM_number','temperature_C','pH','exposure_h','scan_rate_mV_s','ocp_stabilization_min','heat_treatment_temperature_C','heat_treatment_time_min','RE_ppm']:
  missing.append({'field':c,'raw_missing':int(raw[c].isna().sum()),'prepared_missing':int(result[c].isna().sum()),'raw_missing_pct':round(100*raw[c].isna().mean(),2),'prepared_missing_pct':round(100*result[c].isna().mean(),2)})
 pd.DataFrame(missing).to_csv(DEST/'missingness.csv',index=False,encoding='utf-8-sig')
 condition_fields={
  'temperature_information':result.temperature_C.notna()|result.temperature_condition_cat.fillna('').str.contains('room|ambient',case=False,regex=True),
  'grain_information_any_valid_metric':result.grain_size_um.notna()|result.grain_size_ASTM_number.notna(),
  'core_composition_complete':composition_ok,
 }
 pd.DataFrame([{'field':name,'missing_rows':int((~mask).sum()),'missing_pct':round(100*(~mask).mean(),2)} for name,mask in condition_fields.items()]).to_csv(DEST/'condition_information_missingness.csv',index=False,encoding='utf-8-sig')
 # Mask only directly recovered composition values; never use corrosion labels.
 directly_reported={(r['record_id'],r['field']) for r in provenance if r['method'] in ['reported','reported_table_checked'] and r['field'] in CORE and r.get('value') is not None}
 candidates=[(idx,c) for idx,row in raw.iterrows() for c in CORE if (row.record_id,c) in directly_reported and pd.notna(row[c])]
 rng=np.random.default_rng(42);rng.shuffle(candidates);mask_rows=[]
 for idx,c in candidates[:80]:
  observed=float(raw.loc[idx,c]);q=prepared.loc[[idx],['record_id','source_paper_id','steel_family']+CORE].copy();q.loc[idx,c]=np.nan
  source=raw.loc[idx,'source_paper_id'];r=reference[reference.source_paper_id.ne(source)]
  restored,logs=impute_composition(q,r);prediction=restored.loc[idx,c]
  mask_rows.append({'record_id':raw.loc[idx,'record_id'],'source_paper_id':source,'element':c,'observed_wt_pct':observed,'imputed_wt_pct':prediction,'absolute_error_wt_pct':abs(prediction-observed) if pd.notna(prediction) else np.nan,'n_donor_papers':next((x['n_donor_papers'] for x in logs if x['element']==c),0),'source_paper_excluded_from_reference':True})
 masked=pd.DataFrame(mask_rows);masked.to_csv(DEST/'masked_composition_validation.csv',index=False,encoding='utf-8-sig')
 if len(masked):masked.groupby('element').agg(masked_cells=('record_id','size'),restored_cells=('imputed_wt_pct','count'),mae_wt_pct=('absolute_error_wt_pct','mean')).to_csv(DEST/'masked_composition_validation_summary.csv',encoding='utf-8-sig')
 # Meaningful data checks, including target blindness and original file preservation.
 assert len(result)==45 and result.record_id.is_unique and (result.icorr_A_cm2>0).all()
 assert result[core_ok][CORE].notna().all().all()
 assert raw.icorr_A_cm2.equals(result.icorr_A_cm2)
 assert result.grain_size_um.equals(raw.grain_size_um)
 assert result.pH.equals(raw.pH) and result.temperature_C.equals(raw.temperature_C)
 for log in stats:assert log['source_paper_id'] not in json.loads(log['donor_papers']) and 3<=log['n_donor_papers']<=5
 newtarget=result.loc[result.record_id.str.startswith('Vera'),'icorr_A_cm2'].tolist();assert newtarget==[1.03e-5,2.84e-5]
 assert hashlib.sha256((ROOT/'data/training.csv').read_bytes()).hexdigest()==json.loads((ROOT/'models/manifest.json').read_text(encoding='utf-8'))['training_sha256']
 summary={'date':'2026-10-23','screened_labelled_rows':len(result),'source_papers':result.source_paper_id.nunique(),'core_complete_rows':int(core_ok.sum()),'core_complete_papers':result.loc[core_ok,'source_paper_id'].nunique(),'source_only_core_complete_rows':int(raw_core_ok.sum()),'ree_core_complete_rows':int(ree_core.sum()),'detailed_protocol_complete_rows':int(detail_ok.sum()),'composition_complete_rows':int(composition_ok.sum()),'statistically_imputed_cells':len(stats),'source_attribute_records':len(provenance),'missingness':missing,'fold_checks':fold_checks,'source_rejected_papers':[{'doi':'10.3390/met10091174','reason':'Reports grain size/composition but only gravimetric corrosion target; no measured i_corr'}],'training_target_never_imputed':True,'imputation_reference_includes_legacy_source_compositions':True,'model_retrained':False,'original_training_unchanged':True,'independent_AL_benchmark_ready':False,'limitations':['Core-complete is defined by the specified predictor schema, not all conceivable experimental details','pH/exposure/OCP unknowns are never fabricated','ASTM grain number remains separate from diameter','Nominal/proxy/statistical composition is not measured chemistry','Global prepared CSV is review-only; use train-fold imputation for independent evaluation','All rows already have literature labels; new experimental AL requires a genuinely unmeasured feasible candidate pool','Core subset contains only two source papers; not enough for a convincing multi-paper AL benchmark']}
 save_json(DEST/'summary.json',summary)
 inventory=pd.read_csv(ROOT/'data/literature/fulltext_inventory.csv').drop_duplicates('doi').set_index('doi').title.to_dict()
 metadata_path=OUT/'paper_metadata.json'
 if metadata_path.exists():inventory.update({doi:r['title'] for doi,r in json.loads(metadata_path.read_text(encoding='utf-8')).items()})
 inventory.update({'10.3390/met13010066':'Effects of Rare Earth Elements on Microstructure and Corrosion Resistance of Low Alloy Steel Based on Ultra-Thin Cast Strip Process','source:Vera2015_IJES_6187':'Comparative Study of the Behavior of API 5L-X65 Grade Steel and ASTM A53-B Grade Steel against Corrosion in Seawater'})
 papers=result.groupby('source_paper_id').agg(rows=('record_id','size'),verified_target_rows=('target_verified','sum'),core_complete_rows=('core_complete','sum'),composition_complete_rows=('composition_missing_count',lambda s:int(s.eq(0).sum()))).reset_index()
 papers['title']=papers.source_paper_id.map(inventory).fillna('Title not recovered; resolve DOI')
 papers['source_url']=papers.source_paper_id.map(lambda s:SOURCE_URL if s.startswith('source:') else 'https://doi.org/'+s)
 papers.to_csv(DEST/'paper_inventory.csv',index=False,encoding='utf-8-sig')
 save_json(DEST/'feature_schema.json',{'core_composition_wt_pct':CORE,'grain_one_of':['grain_size_um','grain_size_ASTM_number'],'required_conditions':['electrolyte_condition_cat','temperature_C or explicit room/ambient category','scan_rate_mV_s','sample_process_cat','matrix_phase_group'],'target':'icorr_A_cm2','split_group':'source_paper_id','not_predictors':['source_paper_id','record_id','source_sample_id','icorr_A_cm2'],'extra_elements_retained':['Sb','Nb','Ti','V','Al','Co','B','W','Sn','Ce','La','Y'],'detailed_protocol_additionally_requires':['pH','exposure_h','ocp_stabilization_min'],'grain_unit_policy':'ASTM number and micrometre diameter are not interchangeable'})
 predictors=CORE+['Nb','Ti','V','Al','Sb','RE_ppm','RE_element_cat','grain_size_um','grain_size_ASTM_number','grain_size_definition','sample_process_cat','matrix_phase_group','temperature_C','temperature_condition_cat','pH','electrolyte_condition_cat','scan_rate_mV_s','ocp_stabilization_min','heat_treatment_temperature_C','heat_treatment_time_min','exposure_h']
 pd.DataFrame(columns=['record_id','condition_id']+predictors+['icorr_A_cm2']).to_csv(DEST/'unmeasured_candidates_template.csv',index=False,encoding='utf-8-sig')
 print(json.dumps({k:v for k,v in summary.items() if k not in ['missingness','fold_checks','limitations']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
