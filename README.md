# REE Corrosion ML

강재의 조성·공정·부식 환경으로 **log10(i_corr / A·cm⁻²)**를 예측합니다. 현재 사용하는 **환경 SVR + 부트스트랩 AL 위원회**만 남겼습니다. 예측·후보 추천·자체 실험 검증이 모두 같은 모델 파일을 사용합니다.

## 폴더 구성

```text
REE_AL/
├── corrosion_ml/       실행 코드와 전처리
├── models/             svr.joblib 한 개와 모델 정보
├── data/
│   ├── training.csv    학습 자료 279행 · 통계 보완 전 값
│   ├── templates/      실험·후보 입력 양식
│   ├── provenance/     원본 워크북·조성 보완 이력
│   └── literature/     추가 문헌 수집 자료와 정리 엑셀
├── results/
│   ├── training/       현재 SVR의 무작위 검증 결과
│   └── active_learning/  최신 AL 비교와 학습 곡선
├── docs/               사용 방법과 데이터 설명
├── tests/              현재 기능의 검증 코드
├── requirements.txt
└── README.md
```

**사용할 모델은 [models/svr.joblib](models/svr.joblib) 하나입니다.** 중앙 SVR이 예측하고, 15개 부트스트랩 SVR은 AL 선택용 불확실성을 계산합니다. 현재 모델은 상분율을 사용하지 않습니다.

## 바로 실행

프로젝트 루트에서 실행합니다. 입력은 CSV 또는 XLSX를 지원하며 XLSX는 첫 시트를 읽습니다.

```powershell
python -m pip install -r requirements.txt
python -m corrosion_ml predict --data candidates.xlsx
python -m corrosion_ml al recommend --candidates candidates.xlsx --batch-size 5
python -m corrosion_ml validate --data my_experiments.xlsx --output results/my_experiment_test
```

| 작업 | 양식 또는 결과 |
|---|---|
| 후보 작성 | [data/templates/candidates.csv](data/templates/candidates.csv) |
| 내 실험 작성 | [data/templates/experiments.csv](data/templates/experiments.csv) |
| 일반 예측 결과 | results/predictions.csv |
| 다음 실험 추천 | results/queries/next_batch.csv |
| 추가 수집 엑셀 | [data/literature/collected_data.xlsx](data/literature/collected_data.xlsx) |

후보 파일의 i_corr는 빈칸으로 둡니다. 자체 실험 평가에서는 실측 i_corr를 A/cm²로 입력하며 정답은 모델 입력에서 제외합니다. 미상 수치를 0으로 채우지 않습니다.

## 현재 검증 결과

고정 환경 SVR의 **행 기준 무작위 5-fold 평균 테스트 R²는 0.8178**입니다(log10 기준). 동일 논문의 다른 행이 학습·테스트에 포함될 수 있습니다. 자체 실험의 독립 외부 성능은 실제 측정 후 따로 확인해야 합니다.

| 학습 풀 조회량 | 무작위 선택 | AL · 불확실성+다양성 |
|---|---:|---:|
| 50% · 112행 | 0.6094 | **0.7522** |
| 75% · 168행 | 0.7737 | **0.8137** |
| 100% | 0.8178 | 0.8178 |

AL은 기존 측정값을 가리고 조회한 회고적 모의실험입니다. [전체 AL 기록](results/active_learning/REPORT.md)과 [학습 곡선](results/active_learning/learning_curves.png)에 조건과 한계를 남겼습니다.

## 재학습·재현

```powershell
python -m corrosion_ml train --evaluate-only
python -m corrosion_ml train
python -m corrosion_ml al simulate
python -m corrosion_ml plot
python -m unittest discover -s tests -v
```

train은 현재 SVR만 무작위 평가한 뒤 다시 학습합니다. evaluate-only는 저장 모델을 바꾸지 않습니다. al simulate도 완료 후 전체 자료로 학습한 모델을 저장합니다. 자체 실험 평가를 진행하는 동안에는 모델 파일을 고정하세요.

- [내 실험 입력과 외부 검증](docs/experiments.md)
- [모델·데이터 처리 원칙](docs/method.md)
- [문헌 수집 자료](data/literature/README.md)

CSV는 모든 폴더에서 Git 추적 대상이 아닙니다. 이전 모델·실험·원문 캐시는 작업 폴더 밖 백업으로 옮겼으며 위치는 [정리 기록](docs/cleanup_manifest.json)에 있습니다. 모델 가중치를 재학습하지 않고 코드 경로를 정리했으며 이전 예측·불확실성과의 일치를 확인했습니다.

