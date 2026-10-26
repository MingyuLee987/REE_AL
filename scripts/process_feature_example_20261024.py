"""Fixed-settings ablation: legacy vs stage-aware descriptors, same train rows."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np,pandas as pd
from sklearn.model_selection import train_test_split
from corrosion_ml.composition import CompositionDonorImputer
from corrosion_ml.features import CorrosionFeatures
from corrosion_ml.model import make_pre,BootstrapSVR
from corrosion_ml.experiments import metrics
from latest_external_validation_20261024 import prepare

EXTRA_NUM=['stress_relief_temperature_C','stress_relief_time_min','sintering_temperature_C','sintering_time_min','solution_temperature_C','solution_time_min','aging_temperature_C','aging_time_min','laser_power_W','laser_scan_speed_mm_s']
EXTRA_CAT=['material_grade_checked','manufacturing_route_checked','solution_cooling_checked','aging_cooling_checked','aging_state_checked']

def descriptors(d,donor,augmented):
    f=CorrosionFeatures().fit_transform(donor.transform(d))
    if augmented:
        for c in EXTRA_NUM:
            f['stage_'+c]=pd.to_numeric(d[c],errors='coerce') if c in d else np.nan
            if c.endswith('time_min'):
                f['stage_log1p_'+c]=np.log1p(f['stage_'+c])
        for c in EXTRA_CAT:
            f['stage_'+c]=d[c].fillna('not_reported').astype(str)
    return f

def fit_predict(train,test,augmented):
    train=prepare(train);test=prepare(test)
    donor=CompositionDonorImputer().fit(train)
    x=descriptors(train,donor,augmented);pre=make_pre(x)
    z=pre.fit_transform(x)
    m=BootstrapSVR(n_members=2,seed=42).fit(z,np.log10(train.icorr_A_cm2))
    pred=m.predict(pre.transform(descriptors(test,donor,augmented)))
    return pred

def main():
    out=ROOT/'results/process_feature_example_20261024';out.mkdir(parents=True,exist_ok=True)
    raw=pd.read_csv(ROOT/'data/process_adjusted_20261024/adjusted_master_385.csv',float_precision='round_trip')
    d=raw[raw.target_verified.fillna(False).astype(bool)&raw.icorr_A_cm2.gt(0)].reset_index(drop=True)
    ext=pd.read_csv(ROOT/'data/process_adjusted_20261024/external_development_5.csv',float_precision='round_trip')
    ext=ext[ext.evaluation_role.eq('primary_aged')].reset_index(drop=True)
    ext['steel_family']='스테인리스강'
    assert set(d.source_paper_id).isdisjoint(set(ext.source_paper_id))
    tr,te=train_test_split(np.arange(len(d)),test_size=.2,random_state=42)
    summary=dict(n_training_corpus=len(d),n_holdout=len(te),n_external=len(ext),
        protocol='Same random 80:20 seed42; fixed SVR C10 epsilon0.15 gamma=scale; no hyperparameter selection',
        external_status='Previously examined development paper; not a fresh blind test',
        newly_measured_data=0,production_model_changed=False,extra_numeric=EXTRA_NUM,extra_categorical=EXTRA_CAT,results={})
    outputs=[]
    for name,aug in [('baseline',False),('stage_aware',True)]:
        hold=fit_predict(d.iloc[tr],d.iloc[te],aug)
        external=fit_predict(d,ext,aug)
        summary['results'][name]=dict(random_holdout=metrics(np.log10(d.iloc[te].icorr_A_cm2),hold),
            external_development=metrics(np.log10(ext.icorr_A_cm2),external))
        for evaluation,frame,pred in [('random_holdout',d.iloc[te],hold),('external_development',ext,external)]:
            r=frame[['record_id','source_paper_id','source_sample_id','icorr_A_cm2']].copy()
            r['model']=name;r['evaluation']=evaluation;r['predicted_A_cm2']=10.**pred
            r['absolute_fold_error']=10.**abs(pred-np.log10(r.icorr_A_cm2))
            outputs.append(r)
        print(name,json.dumps(summary['results'][name]),flush=True)
    predictions=pd.concat(outputs,ignore_index=True)
    predictions.to_csv(out/'predictions.csv',index=False,encoding='utf-8-sig')
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    rows=predictions[predictions.evaluation.eq('external_development')]
    print(rows[['model','source_sample_id','icorr_A_cm2','predicted_A_cm2','absolute_fold_error']].to_string(index=False))
    lines=['# 단계별 열처리 피처 추가 예시','',
        '기존 377행과 같은 무작위 80:20 분리(seed42), 같은 SVR 설정으로 비교했다. 새 측정값은 추가하지 않았다.',
        '추가한 단계별 정보는 감사된 17-4PH 15행에서만 제공된다. 다른 행은 미확인 상태이며 추정 매핑을 하지 않았다.',
        '학습 쪽의 17-4PH는 SLM/NaCl 또는 소결/황산이며 외부 압연재/NaCl과 다르다. 외부의 8/32시간 시효는 SLM 학습 최대 4시간을 넘는다.',
        '외부 논문은 이미 확인한 개발용 검증자료다. 모델 개선이나 새로운 독립 검증 성공으로 단정하지 않는다.']
    for name,res in summary['results'].items():
        a=res['random_holdout'];b=res['external_development']
        lines.append(f"\n{name}: 무작위 test log R2={a['r2_log10']:.6f}; 외부 log R2={b['r2_log10']:.6f}; 외부 기하평균 배수오차={b['geometric_mean_fold_error']:.3f}")
    lines += ['', '이 예시는 데이터 표현 추가의 효과를 확인하는 고정 설정 비교다. 제조법별 겹치는 관측이 부족하므로 용체화 시간/냉각 효과를 식별했다고 주장하지 않는다. 다음은 압연 17-4PH/NaCl의 같은 범위 실측값을 확보하고 새 논문을 따로 남겨 검증한다.']
    (out/'결과설명.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':main()
