# 조성 DB 수정과 성능 검증

평가일: 2026-10-26. 기존 377행·65개 논문의 icorr와 시편 ID를 유지했다. DB 정보 표현의 개선과 예측 성능 향상을 구분했다.

## 수정 내용

1. 23개 원소에 대해 보고 단일값, 하한, 상한, 보고 형태, 근거와 복구 경로를 분리했다. 모든 함량 필드의 단위는 wt.%다.
2. 과거 검토 자료 45행 중 시편 ID와 논문이 일치하는 37행에서 Nb·Ti 등 추가 원소와 조성 상한을 복구했다. Nb 단일값은 14행, Ti는 5행이다.
3. 확보된 상한은 C 5, Si 5, Mn 5, P 10, S 5, Ni 1, N 5, Nb 1, Ti 1, W 1셀, 합계 39셀이다. 실제 하한이나 양측 구간 자료는 없으므로 임의로 생성하지 않았다. 규격·측정 근거를 완전히 판정하지 못한 값은 근거 미분류 상태로 남겼다.
4. 단일 RE 종류가 명확한 경우에만 총 ppm을 해당 원소 wt.%로 변환했다. 혼합 RE를 임의로 분배하지 않았다. Ce·La 개별 함량이 있는 혼합 시편 1행은 총량과 합계가 일치한다.
5. 복구·변환 100건을 기록했고 충돌 0건을 확인했다. 이 건수는 신규 독립 실험 수가 아니다.
6. 일부 과거 보완 표시 열은 legacy_ 메타데이터로 옮겨 모델 입력에서 제외했다. 원래 verified_377.csv는 유지했다.

DB: data/composition_revised_20261026/database_377.csv

## 비교 설계

외부 무작위 5-fold(seed42) 및 논문별 GroupKFold 5-fold를 사용했다. 조성·전처리·SHAP 선택과 모델 설정은 각 학습자료 내부에서 처리했다. 자동 선택 절차는 내부 3-fold를 사용했으며, 논문별 외부 평가에서는 내부도 논문별로 분할했다. 타깃·출처 ID·근거 경로·legacy 보완표시는 예측 피처로 사용하지 않았다.

- 기존: donor 기반 조성 보완 및 기존 descriptor, SVR C=10.
- 구조화 고정: 조성의 보고값·양 끝점·보고 형태와 복구 원소를 입력. 기존 donor 보완과 상한 절반 규칙을 사용하지 않고 학습 중앙값 대체. SVR C=10.
- 구조화 자동 선택: 기존 방식과 구조화 방식, C=1·10·100 및 TreeSHAP 상위 40·80개 후보를 내부 MAE로 선택. 모든 조합을 탐색한 것은 아니다. epsilon=0.15, gamma=scale 고정.
- 기존+복구 정보: 기존 donor·descriptor·SVR을 유지하고 추가 원소와 기존에 빠졌던 경계만 추가한 별도 고정 비교.

입력의 미보고를 0이라는 실제 함량으로 바꾸지 않았다. 모델은 결측 대체를 사용하므로 모델 내부 수치와 DB 원문값은 구분한다. 단일 보고값의 모델용 두 끝점을 같은 값으로 두는 것은 결정적 인코딩이며 측정 오차 구간을 만들어낸 것이 아니다. 일반 SVR이 입력 구간의 불확실성을 자동 전파하는 구조도 아니다.

## 결과: pooled OOF 지표

| 방식 | 무작위 log R² | 무작위 log MAE | 논문별 log R² | 논문별 log MAE |
|---|---:|---:|---:|---:|
| 기존 | 0.75655 | 0.38958 | -0.02473 | 1.04424 |
| 구조화 고정 | 0.72393 | 0.42076 | 0.00893 | 1.01523 |
| 구조화 자동 선택 | 0.70280 | 0.41488 | -0.25111 | 1.10578 |
| 기존+복구 정보 | 0.73940 | 0.41057 | -0.08218 | 1.06946 |

같은 각 행에 대해 학습에서 제외된 예측을 모아 계산했다. 구조화 고정 방식의 논문별 MAE는 약 2.78% 낮아졌지만 R²는 여전히 약 0이고 실용적인 일반화 성능이 확보된 것은 아니다. 무작위 분할 성능은 모두 기존보다 낮았다. 따라서 DB를 수정했다고 예측력이 향상됐다고 주장하지 않는다.

추가 입력 대부분은 관측 수가 매우 적고 결측이 많다. 양 끝점 표현의 중복, 정보량에 비해 큰 차원, 기존 donor 방식의 제거 등 여러 변화가 섞여 있다. 각 요인별 인과적 기여는 이 비교만으로 분리되지 않는다. 전체 변경과 제한적 추가의 두 비교를 제시했지만, 성능 저하를 오직 상한 피처나 Nb·Ti 탓으로 단정할 수 없다.

기존 selector_comparison 분석의 학습 내부 방법 선택 절차는 무작위 log R²=0.75949, log MAE=0.38073이었다. 이번 DB 구조화가 그 성능을 넘어섰다는 근거도 없다. 반복 검토한 동일 자료에서의 개발 비교이므로 최고 점수만 골라 최종 독립 성능이라고 보고하면 안 된다.

## 적용 결정

출처 추적성과 미래 직접 실험의 입력 정합성을 위해 구조화 DB는 보존한다. 현재 예측 성능을 이유로 기존 운영 모델을 교체하지 않았다. 평가 전후 모델 해시가 동일하다. 이번 candidate_model.joblib는 전체 개발자료의 내부 선택에서 구조화 C=100을 고른 실험 후보일 뿐이며 채택한 운영 모델이 아니다.

모델 성능을 개선하려면 목표 저탄소강의 실제 잔류 조성, S·O, Nb·Ti와 단계별 공정, 동일 프로토콜의 icorr 자료를 확보하는 것이 다음 과제다. 현재 모든 행의 원문 조성을 새로 재감사한 것은 아니며, 기존 검토값과 최소 복구 원본의 근거 수준은 README와 basis에 명시했다.

## 어떤 논문을 참고했나

### [1] 부식 DB의 조성·환경·출처 및 미보고 정보 관리

Nyby et al. (2021), Electrochemical metrics for corrosion resistant alloys, Scientific Data.
https://doi.org/10.1038/s41597-021-00840-y

부식 지표와 조성·환경을 연결하고 문헌 정보를 추적하는 DB 설계의 근거다. 이 논문이 본 연구의 조성 상·하한 2열 입력이나 상한 절반 가정을 제안했다고 주장하지 않는다. 해당 논문의 전위 지표에 대한 경계 자료와 이번 입력 조성의 경계는 다른 문제다.

### [2] 모델 선택과 독립 성능 평가의 분리

Varma and Simon (2006), Bias in error estimation when using cross-validation for model selection, BMC Bioinformatics 7, 91.
https://doi.org/10.1186/1471-2105-7-91

피처와 설정 선택을 외부 평가자료에서 분리하는 중첩 교차검증의 근거다. 논문의 생물학적 데이터와 본 연구의 부식 데이터가 같다는 의미는 아니다.

### [3] SHAP 기반 설명과 선택 순위

Lundberg and Lee (2017), A Unified Approach to Interpreting Model Predictions, NeurIPS 30.
https://papers.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html

SHAP 설명의 이론적 근거다. 이번에는 학습자료의 ExtraTrees에 대한 mean absolute TreeSHAP 순위를 이용한다. SHAP 사용 자체가 예측 향상을 보장하지 않는다. 구현 세부사항은 https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html 을 참고했다.

### [4] 데이터 누수 방지

Kapoor and Narayanan (2023), Leakage and the reproducibility crisis in machine-learning-based science, Patterns.
https://doi.org/10.1016/j.patter.2023.100804

전처리와 선택에 평가자료를 섞지 않고 출처·개발 상태를 구분하는 방법론적 근거다.

### 이번 프로젝트의 별도 설계

원소별 value/lower/upper/reporting_type/basis 구성, 단일값의 모델용 동일 끝점 표현, 복구 우선순위와 비교 후보 목록은 이번 DB에 맞춰 설계한 것이다. 특정 논문의 검증된 조성 구간 알고리즘을 그대로 재현한 것이 아니다. Elastic Net은 이번 수정 평가에 사용하지 않았으므로 사용한 방법으로 서술하지 않는다.

## 재현과 기록

`python -m corrosion_ml.revise_database` : 복구 snapshot을 이용한 DB 생성과 중첩 비교. 최초 복구 이후 휴지통 경로 없이 재실행 가능.

`python -m corrosion_ml.check_augmented_database` : 기존 모델 입력에 복구 정보만 추가한 고정 비교.

metrics.csv, fold_metrics.csv, predictions.csv, inner_cv.csv, augmented_metrics.csv와 augmented_predictions.csv에 결과와 선택 이력을 저장했다. 원본·복구·타깃 불변성은 DB schema와 recovery_log, conflicts에 기록했다.
