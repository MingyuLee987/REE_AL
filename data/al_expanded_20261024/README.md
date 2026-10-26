# 문헌 실험자료 확장 2026-10-24

352행에 원문 확인 33행을 추가한 385행 검토본입니다. 실측 원본은 expanded_source_only.csv, 조성/pH 보완 검토본은 expanded_review.csv입니다.

새 자료: S275 18행, SLM 17-4PH 9행, UNS S41003 6행. 24행은 pH가 원문에 명시되고, 21행은 열처리 온도·시간이 명시됩니다. RE를 미보고한 신규 문헌의 RE_ppm은 0으로 채우지 않습니다. 이번 신규 RE 양성 자료는 0행입니다. 전체 RE 양성은 41행입니다.

완전행은 feature_schema.json의 full_required_fields로 판정합니다. 빈칸 없는 전체 자료로 주장하지 않습니다. 원문 pH와 추정 pH를 구분합니다. 노출시간과 OCP 안정화시간은 다른 항목입니다. S275 시험온도는 열처리 냉각의 실온 표현으로 대체하지 않습니다.

무작위 분리를 주 평가로 사용합니다. 전역 보완 검토본을 바로 평가에 넣지 않고 expanded_source_only.csv에서 먼저 분리한 다음 train 자료에만 대치기·스케일러를 적합합니다. 기존 모델은 그대로 두고 새 평가 결과는 results/random_protocol_20261024에 저장합니다.

screening_log.csv는 미편입 이유, new_source_provenance.csv는 표·페이지·단위, composition_imputation_log.csv는 donor와 추정값, missingness.csv는 결측치 변화를 기록합니다.
