"""Outcome-preserving data redesign; new experimental designs are not observations."""
from pathlib import Path
import json, hashlib, zipfile
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data/process_adjusted_20261024'
OUT.mkdir(parents=True, exist_ok=True)
src = ROOT/'data/al_expanded_20261024/expanded_source_only.csv'
before = hashlib.sha256(src.read_bytes()).hexdigest()
d = pd.read_csv(src, float_precision='round_trip')
original = d.copy(deep=True)
external = pd.read_csv(ROOT/'results/external_paper_20261024/source_inputs.csv')
slm = '10.3390/met15030232'
sinter = '10.1007/s11665-017-2778-4'
extdoi = '10.1016/j.prostr.2025.08.043'
assert extdoi not in set(d.source_paper_id)

def annotate(frame, external=False):
    x = frame.copy()
    x['material_grade_checked'] = 'not_reaudited'
    x['manufacturing_route_checked'] = 'not_reaudited'
    x['dataset_role'] = 'background_training' if not external else 'development_external_already_examined'
    x['environment_family_checked'] = 'not_reaudited'
    for name in ['stress_relief_temperature_C','stress_relief_time_min','sintering_temperature_C','sintering_time_min',
                 'solution_temperature_C','solution_time_min','aging_temperature_C','aging_time_min']:
        x[name] = np.nan
    x['solution_cooling_checked'] = 'not_reported'
    x['aging_cooling_checked'] = 'not_reported'
    x['aging_state_checked'] = 'not_reaudited'
    x['process_mapping_basis'] = 'Not mapped: legacy heat pair and source history preserved; no automated stage guess'
    x['pH_missing_source'] = x.pH.isna()
    x['test_temperature_missing_source'] = x.temperature_C.isna()
    x['log10_icorr_target'] = np.log10(x.icorr_A_cm2)
    for i, r in x.iterrows():
        doi = r.source_paper_id
        if doi not in [slm, sinter, extdoi]:
            continue
        x.loc[i,'material_grade_checked'] = '17-4PH'
        x.loc[i,'process_mapping_basis'] = 'Existing audited heat_history_note and sample mapping; see process_stages.csv'
        if doi == slm:
            x.loc[i,['manufacturing_route_checked','environment_family_checked','dataset_role']] = ['SLM','NaCl','17_4PH_NaCl_SLM_transfer_only']
            x.loc[i,['stress_relief_temperature_C','stress_relief_time_min','solution_temperature_C','solution_time_min']] = [650,60,1040,30]
            x.loc[i,['aging_temperature_C','aging_time_min']] = [r.heat_treatment_temperature_C,r.heat_treatment_time_min]
            x.loc[i,'solution_cooling_checked'] = 'air'
            x.loc[i,'aging_state_checked'] = 'aged'
        elif doi == sinter:
            x.loc[i,['manufacturing_route_checked','environment_family_checked','dataset_role']] = ['powder_sintered','H2SO4','17_4PH_acid_transfer_only']
            x.loc[i,['sintering_temperature_C','sintering_time_min']] = [1340,30]
            if str(r.source_sample_id).startswith('A '):
                x.loc[i,'aging_state_checked'] = 'explicitly_not_aged'
            else:
                import re
                t = float(re.search(r'solution-treated at (\d+)',r.source_sample_id)[1])
                x.loc[i,['solution_temperature_C','solution_time_min','aging_temperature_C','aging_time_min']] = [t,30,r.heat_treatment_temperature_C,60]
                x.loc[i,'solution_cooling_checked'] = 'oil'
                x.loc[i,'aging_state_checked'] = 'aged'
        else:
            x.loc[i,['manufacturing_route_checked','environment_family_checked']] = ['rolled_sheet','NaCl']
            x.loc[i,'dataset_role'] = 'development_external_already_examined'
            if r.evaluation_role == 'primary_aged':
                x.loc[i,['solution_temperature_C','solution_time_min','aging_temperature_C','aging_time_min']] = [1040,60,480,r.heat_treatment_time_min]
                x.loc[i,['solution_cooling_checked','aging_cooling_checked','aging_state_checked']] = ['water','air','aged']
            else:
                x.loc[i,'aging_state_checked'] = 'as_received_prior_history_unknown'
    return x

master = annotate(d)
ex = annotate(external, True)
focus = master[master.material_grade_checked.eq('17-4PH')].copy()
stages=[]
for r in pd.concat([focus,ex]).itertuples():
    sequence=[]
    if r.source_paper_id == sinter:
        sequence += [('debinding',400,60,'not_reported'),('sintering',1340,30,'controlled_10_C_min')]
    if r.source_paper_id == slm:
        sequence += [('stress_relief',650,60,'not_reported')]
    if pd.notna(r.solution_temperature_C):
        sequence += [('solution',r.solution_temperature_C,r.solution_time_min,r.solution_cooling_checked)]
    if pd.notna(r.aging_temperature_C):
        sequence += [('aging',r.aging_temperature_C,r.aging_time_min,r.aging_cooling_checked)]
    for order,(stage,t,minutes,cooling) in enumerate(sequence,1):
        stages.append(dict(record_id=r.record_id,source_paper_id=r.source_paper_id,stage_order=order,
            stage=stage,temperature_C=t,hold_min=minutes,cooling=cooling,
            source_url='https://doi.org/'+r.source_paper_id,evidence=r.heat_history_note,
            evidence_status='structured_from_existing_audited_source_history'))

# Source-level follow-up queue, never impute source values from other papers.
queue=[]
for doi,g in pd.concat([focus,ex]).groupby('source_paper_id',sort=False):
    for field in ['C','P','N','RE_ppm','pH','temperature_C','exposure_h']:
        n=int(g[field].isna().sum())
        if n:
            queue.append(dict(source_paper_id=doi,field=field,missing_rows=n,total_rows=len(g),
                action='Check supplementary material or obtain measurement; otherwise keep missing',
                source_url='https://doi.org/'+doi))

# Proposed first campaign: 480 C aging time-series, same heat and route, 3 independent coupons/condition.
# These are explicitly unmeasured plan rows and are NEVER included in training.
plan=[]
for condition,hours in enumerate([1,4,8,32],1):
    for rep in [1,2,3]:
        plan.append(dict(record_id=f'PLANNED_17_4PH_C{condition}_R{rep}',condition_id=f'C{condition}',replicate_id=rep,
            dataset_role='planned_unmeasured_never_train',material_grade='17-4PH',batch_id='',
            manufacturing_route='rolled_sheet_proposed',solution_temperature_C=1040,solution_time_min=60,
            solution_cooling='water_proposed',aging_temperature_C=480,aging_time_min=hours*60,
            aging_cooling='air_proposed',electrolyte_NaCl_wt_pct=3.5,
            temperature_C=np.nan,pH=np.nan,scan_rate_mV_s=1,ocp_stabilization_min=60,
            exposure_h=np.nan,surface_finish='',aeration='',exposed_area_cm2=np.nan,
            C=np.nan,Si=np.nan,Mn=np.nan,P=np.nan,S=np.nan,Cr=np.nan,Ni=np.nan,Mo=np.nan,Cu=np.nan,N=np.nan,
            icorr_A_cm2=np.nan,Ecorr_V=np.nan,Ecorr_reference='',
            plan_basis='Proposed replication of external-paper conditions, not reported new measurements',
            required_before_run='Set and record pH, test temperature, surface finish, aeration, area; measure batch composition'))

files={'adjusted_master_385.csv':master,'focused_17_4PH_15.csv':focus,
       'external_development_5.csv':ex,'process_stages.csv':pd.DataFrame(stages),
       'source_followup_queue.csv':pd.DataFrame(queue),'planned_experiments_12.csv':pd.DataFrame(plan)}
schema=[]
for field in ['material_grade_checked','manufacturing_route_checked','dataset_role','solution_cooling_checked','aging_cooling_checked','aging_state_checked']:
    schema.append(dict(field=field,type='categorical',use='candidate_input' if field!='dataset_role' else 'split_metadata_never_predictor',missing_policy='Explicit unknown; not zero'))
for field in ['stress_relief_temperature_C','stress_relief_time_min','sintering_temperature_C','sintering_time_min','solution_temperature_C','solution_time_min','aging_temperature_C','aging_time_min']:
    schema.append(dict(field=field,type='numeric',use='candidate_input',missing_policy='Missing and explicitly absent are distinct; never fill an absent stage with 0 C'))
schema.append(dict(field='log10_icorr_target',type='numeric',use='target_never_input',missing_policy='No target imputation'))
files['new_feature_schema.csv']=pd.DataFrame(schema)
for name,frame in files.items():
    frame.to_csv(OUT/name,index=False,encoding='utf-8-sig')
    assert len(pd.read_csv(OUT/name)) == len(frame)
pd.testing.assert_frame_equal(master[original.columns],original)
assert len(focus)==15 and focus.source_paper_id.nunique()==2
assert len(ex)==5 and len(plan)==12
assert pd.DataFrame(plan).icorr_A_cm2.isna().all()
assert hashlib.sha256(src.read_bytes()).hexdigest()==before
summary=dict(raw_rows=385,target_verified_rows=int(d.target_verified.fillna(False).astype(bool).sum()),
    focused_rows=15,focused_papers=2,SLM_NaCl_rows=9,sintered_acid_rows=6,
    confirmed_rolled_17_4PH_NaCl_training_rows=0,external_development_rows=5,
    structured_process_stage_rows=len(stages),planned_unmeasured_rows=12,
    existing_targets_unchanged=True,source_sha256=before,model_retrained=False)
(OUT/'validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
(OUT/'진행방법.md').write_text('''# 실험데이터 조정 및 다음 진행

기존 385행 원문값과 icorr를 모두 보존했다. 새로 측정한 실험값은 추가하지 않았다.

## 이번에 조정한 내용
- adjusted_master_385.csv: 기존 자료에 단계별 열처리 필드와 용도 분류를 추가. 17-4PH 두 논문의 15행만 기존 감사 기록으로 구조화했고 나머지는 not_reaudited로 보존.
- focused_17_4PH_15.csv: SLM/NaCl 9행과 분말소결/H2SO4 6행. 후자는 산성 환경 전이학습 후보이며 NaCl 전용 모델의 직접 동등자료가 아니다.
- process_stages.csv: 탈지, 소결, 응력제거, 용체화, 시효를 순서대로 표현. 각 행에 DOI와 기존 원문 근거를 붙임. 단계 미실시는 명시 상태로 표현하고 0도/0분을 만들지 않음.
- external_development_5.csv: 이미 성능을 확인한 외부 논문 5행. 최종 미관측 테스트로 재사용하지 않음.
- source_followup_queue.csv: 우선 확인할 미보고 조성·환경 조건. 미보고 RE를 0으로 처리하지 않음.

## 데이터 확보 우선순위
1. 압연/단조 17-4PH + NaCl 수용액 + 수치 icorr가 있는 독립 논문을 먼저 확보. 현재 확인된 동등 공정 학습자료는 0행이다.
2. 용체화 온도/시간/냉각과 시효 온도/시간/냉각이 각각 식별되는 조건을 수집. SLM 레이저 조건은 제조법과 함께 별도 입력으로 유지.
3. pH, 실제 부식시험 온도, 표면연마, 탈기, 노출면적, 침지시간, 주사속도, OCP 안정시간을 기록. 시험 전 측정 가능한 피처만 사용.
4. 원문값·단위변환·상한값·결측을 구별. A와 A/cm2, mV와 V를 점검하고 대표 평균을 반복시편으로 복제하지 않음.

## 직접 실험을 할 경우의 첫 설계
planned_experiments_12.csv는 실제 데이터가 아닌 제안서다. 동일 압연재 배치, 1040도 60분 수냉 후 480도 1/4/8/32시간 시효·공냉의 4조건에 독립 쿠폰 3개씩, 총 12시편이다. 기존 논문 비교를 위한 재현 설계이며 최적 조건임을 뜻하지 않는다.
온도·pH·연마·탈기·노출면적은 실행 전에 정해 기록한다. 각 시편의 실측 icorr를 독립적으로 기록하고 측정 전 정답 칸은 비운다. 조건 순서는 무작위화하고 동일 배치/조건/반복 ID를 보존한다. 재현 실험을 추가한 뒤 시효 온도 축 확장을 별도 설계한다.

## 모델 평가
기존 377행 SVR을 기준선으로 고정한다. 공정 필드가 추가된 모델은 별도 구현이 필요하며 기존 파이프라인은 새 열을 자동 사용하지 않는다. 동일 무작위 80:20 분리/seed 42에서 비교하되, 동일 배치·조건의 반복시편은 같은 쪽에 배치한다. 전처리와 튜닝은 학습 자료 안에서만 수행한다.
SVR/트리 기반 모델의 설정은 내부 검증으로 선택한다. 주 지표는 log10(icorr) R2, MAE, 기하평균 배수 오차 및 2배 이내 비율이다. 자료가 2개 논문 15행뿐인 현재 상태에서 이 부분집합의 점수로 일반화 성능을 주장하지 않는다.
이번 외부 논문은 개발용으로만 사용한다. 개선 모델을 고정한 후 별도로 확보한 새 논문을 최종 외부 검증에 쓴다. 적은 자료로 임의의 목표 R2나 성능 개선을 보장하지 않는다.
''',encoding='utf-8')
zip_path=ROOT/'output/data/process_adjusted_20261024.zip'
zip_path.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for p in OUT.iterdir():
        if p.is_file():z.write(p,p.name)
print(json.dumps(summary,indent=2))
print(zip_path)
