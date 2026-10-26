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
