"""Literature-informed random holdout, train-only CV model selection."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np,pandas as pd
from sklearn.model_selection import train_test_split,KFold
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from corrosion_ml.composition import CompositionDonorImputer
from corrosion_ml.features import CorrosionFeatures
from corrosion_ml.model import make_pre
from corrosion_ml.experiments import metrics
from latest_external_validation_20261024 import prepare

def candidates():
    return [(f'SVR_C{c}',lambda c=c:SVR(C=c,epsilon=.15,gamma='scale')) for c in [1,10,100]]+[(f'RF_leaf{l}',lambda l=l:RandomForestRegressor(n_estimators=200,min_samples_leaf=l,random_state=42,n_jobs=-1)) for l in [1,3]]+[(f'Ridge_a{a}',lambda a=a:Ridge(alpha=a)) for a in [1,10,100]]

def transform(train,test):
    donor=CompositionDonorImputer().fit(train)
    f=CorrosionFeatures()
    x=f.fit_transform(donor.transform(train));pre=make_pre(x)
    z=pre.fit_transform(x);zt=pre.transform(f.transform(donor.transform(test)))
    assert set(donor.pool_.record_id).issubset(set(train.record_id))
    return z,zt

def main():
    out=ROOT/'results/reference_protocol_20261024';out.mkdir(parents=True,exist_ok=True)
    raw=pd.read_csv(ROOT/'data/al_expanded_20261024/expanded_source_only.csv',float_precision='round_trip')
    d=prepare(raw[raw.target_verified.fillna(False).astype(bool)&raw.icorr_A_cm2.gt(0)])
    tr,te=train_test_split(np.arange(len(d)),test_size=.2,random_state=42)
    train=d.iloc[tr].reset_index(drop=True);test=d.iloc[te].reset_index(drop=True)
    y=np.log10(train.icorr_A_cm2.to_numpy());yt=np.log10(test.icorr_A_cm2.to_numpy())
    options=candidates();cvrows=[]
    for fold,(a,b) in enumerate(KFold(5,shuffle=True,random_state=42).split(train),1):
        z,zv=transform(train.iloc[a],train.iloc[b])
        for name,factory in options:
            m=factory().fit(z,y[a]);p=m.predict(zv)
            cvrows.append(dict(candidate=name,fold=fold,**metrics(y[b],p)))
        print('Training-only fold',fold,'completed',flush=True)
    cv=pd.DataFrame(cvrows)
    ranking=cv.groupby('candidate',sort=False).agg(cv_rmse_log10=('rmse_log10','mean'),cv_r2_log10=('r2_log10','mean')).sort_values('cv_rmse_log10')
    winner=ranking.index[0]
    z,zt=transform(train,test);rows=[];predictions=[]
    for name,factory in options:
        m=factory().fit(z,y);p=m.predict(zt)
        rows.append(dict(candidate=name,selected_by_training_CV=name==winner,**metrics(yt,p)))
        for i,v in enumerate(p):predictions.append(dict(candidate=name,record_id=test.record_id.iloc[i],source_paper_id=test.source_paper_id.iloc[i],observed_A_cm2=10**yt[i],predicted_A_cm2=10**v))
    results=pd.DataFrame(rows)
    cv.to_csv(out/'training_cv_folds.csv',index=False)
    ranking.to_csv(out/'training_cv_ranking.csv')
    results.to_csv(out/'holdout_metrics.csv',index=False)
    pd.DataFrame(predictions).to_csv(out/'holdout_predictions.csv',index=False)
    pd.concat([train[['record_id']].assign(role='train'),test[['record_id']].assign(role='test')]).to_csv(out/'split.csv',index=False)
    selected=results[results.candidate.eq(winner)].iloc[0].to_dict()
    summary=dict(n_total=len(d),n_train=len(train),n_test=len(test),split='random 80:20 seed42',
        model_selection='5fold shuffled KFold on 301 training rows only, minimum mean log RMSE; not paper-group CV',
        feature_set='Existing environment descriptors; no new stage features in this protocol comparison',
        selected_candidate=winner,selected_holdout=selected,production_model_modified=False,
        caveat='The seed42 holdout has been inspected previously; this is development benchmarking, not a new untouched final test.',
        external_assessment='Previously tested 17-4PH paper retained as a separate application-domain diagnostic; not used to select this model',
        references=[dict(doi='10.1038/s41598-024-68562-w',basis='1428 soil-steel current-density observations; random 80:20; RF/SVR/MLP comparison',difference='Different corrosion environment and target measurement protocol; performance not directly comparable'),dict(doi='10.1038/s41529-025-00700-9',basis='Literature-derived MPEA corrosion data; RF/NN/KRR/LassoIC; train/test R2 averaged over 10 repetitions',difference='Different alloys; no GAN or synthetic outcomes used in our analysis'),dict(url='https://pmc.ncbi.nlm.nih.gov/articles/PMC12387397/',basis='80:20 marine corrosion split; training model optimization with 5fold CV and RMSE',difference='We use a small prespecified grid, not GA or generated data')])
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    text=f'''# 선행 부식 AI 논문에 근거한 평가 방식

외부 논문 R2는 모든 AI 예측 논문의 필수 절차가 아니다. 수집 자료를 무작위로 나눈 테스트 R2와 독립된 논문/실험실에서의 외부 R2는 서로 다른 적용 범위를 평가한다. 논문에서 unseen/test라는 표현을 썼다고 외부 논문 검증을 했다는 뜻은 아니다.

## 확인한 선행 연구
1. Dong et al., Scientific Reports (2024), Machine learning-based corrosion rate prediction of steel embedded in soil. https://doi.org/10.1038/s41598-024-68562-w . 1428건을 무작위 80:20으로 나누고 RF/SVR/MLP를 비교했다. 이는 내부 테스트의 사례이며 토양/LPR 측정으로 우리 수용액/Tafel 자료와 직접적인 R2 우열 비교를 하지 않는다.
2. Ghorbani et al., npj Materials Degradation (2025), Supervised machine learning for corrosion assessment of multi-principal element alloys using experimental and generative datasets. https://doi.org/10.1038/s41529-025-00700-9 . 문헌 자료로 RF/NN/KRR/LassoIC를 비교하고 train/test R2를 10회 반복 평균으로 보고한다. 실험 자료 icorr RF test R2는 약 0.38이다. 이 값을 우리 결과의 성능 기준이나 직접 우열 비교에 사용하지 않는다. GAN 부분을 우리 작업에 적용하지 않았다.
3. An Integrated Approach Using GA-XGBoost and GMM-RegGAN for Marine Corrosion Prediction Under Small Sample Size (2025). https://pmc.ncbi.nlm.nih.gov/articles/PMC12387397/ . 80:20 분리와 최적화 중 5fold CV/RMSE를 사용한다. 여기서 착안한 것은 학습/평가 분리 구조이며 GA/합성데이터를 복제한 것이 아니다.

## 이번 실제 실행
385행 중 검증된 양수 icorr 377행을 사용했다. 무작위 80:20 seed42로 학습301/테스트76을 유지했다. 기존 환경 피처를 사용하고 전처리는 매 내부 fold의 학습 쪽에서만 적합했다. 학습301행 안에서 무작위 5fold CV로 SVR 3설정/RF 2설정/Ridge 3설정의 평균 log RMSE를 비교했다. 논문 단위 5fold가 아니다. 모델 선택을 마친 뒤 76행 결과를 계산했다.

선정 모델: {winner}
test R2(log10 icorr): {selected['r2_log10']:.6f}
test RMSE(log10): {selected['rmse_log10']:.6f}
test MAE(log10): {selected['mae_log10']:.6f}
기하평균 배수 오차: {selected['geometric_mean_fold_error']:.3f}

## 해석과 보고 범위
이 seed42 테스트는 이전 대화에서 이미 여러 번 확인했다. 따라서 이번 결과는 기존 분리에 대한 개발 비교이며 새로운 미관측 최종 테스트라고 표현하지 않는다. 테스트 점수가 가장 좋은 모델이 아니라 학습 내부 CV로 선택한 모델을 대표 결과로 사용한다. 기준선과 후보 전체 결과를 보존한다.
새 논문에서 얻은 큰 오차도 보조 결과로 남긴다. 주 평가를 무작위 test로 정한다고 외부 예측 실패가 없어지는 것은 아니다. 현재 자료와 유사한 조건의 내부 예측 성능과 공정/조건이 다른 논문으로의 적용 한계를 구분해 보고한다. 운영 모델은 변경하지 않았다.
'''
    (out/'선행논문_근거와_평가방식.md').write_text(text,encoding='utf-8')
    print(ranking.to_string());print(results[['candidate','selected_by_training_CV','r2_log10','mae_log10']].to_string(index=False));print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
