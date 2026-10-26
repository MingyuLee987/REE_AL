"""Validate, document, and summarize the delivered literature collection."""
import hashlib,json
import numpy as np
import pandas as pd
from collect_grain_size import ROOT,save_json

def main():
 dest=ROOT/'data/al_heat_expanded_round4_20261023';previous=ROOT/'data/al_heat_expanded_round3_20261023'
 d=pd.read_csv(dest/'al_labeled_heat_treatment_expanded.csv',float_precision='round_trip')
 old=pd.read_csv(previous/'al_labeled_heat_treatment_expanded.csv',float_precision='round_trip')
 checked=pd.read_csv(dest/'al_heat_checked_labels.csv',float_precision='round_trip')
 added=pd.read_csv(dest/'new_rows_this_round.csv',float_precision='round_trip')
 schema=json.loads((dest/'feature_schema.json').read_text(encoding='utf-8'));summary=json.loads((dest/'summary.json').read_text(encoding='utf-8'))
 process=['heat_treatment_temperature_C','heat_treatment_time_min']
 assert len(checked)>=300 and d.record_id.is_unique and checked.record_id.is_unique
 assert set(old.record_id)<=set(d.record_id)
 assert np.array_equal(old.icorr_A_cm2.to_numpy(),d.set_index('record_id').loc[old.record_id,'icorr_A_cm2'].to_numpy())
 assert checked.target_verified.all() and checked[process].notna().all().all()
 assert added[process].notna().all().all() and added.icorr_A_cm2.gt(0).all()
 assert checked.heat_treatment_temperature_C.between(-273.15,2000).all() and checked.heat_treatment_time_min.gt(0).all()
 assert schema['numeric_process_features']==process and not schema['grain_and_phase_used']
 assert not any('grain' in x.lower() or 'phase' in x.lower() for x in schema['predictor_columns'])
 assert summary['added_this_round_rows']==len(added)==99
 assert summary['added_this_round_positive_RE_rows']==int(added.RE_ppm.gt(0).sum())==14
 expected={'data/training.csv':'f8ad6c03486d960605c9883acb8332e5ec02ce8f691335d7fbc498a7a2daf101','models/svr.joblib':'716884026724c425e9c003f9517497aaf116c98f6ceed2e23df8250c744ef4f4'}
 for path,digest in expected.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
 missing=[]
 for col in schema['predictor_columns']:
  missing.append(dict(field=col,missing_rows=int(checked[col].isna().sum()),missing_pct=round(checked[col].isna().mean()*100,2)))
 pd.DataFrame(missing).to_csv(dest/'missingness_checked_labels.csv',index=False,encoding='utf-8-sig')
 counts=added.groupby('source_paper_id').agg(added_rows=('record_id','size'),positive_RE_rows=('RE_ppm',lambda x:int(x.gt(0).sum()))).reset_index()
 counts.to_csv(dest/'added_paper_counts.csv',index=False,encoding='utf-8-sig')
 notes='''## 이번 버전의 실제 검토 방식과 제한

기존 237행의 타깃을 보존하고 11개 출처의 99행을 추가했습니다. 전체 336행/57개 출처이며, icorr와 온도·시간이 확인된 별도 CSV는 317행입니다. 300행 목표는 확인본 기준으로 충족했습니다. 확인본도 조성·시험조건 결측이 남아 있으므로 모든 피처가 실측된 완전 학습자료를 뜻하지 않습니다.

추가 RE 양성 자료는 Ce 95 ppm S31254강 12행과 La 4900 ppm 초오스테나이트강 2행입니다. Ce 0.0095 wt.% 및 La 0.49 wt.% 벌크 분석값을 각각 10000배하여 ppm으로 변환했습니다. 명목 La 0.5 wt.%와 실측 La 0.49 wt.%를 구분했습니다. Ce 무첨가 비교군 4행과 La 무첨가 비교군 1행도 포함했습니다. 같은 논문에서 여러 시험조건을 측정한 행들이며, 서로 다른 독립 논문 14편을 뜻하지 않습니다.

수집 중 OpenAI API가 HTTP 429, credit_balance_exhausted를 반환했습니다. 이후 API 호출을 중단하고 이미 확보한 원문을 직접 대조했습니다. API 보조 검토와 직접 대조를 target_review_status 및 new_source_provenance.csv의 method에서 구분합니다. 직접 대조 기록은 scripts/verify_heat_round4_primary.py와 outputs/heat_expansion_round4_manual_20261023/에 있습니다. 직접 검토를 별도 API 재검토라고 표기하지 않았습니다.

Ce 문헌은 출판사 HTML Table IV의 rowspan을 기계적으로 전개하여 S0/S2 시편 대응을 복구했습니다. 0분 미처리/반복 기준값은 제외했습니다. 나노유체 담금질 탄소강 40행은 공개 PDF 7–8쪽 Tables 5–6의 Icorr 열과 Table 2의 열처리를 직접 대조했습니다. 표에 인쇄된 전류밀도를 보존하며, 인접 부식률과 불일치하는 값을 부식률로 역산하여 수정하지 않았습니다. 담금질 냉각매체 차이는 메타데이터로 남겼으며 공정 입력은 요청대로 온도와 시간 두 개뿐입니다. 이 두 피처만으로 냉각매체·다단계 이력의 효과를 분리할 수 없습니다.

온도·시간과 icorr는 통계적으로 채우지 않았습니다. 조성만 제공 PDF의 출처/proxy/범위 가정/같은 계열의 논문 간 donor 정책을 따릅니다. 전체 검토본의 전역 조성 보완값은 검토용이며, 평가 시 논문 단위 분리와 fold 안에서의 보완이 필요합니다. RE 미보고는 0으로 채우지 않았습니다. 기존 운영 CSV와 모델 파일은 그대로 보존했고 재학습하지 않았습니다.

전체 검토본의 온도·시간 결측은 각 19/336행(5.65%)이고, 317행 확인본에서는 각각 0%입니다. 조성·환경별 결측은 missingness.csv(336행)와 missingness_checked_labels.csv(317행)를 구분해서 확인하세요.
'''
 readme=(dest/'README.md').read_text(encoding='utf-8')
 oldparagraph='추가 문헌 {n}편을 처리했습니다.'
 # Keep historical detail, but make the current review methods explicit before it.
 (dest/'README.md').write_text('# 300행 목표 수집 결과\n\n'+notes+'\n---\n\n'+readme,encoding='utf-8')
 (dest/'collection_round4_notes.md').write_text(notes,encoding='utf-8')
 summary.update(checked_rows_goal_300_met=True,api_credit_balance_exhausted=True,direct_primary_review_rows=int(d.target_review_status.eq('direct_primary_table_and_protocol_review').sum()),added_Ce_positive_rows=12,added_La_positive_rows=2)
 save_json(dest/'summary.json',summary)
 checks=json.loads((dest/'validation.json').read_text(encoding='utf-8'));checks.update(previous_237_targets_unchanged=True,checked_rows_at_least_300=True,all_checked_target_and_heat_present=True,checked_physical_heat_ranges_valid=True,RE_units_directly_verified=True,checked_rows=len(checked),new_rows=len(added))
 save_json(dest/'validation.json',checks)
 # Export files must never contain API credentials.
 from collect_grain_size import env
 secrets=[v for k,v in env().items() if k.endswith(('KEY','TOKEN')) and v]
 for path in dest.iterdir():
  if path.is_file():
   txt=path.read_text(encoding='utf-8-sig',errors='replace');assert not any(secret in txt for secret in secrets),path
 print(json.dumps(dict(rows=len(d),checked=len(checked),new=len(added),papers=d.source_paper_id.nunique(),new_RE_positive=int(added.RE_ppm.gt(0).sum()),checks='passed'),ensure_ascii=False))

if __name__=='__main__':main()
