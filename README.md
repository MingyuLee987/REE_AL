# 부식전류밀도 예측

기존 279행으로 학습한 저장 SVR 모델을 사용합니다. 모델 가중치는 변경하지 않았습니다.

## 실행

```powershell
python -m pip install -r requirements.txt
python -m corrosion_ml predict --data data/templates/candidates.csv
```

입력 양식은 비어 있으므로 복사하여 후보의 조성·공정·환경 값을 작성하세요. 열 이름을 유지하고 고유한 record_id를 넣어야 합니다. CSV와 XLSX를 지원합니다. 미보고 값을 임의로 0으로 채우지 마세요.

기본 결과는 실행 시 생성되는 `results/predictions.csv`입니다.

- pred_log10_icorr: log10(icorr / A cm^-2)
- pred_icorr_geometric_A_cm2: 예측 부식전류밀도
- bootstrap_std_log10: bootstrap 모델 간 예측 편차. 보정된 신뢰구간이 아닙니다.

## 폴더

- corrosion_ml: 예측 실행과 저장 모델 로딩에 필요한 코드
- models: 저장 모델과 학습 당시 명세
- data/templates/candidates.csv: 후보 입력 양식
- output/pdf: 요청한 선행연구·novelty 정리 PDF

2026-10-26 사용자 요청으로 문헌 수집 자료, 학습 데이터베이스, 과거 평가 결과, 실험계획, 보고서와 AL·학습 전용 코드를 휴지통으로 이동했습니다. Git 이력과 환경 설정은 유지했습니다. 저장 모델은 전처리·조성 보완에 필요한 학습 당시 정보를 내부에 포함하므로 학습 CSV 없이 예측할 수 있습니다. 예측 코드에 남은 공통 데이터·모델 클래스는 저장 모델 로딩에 필요합니다.

## 복구한 확장 데이터

- `data/verified_377.csv`: 원문 기반 385행 중 target_verified=True이고 icorr_A_cm2>0인 377행, 65개 논문. 확장 데이터 평가에 사용했던 조건으로 추출한 자료입니다.
- `data/al_expanded_20261024/expanded_source_only.csv`: 복구한 원본 385행. 출처와 검토 정보를 보존합니다.

377행은 icorr 확인 기준이며 희토류·단계별 열처리·환경 입력이 모두 완비된 뜻은 아닙니다. 현재 저장 모델은 여전히 기존 279행 학습본입니다. 데이터 복구만 수행했으며 377행 재학습이나 모델 교체는 하지 않았습니다.

## 조성 정보를 보존한 수정 DB

`data/composition_revised_20261026/database_377.csv`에 조성 보고값·상하한·보고 형태·근거를 분리했습니다. 추가 원소와 원문 상한 복구 이력도 같은 폴더에 있습니다. 이 DB의 모든 값이 실측 조성이라는 뜻은 아니며 basis를 확인해야 합니다.

동일 분할의 비교에서는 무작위 예측 성능이 개선되지 않아 운영 모델을 교체하지 않았습니다. 결과와 참고논문은 `results/composition_revised_20261026/REPORT.md`에 있습니다.
