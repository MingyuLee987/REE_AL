# 무작위 5-fold 피처 선택 비교

377행에 대해 기존 고정 RBF SVR(C=10, epsilon=0.15, gamma=scale)을 비교했다.

## 방법

외부 random 5-fold(seed42)에서 성능을 평가하고 각 외부 학습자료 안의 내부 random 3-fold(seed71)에서 피처 수를 선택했다. ExtraTrees(200 trees)로 인코딩된 피처 중요도 순위를 계산하고 상위 10·20·40·80개 및 전체를 비교했다. 선택 기준은 내부 평균 log MAE였다. 조성 보완, 결측 대체, 인코딩, 스케일링, 중요도와 피처 수 결정은 각각 해당 학습자료에만 적합했다. 상수 피처는 축소 후보에서 제외했다. 평가 fold의 정답은 선택에 사용하지 않았다.

## 결과

| 항목 | 전체 피처 | 선택 피처 |
|---|---:|---:|
| 최종 인코딩 차원(외부 fold) | 176~180 | 80 |
| pooled log R² | 0.75655 | 0.75504 |
| fold log R² 평균 ± 표준편차 | 0.75569 ± 0.01224 | 0.75354 ± 0.02644 |
| log MAE | 0.38958 | 0.38770 |
| log RMSE | 0.62315 | 0.62508 |
| 기하평균 배수 오차 | 2.4523 | 2.4417 |
| 2배 이내 비율 | 59.68% | 61.54% |

피처 차원은 약 55% 감소했지만 R²와 RMSE는 개선되지 않았다. MAE 개선은 약 0.48%로 작다. 통계적으로 유의한 개선이나 전반적인 정확도 향상을 입증한 결과가 아니다. 피처를 줄여 비슷한 성능을 유지한 후보로 해석한다. 전체 모델보다 fold 간 변동도 커졌다.

모든 외부 fold와 전체 개발자료의 내부 선택에서 80개가 선택됐다. 전체 자료로 학습한 축소 후보는 candidate_model.joblib에 별도 저장했다. 이 파일은 구성요소를 담은 개발용 bundle이며 기존 predict CLI가 사용하는 모델 파일을 교체하지 않았다. 이 최종 후보 자체를 전체 학습자료로 평가한 값을 독립 성능으로 보고하지 않는다.

80개는 실험 변수 80종이 아니라 원핫 인코딩·결측 표시·파생 피처를 포함한 차원 수이다. 중요도는 인과 효과가 아니며 결측 패턴·강종·환경이 논문 출처의 차이를 반영할 수 있다. 낮은 중요도만으로 향후 RE·열처리 실험 변수를 제거할 근거는 되지 않는다.

## 해석 범위

5-fold는 최신 기법이라서 선택하는 것이 아니라 단일 holdout 분할의 우연성을 줄이고 모든 행을 한 번씩 평가하기 위해 사용한다. 각 회차는 약 80:20이므로 80:20과 반대되는 개념도 아니다. 무작위 fold에서는 동일 논문이 양쪽에 있을 수 있다. 기존 논문별 분할에서의 낮은 일반화 성능은 이번 평가로 해결되었다고 볼 수 없다. 이미 검토한 자료의 개발 비교이며 새로운 blind validation은 아니다.

## 파일

- metrics.csv: 전체·축소 pooled 및 fold 요약
- fold_metrics.csv: fold별 성능·차원 수
- predictions.csv: 각 행의 OOF 예측
- selected_features_by_fold.csv, feature_stability.csv: 선택 피처와 선택 빈도
- final_selected_features.csv: 전체 개발자료로 선택한 최종 목록
- inner_cv_selection.csv: 피처 수별 내부 검증 MAE
- summary.json: 프로토콜·결과
- candidate_model.joblib: 별도 개발용 축소 후보

재실행: `python -m corrosion_ml.select_features`

방법 참고: https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html
