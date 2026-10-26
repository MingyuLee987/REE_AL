# 내 실험으로 예측력 확인하기

현재 모델은 **조성·공정·환경**을 사용하며 상분율을 사용하지 않습니다. 상분율은 기록·점검용으로 보존합니다. 상분율 효과를 확인하려면 측정 자료가 쌓인 뒤 별도의 포함/제외 모델 비교가 필요합니다.

## 1. 실험 양식 작성

[data/templates/experiments.csv](../data/templates/experiments.csv)를 Excel에서 열어 작성하고 CSV 또는 XLSX로 저장합니다. 헤더는 유지하고 미상은 빈칸으로 둡니다. 범주 표기는 [category_reference.json](../data/templates/category_reference.json)을 참고합니다.

| 입력 | 기준 |
|---|---|
| record_id | 측정마다 고유 ID. 예: EXP_C01_R01 |
| condition_id | 조성·열처리·부식 조건이 같은 반복은 같은 ID |
| replicate_id / batch_id | 독립 시편 반복과 제조 배치 기록 |
| C, Si, Mn, P, S, Cr, Ni, Mo, Cu, N | wt%. 미기재·검출한계 미만을 무조건 0으로 만들지 않음 |
| RE_ppm / RE_element_cat | ppm / Ce, La, Ce+La 등. 확인된 무첨가면 0 / none |
| steel_family | 일반·합금강 / 스테인리스강 / Fe계 특수재료 |
| electrolyte_condition_cat | 성분·농도·기준을 명시. 예: 3.5 wt.% NaCl |
| temperature_C / pH | °C / 실제 pH |
| exposure_h / scan_rate_mV_s | h / mV/s |
| ocp_stabilization_min | OCP 안정화 시간 min |
| heat_treatment_temperature_C / heat_treatment_time_min | °C / min |
| austenite/ferrite/martensite/bainite/pearlite_fraction_pct | %. 65%는 65로 작성 |
| other_fraction_pct / phase_method / phase_fraction_basis | 기타 분율, 측정법, 면적·체적·질량 기준 기록 |
| icorr_A_cm2 | 실측 A/cm². 예측 전에는 빈칸 |

상분율의 항목 정의가 겹치지 않게 기록하고, 모르는 상을 0으로 만들지 않습니다. 분율을 100%로 자동 정규화하지 않습니다. 도구는 개별 0~100%, 합계 101% 이내를 점검하며 1%p는 반올림 확인 여유입니다. 상분율은 예측 시점에 얻을 수 있는 값이어야 합니다. 구별 가능한 상/조직 성분의 점계수 방법은 [ASTM E562](https://store.astm.org/standards/e562)를 참고할 수 있습니다.

## 2. i_corr 측정 전에 예측 고정

```powershell
python -m corrosion_ml validate --data my_experiments.xlsx --predict-only --output results/exp_before
```

이 명령은 모델을 재학습하지 않습니다. predictions.csv에 예측을, metrics.json에 모델·입력 해시를 저장합니다. XLSX는 첫 시트를 읽으며 다른 시트는 `--sheet 시트이름`으로 지정합니다. 모델 파일을 이후 평가까지 고정합니다.

## 3. 측정값 입력 후 평가

3 μA/cm²는 3e-6 A/cm², 0.2 mA/cm²는 2e-4 A/cm²입니다. 총전류만 있다면 확인된 노출 면적 cm²로 나눠야 합니다. 검출한계나 음의 피팅 결과를 임의의 양수로 바꾸지 않습니다.

```powershell
python -m corrosion_ml validate --data my_experiments_measured.xlsx --output results/exp_test
```

초기 모델 해시를 검사하려면 `--expected-model-sha256 실제해시값`을 붙입니다. 측정 i_corr는 예측 입력에서 제거한 후 정답과 비교합니다. 기존 예측을 보존하려고 같은 출력 폴더에 덮어쓰지 않습니다.

## 4. 결과 해석

- predictions.csv: 시편별 예측·실측과 배수 오차. absolute_fold_error=2이면 두 값이 2배 차이입니다.
- condition_predictions.csv: 같은 조건의 반복을 log 평균, 즉 원 단위 기하평균으로 요약합니다.
- metrics.json의 replicate_level / condition_level: 개별 반복과 조건 수준 지표를 구분합니다. log10 R²·RMSE·MAE와 원 단위 점수, 2배 오차 안에 든 비율을 확인합니다.

R²=0.8은 80%의 실험을 맞혔다는 뜻이 아닙니다. 조건이 하나뿐이거나 정답이 모두 같으면 R²는 null입니다. 표본이 적거나 정답 범위가 좁을 때도 R²는 불안정하므로 배수 오차와 반복 산포를 같이 봅니다. 반복 60행이 있어도 독립 조건 20개라면 조건 수는 20개입니다.

내 실험 전체의 외부 점수를 먼저 기록한 뒤 모델을 업데이트합니다. 상분율 포함 모델을 개발할 때는 같은 학습 행·같은 검증 조건에서 포함/제외 모델을 비교합니다. 조건을 무작위로 나누되 같은 조건의 반복은 같은 쪽에 두고, 최종 테스트 조건은 AL 후보나 재학습 자료에 넣지 않습니다.
