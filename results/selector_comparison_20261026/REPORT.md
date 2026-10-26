# SHAP 등 피처 선택 방법 비교

377행, 무작위 외부 5-fold(seed42)와 내부 3-fold(seed71). 예측 모델은 고정 RBF SVR(C=10, epsilon=0.15, gamma=scale)이다.

## 방법

- TreeSHAP: 학습자료에 적합한 ExtraTrees 200개 트리의 mean(abs(SHAP))으로 순위화. SHAP 0.54.1, tree_path_dependent, additivity 확인. 이 설명은 트리 선택 모델에 대한 것이며 SVR 자체의 SHAP 설명이 아니다.
- Lasso: alpha=0.01의 L1 규제 선형모델 절대 계수로 순위화. 0이 아닌 계수만 축소 후보로 사용. alpha는 추가 튜닝하지 않았다.
- 상호정보량: 각 피처와 연속 타깃 사이의 상호정보량으로 순위화. 이진 인코딩은 이산 변수로 취급.
- 트리 중요도: ExtraTrees의 불순도 기반 중요도. 기존 방식의 비교 기준.
- 각 방법은 상위 10·20·40·80개와 전체 피처 중 내부 MAE로 개수를 결정했다. 양의 점수 피처가 적으면 해당 개수까지 사용한다.
- 별도로 방법 자체도 내부 MAE로 선택하는 절차(inner_selected_method)를 평가했다. 외부 테스트 성능을 보고 방법을 고르는 것과 구분한다.
- 모든 결측 대체·조성 보완·스케일링·인코딩·피처 순위·개수·방법 선택은 해당 학습자료 내부에서만 수행했다.

## 외부 OOF 결과

| 선택 방법 | fold별 차원 | pooled log R² | log MAE | log RMSE | 기하평균 배수 오차 | 2배 이내 |
|---|---:|---:|---:|---:|---:|---:|
| 전체 피처 | 176~180 | 0.75655 | 0.38958 | 0.62315 | 2.4523 | 59.68% |
| 트리 중요도 | 80 | 0.75504 | 0.38770 | 0.62508 | 2.4417 | 61.54% |
| TreeSHAP | 40~80 | 0.75497 | 0.38618 | 0.62517 | 2.4332 | 61.54% |
| Lasso | 40~180 | 0.74990 | 0.40228 | 0.63160 | 2.5251 | 57.56% |
| 상호정보량 | 40~80 | 0.74600 | 0.39791 | 0.63650 | 2.4998 | 58.89% |
| 학습 내부에서 방법까지 선택 | 80 | 0.75949 | 0.38073 | 0.61937 | 2.4029 | 62.07% |

5-fold OOF를 합쳐 계산한 지표이다. fold별 R² 평균·표준편차는 metrics.csv에 별도 저장했다.

## 해석

SHAP은 피처의 예측 기여를 설명하는 도구이며 mean absolute SHAP 순위를 이용해 선택에 활용했다. SHAP 선택만으로 전체 모델 대비 R² 개선은 없었다. MAE는 약 0.87% 낮아졌다. 전체 학습 내부에서 선택 방식과 개수를 고르는 절차는 R²가 0.75655에서 0.75949로, MAE가 0.38958에서 0.38073으로 약 2.27% 개선되었다. 차이는 작고 통계적 유의성을 입증한 결과가 아니다.

방법 자동 선택은 fold마다 TreeSHAP, 트리 중요도, 상호정보량이 달랐다. 전체 377행에서 별도 내부 CV로 최종 개발 후보를 고르면 상호정보량 80개가 선택되었다. 이 최종 모델의 성능을 상호정보량 방법의 고정 선택 OOF 결과나 자동 선택 절차의 OOF 결과와 혼동하면 안 된다. OOF 결과는 각 절차를 평가한 값이며 최종 단일 fitted model의 새로운 blind test가 아니다.

모델에 대한 중요도는 재료의 인과 영향이 아니다. Mo 등 조성의 미보고 여부가 높게 나타나므로 문헌별 보고 패턴에 대한 의존 가능성이 남는다. 범주형·결측·파생값을 포함한 차원 수이므로 80개가 독립 실험 변수 80종을 의미하지 않는다. RE·열처리 변수의 실험적 중요성을 이 결과만으로 배제하면 안 된다.

모든 평가는 무작위 분할이며 동일 논문의 행이 학습·평가 양쪽에 있을 수 있다. 과거 논문별 분할의 낮은 성능이 해결됐다는 근거는 아니다. 반복 확인한 데이터의 개발 비교이며 최종 독립 실험 검증이 필요하다.

## 산출물

- metrics.csv, fold_metrics.csv: 집계 및 fold별 성능
- predictions.csv: OOF 실제값과 예측값
- inner_cv_selection.csv: 내부 선택 점수
- selected_features_by_fold.csv, selection_stability.csv: 선택 목록과 빈도
- tree_SHAP_final_features.csv 등: 각 방법으로 전체 개발자료에서 고른 목록
- tree_SHAP_importance.png, tree_SHAP_summary.png: 전체 개발자료의 트리 선택모델 SHAP 설명. 독립 평가 그림은 아니다.
- candidate_model.joblib: 최종 내부 선택에 따른 개발 후보 bundle. 저장·재로딩 예측 일치 확인. 기존 predict CLI 모델은 변경하지 않았다.
- summary.json: 설정, SHAP 버전, 결과

재실행: `python -m corrosion_ml.compare_selectors`

근거: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html

근거: https://scikit-learn.org/stable/modules/feature_selection.html
