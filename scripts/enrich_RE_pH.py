"""Keep source values intact; add RE observations and explicit, fold-safe pH estimates."""
import copy,hashlib,json,re
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from collect_grain_size import ROOT,key,norm,save_json
from build_al_dataset import CORE,impute_composition

BASE=ROOT/'data/al_heat_expanded_round4_20261023'
DEST=ROOT/'data/al_RE_pH_enriched_20261023'
EVIDENCE=ROOT/'outputs/heat_expansion_20261023'
PROCESS=['heat_treatment_temperature_C','heat_treatment_time_min']
DONORS=['10.1155/ijco/5531986','10.3390/ma14247863','10.3390/ma17235687']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def load(name):return pd.read_csv(BASE/name,float_precision='round_trip')
def write(df,name):df.to_csv(DEST/name,index=False,encoding='utf-8-sig')

def supplemental(columns):
 rows=[];logs=[]
 for doi,element in [('10.3390/ma18010069','Ce'),('10.3390/ma17184467','La')]:
  ex=read(EVIDENCE/'extractions'/f'{key(doi)}.json');inp=read(EVIDENCE/'inputs'/f'{key(doi)}.json');cmap={c['record_id']:c for c in inp['candidates']}
  for rec in ex['records']:
   c=cmap[rec['candidate_id']];assert np.isclose(rec['target_value_A_cm2'],c['icorr_A_cm2'],rtol=1e-12,atol=0)
   assert any(norm(rec['target_quote']) in norm(b['text']) for b in inp['source_blocks'])
   r={col:np.nan for col in columns};r.update(record_id='RE_PH_'+rec['candidate_id'],source_paper_id=doi,source_sample_id=rec['sample_label'],source_url='https://doi.org/'+doi,seed_origin='additional_RE_primary_table',target_verified=True,target_review_status='direct_primary_target_RE_review_thermal_hold_unreported',icorr_A_cm2=rec['target_value_A_cm2'],heat_treatment_stage='solution treatment' if element=='Ce' else 'coiling hold unreported',heat_history_note='Final solution treatment 1050 C, duration not reported; earlier 1200 C/2 h belongs to pre-forging stage.' if element=='Ce' else '1200 C/1 h homogenization preceded rolling and coiling at 550 C; coiling hold unreported. Earlier homogenization is not used as final heat pair.',thermal_history_incomplete=True,thermal_pair_available=False,checked_heat_label_available=False,core_conditions_complete=False,composition_input_basis='reported_bulk_Table2' if element=='Ce' else 'reported_bulk_Table1',composition_uses_assumptions=False,composition_statistically_filled_count=0,steel_family='스테인리스강' if element=='Ce' else '일반·합금강')
   # Previous audit rejected the thermal mapping only; retain source-supported chemistry and test conditions.
   for a in rec['attributes']:
    if a['field'].startswith('heat_treatment') or not a.get('quote_verified'):continue
    assert any(norm(a['quote']) in norm(b['text']) for b in inp['source_blocks'])
    if a['value'] is not None:r[a['field']]=a['value']
    elif a['field'].endswith('_cat'):r[a['field']]=a['text']
    logs.append(dict(record_id=r['record_id'],field=a['field'],value=a['value'] if a['value'] is not None else a['text'],method='reported_primary_table_or_protocol',source_url='https://doi.org/'+doi,quote=a['quote'],location=a['location']))
   assay=next(a for a in rec['attributes'] if a['field']==element)
   r['RE_ppm']=assay['value']*10000;r['RE_element_cat']=element
   r['heat_treatment_temperature_C']=1050 if element=='Ce' else np.nan;r['heat_treatment_time_min']=np.nan
   r['composition_missing_count']=sum(pd.isna(r.get(c)) for c in CORE)
   logs += [dict(record_id=r['record_id'],field='RE_ppm',value=r['RE_ppm'],method='reported_bulk_wt_percent_times_10000',source_url=r['source_url'],quote=assay['quote'],location=assay['location']),dict(record_id=r['record_id'],field='icorr_A_cm2',value=r['icorr_A_cm2'],method='direct_primary_table_unit_and_sample_review',source_url=r['source_url'],quote=rec['target_quote'],location=rec['target_location'])]
   rows.append(r)
 assert len(rows)==8
 return pd.DataFrame(rows),logs

def plain_salt(text):
 t=str(text).lower().replace('without co2 saturation','').replace('without co2','')
 return bool(re.search(r'3\.5\s*(?:wt\.?\s*)?(?:mass\s*)?%\s*(?:aqueous\s*)?nacl',t)) and not re.search(r'co2|co₂|h2so4|hcl|ch3cooh|naoh|buffer|ringer|nahso3|seawater|brine|deaerat|purg',t)
def ambient(row):
 t=row.get('temperature_C',np.nan)
 return (pd.notna(t) and 20<=float(t)<=30) or bool(re.search(r'room|ambient',str(row.get('temperature_condition_cat','')),re.I))
def ph_fill(frame,held=()):
 d=frame.copy();d['pH_reported']=d['pH'];d['pH_basis']=np.where(d.pH.notna(),'previous_source_reported','unreported');d['pH_is_estimated']=False;d['pH_donor_papers']='';d['pH_reference_min']=np.nan;d['pH_reference_max']=np.nan
 # Three independent primary papers, one value per paper. Never use estimated pH as a donor.
 source=d[d.source_paper_id.isin(DONORS)&~d.source_paper_id.isin(held)&d.pH_reported.notna()&d.electrolyte_condition_cat.map(plain_salt)]
 donor=source.groupby('source_paper_id').pH_reported.median()
 logs=[]
 for i,r in d.iterrows():
  if pd.notna(r.pH):continue
  if r.source_paper_id=='10.3390/ma16030899':
   # Same-paper solution proxy, not a reported Tafel-test pH.
   d.loc[i,'pH']=3.;d.loc[i,'pH_basis']='same_paper_same_concentration_solution_proxy';d.loc[i,'pH_is_estimated']=True
   logs.append(dict(record_id=r.record_id,value=3.,method='same_paper_solution_proxy',donor_papers=json.dumps([r.source_paper_id]),note='pH 3.0 is stated for the stress-corrosion 0.1 M H2S solution; electrochemical section states the same nominal electrolyte but does not explicitly repeat pH. Proxy, not a directly measured Tafel pH.'))
  elif plain_salt(r.electrolyte_condition_cat) and ambient(r):
   usable=donor.drop(index=r.source_paper_id,errors='ignore')
   if len(usable)<3:continue
   value=float(usable.median());d.loc[i,'pH']=value;d.loc[i,'pH_basis']='same_electrolyte_3_paper_median_estimate';d.loc[i,'pH_is_estimated']=True;d.loc[i,'pH_donor_papers']=json.dumps(list(usable.index));d.loc[i,'pH_reference_min']=float(usable.min());d.loc[i,'pH_reference_max']=float(usable.max())
   logs.append(dict(record_id=r.record_id,value=value,method='same_electrolyte_3_paper_median_estimate',donor_papers=json.dumps(list(usable.index)),note='Unbuffered 3.5% NaCl class, ambient/20–30 C only; paper medians 5.9, 6.5, 7.4. Reference range is not a confidence interval. No target or composition used.'))
 # A bound is not an exact pH, and cannot be turned into a midpoint.
 d['pH_lower_bound']=np.nan;d['pH_bound_relation']=''
 mask=d.source_paper_id.eq('10.1038/s41529-025-00682-8');d.loc[mask,'pH_lower_bound']=14.;d.loc[mask,'pH_bound_relation']='greater_than';d.loc[mask,'pH_basis']='reported_lower_bound_only'
 return d,logs

def main():
 DEST.mkdir(parents=True,exist_ok=True)
 base=load('al_labeled_heat_treatment_expanded.csv');raw=load('source_only_before_composition_imputation.csv');prep=load('before_statistical_imputation.csv');ref=load('composition_reference_source_values.csv');schema=read(BASE/'feature_schema.json')
 new,provenance=supplemental(raw.columns)
 # Restore explicit zero-Y controls from their reviewed table, not from missingness.
 for frame in [base,raw,prep]:
  mask=frame.source_paper_id.eq('10.3390/met15090935') & frame.source_sample_id.isin(['Q','QT'])
  frame.loc[mask,'RE_ppm']=0.;frame.loc[mask,'RE_element_cat']='Y'
 raw=pd.concat([raw,new],ignore_index=True);prep=pd.concat([prep,new],ignore_index=True)
 querycols=['record_id','source_paper_id','steel_family']+CORE+[c for c in prep if c.endswith('_upper_bound')]
 reference=pd.concat([ref,new[['record_id','source_paper_id','steel_family']+CORE]],ignore_index=True).drop_duplicates('record_id')
 # Keep previous composition estimates; only prepare chemistry for newly added observations.
 nf,nlogs=impute_composition(new[querycols],reference);newprepared=new.copy();newprepared[CORE]=nf[CORE];newprepared['composition_statistically_filled_count']=sum(new[c].isna()&newprepared[c].notna() for c in CORE);newprepared['composition_uses_assumptions']=newprepared.composition_statistically_filled_count.gt(0);newprepared['composition_missing_count']=newprepared[CORE].isna().sum(axis=1)
 reported=pd.concat([base,newprepared[base.columns]],ignore_index=True)
 output,phlogs=ph_fill(reported)
 write(output,'al_RE_pH_prepared_review.csv');write(output[output.checked_heat_label_available],'al_heat_checked_pH_prepared_review.csv');write(reported,'al_RE_pH_source_values.csv');write(raw,'source_only_before_imputation.csv');write(output[output.RE_ppm.notna()],'RE_content_available.csv');write(newprepared,'new_RE_rows_thermal_incomplete.csv');write(pd.DataFrame(phlogs),'pH_imputation_log.csv');write(pd.DataFrame(provenance),'new_RE_source_provenance.csv');write(pd.DataFrame(nlogs),'new_RE_composition_imputation_log.csv')
 write(pd.DataFrame([dict(field=c,before_missing=int(reported[c].isna().sum()),after_missing=int(output[c].isna().sum()),after_missing_pct=round(output[c].isna().mean()*100,2)) for c in schema['predictor_columns']]),'missingness.csv')
 folds=[]
 for k,(tr,te) in enumerate(GroupKFold(5).split(prep,groups=prep.source_paper_id)):
  held=set(prep.iloc[te].source_paper_id);ff,ll=impute_composition(prep[querycols],reference[~reference.source_paper_id.isin(held)]);fd=prep[['record_id','source_paper_id']+schema['predictor_columns']+['icorr_A_cm2','target_verified']].copy();fd[CORE]=ff[CORE]
  fd,pl=ph_fill(fd,held);fd['role']='train';fd.loc[te,'role']='test';write(fd,f'paper_group_fold_{k}.csv');write(pd.DataFrame(pl),f'fold_{k}_pH_imputation_log.csv')
  assert all(not(set(json.loads(x['donor_papers']))&held) for x in ll)
  # Same-paper proxy is a source-based operation; cross-paper median donors must all be training papers.
  assert all(not(set(json.loads(x['donor_papers']))&held) for x in pl if x['method']=='same_electrolyte_3_paper_median_estimate')
  folds.append(dict(fold=k,test_rows=len(te),cross_paper_pH_estimates=sum(x['method']=='same_electrolyte_3_paper_median_estimate' for x in pl),no_held_out_statistical_donors=True))
 oldbase=load('al_labeled_heat_treatment_expanded.csv')
 assert len(output)==344 and len(new)==8 and new.RE_ppm.gt(0).sum()==6
 assert np.array_equal(oldbase.icorr_A_cm2.to_numpy(),output.set_index('record_id').loc[oldbase.record_id,'icorr_A_cm2'].to_numpy())
 assert output.record_id.is_unique and output.icorr_A_cm2.gt(0).all()
 assert int(output.checked_heat_label_available.sum())==317
 assert output.loc[output.checked_heat_label_available,PROCESS].notna().all().all()
 assert reported.pH.equals(output.pH_reported)
 assert all(np.isnan(x) for x in output.loc[output.source_paper_id.eq('10.1038/s41529-025-00682-8'),'pH'])
 summary=dict(previous_rows=len(base),rows=len(output),papers=int(output.source_paper_id.nunique()),new_RE_rows=8,new_RE_positive_rows=6,RE_available_before=int(oldbase.RE_ppm.notna().sum()),RE_available_after=int(output.RE_ppm.notna().sum()),RE_positive_before=int(oldbase.RE_ppm.gt(0).sum()),RE_positive_after=int(output.RE_ppm.gt(0).sum()),pH_available_before=int(reported.pH.notna().sum()),pH_available_after=int(output.pH.notna().sum()),pH_estimated_rows=int(output.pH_is_estimated.sum()),pH_missing_pct=round(output.pH.isna().mean()*100,2),checked_heat_rows=317,new_RE_rows_checked_heat=0,fold_checks=folds,all_previous_targets_preserved=True,model_retrained=False,PDF_explicit_pH_imputation_rule=False)
 save_json(DEST/'summary.json',summary)
 schema['metadata_not_predictors'] += ['pH_reported','pH_basis','pH_is_estimated','pH_donor_papers','pH_reference_min','pH_reference_max','pH_lower_bound','pH_bound_relation'];save_json(DEST/'feature_schema.json',schema)
 notes=f'''# 희토류 함량 및 pH 보완본

전체 {len(output)}행, 열처리 온도·시간과 타깃 확인본 317행입니다. 기존 336행과 타깃을 보존했습니다. 새 Ce/La 시험 8행(양성 6행, 무첨가 비교군 2행)은 마지막 열처리 유지시간이 없어 확인본에 포함하지 않았습니다. Ce 23/82 ppm, La 67/110/230/310 ppm을 벌크 wt.%에서 환산했습니다. 새 행의 이전 1200 C 유지조건을 마지막 열처리 조건으로 잘못 연결하지 않았습니다.

- al_RE_pH_prepared_review.csv: 희토류와 표시된 pH 추정치를 포함한 전체 검토본.
- al_heat_checked_pH_prepared_review.csv: 기존 열처리 확인 317행. pH 추정치가 포함됩니다.
- al_RE_pH_source_values.csv: pH 통계 보완을 하지 않은 비교본. 기존 조성 추정치는 포함됩니다.
- RE_content_available.csv: RE 함량이 명시된 행만 모은 자료. 열처리 미확인 행도 있으므로 상태 열을 확인하세요.
- new_RE_rows_thermal_incomplete.csv: 신규 8행, 현재 2개 공정 피처로 완전한 학습 입력이 아닙니다.

## 제공 PDF의 적용 범위

문헌데이터_수집과정_정리_조성보완_개정본.pdf 4쪽은 원문 복구 우선, 방법·출처 기록, 서로 다른 3–5개 논문의 참고값 사용, target 미사용 원칙을 설명합니다. 5쪽은 pH를 새로 계산한 문서가 아니라고 명시합니다. 따라서 아래 pH 규칙은 PDF에 있는 공식이 아니라 그 원칙을 적용한 프로젝트 확장입니다. 조성의 제조사 대표값/U/2 규칙을 pH에 그대로 적용하지 않았습니다.

## pH 규칙과 한계

원문 pH {summary['pH_available_before']}개를 pH_reported에 보존했습니다. pH 열은 원문값을 우선하고, 부족한 경우 아래 표시된 대리값/통계 추정을 허용한 검토용 입력입니다. pH 보완 {summary['pH_estimated_rows']}행, 보완 후 결측 {summary['pH_missing_pct']}%입니다.

1. 0.1 M H2S 연구의 pH 3.0은 같은 논문의 응력부식 용액에 보고되었습니다. 전기화학 절에는 같은 농도의 H2S가 제시되지만 pH가 반복 명시되지 않으므로 4행에 같은 논문 용액 proxy로만 표기했습니다. 이를 Tafel 시험의 직접 측정 pH라고 부르지 않습니다.
2. 완충제·산·CO2·해수·탈기 조건이 명시되지 않은 단순 3.5% NaCl, 실온 또는 20–30 C 행만 통계 보완 대상으로 삼았습니다. 서로 다른 3개 논문의 원문 보고 pH 5.9, 6.5, 7.4를 논문별 한 표로 만든 후 중앙값 6.5를 사용했습니다. 단순 NaCl이라는 이유로 pH 7을 가정하지 않았습니다. 출처는 10.3390/ma17235687, 10.1155/ijco/5531986, 10.3390/ma14247863이며, 이 값들은 각기 다른 제조·조정·가스 조건에 영향받을 수 있어 강한 추정 근거가 아닙니다. pH_reference_min/max는 5.9–7.4 범위이지 신뢰구간이 아닙니다. 이 추정은 미보고 실제 pH를 복원했다는 뜻이 아닙니다.
3. 산성·알칼리·해수·CO2·5%/10% 염수에는 이 중앙값을 이전하지 않았습니다. ASW의 pH >14는 하한 및 부등호로 보존하고 pH=14로 대입하지 않았습니다. 세척용 PBS pH 7.4를 부식시험 pH로 사용하지 않았습니다.
4. pH는 target, 조성, 성능 지표를 보지 않고 보완했습니다. 보완된 pH는 donor가 아닙니다. 논문 단위 5개 fold에서 held-out 논문을 통계 donor에서 제외했습니다. 보고된 pH를 가진 논문이 3개뿐이므로 그중 하나가 검증 fold이면 3개 donor를 만족하지 못해 상당수 pH 결측이 다시 남습니다. 전역 검토본을 성능 평가에 그대로 사용하지 마세요. pH 원문만 사용한 경우와 보완한 경우를 비교해야 합니다.

## 희토류 출처

Ce: https://doi.org/10.3390/ma18010069, Table 2(벌크 조성), Table 4(분극 부식전류). La: https://doi.org/10.3390/ma17184467, Tables 1–2. LaCl3를 용액에 넣은 억제제 실험은 제외하고 0 g/L 용액의 합금 시편만 포함했습니다. 미보고 RE는 여전히 결측입니다. Y 무첨가 Q/QT 비교군 2행은 기존 검토에서 확인된 Y=0을 RE_ppm=0으로 단위 정리했습니다.

공정 피처는 온도와 시간 두 개이며 pH 보완 상태/출처/범위는 메타데이터입니다. 기존 모델과 data/training.csv를 변경하거나 재학습하지 않았습니다.
'''
 (DEST/'README.md').write_text(notes,encoding='utf-8')
 expected={'data/training.csv':'f8ad6c03486d960605c9883acb8332e5ec02ce8f691335d7fbc498a7a2daf101','models/svr.joblib':'716884026724c425e9c003f9517497aaf116c98f6ceed2e23df8250c744ef4f4'}
 for path,digest in expected.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
 print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
