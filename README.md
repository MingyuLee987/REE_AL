# REE_AL

희토류 첨가 강의 부식 데이터를 이용해 **다음에 측정할 실험 조건을 선택하는 active learning** 프로젝트입니다. 예측 목표는 `log10(icorr_A_cm2)`이며 값이 작을수록 부식전류밀도가 낮습니다.

## 현재 데이터와 출발점

`rare_earth_steel_single_sheet_sources.xlsx`의 `ENRICHED_DATA` 시트를 사용합니다. 현재 304개 기록, 48개 `source_paper_id`가 있고 모든 기록의 `icorr_A_cm2`가 양수로 채워져 있습니다. 따라서 이 파일 자체에는 미측정 후보가 없습니다. 기존 레이블을 일부 숨기는 모의 실험으로 선택 전략을 비교한 다음, 실제 제조·측정 가능한 후보 목록을 따로 작성해야 합니다.

조성 원소에는 결측이 많습니다. 미보고 Mo, N 등을 무조건 0으로 해석하지 않습니다. 상분율의 `phase_confidence`는 low 160건, medium 86건, qualitative 32건, reported_complete 19건, reported_partial 7건입니다. 수치가 채워진 상분율도 모두 실측값이라는 뜻은 아닙니다. `RE_ppm`도 실측·명목 조성 변환·미보고를 구분해야 합니다. 원본 엑셀은 수정하지 않습니다.

기존 `test.py`는 현재 없는 `ML_FINAL.xlsx / ML_DATA`와 다른 상분율 열 이름을 참조하고 전처리를 분할 전에 학습합니다. 과거 스크립트는 보존했으며 아래 `active_learning.py`를 새 진입점으로 사용합니다.

## 권장 연구 절차

1. **비교할 실험 범위를 고정합니다.** 강종, 전해질 종류·농도·농도 기준, 온도, pH, 노출 시간, 스캔 속도를 통제하고 RE 종류와 함량 등 변경할 인자를 정합니다. 서로 다른 전해질의 낮은 전류를 하나의 최적 합금 효과로 해석하면 안 됩니다. 원소 조성의 wt.% 기준과 RE ppm의 질량 기준을 원문에서 확인합니다. 열처리·표면 상태·용존산소 등 현재 열에 없는 주요 조건도 별도 기록합니다.
2. **원문과 측정 품질을 점검합니다.** `source_paper_id`, `source_sample_id`, 단위, RE 환산 방법, 상분율 출처, 중복 시험을 검토합니다. 문자 인코딩이 깨진 일부 `steel_family` 범주는 원문에 따라 정규화하고 변경 이력을 남깁니다. 불확실한 값은 측정값으로 승격하지 않습니다. 단위가 불명확한 문헌은 검증 후 포함합니다.
3. **모의 active learning을 실행합니다.** 논문 단위로 약 20%의 그룹을 테스트에 고정합니다. 남은 풀에서 초기 40개를 무작위 선택하고, 매 회 5개씩 추가합니다. 동일 seed의 세 전략은 초기 집합과 테스트 집합이 같습니다. 매 회 전처리와 모델을 현재 레이블 집합으로만 다시 학습합니다. 미선택 레이블은 추천 점수에 사용하지 않습니다.
4. **학습 효율과 최적화 목적을 구분합니다.** 예측 성능 개선이 목적이면 uncertainty를 먼저 검토합니다. 같은 예산에서 random 대비 테스트 MAE/RMSE가 줄어드는지 확인합니다. 낮은 부식전류를 찾는 목적이면 LCB를 검토하되, 현재 모의 실험의 테스트 오차만으로 최적화 성공을 판단하지 않습니다. 최적화 연구에는 동일 환경 내 best-so-far, 대조군 대비 개선, 실측 반복성도 추가 평가해야 합니다.
5. **실험 가능한 후보 CSV를 만듭니다.** 연구자가 조성·공정·시험 조건의 허용 범위를 정하고 제조 가능성, 합금 원소 합계, 비용을 검토한 행만 넣습니다. 코드가 실험 공간을 임의로 생성하지 않습니다. 학습 데이터와 동일한 feature 조합은 제외하므로 반복 측정 대조군은 별도 실험 계획으로 관리합니다.
6. **추천 배치를 검토하고 측정합니다.** 처음에는 uncertainty 전략으로 3–5개를 선택하고, 별도로 무첨가 대조군과 반복 측정을 확보하는 방식을 권장합니다. 상위 후보가 유사한 조성에 몰리면 제조 가능한 범위에서 RE 함량 간격이나 강종별 할당을 사람이 조정합니다. 현재 코드는 배치 내 다양성 최적화를 수행하지 않습니다.
7. **측정 결과를 추가하고 반복합니다.** `next_batch.csv`의 ID를 유지하고 실제 측정한 양수 `icorr_A_cm2`와 출처/실험 식별자를 넣어 학습 CSV에 추가합니다. 추천 파일의 예측값을 정답 열에 복사하지 않습니다. 측정 완료·진행 중·실패 후보는 다음 미측정 후보 풀에서 제거합니다. 실패 기록은 별도 보존합니다.
8. **중단 기준을 사전에 정합니다.** 예산 상한, 목표 전류, 동일 시험 조건에서의 실측 개선 한계 등을 정합니다. 예를 들어 연속 3회 개선이 반복 측정 변동보다 작으면 중단을 검토할 수 있습니다. 테스트셋을 반복 확인하며 beta나 모델을 고르지 말고 별도 논문 그룹 검증셋을 사용합니다. 최종 보고용 독립 실험을 확보합니다.

논문 그룹 분할은 같은 논문이 학습·테스트에 함께 들어가는 것을 막습니다. 서로 다른 논문이 동일 원자료를 재사용한 경우에는 원자료 단위로 그룹을 통합해야 합니다. 테스트셋은 그룹 수의 20%이므로 행 수는 정확히 20%가 아닙니다. 기본 3개 seed는 빠른 비교용이며 결론을 내릴 때는 반복 수를 늘리고 그룹별 편차도 확인하십시오. 모의 실험은 남은 논문 내 시료의 레이블을 점차 얻는 상황이며, 새로운 논문 전체를 한 번에 확보하는 획득 방식은 구현하지 않았습니다.

## 모델과 선택 규칙

기본 입력은 C, Si, Mn, P, S, Cr, Ni, Mo, Cu, N, RE_ppm, temperature_C, pH, exposure_h, scan_rate_mV_s와 RE_element_cat, electrolyte_condition_cat, steel_family입니다. ID·출처·노트·목표와 사후 측정 결과를 설명변수에 넣지 않습니다.

수치 결측은 현재 학습 집합의 중앙값으로 대치하고 결측 지시자를 추가합니다. 현재 학습 집합에서 전부 결측인 열은 전처리상 0으로 유지되지만 이는 물리적 0을 의미하지 않으며 해당 열의 효과를 학습할 수 없습니다. 범주는 one-hot encoding하고 미지 범주를 허용합니다. 원본 상분율과 `matrix_phase_group`은 기본적으로 제외합니다. `--with-phase`는 후보 시점에 알 수 있는 신뢰할 만한 상분율을 확보했을 때만 민감도 분석에 사용합니다. 추정 상분율과 실측 상분율을 혼합한 결과를 별도로 비교하십시오.

150개 트리의 random forest에서 트리 예측의 평균 μ와 표준편차 σ를 계산합니다. 모두 log10 단위입니다.

| 전략 | 선택 규칙 | 목적 |
| --- | --- | --- |
| random | 무작위 비복원 추출 | 동일 예산 기준선 |
| uncertainty | σ가 큰 순서 | 모델 간 불일치가 큰 조건 측정 |
| lcb | μ − beta × σ가 작은 순서 | 낮은 전류 예측과 탐색의 절충 |

트리 간 표준편차는 **보정된 신뢰구간이나 측정 오차가 아닙니다**. 데이터 범위 밖에서 작게 나올 수도 있습니다. LCB는 이 휴리스틱을 이용하며 최적해 보장을 제공하지 않습니다. beta를 높이면 불확실한 후보를 더 선호합니다. 결과의 `10**μ`는 로그 예측을 역변환한 기하 척도 예측이며 원 단위의 산술 평균 예측은 아닙니다. log10 MAE 0.3은 평균 절대 로그 오차가 약 2배 배율에 해당한다는 뜻입니다.

## 설치와 실행

Python 3.10 이상, 프로젝트 디렉터리에서 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python active_learning.py simulate
```

빠른 실행과 반복 수를 늘린 실행:

```powershell
python active_learning.py simulate --seeds 42 --rounds 2 --output outputs/smoke
python active_learning.py simulate --seeds 0 1 2 3 4 5 6 7 8 9 --initial 40 --rounds 8 --batch-size 5 --output outputs/benchmark
```

`--data`로 다른 CSV/XLSX를 지정할 수 있습니다. XLSX 시트 기본값은 `ENRICHED_DATA`이며 `--sheet`로 바꿉니다. 초기 크기가 학습 풀보다 크거나 같은 경우 오류를 냅니다. 풀 소진 시 종료하며 마지막 배치는 5개보다 작을 수 있습니다.

| 출력 | 내용 |
| --- | --- |
| learning_curves.csv | seed·전략·회차별 학습 개수와 테스트 log10 MAE/RMSE/R² |
| summary.csv | 전략·학습 개수별 seed 평균과 표준편차. seed가 1개이면 표준편차는 공란 |
| queries.csv | 각 회차에서 새로 획득한 record_id |
| splits.csv | seed별 test/initial/pool ID와 논문 식별자. pool은 최초 분할 기준 |
| run.json | 실행 옵션·입력 파일 SHA256·레코드 수 |

출력 경로는 실행별로 다르게 지정하십시오. 동일 경로의 파일은 덮어씁니다. 초기 데이터가 채워져 있더라도 모든 유효한 라벨을 쓰는 최종 모델과 모의 실험 모델을 구분해야 합니다.

## 기본 실행 결과와 해석

현재 엑셀에 대해 seed 42, 43, 44, 초기 40개, 5개씩 8회 추가한 실행을 완료했습니다. 아래는 고정 논문 홀드아웃에 대한 seed 평균이며 로그 척도입니다. 결과 파일은 `outputs/baseline/`에 있습니다.

| 전략 | 초기 MAE | 80개 학습 후 MAE | 80개 학습 후 RMSE | 80개 학습 후 R² |
| --- | --- | --- | --- | --- |
| random | 0.9899 | 0.8596 | 1.0252 | -0.0740 |
| uncertainty | 0.9899 | 0.9841 | 1.2211 | -0.5468 |
| lcb | 0.9899 | 0.9706 | 1.1998 | -0.5597 |

이 설정에서는 random이 더 좋았으며 **active learning의 우위가 확인되지 않았습니다**. 음수 R²와 큰 로그 오차는 새로운 논문으로의 일반화가 아직 부족함을 보여줍니다. 따라서 바로 추천을 신뢰해 실험 예산을 집중하기보다 단위·환경·강종을 정리하고, 연구할 동일 환경의 부분집합을 확보하는 것이 우선입니다. seed별 테스트 행 수는 27, 64, 56개로 차이가 있어 개별 결과와 변동도 함께 봐야 합니다. 이 수치는 beta나 모델을 고르는 근거로 재사용하지 말고 별도 검증셋에서 비교하십시오.

## 실제 새 실험 추천

UTF-8 `candidates.csv`를 작성합니다. 필수 열은 고유한 `record_id`와 위 기본 입력 18개입니다. 수치의 미보고 값은 빈칸으로 둡니다. 범주도 미보고는 빈칸으로 둘 수 있습니다. 목표 열은 없거나 전부 비어 있어야 합니다. `--with-phase` 사용 시 상분율 5개와 `matrix_phase_group`도 필요합니다. 후보 ID는 학습 ID와 겹치면 안 됩니다. 예측에 쓰이지 않는 공정·비용·제조 메모 열은 추가해도 됩니다.

```powershell
python active_learning.py recommend --candidates candidates.csv --strategy uncertainty --batch-size 5 --output outputs/round01
python active_learning.py recommend --data updated_training.csv --candidates remaining_candidates.csv --strategy lcb --beta 1.0 --output outputs/round02
```

`ranked_candidates.csv`에 전체 순위, `next_batch.csv`에 다음 배치를 저장합니다. 원래 후보 열과 예측 μ, 트리 표준편차, 기하 척도 전류, LCB 점수를 포함합니다. random 사용 시 순위는 무작위입니다. 같은 feature 조합은 후보 내 하나만 남기고, 학습 데이터와 같은 조합은 제외합니다. 중복 비교에서는 CSV 직렬화 오차를 흡수하기 위해 수치를 소수점 10자리로 반올림합니다. feature에 없는 열처리 조건만 다른 후보도 같다고 처리하므로 공정 효과를 연구하려면 해당 열을 모델과 데이터 스키마에 먼저 추가해야 합니다. 자동 범위 외삽 감지와 제조 제약 검증은 구현하지 않았으므로 후보 작성 시 검토합니다.

새 결과는 원본을 보존하면서 별도 `updated_training.csv`로 관리하는 편이 좋습니다. 기존 행과 새 측정 행의 열 이름·단위를 맞추고 모든 행의 고유 ID를 유지하십시오. recommend는 지정한 학습 파일의 모든 양수 라벨로 다시 학습합니다. 고정 평가셋을 별도로 보유했다면 학습 파일에서 제외합니다.

## 구현 확인

```powershell
python -m unittest discover -s tests -v
```

레이블 검증, 논문 분리와 동일 초기 집합, 후보 중복 제거, 추천 실행을 확인합니다. 원본 엑셀을 덮어쓰지 않습니다.

## 참고

- [scikit-learn RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html): 트리 앙상블 및 난수 고정.
- [scikit-learn SimpleImputer](https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer.html): 결측 지시자와 전부 결측인 열 처리.
- [scikit-learn GroupShuffleSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html): 그룹 단위 홀드아웃.
