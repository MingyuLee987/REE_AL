# 결정립 크기 수집 결과와 후속 분석 방법

작성일: 2026-10-23 (Asia/Seoul)

## 결론

API와 보관 원문을 활용하면 현재 CSV에 결정립 크기를 추가할 수 있다. 실제로 기존 279행 중 17행에 개별 시료의 원문 보고값을 연결했다. 이는 5편, 12개 재료 상태의 결정립 정보이며, 노출 전후 행에 같은 시작 미세조직 값이 공유되므로 17개의 독립적인 결정립 측정이 아니다. 추가로 시료군의 값만 보고된 4행과 구오스테나이트립 크기의 하한만 보고된 1행을 별도 열로 보존했다.

추가 문헌 4편에서는 16개 재료 조건에 대해 grain size–실측 i_corr 21쌍을 구성했다. 16쌍은 Tafel 분극, 5쌍은 같은 일부 시료의 LPR 결과이므로 21개의 독립적인 재료가 아니다. 이 자료는 별도 비교자료이며 기존 희토류 강재 학습자료에 자동 병합하지 않았다.

## 수행 범위와 결과물

- 보관 원문과 새로 받은 자료를 합친 903개 고유 출처의 본문·표·그림 설명을 검색했다. 숫자와 단위가 동반된 grain-size 문맥을 검색했으며, 전 원문의 모든 그림을 판독한 것은 아니다.
- 기존 43개 출처 중 28개는 확보된 본문 블록이 8,000자를 넘는다. 이 숫자는 본문 길이 기준의 접근 현황으로, 완전한 원문 여부나 결정립 크기의 보고 여부를 보증하지 않는다.
- Wiley TDM에서 PDF 4편, 출판사 공개 PDF에서 4편을 새로 확보했다.
- OpenAI 모델은 .env의 OPENAI_MODEL 설정을 사용했다. 26개 출처의 최종 구조화 추출 결과에 56개 후보 기록이 있다. 인용문·입자 크기·질적 설명을 제외하도록 지시하고 정확한 원문 구절의 존재를 프로그램으로 검사했다.
- 최종 연결값은 추가로 본문 문맥과 시료 ID를 확인했다. 75Cr1 PDF page 5와 0.4Sb강 PDF pages 5–6은 렌더링하여 시각적으로 확인했다.
- 0.03LaCe의 1.28 µm는 본문 텍스트 추출에서 빠졌지만 Figure 2(b3)의 인쇄된 숫자 라벨을 직접 읽어 확보했다. 이미지의 길이를 임의로 재거나 histogram에서 평균을 계산한 값이 아니다.
- .env의 실제 값은 결과 파일에 기록하지 않았다. Elsevier API는 AUTHENTICATION_ERROR/403과 'Requestor configuration settings insufficient for access to this resource'를 반환했다. 키 존재만으로 모든 출판사 원문 권한이 확보되는 것은 아니다.

주요 파일:

| 파일 | 용도 |
|---|---|
| `data/training_with_grain_size.csv` | 기존 279행·82개 원래 열에 결정립 정보와 출처 메타데이터를 추가한 버전 |
| `data/literature/grain_size/grain_measurements_reviewed.csv` | 확인된 결정립 정보의 긴 형식 원장; 개별·시료군·범위·하한 구분 |
| `data/literature/grain_size/grain_record_links.csv` | 원장과 기존 record_id 연결; 공유 측정의 중복 확인용 |
| `data/literature/grain_size/additional_grain_icorr_pairs.csv` | 추가 4편의 실측 grain-size/i_corr 21쌍; 원 단위·측정법·원문 표 행 포함 |
| `data/literature/grain_size/grain_size_icorr_by_paper.png` | 기존 자료 중 개별값 17행의 논문별 비교; 시료군·하한 제외 |
| `data/literature/grain_size/grain_candidates.csv` | 자동 추출 후보 전체; 검증 완료 데이터와 혼용 금지 |
| `data/literature/grain_size/external_paper_queue.csv` | 추가 문헌의 확인·입력 허용 상태 |
| `data/literature/grain_size/paper_screen.csv` | 검색한 출처별 본문과 grain-size 언급 현황 |
| `docs/grain_review_decisions.json` | 시료 연결과 개별/시료군 구분에 대한 명시적 검토 판단 |

원문 캐시·추출 입력·API 사용량·이전 오류 기록은 Git에서 제외된 `outputs/grain_size_20261023/`에 보존했다. 라이선스가 다른 원문 캐시를 공개 데이터셋에 그대로 재배포하는 작업은 하지 않았다.

## 기존 자료에 연결한 값

| 논문 | 보고값 (µm) | 저장 해석 |
|---|---|---|
| 10.3390/met13010066 | Q235B(R) 41, Q235BRE(R) 24 | 개별 보고값. 평균 통계의 명칭은 원문에서 확정되지 않아 '실측 평균'이라고 일괄 표시하지 않음 |
| 같은 논문 | Q235BRE(C) >150 | 구오스테나이트립 크기, 하한 150 및 연산자 >. `grain_size_um`에는 넣지 않음 |
| 10.1002/srin.202400576 | S1 18.14, S2 15.67 | EBSD crystallographic grain size. PDF p.5의 Table 4 i_corr가 기존 두 행과 일치함을 확인 |
| 10.3390/ma19122685 | 0RE 1.87, 0.03LaCe 1.28, 0.3LaCe 1.11 | EBSD 분포, 원문은 평균으로 설명. 중간값은 Figure 2(b3) 라벨 판독 |
| 10.1016/j.isci.2025.113319 | 1Ce 10±0.5, 1.5Ce 5±0.5, 2Ce 2±0.5 | SASS 쪽 HAZ의 평균 절편 크기. 0/288 h 행에 동일 시작 조직값 연결 |
| 10.1007/s10853-025-11514-0 | 0La 4.5±1, 0.5La 6.0±1.5 | 용융부 조직의 보고값. 전체 용접부/HAZ를 대표하는 값으로 해석하지 않음 |
| 같은 논문 | La >1.0 wt% 시료군 2.2±0.5, 요약 범위 2–6 | 1.5/2.0La에 해당하는 시료군 설명. `grain_size_group_um`와 범위 열에만 저장 |

위 ±값은 표준편차/표준오차/신뢰구간 중 어느 것인지 확인되지 않은 경우 임의로 분류하지 않았다. 불확실성 크기는 별도 열에 기록하고 원문 통계 표현을 함께 보존했다.

`grain_size_um`이 빈 셀이라는 이유로 0, 강종 평균, 열처리 추정값을 넣지 않았다. 결정립 크기·구오스테나이트립 크기·결정자 크기·입자 크기·래스 폭을 동일 변수로 합치지 않았다. 현재 grain-size 특성은 모형 예측치가 아닌 문헌 보고값이다.

## 추가로 구성한 grain size–i_corr 자료

1. **X65 pipeline steel, 10.1186/s40712-025-00240-9**
   - 결정립 크기 8, 11.5, 13, 19 µm에 대해 Table 3의 실측 i_corr는 각각 10.2, 13.2, 17.2, 23.1 µA/cm²다.
   - 산성 전해질: 5 wt% NaCl + 0.5 wt% CH3COOH + 1 wt% H2SO4 + 3 g/L NH4SCN, pH 1.3.
   - 875/1000/1075/1150 °C에서 각 10 min 유지 후 노냉한 조건을 대응시켰다. 3.4 µm의 입고재와 12.2/16.6 µm의 추가 검증 시료는 대응하는 실측 전류 표가 확인되지 않아 이 비교쌍에서 제외했다.
   - 이 논문은 현상론적 passivation 모형을 다루며, AI 학습자료 수집 논문이라고 부르지 않는다.

2. **35CrMoV, 10.3390/ma12091455**
   - 850 °C/0.01 s⁻¹: 12.5 µm, 2.441 µA/cm².
   - 1050 °C/0.01 s⁻¹: 15.4 µm, 5.393 µA/cm².
   - 850 °C/10 s⁻¹: 10.7 µm, 2.332 µA/cm².
   - 변형 온도와 변형률 속도를 모두 맞췄다. 950 °C 조건 등의 결정립 크기를 보간하지 않았다.

3. **Super austenitic stainless steel, 10.3390/ma15248780**
   - T30/T60/T120 및 AT11/AT13의 보고값 108/177/280/42/392 µm를 시료별로 연결했다.
   - 각 시료의 LPR와 CPDP-Tafel 값이 다르므로 각 방법을 구분한 10행으로 보존했다.
   - AT12는 T120과 같은 재료 조건이므로 추가 독립 시료로 세지 않았다. Tafel 표의 T120/AT12 수치가 0.120/0.123 µA/cm²로 약간 다르므로 평균내지 않고 T120의 원 보고값을 선택했다.

4. **Sintered 316L, 10.1038/s41598-026-65428-1**
   - 1000/1050/1100/1150 °C 소결 시 16.48/24.41/37.74/61.90 µm.
   - 72 h 노출 후 실측 i_corr는 6.27e-5/5.70e-5/1.72e-5/2.73e-5 A/cm².
   - 결정립 크기뿐 아니라 치밀화·기공률이 같이 변하므로 결정립 단독 효과로 주장할 수 없다.

추가 자료의 RE 미보고는 0 ppm으로 바꾸지 않았다. 조성과 기타 입력 항목을 기존 모형 스키마에 맞춰 다시 확인하기 전에는 학습용 279행에 합치지 않는다.

## 내부식 AI 논문에서 적용한 수집 원칙

### 1. Grain size를 실제로 포함한 내후성강 AI 연구

[Multi-objective optimization of corrosion resistance, strength, ductility properties of weathering steel utilizing interpretable attention-based deep learning model](https://doi.org/10.1038/s41529-025-00654-y)

Methods의 Dataset construction은 조성·grain size·환경·시간·질량감소 부식률을 포함한 417개 부식 시료를 설명한다. 중요한 점은 비교 조건을 맞추기 위해 모사 오염 해양 환경의 576 h 질량감소율을 중심 지표로 선택했다는 것이다. 현재 연구도 단순히 다른 논문의 모든 i_corr를 섞기보다, 전해질·시간·측정법을 맞추거나 구분해야 한다.

이 논문의 목표는 질량감소율이므로 그 417행을 i_corr 정답으로 변환해 사용하지 않았다. 공개 GitHub 저장소에서 확인한 것은 코드·설명·발표자료 등이며, 사용 가능한 417행 원자료 파일을 확보했다고 주장하지 않는다. 논문은 부식 데이터 출처로 corrdata.org.cn을 제시한다.

### 2. 문헌 기반 i_corr 데이터 수집 연구

[Supervised machine learning for corrosion assessment of multi-principal element alloys using experimental and generative datasets](https://doi.org/10.1038/s41529-025-00700-9)

619개 문헌 기반 MPEA 관측치에 조성·환경·미세조직 상 정보와 Ecorr/i_corr/Epit를 정리한다. 실험 데이터와 GAN 생성 데이터를 명시적으로 구분한다. 현재 수집도 자동 후보, 원문 확인값, 시료군 설명값을 구분하고, 생성 또는 추정 자료를 실험 관측치로 세지 않는 원칙을 적용했다. MPEA 자료를 희토류 강재와 같은 모집단으로 병합하지 않았다.

### 3. LLM 정보 추출의 검증 방법

[Extracting accurate materials data from research papers with conversational language models and prompt engineering](https://doi.org/10.1038/s41467-024-45914-8)

ChatExtract는 관련 문장 탐색, 물질–값–단위 추출, 후속 질문을 통한 확인을 분리한다. 특히 여러 시료와 값이 한 문장에 있을 때 대응 관계를 재확인한다. 이번 구현은 관련 문맥 선택 → 구조화 추출 → 원문 구절 일치 검사 → 시료·처리상태 검토 순서다. 논문의 추출 정확도가 현재 파이프라인에도 보장된다고 주장하지 않으며, 별도의 정답셋으로 precision/recall을 측정한 것은 아니다.

OpenAI API 구현은 [Structured Outputs 공식 문서](https://developers.openai.com/api/docs/guides/structured-outputs)를 확인하여 JSON 스키마로 출력 구조를 제한했다. 스키마 준수와 과학적 사실의 정확성은 별개이므로 원문 확인 단계를 유지했다.

## 현재 자료에서 보이는 관계와 분석 권고

논문별 그림을 보면 Q235·75Cr1·0.4Sb강에서는 작은 결정립 쪽이 낮은 i_corr를 보이지만, Ce 첨가 HAZ에서는 작은 결정립만으로 가장 낮은 i_corr를 설명할 수 없다. La 용접부의 0/0.5La 두 시료 비교는 0 h와 288 h에서 방향이 달라진다. 이는 RE 함량, 개재물, 피막, 노출시간 등이 함께 작용함을 보여주는 기술적 관찰이며 결정립 크기의 독립적인 인과효과를 입증하지 않는다.

권장 순서:

1. 그림의 선은 같은 논문·같은 전해질·같은 측정법·같은 노출시간 안에서만 연결한다.
2. 목표값은 `log10(i_corr / A cm^-2)`로 표현하고, 반복 행의 독립 단위는 원래 재료 상태/측정 ID로 구분한다.
3. grain size는 크기의 원 정의와 영역(HAZ, fusion zone, EBSD bulk 등)을 함께 사용한다. 같은 micrometre 단위라는 이유만으로 동일한 물리량으로 취급하지 않는다.
4. M0(조성·환경·공정)와 M1(M0+grain size)을 같은 확인 자료와 같은 논문 단위 분할에서 비교한다. 데이터 수가 작고 재료군이 다른 현재 상태에서는 성능 향상을 주장하지 않는다.
5. 그룹 보고값과 >150 하한은 기본 분석에서 제외하고 별도 민감도 분석에서만 활용한다. 그룹값을 개별 평균처럼 대체하지 않는다.
6. 후속 수집은 남은 후보 중 grain-size 표와 실측 i_corr 표가 모두 있는 강재 논문을 우선한다. 추가 큐에서 기계적 성질 전용 논문, coherent crystallite size, WC 입자 크기 등은 목표 변수의 의미가 다르므로 제외하거나 별도로 관리한다.
7. 그림만 있는 추가 시료는 우선 인쇄된 수치 라벨을 확인한다. 직접 조직 영상을 분할해야 하는 경우에는 길이 보정·입계 판정·표본 수가 필요한 별도 영상측정 자료로 관리하고 현재 보고값과 섞지 않는다.

## 검증 및 재실행

기존 `data/training.csv` SHA256은 `f8ad6c03486d960605c9883acb8332e5ec02ce8f691335d7fbc498a7a2daf101`이다. 보강 파일을 다시 읽어 기존 279행과 82개 원래 필드가 같음을 검증했다. 저장 모델과 원래 학습자료를 수정하거나 재학습하지 않았다.

출처·record ID·단위 변환·양수 범위·시료군/하한의 개별값 열 혼입 방지를 검사했다. 추가 21쌍은 원문 XML의 해당 표, 원 보고 수치와 단위 계수, 시료/처리조건을 확인했다. 통계적 모형 검증이나 새 외부실험 검증을 수행한 것은 아니다.

```powershell
python scripts/collect_grain_size.py scan
python scripts/collect_grain_size.py fetch
python scripts/collect_grain_size.py refresh
python scripts/collect_grain_size.py extract --external 12 --limit 60
python scripts/finalize_grain_size.py
python scripts/collect_grain_pairs.py
```

`scan`은 보관 원문 전체를 검색한다. `fetch`는 .env의 허용된 출판사 자격증명으로 원문을 요청한다. `extract`는 실제 OpenAI API 요청을 발생시키며 기존 결과는 캐시한다. `finalize`는 명시적 검토 결정에 포함된 후보만 기존 record_id에 연결한다. 외부 원문·추출 내용이 바뀌면 검토 결정을 먼저 다시 확인해야 한다.
