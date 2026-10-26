"""Build traceable CSVs from independently reviewed primary-paper extractions."""
import hashlib
import json
import sys
import numpy as np
import pandas as pd
from collect_grain_size import ROOT, key, save_json
from expand_heat_treatment_data import OUT,FIELDS,TEXT,candidate_target
from build_al_dataset import CORE, impute_composition
from sklearn.model_selection import GroupKFold

DEST=ROOT/'data/al_heat_expanded_20261023'
OLD=ROOT/'data/al_curated_20261023'
PROCESS=['heat_treatment_temperature_C','heat_treatment_time_min']
CONDITIONS='electrolyte_condition_cat temperature_C temperature_condition_cat pH exposure_h scan_rate_mV_s ocp_stabilization_min'.split()
PREDICTORS=CORE+['RE_ppm','RE_element_cat']+CONDITIONS+PROCESS

def main():
    global DEST
    if '--round2' in sys.argv:DEST=ROOT/'data/al_heat_expanded_round2_20261023'
    if '--round3' in sys.argv:DEST=ROOT/'data/al_heat_expanded_round3_20261023'
    if '--round4' in sys.argv:DEST=ROOT/'data/al_heat_expanded_round4_20261023'
    sys.stdout.reconfigure(encoding='utf-8');DEST.mkdir(parents=True,exist_ok=True)
    candidate_frames=[pd.read_csv(ROOT/'data/literature/icorr_candidates.csv',float_precision='round_trip')]
    round_number=4 if '--round4' in sys.argv else (3 if '--round3' in sys.argv else (2 if '--round2' in sys.argv else 1))
    candidate_frames += [pd.read_csv(OUT/f'round{r}_candidates.csv',float_precision='round_trip') for r in range(2,round_number+1) if (OUT/f'round{r}_candidates.csv').exists()]
    if round_number>=4 and (OUT/'round4_extra_candidates.csv').exists():
        candidate_frames.append(pd.read_csv(OUT/'round4_extra_candidates.csv',float_precision='round_trip'))
    if round_number>=4 and (OUT/'round4_more_candidates.csv').exists():
        candidate_frames.append(pd.read_csv(OUT/'round4_more_candidates.csv',float_precision='round_trip'))
    if round_number>=4 and (OUT/'round4_ce_candidates.csv').exists():
        candidate_frames.append(pd.read_csv(OUT/'round4_ce_candidates.csv',float_precision='round_trip'))
    candidates=pd.concat(candidate_frames,ignore_index=True).drop_duplicates('record_id').set_index('record_id')
    rows=[];provenance=[];rejected=[];papers=[]
    for f in sorted((OUT/'extractions').glob('*.json')):
        ex=json.loads(f.read_text(encoding='utf-8'));reviewfile=OUT/'reviews'/f.name
        if ex.get('records') and not any(r['candidate_id'] in candidates.index for r in ex['records']):continue
        review=json.loads(reviewfile.read_text(encoding='utf-8')) if reviewfile.exists() else {}
        decisions={r['candidate_id']:r for r in review.get('reviews',[])}
        review_method=review.get('review_method','exact_quote_plus_independent_API_review')
        papers.append(dict(source_paper_id=ex['doi'],title=ex['title'],extracted_records=len(ex.get('records',[])),extraction_error=ex.get('error',''),retry_partial_failure=bool(ex.get('retry_partial_failure',False)),review_available=bool(reviewfile.exists())))
        for rec in ex.get('records',[]):
            cid=rec['candidate_id'];v=decisions.get(cid,{})
            if cid not in candidates.index:continue
            reason=''
            if any(t in ex['title'].lower() for t in ['ion implantation','laser surface alloying','post-deposition aluminizing','laser remelted','surface-grinding','femtosecond laser']):reason='Surface modification requires additional process features; outside composition plus thermal-pair scope'
            elif v.get('decision')!='accept' or v.get('protocol_ambiguity'):reason=v.get('reason','No accepting independent review')
            elif not rec.get('candidate_exists') or not rec.get('target_quote_verified'):reason='Target evidence failed exact-quote check'
            elif rec['steel_family']=='other_ferrous':reason='Other ferrous alloy/intermetallic, outside steel scope'
            if reason:
                rejected.append(dict(source_paper_id=ex['doi'],candidate_id=cid,reason=reason));continue
            c=candidates.loc[cid]
            target_value,target_factor,header_fixed=candidate_target(c,ex['doi'])
            if target_value is None or not np.isclose(target_value,float(rec['target_value_A_cm2']),rtol=1e-5,atol=0):
                rejected.append(dict(source_paper_id=ex['doi'],candidate_id=cid,reason='Candidate target mismatch'));continue
            row={f:np.nan for f in FIELDS}
            row.update({f:'' for f in TEXT})
            row.update(record_id='HEAT_'+cid,source_paper_id=ex['doi'],source_sample_id=rec['sample_label'],source_url='https://doi.org/'+ex['doi'],icorr_A_cm2=target_value,target_verified=True,target_review_status=review_method,target_source_location=rec['target_location'],seed_origin='new_heat_API_collection',steel_family='스테인리스강' if rec['steel_family']=='stainless_steel' else '일반·합금강',heat_treatment_stage=rec['heat_stage'],heat_history_note=rec['heat_history_note'],thermal_history_incomplete=v['thermal_history_incomplete'],protocol_ambiguity=False,composition_uses_assumptions=False,composition_input_basis='source_specific_see_provenance')
            seen={};invalid=set(v.get('invalid_attribute_indices',[]))
            for j,a in enumerate(rec['attributes']):
                field=a['field']
                # Manually checked primary Tables 1: feedstock chemistry is a
                # useful pre-manufacture proxy, explicitly NOT a bulk assay.
                proxy_tables={
                    '10.3390/ma17122807':dict(C=.016,Si=.3,Mn=.4,P=.024,S=.001,Cr=25.2,Ni=6.3,Mo=3.8,Cu=.15,N=.35),
                    '10.1038/s41598-024-75382-5':dict(C=.029,Si=.45,Mn=1.06,P=.02,S=.002,Cr=19.5,Ni=9.75)}
                proxy=field in proxy_tables.get(ex['doi'],{}) and a['value'] is not None and np.isclose(a['value'],proxy_tables[ex['doi']][field],rtol=1e-10,atol=0)
                if (j in invalid and not proxy) or not a['quote_verified']:continue
                value=a['text'] if field in TEXT else a['value']
                if field in CORE+['Nb','Ti','V','Al','Co','B','W','Sn','Sb','Ce','La','Y'] and a['unit'].lower().replace(' ','') not in ['wt.%','wt%','weight%','wt.percent','mass%','mass.%','%','wt.%(%mass)','wt.%/mass%']:
                    continue
                if a['basis'] in ['upper_bound','range'] or (field in FIELDS and value is None and (a['upper'] is not None or a['lower'] is not None)):
                    if a['upper'] is not None:row[field+'_upper_bound']=a['upper']
                    if a['lower'] is not None:row[field+'_lower_bound']=a['lower']
                    value=np.nan
                if field in seen and str(seen[field])!=str(value):
                    row[field]='' if field in TEXT else np.nan
                    seen[field]='CONFLICT';continue
                if seen.get(field)=='CONFLICT':continue
                seen[field]=value;row[field]=value
                if a['basis'] in ['nominal','same_paper_parent_proxy']:row['composition_uses_assumptions']=True
                if proxy:
                    row['composition_input_basis']='feedstock_proxy_not_bulk_assay';row['composition_uses_assumptions']=True
                provenance.append(dict(record_id=row['record_id'],source_paper_id=ex['doi'],field=field,value=value,basis='same_paper_feedstock_proxy' if proxy else a['basis'],unit=a['unit'],quote=a['quote'],location=a['location'],lower=a['lower'],upper=a['upper'],method='manual_verified_Table1_feedstock_proxy' if proxy else review_method,manual_correction_note=a.get('manual_correction_note','')))
            if any(pd.isna(row.get(f)) for f in PROCESS):
                rejected.append(dict(source_paper_id=ex['doi'],candidate_id=cid,reason='Thermal pair absent after attribute review'));continue
            rows.append(row)
            provenance.append(dict(record_id=row['record_id'],source_paper_id=ex['doi'],field='icorr_A_cm2',value=row['icorr_A_cm2'],basis='reported',unit='A/cm2',quote=rec['target_quote'],location=rec['target_location'],method='source_header_unit_parser_recovery_and_independent_API_review' if header_fixed else review_method,reported_value=c.icorr_reported,reported_header=c.target_header,conversion_factor=target_factor))
    new=pd.DataFrame(rows).drop_duplicates('record_id') if rows else pd.DataFrame(columns=['record_id','source_paper_id']+FIELDS+TEXT)
    oldraw=pd.read_csv(OLD/'al_labeled_raw.csv',float_precision='round_trip')
    raw=pd.concat([oldraw,new],ignore_index=True)
    raw['heat_treatment_stage']=raw.get('heat_treatment_stage',pd.Series(index=raw.index,dtype=object))
    stage_map={'10.3390/ma15248780':'solution_treatment','10.3390/ma18081823':'aging','10.3390/ma19122685':'billet_reheating','10.1186/s40712-025-00240-9':'annealing','10.1038/s41598-026-65428-1':'sintering','10.3390/ma18122722':'HIP_sintering'}
    raw['heat_treatment_stage']=raw.heat_treatment_stage.fillna(raw.source_paper_id.map(stage_map))
    # Collapse only exact same-paper sample/condition/target duplicates, never arbitrary equal target values.
    sigcols=['source_paper_id','source_sample_id','icorr_A_cm2']+PROCESS+CONDITIONS
    duplicate=raw.duplicated(sigcols,keep='first');raw.loc[duplicate].to_csv(DEST/'duplicates_removed.csv',index=False,encoding='utf-8-sig');raw=raw.loc[~duplicate].reset_index(drop=True)
    prepared=raw.copy();limits=[]
    for i,r in raw.iterrows():
        for element in CORE:
            if pd.notna(r[element]):continue
            lo=r.get(element+'_lower_bound',np.nan);hi=r.get(element+'_upper_bound',np.nan)
            if pd.notna(hi):
                value=(lo+hi)/2 if pd.notna(lo) else hi/2
                prepared.loc[i,element]=value;prepared.loc[i,'composition_uses_assumptions']=True
                limits.append(dict(record_id=r.record_id,source_paper_id=r.source_paper_id,element=element,value=value,method='reported_range_midpoint_assumption' if pd.notna(lo) else 'reported_limit_half_assumption'))
    # Preserve the earlier explicitly documented manufacturer Mo upper-limit proxy.
    m=prepared.source_paper_id.eq('10.3390/ma18081823')&prepared.Mo.isna()
    prepared.loc[m,'Mo']=.30
    ref=pd.read_csv(OLD/'composition_reference_source_values.csv',float_precision='round_trip')
    reference=pd.concat([prepared[['record_id','source_paper_id','steel_family']+CORE],ref],ignore_index=True).drop_duplicates('record_id',keep='first')
    reference=reference[reference[CORE].notna().sum(axis=1).ge(3)]
    querycols=['record_id','source_paper_id','steel_family']+CORE+[c for c in prepared if c.endswith('_upper_bound')]
    filled,logs=impute_composition(prepared[querycols],reference)
    result=prepared.copy();result[CORE]=filled[CORE]
    result['composition_statistically_filled_count']=sum(prepared[c].isna()&result[c].notna() for c in CORE)
    result['composition_uses_assumptions']=result.composition_uses_assumptions.fillna(False)|result.composition_statistically_filled_count.gt(0)
    result['composition_missing_count']=result[CORE].isna().sum(axis=1)
    result['thermal_pair_available']=result[PROCESS].notna().all(axis=1)
    result['checked_heat_label_available']=result.target_verified.fillna(False)&result.thermal_pair_available
    tempinfo=result.temperature_C.notna()|result.temperature_condition_cat.fillna('').str.contains('ambient|room',case=False,regex=True)
    electrolyte=result.electrolyte_condition_cat.fillna('').ne('')
    result['core_conditions_complete']=result.checked_heat_label_available&result.composition_missing_count.eq(0)&tempinfo&electrolyte&result.scan_rate_mV_s.notna()
    result['composition_input_basis']=result.composition_input_basis.fillna('legacy_source_proxy_or_estimate')
    meta=['record_id','source_paper_id','source_sample_id','source_url','seed_origin','target_verified','target_review_status','heat_treatment_stage','heat_history_note','thermal_history_incomplete','composition_input_basis','composition_uses_assumptions','composition_statistically_filled_count','composition_missing_count','thermal_pair_available','checked_heat_label_available','core_conditions_complete']
    selected=result[meta+PREDICTORS+['icorr_A_cm2']]
    selected.to_csv(DEST/'al_labeled_heat_treatment_expanded.csv',index=False,encoding='utf-8-sig')
    selected[selected.checked_heat_label_available].to_csv(DEST/'al_heat_checked_labels.csv',index=False,encoding='utf-8-sig')
    selected[selected.core_conditions_complete].to_csv(DEST/'al_heat_core_review.csv',index=False,encoding='utf-8-sig')
    obsolete=DEST/'al_heat_complete_review.csv'
    if obsolete.exists():obsolete.unlink()
    selected[~selected.target_verified.fillna(False)].to_csv(DEST/'quarantine_legacy_targets.csv',index=False,encoding='utf-8-sig')
    raw.to_csv(DEST/'source_only_before_composition_imputation.csv',index=False,encoding='utf-8-sig')
    prepared.to_csv(DEST/'before_statistical_imputation.csv',index=False,encoding='utf-8-sig')
    reference.to_csv(DEST/'composition_reference_source_values.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(provenance).to_csv(DEST/'new_source_provenance.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(rejected).to_csv(DEST/'rejected_or_unresolved.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(logs).to_csv(DEST/'composition_imputation_log.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(limits).to_csv(DEST/'composition_limit_assumptions.csv',index=False,encoding='utf-8-sig')
    inventory=pd.DataFrame(papers);counts=new.groupby('source_paper_id').size() if len(new) else pd.Series(dtype=int)
    inventory['accepted_added_rows']=inventory.source_paper_id.map(counts).fillna(0).astype(int)
    inventory.to_csv(DEST/'paper_inventory.csv',index=False,encoding='utf-8-sig')
    missing=pd.DataFrame([dict(field=c,source_missing=int(raw[c].isna().sum()) if c in FIELDS else int(raw[c].fillna('').eq('').sum()),prepared_missing=int(selected[c].isna().sum()) if c in FIELDS else int(selected[c].fillna('').eq('').sum()),prepared_missing_pct=round((selected[c].isna().mean() if c in FIELDS else selected[c].fillna('').eq('').mean())*100,2)) for c in PREDICTORS])
    missing.to_csv(DEST/'missingness.csv',index=False,encoding='utf-8-sig')
    # Imputation reference for each fold excludes ALL held-out paper rows before IQR/donor selection.
    folds=[]
    for fold,(tr,te) in enumerate(GroupKFold(5).split(prepared,groups=prepared.source_paper_id)):
        held=set(prepared.iloc[te].source_paper_id);rr=reference[~reference.source_paper_id.isin(held)]
        ff,ll=impute_composition(prepared[querycols],rr)
        assert all(not(set(json.loads(x['donor_papers']))&held) for x in ll)
        folddata=prepared[['record_id','source_paper_id']+PREDICTORS+['icorr_A_cm2','target_verified']].copy();folddata[CORE]=ff[CORE]
        folddata['role']='train';folddata.loc[te,'role']='test'
        folddata.to_csv(DEST/f'paper_group_fold_{fold}.csv',index=False,encoding='utf-8-sig')
        pd.DataFrame(ll).to_csv(DEST/f'fold_{fold}_imputation_log.csv',index=False,encoding='utf-8-sig')
        folds.append(dict(fold=fold,held_out_papers=len(held),test_rows=len(te),no_held_out_donors=True))
    save_json(DEST/'feature_schema.json',dict(predictor_columns=PREDICTORS,numeric_process_features=PROCESS,target='log10(icorr_A_cm2)',split_group='source_paper_id',metadata_not_predictors=meta,grain_and_phase_used=False,globally_filled_file_for_review_only=True,requires_fold_specific_imputation=True))
    summary=dict(original_rows=len(oldraw),added_rows=len(new),expanded_rows=len(result),expanded_papers=result.source_paper_id.nunique(),new_papers=new.source_paper_id.nunique() if len(new) else 0,screened_new_papers=len(inventory),checked_target_and_heat_rows=int(result.checked_heat_label_available.sum()),core_conditions_complete_review_rows=int(result.core_conditions_complete.sum()),core_conditions_complete_papers=result.loc[result.core_conditions_complete,'source_paper_id'].nunique(),all_selected_predictors_present_rows=int(selected[PREDICTORS].replace('',np.nan).notna().all(axis=1).sum()),missing_temperature_time_rows=int((~result.thermal_pair_available).sum()),missing_temperature_time_pct=round((~result.thermal_pair_available).mean()*100,2),legacy_unverified_targets=int((~result.target_verified.fillna(False)).sum()),statistically_imputed_cells=len(logs),fold_checks=folds,model_retrained=False,source_target_never_imputed=True)
    summary.update(test_temperature_information_missing_rows=int((~tempinfo).sum()),new_rows_with_explicit_positive_RE_ppm=int(new.RE_ppm.gt(0).sum()) if 'RE_ppm' in new else 0)
    save_json(DEST/'summary.json',summary)
    if round_number>=2:
        previous_dir='al_heat_expanded_round3_20261023' if round_number==4 else ('al_heat_expanded_round2_20261023' if round_number==3 else 'al_heat_expanded_20261023')
        previous=pd.read_csv(ROOT/'data'/previous_dir/'al_labeled_heat_treatment_expanded.csv',float_precision='round_trip')
        added_mask=~selected.record_id.isin(previous.record_id)
        selected.loc[added_mask].to_csv(DEST/'new_rows_this_round.csv',index=False,encoding='utf-8-sig')
        assert set(previous.record_id)<=set(selected.record_id)
        assert np.array_equal(selected.set_index('record_id').loc[previous.record_id,'icorr_A_cm2'].to_numpy(),previous.icorr_A_cm2.to_numpy())
        summary.update(previous_expanded_rows=len(previous),added_this_round_rows=int(added_mask.sum()),added_this_round_papers=int(selected.loc[added_mask,'source_paper_id'].nunique()),added_this_round_positive_RE_rows=int(selected.loc[added_mask,'RE_ppm'].gt(0).sum()),previous_targets_preserved=True)
        save_json(DEST/'summary.json',summary)
    publisher=json.loads((OUT/'publisher_api_status.json').read_text(encoding='utf-8'))
    save_json(DEST/'publisher_api_status.json',publisher)
    save_json(DEST/'additional_source_access_status.json',json.loads((OUT/'elsevier_fulltext_status.json').read_text(encoding='utf-8')) if (OUT/'elsevier_fulltext_status.json').exists() else [])
    readme=f'''# 열처리 온도·시간 피처를 사용하는 문헌 시험데이터 확장

기존 {len(oldraw)}행에 원문 근거와 API 보조 재검토 또는 원문 직접 대조를 통과한 {len(new)}행을 추가했습니다. 전체 {len(result)}행, {result.source_paper_id.nunique()}개 출처입니다. 이는 서로 다른 논문 수나 독립 반복실험 수와 같은 의미가 아닙니다. 각 행의 실제 검토 방식은 target_review_status와 provenance의 method를 확인하세요.

## 사용할 파일

- al_labeled_heat_treatment_expanded.csv: 기존 행을 보존한 전체 검토본. 미검증 기존 타깃도 상태 표시와 함께 보존합니다.
- al_heat_checked_labels.csv: icorr 타깃과 열처리 온도·시간을 확인한 {int(result.checked_heat_label_available.sum())}행. 조성·시험조건 결측은 남아 있습니다.
- al_heat_core_review.csv: 조성 10개와 전해질·시험온도 정보(명시된 실온 포함)·주사속도까지 확보/보완한 {int(result.core_conditions_complete.sum())}행. 조성 추정값이 포함되므로 모두 실측 완전자료라는 뜻은 아닙니다. pH·침지시간·OCP·RE 등의 결측도 별도로 확인해야 합니다. 모든 선택 피처가 완비됐다는 의미가 아닙니다.
- source_only_before_composition_imputation.csv: 조성 통계 보완 전 자료와 출처 정보. 기존 45행의 원문/proxy 이력은 이전 data/al_curated_20261023/source_and_proxy_provenance.csv도 함께 참조합니다.
- paper_group_fold_*.csv: 해당 fold의 검증 논문을 조성 donor와 IQR 산정에서 제외한 데이터. target_verified와 열처리 조건을 확인한 뒤 사용해야 하며, 이 파일 자체가 성능 검증 결과는 아닙니다.

## 실제 피처

공정 피처는 heat_treatment_temperature_C와 heat_treatment_time_min 두 개뿐입니다. 결정립 크기·상·냉각방법·압연·용접 피처는 모델 입력에서 제외했습니다. 모든 입력 컬럼은 feature_schema.json의 predictor_columns에 명시했습니다. source_paper_id, heat_treatment_stage, heat_history_note, 검토/추정 상태 등은 출처·감사 메타데이터이며 피처가 아닙니다.

온도·시간 두 값만으로 다단계 이력을 완전히 표현할 수 없습니다. 신규 추출은 마지막 명시적 등온 유지단계를 선택하고 앞선 이력을 메타데이터에 기록했습니다. 기존 자료는 이전에 확인한 단계를 보존합니다. 예를 들어 ma15248780은 용체화, ma18081823은 시효, ma19122685는 압연 전 빌릿 재가열입니다. 따라서 서로 다른 처리 단계를 단순히 동일한 열처리로 해석해서는 안 됩니다. 같은 강종·같은 열처리 단계·같은 시험환경에 한정한 AL을 우선 권장합니다.

## 수집·검증과 결측 보완

추가 문헌 {len(inventory)}편을 처리했습니다. OpenAI API로 원문 표·실험조건을 추출하고, 별도 모델 호출로 단위·시편·타깃·온도/시간 연결을 재검토했습니다. 인용문이 실제 확보한 본문에 그대로 존재하는지도 코드로 확인했습니다. 이는 API 보조 검증이며 사람이 모든 원문을 독립 검토한 자료라고 주장하지 않습니다. 모든 신규 값의 인용문·원문 위치·원래 단위는 new_source_provenance.csv에 있습니다. 억제제·코팅·비철/금속간화합물·미처리 시편의 미보고 열처리값·부식률/부동태전류 등은 추가하지 않았습니다.

열처리 온도·시간과 icorr는 추정하지 않았습니다. 조성은 제공 PDF의 정책에 따라 원문/동일 논문 모재를 우선하고, 상한의 1/2 또는 범위 중간값을 명시적 가정으로 구분합니다. 사전 입력이라는 목적에 맞춰 ma17122807의 분말 조성과 s41598-024-75382-5의 와이어 조성을 Table 1에서 직접 확인하여 feedstock proxy로 보존했습니다. 이는 PDF의 모재 proxy 원칙을 원료에 확장한 선택이며 제조 후 벌크 실측값이 아닙니다. composition_input_basis와 provenance의 manual_verified_Table1_feedstock_proxy로 구분합니다. 그 외 API 검토에서 거절된 조성을 임의 복구하지 않았습니다. 나머지는 같은 강종 계열, 관측 원소 2개 이상 겹침, IQR 거리 기준 3–5개 다른 논문의 중앙값을 사용합니다. donor가 3개 미만이면 결측으로 둡니다. 타깃은 조성 보완에 전달하지 않습니다. 통계 추정 조성을 재차 donor로 넣지 않습니다.

전체 검토본의 조성 보완값은 독립 검증에 바로 사용하면 안 됩니다. 논문 단위로 분리한 뒤 fold별 보완값을 사용해야 합니다. RE 첨가량과 실제 잔류량/분석 조성은 제조 전에 동일하게 알려지는 정보가 아니므로, 실제 AL 후보에는 명목 배합과 잔류 분석값의 구분이 추가로 필요합니다. RE 미보고를 0으로 채우지 않았습니다.

## 접근 제한과 원문 충돌

Elsevier 검색 API는 단순 검색식 재시도로 20건의 메타데이터를 받았으나, 추가 15편의 FULL 원문 요청은 HTTP 403이었습니다. Springer metadata/OA는 HTTP 403이었습니다. Wiley TDM은 10.1002/eng2.12105 PDF를 받았습니다. 이 논문은 방법의 H2SO4 0.05 M과 결과/표의 2 M 표기가 충돌하여 새 학습행으로 추가하지 않았습니다. 접근하지 못한 원문 수치를 추측해 채우지 않았습니다.

온도·시간 결측은 전체 검토본에서 각각 {int((~result.thermal_pair_available).sum())}/{len(result)}행({summary['missing_temperature_time_pct']}%)입니다. 나머지 피처 결측률은 missingness.csv를 확인하세요. 기존 운영 모델과 data/training.csv는 수정하거나 재학습하지 않았습니다.

추가 {len(new)}행은 일반강·스테인리스강의 열처리/부식 시험 확장입니다. 이 추가분에서 명시적인 RE_ppm > 0인 행은 {summary['new_rows_with_explicit_positive_RE_ppm']}행입니다. 이를 RE 첨가 내부식강 시험을 {len(new)}행 새로 확보했다는 의미로 해석하면 안 됩니다. 숫자 시험온도 또는 명시된 실온/주변온도 정보가 모두 없는 행은 전체 {summary['test_temperature_information_missing_rows']}행입니다.
'''
    (DEST/'README.md').write_text(readme,encoding='utf-8')
    if '--round2' in sys.argv:
        addition=f'''\n## 이번 추가 수집분\n\n이전 확장본 {summary['previous_expanded_rows']}행에서 {summary['added_this_round_rows']}행을 추가하여 {len(result)}행으로 확장했습니다. 이번 추가분은 {summary['added_this_round_papers']}개 출처이며 new_rows_this_round.csv에서 따로 볼 수 있습니다. 이번 추가분의 RE_ppm > 0 행은 {summary['added_this_round_positive_RE_rows']}행입니다.\n\n이번 수집은 새로 확보한 공개 원문/PDF와 추가 API 추출·재검토를 사용했습니다. 표뿐 아니라 본문에 시편별 icorr 수치가 명시된 경우도 포함했습니다. 예를 들어 10.3390/met15090935의 Q/YQ/QT/YQT 값은 PDF 10쪽 본문에 직접 보고되어 있어 곡선을 디지타이징하지 않았습니다. Y 함량 0.014 wt.%는 140 ppm으로 단위 변환했으며 원문의 nominal 표기를 실제 잔류량 실측으로 단정하지 않습니다.\n\n10.3390/ma16020876의 CGHAZ 시험은 1320 C/2 s가 확인되지만 Table 4 전류 단위가 A·cm2로 표기되어 있어 재검토에서 보류했습니다. Al+Ca+Zr+Ti+RE 합계 0.04 wt.%를 RE 단독 함량으로 취급하지 않았습니다. 원문 표 없이 곡선만 제공하는 연구, 전극 면적으로 정규화되지 않은 A 단위 전류는 포함하지 않았습니다.\n'''
        with (DEST/'README.md').open('a',encoding='utf-8') as stream:stream.write(addition)
    if '--round3' in sys.argv:
        addition=f'''\n## 3차 추가 수집\n\n직전 179행 자료를 보존한 별도 버전입니다. 이번에 {summary['added_this_round_papers']}개 출처의 {summary['added_this_round_rows']}행을 추가했으며, new_rows_this_round.csv에서 추가분만 볼 수 있습니다. 희토류 첨가 여부로 제한하지 않고 탄소강·저합금강·스테인리스강·공구강의 실제 시험을 대상으로 했습니다. 공정 피처는 온도와 유지시간 두 개로 유지했습니다.\n\nAPI로 출처와 단위·시편 대응을 검토하고, 원문에 보고된 조성 및 시험조건을 우선 보존했습니다. 문헌 수와 시험행 수는 다르며, 표의 표준편차나 같은 기준 시편의 반복 인용을 독립 실험행으로 세지 않았습니다. 타깃과 온도·시간을 통계적으로 채우지 않았습니다. 원문 접근과 후보 발견 이력은 outputs/heat_expansion_round3_20261023/에 있습니다.\n\n앞서 생성한 열처리 방법 PDF의 179행 집계는 2차 수집 시점의 기록이며, 이번 CSV 집계와 버전이 다릅니다.\n'''
        with (DEST/'README.md').open('a',encoding='utf-8') as stream:stream.write(addition)
    if '--round4' in sys.argv:
        addition=f'''\n## 300행 목표 추가 수집\n\n직전 237행 자료를 보존한 별도 버전입니다. 이번에 {summary['added_this_round_papers']}개 출처의 {summary['added_this_round_rows']}행을 추가하여 전체 {len(result)}행을 만들었습니다. 열처리 쌍과 타깃을 확인한 행은 {summary['checked_target_and_heat_rows']}행입니다. 전체 검토본과 확인본의 행 수를 혼용하지 않습니다. 이번 추가분만 보려면 new_rows_this_round.csv를 사용하세요.\n\n희토류 첨가 강재를 우선 확인하되 일반 철강의 열처리·전기화학 시험도 포함했습니다. 그래프만 제공된 수치를 임의 추정하거나 미보고 조건을 복제하여 행 수를 늘리지 않았습니다. 문헌 원문 수집·소규모 API 추출 이력은 outputs/heat_expansion_round4_20261023/에 있습니다.\n\n앞서 생성한 열처리 방법 PDF의 179행 집계는 당시의 이력입니다. 현재 CSV의 집계는 이 폴더의 summary.json과 missingness.csv를 기준으로 합니다. 모델은 이번 자료로 재학습하지 않았습니다.\n'''
        with (DEST/'README.md').open('a',encoding='utf-8') as stream:stream.write(addition)
    checks=dict(positive_targets=bool(result.icorr_A_cm2.gt(0).all()),unique_record_ids=bool(result.record_id.is_unique),process_features_exactly_two=True,all_added_rows_have_thermal_pairs=bool(result.loc[result.seed_origin.eq('new_heat_API_collection'),PROCESS].notna().all().all()),original_45_targets_unchanged=bool(np.array_equal(result.set_index('record_id').loc[oldraw.record_id,'icorr_A_cm2'].to_numpy(),oldraw.icorr_A_cm2.to_numpy())),production_training_sha256=hashlib.sha256((ROOT/'data/training.csv').read_bytes()).hexdigest(),production_model_sha256=hashlib.sha256((ROOT/'models/svr.joblib').read_bytes()).hexdigest())
    assert checks['positive_targets'] and checks['unique_record_ids'] and checks['all_added_rows_have_thermal_pairs'] and checks['original_45_targets_unchanged']
    save_json(DEST/'validation.json',checks)
    # Key values must not appear anywhere in generated deliverables.
    from collect_grain_size import env
    secrets=[v for k,v in env().items() if any(x in k for x in ['KEY','TOKEN']) and len(v)>12]
    assert all(not any(secret in p.read_text(encoding='utf-8-sig') for secret in secrets) for p in DEST.iterdir() if p.suffix in ['.csv','.json','.md'])
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
