"""Source-audited additions; retain observed values and separate review imputation."""
import sys,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
from collect_grain_size import ROOT,key,save_json
from build_al_dataset import CORE,impute_composition
from enrich_RE_pH import ph_fill
import add_confirmed_RE_experiments as previous
DEST=ROOT/'data/al_expanded_20261024';SRC=ROOT/'outputs/expansion_20261024'
DEST.mkdir(parents=True,exist_ok=True)
schema=json.loads((ROOT/'data/al_RE_more_confirmed_20261023/feature_schema.json').read_text(encoding='utf-8'))
FIELDS=schema['predictor_columns'];logs=[]
papers={}
def evidence(doi,loc):
 if doi not in papers:papers[doi]=json.loads((SRC/'sources'/f'{key(doi)}.json').read_text(encoding='utf-8'))
 return next(b['text'] for b in papers[doi]['blocks'] if b['location']==loc)
def log(r,field,value,loc,method='reported_primary_table'):
 logs.append(dict(record_id=r['record_id'],source_paper_id=r['source_paper_id'],field=field,value=value,method=method,location=loc,quote=evidence(r['source_paper_id'],loc),source_url=r['source_url']))
def new(doi,sample,target,loc,**kw):
 r={c:np.nan for c in FIELDS};r.update(record_id='EXP24_'+key(doi+'|'+sample),source_paper_id=doi,source_sample_id=sample,source_url='https://doi.org/'+doi,seed_origin='primary_audit_20261024',target_verified=True,target_review_status='primary_table_unit_and_sample_checked',icorr_A_cm2=target,thermal_pair_available=False,checked_heat_label_available=False,thermal_history_incomplete=True,composition_input_basis='reported_bulk_composition',composition_uses_assumptions=False,composition_statistically_filled_count=0,RE_content_basis='not_reported_not_zero',RE_addition_confirmed=False,pH_reported=np.nan,pH_is_estimated=False,pH_basis='not_reported',heat_treatment_stage='not_reported',current_model_scope_note='',**kw)
 log(r,'icorr_A_cm2',target,loc,'reported_microA_cm2_multiplied_by_1e-6' if 'met1208' in doi or 'met15030232' in doi else 'reported_A_cm2_central_value');return r
def assign(r,values,loc):
 for c,v in values.items():r[c]=v;log(r,c,v,loc)
def make_rows():
 rows=[];doi='10.3390/met12081386'
 for salt,table,pg,groups in [('NaCl',6,10,[(4,'A',[28,24,33],[-556,-539,-537]),(7,'B',[21,16,25],[-648,-601,-491]),(10,'C',[18,16,20],[-579,-475,-617])]),('Na2SO4',7,12,[(4,'D',[52,41,55],[-543,-543,-550]),(7,'E',[39,39,42],[-502,-408,-546]),(10,'F',[20,16,21],[-509,-467,-547])])]:
  for j,(ph,code,vals,potentials) in enumerate(groups):
   loc=f'page{pg}_block{13+j if pg==10 else 12+j}'
   for kind,value,ecorr in zip('OQT',vals,potentials):
    sample=f'{kind}{code}; {salt}; pH {ph}'
    r=new(doi,sample,value*1e-6,loc,steel_family='일반·합금강')
    assign(r,dict(C=.16,Mn=.4,Si=.03,P=.11,S=.1,Cu=.05),'page3_block9')
    assign(r,dict(pH=float(ph),electrolyte_condition_cat=f'3.5% {salt}; pH adjusted with acetic acid or NaOH'),'page3_block7')
    assign(r,dict(scan_rate_mV_s=1.,ocp_stabilization_min=60.),'page6_block3')
    r.update(pH_reported=float(ph),pH_basis='reported_primary_protocol',Ecorr_V=ecorr/1000,Ecorr_reference='Ag/AgCl',sample_process_cat={'O':'as_received','Q':'quenching','T':'tempering'}[kind],heat_history_note='HT2 selected (Section 3.1): 1000 C /45 min water quench; T additionally 600 C /30 min air cool. No test temperature or exposure duration assumed.',current_model_scope_note='P 0.11 and S 0.10 wt.% retained exactly as printed; unusually high values flagged. Unreported RE and temperature remain missing. Ecorr retained as output metadata only.')
    log(r,'Ecorr_V',r['Ecorr_V'],loc,'mV_vs_AgAgCl_divided_by_1000')
    if kind!='O':
     assign(r,dict(heat_treatment_temperature_C=1000. if kind=='Q' else 600.,heat_treatment_time_min=45. if kind=='Q' else 30.),'page3_block11' if kind=='Q' else 'page4_block3')
     r.update(thermal_pair_available=True,checked_heat_label_available=True,thermal_history_incomplete=False,heat_treatment_stage='austenitizing' if kind=='Q' else 'tempering')
     log(r,'HT2_selection','HT2 only used for corrosion','page7_block8')
    rows.append(r)
 doi='10.3390/met15030232'
 specs=[(170,700,60,480,5.6,-336.5),(170,800,150,550,3.3,-395.8),(170,900,240,620,13.,-360.8),(195,700,150,620,4.7,-413.6),(195,800,240,480,3.6,-407.0),(195,900,60,550,6.6,-308.6),(220,700,240,550,3.2,-388.2),(220,800,60,620,2.1,-328.0),(220,900,150,480,1.9,-372.5)]
 for i,(power,velocity,duration,temp,value,ecorr) in enumerate(specs,1):
  loc=f'page6_block{i+5}';r=new(doi,f'L9 sample {i}',value*1e-6,loc,steel_family='스테인리스강')
  assign(r,dict(Mn=.06,S=.06,Si=.16,Cr=17.32,Ni=3.96,Cu=3.34),'page3_block14')
  assign(r,dict(temperature_C=20.,temperature_condition_cat='reported 20 +/- 1 C',electrolyte_condition_cat='3.5 wt.% NaCl',scan_rate_mV_s=1.,ocp_stabilization_min=60.),'page4_block2')
  assign(r,dict(heat_treatment_temperature_C=float(temp),heat_treatment_time_min=float(duration)),loc)
  r.update(thermal_pair_available=True,checked_heat_label_available=True,thermal_history_incomplete=False,heat_treatment_stage='aging',heat_history_note='SLM; stress relief 650 C/60 min; anneal 1040 C/30 min air cool; aging temperature/time from Table 3.',sample_process_cat='SLM',laser_power_W=power,laser_scan_speed_mm_s=velocity,Ecorr_V=ecorr/1000,Ecorr_reference='SCE',current_model_scope_note='SLM power and scanning speed vary and affect corrosion; metadata retained. Model with only thermal process predictors does not identify independent thermal causality. C/P dash is missing, not zero. S=0.06 wt.% retained as printed.')
  log(r,'Ecorr_V',r['Ecorr_V'],loc,'mV_vs_SCE_divided_by_1000');log(r,'prior_heat_history',r['heat_history_note'],'page3_block15');rows.append(r)
 doi='10.3390/met15080880'
 for ph,loc,vals in [(5.8,'page9_block6',[6.28e-8,3.21e-8]),(4.,'page9_block7',[3.65e-7,3.84e-7]),(2.,'page9_block8',[2.02e-4,1.56e-4])]:
  for kind,value,comp,cl in [('410F',vals[0],[.03,.517,.727,10.90,.376,.064,.014,.054],'page3_block4'),('410T',vals[1],[.03,.576,.672,10.99,.398,.092,.010,.073],'page3_block5')]:
   r=new(doi,f'{kind}; pH {ph}',value,loc,steel_family='스테인리스강')
   assign(r,dict(zip(['C','Mn','Si','Cr','Ni','P','S','additional_element_W_wt_pct'],comp)),cl)
   assign(r,dict(temperature_C=25.,temperature_condition_cat='reported 25 C',scan_rate_mV_s=1.,ocp_stabilization_min=60.),'page4_block5')
   assign(r,dict(pH=ph,electrolyte_condition_cat=f'500 mg/L NaCl; HCl pH adjustment to {ph}; final chloride '+str({5.8:500,4.:504,2.:853}[ph])+' ppm'),'page4_block4')
   r.update(pH_reported=ph,pH_basis='reported_primary_protocol',sample_process_cat='as_received_ferritic' if kind=='410F' else 'industrial_thermomechanical',heat_history_note='410T hot rolling and rapid cooling; complete thermal conditions withheld by industrial confidentiality. No hold inferred from >937 C heating.',current_model_scope_note='Test pH/temperature/scan/OCP known. Thermal time/setpoint pair unavailable; excluded from thermal-confirmed evaluation cohort.')
   log(r,'thermal_missing_reason',r['heat_history_note'],'page3_block8');rows.append(r)
 return pd.DataFrame(rows)
def main():
 base=pd.read_csv(ROOT/'data/al_RE_more_confirmed_20261023/al_RE_expanded_review.csv',float_precision='round_trip')
 raw0=pd.read_csv(ROOT/'data/al_RE_pH_enriched_20261023/source_only_before_imputation.csv',float_precision='round_trip')
 raw8=previous.make_rows()
 rawbase=pd.concat([raw0,raw8],ignore_index=True).set_index('record_id').reindex(base.record_id).reset_index()
 assert len(rawbase)==352 and rawbase.record_id.is_unique
 # Carry reviewed metadata, but restore every actual numeric source cell before evaluation.
 sourcebase=base.copy()
 for c in CORE+['pH','RE_ppm','temperature_C','scan_rate_mV_s','ocp_stabilization_min','exposure_h']:
  sourcebase[c]=rawbase[c].to_numpy()
 for c in ['sample_process_cat','sample_region_cat','P_upper_bound','S_upper_bound']:
  if c in rawbase:sourcebase[c]=rawbase[c].to_numpy()
 newrows=make_rows();assert len(newrows)==33
 assert not set(newrows.source_paper_id)&set(base.source_paper_id)
 assert newrows.record_id.is_unique and newrows.icorr_A_cm2.gt(0).all()
 allraw=pd.concat([sourcebase,newrows],ignore_index=True)
 ref=pd.read_csv(ROOT/'data/al_heat_expanded_round4_20261023/composition_reference_source_values.csv',float_precision='round_trip')
 filled,clogs=impute_composition(newrows[['record_id','source_paper_id','steel_family']+CORE],ref)
 prepared=newrows.copy();prepared[CORE]=filled[CORE]
 prepared['composition_statistically_filled_count']=sum(newrows[c].isna()&prepared[c].notna() for c in CORE)
 prepared['composition_uses_assumptions']=prepared.composition_statistically_filled_count.gt(0)
 prepared['composition_missing_count']=prepared[CORE].isna().sum(axis=1)
 # Same declared pH rule; direct pH remains observed, no generic seawater/acid pH invented.
 ph,plogs=ph_fill(pd.concat([sourcebase,prepared],ignore_index=True))
 prepared=ph.iloc[len(base):].copy();combined=pd.concat([base,prepared],ignore_index=True)
 # Explicit completeness definitions do not depend on stale legacy flags.
 essential=CORE+['RE_ppm','electrolyte_condition_cat','temperature_C','pH','scan_rate_mV_s','ocp_stabilization_min','heat_treatment_temperature_C','heat_treatment_time_min']
 for frame in [allraw,combined]:
  frame['full_required_fields_complete']=frame[essential].notna().all(axis=1)
  frame['composition_missing_count']=frame[CORE].isna().sum(axis=1)
 def save(d,name):d.to_csv(DEST/name,index=False,encoding='utf-8-sig')
 save(newrows,'new_rows_source_only.csv');save(prepared,'new_rows_prepared_review.csv');save(combined,'expanded_review.csv');save(allraw,'expanded_source_only.csv')
 save(combined[combined.full_required_fields_complete],'complete_required_fields_review.csv')
 save(allraw[allraw.full_required_fields_complete],'complete_required_fields_source_only.csv')
 save(pd.DataFrame(logs),'new_source_provenance.csv');save(pd.DataFrame(clogs),'composition_imputation_log.csv');save(pd.DataFrame(plogs),'pH_imputation_audit.csv')
 missing=[]
 for c in FIELDS:
  missing.append(dict(field=c,previous_missing=int(base[c].isna().sum()),previous_n=352,new_source_missing=int(newrows[c].isna().sum()),new_prepared_missing=int(prepared[c].isna().sum()),new_n=33,expanded_missing=int(combined[c].isna().sum()),expanded_n=len(combined)))
 save(pd.DataFrame(missing),'missingness.csv')
 screen=[]
 reasons={'10.1002/adem.202402545':'Quantitative icorr not found in primary text/tables; no thermal setpoint/hold. Do not digitize or infer from mass loss.', '10.1016/j.jmrt.2023.12.189':'Publisher API returned 403. Search snippets insufficient for full sample/thermal/chemistry mapping; not merged.', '10.1016/j.jmrt.2025.01.207':'Publisher API returned 403; not merged.', '10.3390/ma18112443':'icorr curves but no explicit numeric target table; not digitized.', '10.3390/ma16020876':'RE bundled with Al+Ca+Zr+Ti total, cannot derive bulk RE ppm; not merged.', '10.3390/ma15010024':'No tabulated numerical icorr found; not digitized.', '10.3390/ma15051746':'No eligible new complete tabulated icorr accepted; not digitized.', '10.3390/ma14010123':'Wrong article identifier during discovery; title mismatch rejected.', '10.3390/met16050464':'Current µA and area 1 cm2 reported, but thermal setpoint/time and test pH/temperature missing; completeness priority, not merged.', '10.3390/met15020137':'Reports breakdown/protection potential; no explicit numeric icorr table found.', '10.1007/s13369-024-09647-6':'LPR-only icorr and external-DC pre-exposure; not mixed with Tafel target cohort.'}
 for p in sorted((SRC/'sources').glob('*.json')):
  a=json.loads(p.read_text(encoding='utf-8'));doi=a['doi'];count=int(newrows.source_paper_id.eq(doi).sum());screen.append(dict(doi=doi,title=a['title'],accepted_rows=count,decision='accepted' if count else 'not_merged',reason='Primary target table and protocol audited; missing values retained.' if count else reasons.get(doi,'Not eligible'),source_paths=json.dumps(a.get('source_paths',[]),ensure_ascii=False)))
 save(pd.DataFrame(screen),'screening_log.csv')
 summary=dict(previous_rows=352,added_rows=33,expanded_rows=len(combined),added_papers=int(newrows.source_paper_id.nunique()),screened_sources=len(screen),new_target_verified=33,new_reported_pH=int(newrows.pH.notna().sum()),new_reported_test_temperature=int(newrows.temperature_C.notna().sum()),new_thermal_pair=int(newrows.thermal_pair_available.sum()),new_reported_scan_rate=int(newrows.scan_rate_mV_s.notna().sum()),new_reported_ocp=int(newrows.ocp_stabilization_min.notna().sum()),new_RE_quantified=int(newrows.RE_ppm.notna().sum()),RE_positive_total=int(combined.RE_ppm.gt(0).sum()),complete_required_source=int(allraw.full_required_fields_complete.sum()),complete_required_review=int(combined.full_required_fields_complete.sum()),new_complete_required_source=int(newrows[essential].notna().all(axis=1).sum()),new_complete_required_review=int(prepared[essential].notna().all(axis=1).sum()),new_composition_estimated_cells=len(clogs),new_pH_estimated=int(prepared.pH_is_estimated.fillna(False).sum()),previous_targets_preserved=bool(np.array_equal(base.icorr_A_cm2,combined.iloc[:352].icorr_A_cm2)),production_model_updated=False)
 save_json(DEST/'summary.json',summary)
 schema.update(primary_evaluation='random 80:20 holdout, seed 42; random 5-fold supplementary',split_group='source_paper_id retained as audit metadata, not mandatory main split',full_required_fields=essential)
 save_json(DEST/'feature_schema.json',schema)
 (DEST/'README.md').write_text('# 문헌 실험자료 확장 2026-10-24\n\n352행에 원문 확인 33행을 추가한 385행 검토본입니다. 실측 원본은 expanded_source_only.csv, 조성/pH 보완 검토본은 expanded_review.csv입니다.\n\n새 자료: S275 18행, SLM 17-4PH 9행, UNS S41003 6행. 24행은 pH가 원문에 명시되고, 21행은 열처리 온도·시간이 명시됩니다. RE를 미보고한 신규 문헌의 RE_ppm은 0으로 채우지 않습니다. 이번 신규 RE 양성 자료는 0행입니다. 전체 RE 양성은 41행입니다.\n\n완전행은 feature_schema.json의 full_required_fields로 판정합니다. 빈칸 없는 전체 자료로 주장하지 않습니다. 원문 pH와 추정 pH를 구분합니다. 노출시간과 OCP 안정화시간은 다른 항목입니다. S275 시험온도는 열처리 냉각의 실온 표현으로 대체하지 않습니다.\n\n무작위 분리를 주 평가로 사용합니다. 전역 보완 검토본을 바로 평가에 넣지 않고 expanded_source_only.csv에서 먼저 분리한 다음 train 자료에만 대치기·스케일러를 적합합니다. 기존 모델은 그대로 두고 새 평가 결과는 results/random_protocol_20261024에 저장합니다.\n\nscreening_log.csv는 미편입 이유, new_source_provenance.csv는 표·페이지·단위, composition_imputation_log.csv는 donor와 추정값, missingness.csv는 결측치 변화를 기록합니다.\n',encoding='utf-8')
 assert summary['previous_targets_preserved'] and len(combined)==385
 assert all(evidence(r['source_paper_id'],r['location'])==r['quote'] for r in logs)
 assert combined.record_id.is_unique
 for f in ['data/training.csv','models/svr.joblib']:
  summary[f+'_sha256']=hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
 save_json(DEST/'validation.json',dict(unique_ids=True,all_new_targets_source_linked=True,no_target_imputation=True,no_RE_zero_imputation=True,old_targets_preserved=True,source_log_rows=len(logs),**{k:v for k,v in summary.items() if 'sha256' in k}))
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
