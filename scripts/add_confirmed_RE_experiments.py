"""Add only source-linked positive RE observations; preserve incomplete/protocol flags."""
import hashlib,json
import numpy as np
import pandas as pd
from collect_grain_size import ROOT,key,norm,save_json
from build_al_dataset import CORE,impute_composition
from enrich_RE_pH import ph_fill

BASE=ROOT/'data/al_RE_pH_enriched_20261023'
DEST=ROOT/'data/al_RE_more_confirmed_20261023'
SRC=ROOT/'outputs/RE_more_20261023'
logs=[]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def source(doi,tag=None):
 if tag:return read(SRC/(tag+'.json'))
 path=SRC/'sources'/f'{key(doi)}.json'
 if not path.exists():path=ROOT/'outputs/grain_size_20261023/papers'/f'{key(doi)}.json'
 return read(path)
def evidence(p,location):return next(b['text'] for b in p['blocks'] if b['location']==location)
def log(r,field,value,p,location,method='reported_primary_table'):
 quote=evidence(p,location);logs.append(dict(record_id=r['record_id'],source_paper_id=r['source_paper_id'],field=field,value=value,method=method,quote=quote,location=location,source_url=r['source_url']))
def row(doi,sample,p,target,loc):
 r=dict(record_id='RE_MORE_'+key(doi+'|'+sample),source_paper_id=doi,source_sample_id=sample,source_url='https://doi.org/'+doi,seed_origin='positive_RE_primary_collection',target_verified=True,target_review_status='direct_primary_table_unit_sample_review',icorr_A_cm2=target,heat_treatment_temperature_C=np.nan,heat_treatment_time_min=np.nan,heat_treatment_stage='unreported_final_hold',heat_history_note='Final isothermal temperature/time pair not reported.',thermal_history_incomplete=True,thermal_pair_available=False,checked_heat_label_available=False,core_conditions_complete=False,composition_input_basis='source_bulk_composition',composition_uses_assumptions=False,composition_statistically_filled_count=0,RE_content_basis='reported_bulk_wt_percent',RE_addition_confirmed=True,additional_element_W_wt_pct=np.nan,current_model_scope_note='',steel_family='일반·합금강')
 log(r,'icorr_A_cm2',target,p,loc,'direct_source_unit_and_sample_mapping');return r
def composition(r,p,loc,values):
 for field,v in values.items():r[field]=v;log(r,field,v,p,loc)
def make_rows():
 rows=[]
 # Two differently deoxidized alloys: ICP-MS La 0.002 + Ce 0.003 wt.%.
 doi='10.3390/ma12203359';p=source(doi)
 for sample,target,comp in [('Al deoxidized RE steel',4.60e-5,dict(C=.053,Si=.23,Mn=.13,P=.005,S=.003,Cu=.39,Cr=1.21,Ni=.31)),('Ti/Zr deoxidized RE steel',2.93e-5,dict(C=.050,Si=.22,Mn=.13,P=.005,S=.003,Cu=.43,Cr=1.22,Ni=.33))]:
  r=row(doi,sample,p,target,'materials-12-03359-t002');composition(r,p,'materials-12-03359-t001',comp);r.update(RE_ppm=50.,RE_element_cat='La+Ce',temperature_C=25.,electrolyte_condition_cat='3.5 wt.% NaCl solution',scan_rate_mV_s=.333,heat_history_note='Smelted, hot rolled to 20 mm and cooled at room temperature; rolling hold is unreported. No thermal pair invented.')
  log(r,'RE_ppm',50.,p,'materials-12-03359-t001','La 0.002 wt.% + Ce 0.003 wt.%, sum multiplied by 10000');log(r,'test_conditions','25 +/-1 C; 3.5 wt.% NaCl; 0.333 mV/s',p,'p8');rows.append(r)
 # Trace Ce bridge steels: the Tafel table uses microA/cm2.
 doi='10.3390/met15010085';p=source(doi)
 for sample,ppm,target,comp in [('2# (6 ppm RE)',6.,330e-6,dict(C=.08,Si=.24,Mn=1.21,Ni=.343,Cr=.584,Cu=.456)),('3# (10 ppm RE)',10.,319e-6,dict(C=.07,Si=.25,Mn=1.19,Ni=.379,Cr=.548,Cu=.415))]:
  r=row(doi,sample,p,target,'page19_block5');composition(r,p,'page4_block4',comp);r.update(RE_ppm=ppm,RE_element_cat='Ce',electrolyte_condition_cat='3.5% NaCl; rusted specimen after 9-day salt-spray exposure',exposure_h=216.,heat_history_note='TMCP rolling temperatures are reported, but no isothermal holding duration. Do not substitute a rolling temperature for heat treatment.',current_model_scope_note='Polarization scan rate printed as 1.0 mV without time denominator; left missing.')
  log(r,'RE_ppm',ppm,p,'page4_block4','bulk Ce wt.% multiplied by 10000');log(r,'exposure_h',216.,p,'page18_block5','9 days multiplied by 24');log(r,'thermal_history_note',r['heat_history_note'],p,'page3_block6');rows.append(r)
 # Final 1000 C / 1 min recrystallization anneal, NOT preceding 10 min anneal.
 doi='10.20964/2019.03.31';p=source(doi,'ferritic_Ce')
 specs=[('FSS2',480.,250e-6,dict(C=.009,Si=.52,Mn=.32,P=.008,S=.008,Cr=19.5,N=.072,Mo=1.97),np.nan,'page3_block9'),('FSS3',560.,235e-6,dict(C=.007,Si=.50,Mn=.32,P=.010,S=.009,Cr=19.1,N=.071,Mo=1.95),.58,'page3_block10'),('FSS4',530.,172e-6,dict(C=.010,Si=.53,Mn=.35,P=.008,S=.010,Cr=19.9,N=.071,Mo=2.03),1.12,'page3_block11')]
 for sample,ppm,target,comp,w,loc in specs:
  r=row(doi,sample,p,target,'page4_block25');composition(r,p,loc,comp);r.update(RE_ppm=ppm,RE_element_cat='Ce',temperature_C=25.,electrolyte_condition_cat='1.0 mol/L H2SO4 + 0.5 mol/L NaCl',scan_rate_mV_s=.5,heat_treatment_temperature_C=1000.,heat_treatment_time_min=1.,heat_treatment_stage='final recrystallization annealing',thermal_pair_available=True,checked_heat_label_available=True,steel_family='스테인리스강',additional_element_W_wt_pct=w,heat_history_note='Hot rolled; annealed 1000 C/10 min; cold rolled; final recrystallization anneal 1000 C/1 min. Cathodic cleaning is not a heat treatment.',current_model_scope_note='Known W is metadata; current predictors cannot model its effect.' if pd.notna(w) else 'Other alloying Nb/Ti are not current predictors; assess scope before training.')
  log(r,'RE_ppm',ppm,p,loc,'bulk Ce wt.% multiplied by 10000');log(r,'thermal_pair','1000 C / 1 min final stage',p,'page3_block4');log(r,'test_conditions','25 C; 0.5 mV/s',p,'page3_block13');rows.append(r)
 # A negative/neutral RE effect on icorr is retained; do not select only improved results.
 doi='10.2320/matertrans.M2015145';p=source(doi,'duplex_Ce');r=row(doi,'CE190',p,102.4e-6,'page4_block55');composition(r,p,'page2_block13',dict(C=.020,Cr=27.,Ni=6.60,Mo=2.50,Si=.29,Mn=.93,Cu=1.50,N=.32));r.update(RE_ppm=190.,RE_element_cat='Ce',temperature_C=338.-273.15,electrolyte_condition_cat='Deaerated 2 M H2SO4',scan_rate_mV_s=1.,heat_treatment_temperature_C=1333.-273.15,heat_treatment_time_min=30.,heat_treatment_stage='solution annealing',thermal_pair_available=True,checked_heat_label_available=True,steel_family='스테인리스강',additional_element_W_wt_pct=3.40,heat_history_note='Solution annealed at 1333 K for 30 min, water quenched; K converted by subtracting 273.15. Source retrieved as publisher advance-view proof.',current_model_scope_note='3.40 wt.% W is metadata; current predictors cannot model its effect.')
 log(r,'RE_ppm',190.,p,'page2_block13','bulk 0.019 mass% Ce multiplied by 10000');log(r,'thermal_pair','1059.85 C / 30 min',p,'page2_block2','1333 K minus 273.15');log(r,'test_temperature_C',64.85,p,'page2_block3','338 K minus 273.15');rows.append(r)
 assert len(rows)==8 and all(r['RE_ppm']>0 for r in rows)
 return pd.DataFrame(rows)

def separate_candidates():
 # Flux-additive dosing is not retained bulk RE concentration. Keep outside main dataset.
 doi='10.1155/2018/4071352';p=source(doi,'weld_RE');rows=[]
 for sample,dose,target,comp in [('REE1',.3,13.4e-6,[.12,.25,.97,.11,1.07]),('REE2',.5,14.e-6,[.16,.29,1.44,.17,1.77]),('REE3',.7,13.6e-6,[.056,.42,1.47,.23,2.41]),('REE4',1.,16.5e-6,[.036,.33,1.42,.25,2.34])]:
  r=row(doi,sample,p,target,'page9_block5');r.update(RE_addition_confirmed=True,RE_ppm=np.nan,RE_element_cat='Ce+La+Nd+Pr+Sm',RE_content_basis='REE-Si-Fe flux additive percentage; not bulk RE mass fraction',REE_Si_Fe_flux_additive_pct=dose,heat_history_note='FCAW as-welded metal. No explicit isothermal heat-treatment pair. Flux additive amount cannot be converted to retained RE ppm.',electrolyte_condition_cat='3.5 wt.% NaCl',temperature_condition_cat='room temperature',scan_rate_mV_s=1.,ocp_stabilization_min=30.);r.update(dict(zip(['C','Si','Mn','Mo','Ni'],comp)));log(r,'REE_Si_Fe_flux_additive_pct',dose,p,'page2_block5','nominal flux additive amount, not steel chemistry');rows.append(r)
 pd.DataFrame(rows).to_csv(DEST/'RE_flux_addition_only_separate.csv',index=False,encoding='utf-8-sig')
 # Primary EH36 paper has contradictory scan-window and concentration statements.
 doi='10.3390/coatings14040413';p=source(doi);rows=[]
 for sample,element,ppm,target in [('1#','La',31.,6.59e-5),('2#','Ce',24.,7.57e-5),('3#','Pr',1.,9.53e-5)]:
  r=row(doi,sample,p,target,'page8_block6');r.update(RE_element_cat=element,RE_ppm=ppm,target_verified=False,target_review_status='needs_protocol_review',RE_content_basis='ICP-MS Table 2',current_model_scope_note='Method states +/-5 mV polarization window, inconsistent with a conventional Tafel sweep; Table 2 Ce 0.0024 wt.% differs from introduction 0.0027 wt.%. Not merged into main data.');log(r,'RE_ppm',ppm,p,'page3_block10','bulk assay Table 2, conflict retained');rows.append(r)
 pd.DataFrame(rows).to_csv(DEST/'RE_protocol_unresolved_separate.csv',index=False,encoding='utf-8-sig')

def main():
 DEST.mkdir(parents=True,exist_ok=True)
 base=pd.read_csv(BASE/'al_RE_pH_prepared_review.csv',float_precision='round_trip');reported=pd.read_csv(BASE/'al_RE_pH_source_values.csv',float_precision='round_trip');new=make_rows()
 for col in CORE:
  if col not in new:new[col]=np.nan
 ref=pd.read_csv(ROOT/'data/al_heat_expanded_round4_20261023/composition_reference_source_values.csv',float_precision='round_trip')
 q=new[['record_id','source_paper_id','steel_family']+CORE];filled,clogs=impute_composition(q,ref)
 new['composition_statistically_filled_count']=sum(new[c].isna()&filled[c].notna() for c in CORE);new['composition_uses_assumptions']=new.composition_statistically_filled_count.gt(0);new[CORE]=filled[CORE];new['composition_missing_count']=new[CORE].isna().sum(axis=1)
 combined=pd.concat([reported,new],ignore_index=True);ph,plogs=ph_fill(combined)
 # Preserve every old prepared cell; assign new-row pH metadata from the same declared procedure.
 new=ph.iloc[len(base):].copy();out=pd.concat([base,new],ignore_index=True)
 out['RE_addition_confirmed']=out.RE_ppm.gt(0)
 out['RE_content_basis']=out.RE_content_basis.fillna('existing_source_or_nominal_basis_see_previous_provenance')
 assert len(out)==352 and out.record_id.is_unique and int(out.RE_ppm.gt(0).sum())==41
 assert np.array_equal(base.icorr_A_cm2.to_numpy(),out.iloc[:len(base)].icorr_A_cm2.to_numpy())
 assert np.array_equal(base.pH.to_numpy(),out.iloc[:len(base)].pH.to_numpy(),equal_nan=True)
 assert int(out.checked_heat_label_available.sum())==321
 for df,name in [(out,'al_RE_expanded_review.csv'),(out[out.checked_heat_label_available.fillna(False)],'al_heat_checked_RE_expanded.csv'),(out[out.RE_ppm.gt(0)],'RE_positive_quantified.csv'),(new,'new_RE_positive_rows.csv')]:df.to_csv(DEST/name,index=False,encoding='utf-8-sig')
 separate_candidates()
 pd.DataFrame(logs).to_csv(DEST/'new_source_provenance.csv',index=False,encoding='utf-8-sig');pd.DataFrame(clogs).to_csv(DEST/'new_composition_imputation_log.csv',index=False,encoding='utf-8-sig');pd.DataFrame(plogs).to_csv(DEST/'pH_method_audit.csv',index=False,encoding='utf-8-sig')
 summary=dict(previous_rows=344,expanded_rows=352,previous_RE_positive_quantified_rows=33,RE_positive_quantified_rows=41,added_RE_positive_quantified_rows=8,added_papers=4,RE_content_available_rows=int(out.RE_ppm.notna().sum()),checked_heat_rows=321,added_heat_checked_RE_rows=4,flux_addition_only_rows_separate=4,protocol_unresolved_rows_separate=3,pH_missing_pct=round(out.pH.isna().mean()*100,2),RE_missing_pct=round(out.RE_ppm.isna().mean()*100,2),previous_targets_and_pH_preserved=True,model_retrained=False)
 save_json(DEST/'summary.json',summary)
 schema=read(BASE/'feature_schema.json');schema['metadata_not_predictors']+=['RE_addition_confirmed','RE_content_basis','additional_element_W_wt_pct','current_model_scope_note'];save_json(DEST/'feature_schema.json',schema)
 pd.DataFrame([dict(field=c,missing=int(out[c].isna().sum()),missing_pct=round(out[c].isna().mean()*100,2)) for c in schema['predictor_columns']]).to_csv(DEST/'missingness.csv',index=False,encoding='utf-8-sig')
 notes='''# 희토류 함량이 확인된 양성 자료 추가

기존 344행을 보존하고 희토류 함량이 0보다 큰 8행을 추가했습니다. 전체 352행, RE 함량이 수치로 기입된 행 52행(무첨가 비교군 포함), RE 양성 41행입니다. 양성 41행이 모두 열처리·환경·조성을 완비한 것은 아닙니다. 전체 열처리 쌍+타깃 확인본은 321행입니다.

## 이번 추가 8행

- 10.3390/ma12203359: ICP-MS La 0.002 + Ce 0.003 wt.%, 합계 50 ppm인 Al 탈산강 및 Ti/Zr 탈산강 2행. Table 2의 4.60/2.93 ×10^-5 A/cm2. 압연 후 냉각만 보고되어 등온 열처리 쌍은 결측입니다.
- 10.3390/met15010085: Ce 6/10 ppm 교량강 2행. Tables 1/7, icorr 330/319 microA/cm2를 1e-6배했습니다. 9일 부식 후 시편이며 TMCP 유지시간 미보고입니다. 주사속도 원문 단위에 시간 분모가 없어 임의로 mV/s로 바꾸지 않았습니다.
- 10.20964/2019.03.31: Ce 480/560/530 ppm 444형 스테인리스 FSS2/3/4, 3행. Tables 1/2의 최우측 icorr 250/235/172 microA/cm2입니다. 왼쪽 critical current ic와 passive current ip를 타깃으로 혼동하지 않았습니다. 마지막 재결정 소둔 1000 C/1 min을 사용했으며 앞선 소둔 10 min과 구분했습니다.
- 10.2320/matertrans.M2015145: Ce 190 ppm CE190 1행. Table 2 icorr 102.4 microA/cm2. 1333 K/30 min 용체화는 1059.85 C/30 min, 시험 338 K는 64.85 C로 환산했습니다. Ce 시편의 icorr가 기준 시편보다 커도 배제하지 않았습니다. 출판사 advance-view proof 원문을 확보했습니다.

W 0.58/1.12/3.40 wt.%가 알려진 시편은 additional_element_W_wt_pct 메타데이터에 기록했습니다. 현재 모델의 핵심 10개 조성은 W 효과를 표현하지 못하므로, 이들 시편을 독립 AL 후보로 사용하려면 모델 범위를 재검토해야 합니다. 공정 피처는 요청대로 온도·시간 두 개뿐이며 W나 검토 상태를 피처로 자동 추가하지 않았습니다. 열처리 확인 행 수는 모델 적합성이나 완전자료 행 수가 아닙니다.

## 별도 보관

RE_flux_addition_only_separate.csv 4행은 10.1155/2018/4071352의 FCAW 용접금속입니다. REE-Si-Fe를 플럭스에 넣은 사실과 icorr는 확인되지만, 실제 강재의 잔류 RE wt.%는 보고되지 않았습니다. 플럭스 첨가제 0.3/0.5/0.7/1.0%를 강재의 RE ppm으로 변환하지 않았고, 41행이나 전체 352행에 합산하지 않았습니다. 본문 일부의 0.2%와 Table 2의 0.3%도 충돌하므로 표 기준과 구분을 유지합니다.

RE_protocol_unresolved_separate.csv 3행은 EH36 La/Ce/Pr 첨가강입니다. ICP-MS 함량과 본문 icorr는 있지만, 시험법의 +/-5 mV 주사범위와 Tafel 설명이 충돌하며 Ce 함량도 Table 2와 서론이 다릅니다. 따라서 주 자료에 넣지 않았습니다. 억제제·코팅·비철 합금 연구도 RE 첨가 철강으로 합산하지 않았습니다.

기존 pH 100개 대리/추정값의 값과 상태를 보존했습니다. 신규 행은 같은 선언된 pH 규칙으로 처리했으며 원문 pH와 구분합니다. 전역 조성/pH 보완본은 검토용이고, 독립 평가에는 논문별 분리 후 학습 fold에서만 대치기를 맞춰야 합니다. 이전 버전 fold 파일은 새 352행 버전의 fold 파일이 아닙니다. 운영 data/training.csv와 모델은 수정·재학습하지 않았습니다.

추출값과 단위·원문 위치는 new_source_provenance.csv, 공개 원문과 표 렌더는 outputs/RE_more_20261023에 있습니다. 신규 8행은 직접 원문 대조했으며 OpenAI 추출 API를 사용했다고 주장하지 않습니다.
'''
 (DEST/'README.md').write_text(notes,encoding='utf-8')
 for file,expected in [('data/training.csv','f8ad6c03486d960605c9883acb8332e5ec02ce8f691335d7fbc498a7a2daf101'),('models/svr.joblib','716884026724c425e9c003f9517497aaf116c98f6ceed2e23df8250c744ef4f4')]:assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==expected
 save_json(DEST/'validation.json',dict(unique_record_ids=True,previous_344_targets_preserved=True,previous_pH_values_preserved=True,new_rows_all_positive_RE=True,all_added_targets_source_linked=True,known_thermal_rows=321,thermal_and_target_not_imputed=True,production_hashes_unchanged=True))
 print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
