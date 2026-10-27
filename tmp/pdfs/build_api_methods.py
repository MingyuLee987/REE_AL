from pathlib import Path
base=Path('tmp/pdfs/build_collection_methods.py').read_text(encoding='utf-8').split("p('REE_AL · METHODS NOTE")[0]
base=base.replace('REE_AL_data_collection_methodology_20261027.pdf','REE_AL_API_literature_methods_revised_20261027.pdf')
exec(compile(base,'pdf_helpers','exec'))

p('REE_AL · MATERIALS AND METHODS · 2026.10.27','small')
p('API 기반 문헌 데이터 수집<br/>및 구조화 방법론','title')
p('선행연구의 방법론적 근거와 본 연구의 적용','sub')
p('본 연구에서는 희토류 첨가 철강의 부식전류밀도 예측에 활용하기 위해 출판사 API를 통한 문헌 확보, LLM 보조 정보 추출, 시편별 조건 연결 및 원문 검증을 결합한 문헌 기반 데이터 수집 체계를 구성하였다. 문헌을 검색·확보하는 API와 확보한 문헌에서 정보를 추출하는 LLM API를 구분하고, 최종 데이터에는 원문 수치와 출처 및 처리 근거를 연결하였다.')
h('1. 선행연구에 근거한 방법 설계')
p('Kononova et al. (2021)은 재료 분야의 문헌 마이닝을 문서 확보와 전처리, 정보 추출 및 후속 분석으로 이어지는 흐름으로 정리하였다 [1]. 이 구분에 근거하여 본 연구도 문헌 확보와 데이터 추출을 독립된 단계로 구성하였다. Swain and Cole (2016)은 본문과 표에 분산된 화학 정보의 관계를 문서 수준에서 해소하는 처리의 필요성을 제시하였다 [2]. 본 연구에서는 이 원칙을 시편 ID를 이용한 조성표·열처리·부식 결과의 연결에 반영하였다.')
p('Polak and Morgan (2024)은 ChatExtract를 통해 대화형 LLM의 제로샷 프롬프트로 재료–값–단위 정보를 추출하고, 후속 질문으로 근거를 재확인하는 접근을 제시하였다 [3]. 이는 별도 미세조정 없이 지시문으로 구조화 추출을 수행하는 방법의 근거가 된다. Nyby et al. (2021)은 부식 지표에 조성·시험환경·열처리·주사속도 및 출처를 연결하여 부식 데이터베이스를 구축하였다 [4]. 본 연구의 부식 관측치 구성은 이러한 데이터 설계 원칙을 참고하였다.')
table([['선행연구','방법론적 근거','본 연구의 연결'],['Kononova et al. [1]','문헌 마이닝의 단계 구분','검색·확보와 추출·정리를 분리'],['Swain and Cole [2]','문서 내 분산 정보의 관계 해소','동일 시편의 조성·공정·결과 연결'],['Polak and Morgan [3]','제로샷 구조화 추출과 재확인','LLM 보조 추출의 방법론적 근거'],['Nyby et al. [4]','부식값과 조성·시험조건 통합','부식전류밀도 중심 데이터 스키마']],[127,174,198])
p('위 문헌은 본 절차의 방법론적 근거를 설명한다. 특정 알고리즘의 직접 재현이나 모든 문헌을 수집 당시부터 참조했다는 의미는 아니다. 저자가 두 명인 논문은 et al. 대신 두 저자명을 표기하였다.','small')
page()
h('2. API 기반 문헌 검색 및 원문 확보')
p('문헌 검색에는 rare earth, Ce, La 및 yttrium과 steel, stainless steel, corrosion, polarization 및 corrosion current density를 조합하였다. Elsevier, Springer Nature 및 Wiley를 주요 대상으로 하였으며, DOI를 중심으로 기존 보유 자료와 대조하였다. Crossref, 공개 저장소와 저자 학위논문은 서지정보와 원문을 보완하는 경로로 활용하였다. 이러한 확보 단계는 문서 수집을 정보 추출의 선행 단계로 구분한 Kononova et al. [1]의 문헌 마이닝 흐름과 부합한다.')
p('출판사 API에는 필요한 인증 키를 사용하여 후보 문헌의 메타데이터, 초록 또는 이용 가능한 전문을 요청하였다. Elsevier의 Scopus 검색·초록 경로는 후보 탐색에, Springer 메타데이터와 공개 XML/PDF는 서지·원문 확보에, Wiley TDM은 확인한 DOI의 전문 요청에 활용하였다. 출판사 API의 인증 성공과 전문 수신 성공은 별도로 기록하였다. API 키는 문헌 접근을 위한 인증 수단이며, 데이터 추출 알고리즘이나 미보고값의 추정 근거에 해당하지 않는다 [7].')
p('전문 API에 접근 제한이 발생한 경우에는 공개 PDF, 저자기관 저장소 및 기존 원문 캐시를 보완적으로 사용하였다. 초록만 확보한 자료는 전문 조건이 확인된 자료와 구분하였다. 중국어 본문 논문은 수집 범위에서 제외하였으며, 저자 국적이나 소속 국가를 제외 기준으로 사용하지 않았다. 본 검색은 목적 지향적 데이터 수집으로 수행하였다.')
h('2.1. 출처와 관측치의 정의')
p('관측 단위는 한 시편 조성, 재료 상태 및 부식시험 조건의 조합으로 정의하고 필요한 경우 시험 시점을 구분하였다. 동일 논문에서도 조성, 열처리 또는 전해질이 다른 경우 별도 관측치로 기록하였다. 반복 측정의 평균과 표준편차는 중심값 한 행으로 보존하고 반복 횟수만큼 복제하지 않았다. 원문 DOI, 시편명, 파일 경로와 해시, 표·절·페이지 위치 및 근거 문구를 관측치에 연결하였다.')
p('이러한 구조는 Nyby et al. [4]이 서로 다른 부식 지표를 구분하고 각 측정에 재료 및 환경 정보를 연결한 접근을 따른다. 부식전위, 공식전위, 수동태전류 및 전하이동저항은 부식전류밀도를 대신하는 타깃으로 사용하지 않았다.')
page()
h('3. LLM API를 이용한 구조화 추출')
p('기존 수집 기록에 따르면 구조화 추출은 Responses API와 gpt-6.1-sol 모델을 보조적으로 사용하였으며, 별도의 과제 특화 미세조정은 수행하지 않았다. 문헌에서 확보한 본문과 표를 입력으로 사용하고, 사전에 정의한 스키마에 따라 시편 조성, 희토류 정보, 재료 상태, 미세조직, 열처리 및 전기화학 시험조건을 부식전류밀도와 연결하였다. 반환된 값에는 원문 단위, 근거 문구 및 위치를 함께 기록하였다.')
p('Polak and Morgan [3]은 정답 시범 없이 지시문으로 재료–값–단위를 추출하는 제로샷 접근을 제시하였다. 본 연구의 비미세조정 LLM 추출은 이러한 프롬프트 기반 접근과 연결된다. 다만 “제로샷”이라는 명칭은 실제 프롬프트에 입력–정답 시범을 제공하지 않은 실행에 한해 적용한다. 원문과 출력 필드 정의를 제공하는 것은 정답 시범과 구분된다. 여러 번의 확인 질문을 사용하더라도 정답 시범을 주지 않으면 제로샷으로 구성할 수 있다.')
p('본 연구에서 필요한 관계는 단순 재료–값–단위보다 넓으므로, 시편–조성–열처리–시험환경–부식전류밀도로 확장하였다. Sasidhar et al. (2023)은 부식 예측에서 수치 조성·환경 변수와 함께 재료 준비 및 시험방법의 텍스트 정보를 활용하였다 [5]. 이 결과는 본 연구에서도 공정 및 시험 문맥을 보존하는 근거가 되며, 해당 NLP-DNN 모델을 그대로 구현했다는 뜻은 아니다.')
h('3.1. 시편 연결 및 원문 대조')
p('조성표와 재료 준비 절, 전기화학 시험방법 및 결과표에 나타나는 동일 시편을 연결하였다. 이는 Swain and Cole [2]이 논의한 문서 수준 관계 해소에 대응한다. 조성 원료와 최종 강재의 분석 조성, 열처리 온도와 시험온도, OCP 안정화 시간과 침지시간을 구분하였다. 원문에 없는 항목은 결측으로 유지하고, LLM이 반환한 수치만으로 최종 편입을 결정하지 않았다.')
p('추출 결과는 원문의 변수명, 행·열 머리글, 단위 및 지수와 대조하였다. DOI와 관측치 ID를 검사하여 중복 편입을 점검하고, 시편 연결이나 단위 해석이 불명확한 자료는 보류 상태로 관리하였다. 10월 24일 추가 수집 라운드는 별도의 AI 추출 API 검증을 주장하지 않고, 원문 표와 프로토콜을 직접 대조한 절차로 구분하였다. 전체 데이터베이스는 API 보조 추출과 원문 직접 확인이 결합된 자료이다.')
p('최종 원문 대조는 추출 오류를 줄이기 위한 과정이다. 독립적인 정답셋으로 수정 전 LLM 출력을 평가한 결과가 없으므로, ChatExtract 논문의 추출 성능을 본 자료의 정확도로 이전하지 않는다.','small')
page()
h('4. 수치 표준화 및 결측치 정리')
p('부식전류밀도는 A/cm²로 통일하고, μA/cm² 값에 10⁻⁶을 곱하였다. 전위와 주사속도 등은 정해진 단위로 변환하되 원래 값과 단위를 보존하였다. 미보고 조성과 시험조건을 일괄 0으로 처리하지 않았다. 이는 Nyby et al. [4]이 조성 결측을 NA로 보존하고 시험환경의 차이를 고려한 원칙에 근거한다.')
p('기존 데이터 준비 과정에는 조성 범위의 중간값, 상한 대리값, RT의 25 °C 표현 및 일부 시험조건 대입 이력이 포함된다. 이러한 값은 실측과 구분하여 근거를 관리하였다. 후속 조성 개정에서는 단일 보고값과 상·하한 및 보고 형태를 분리하여, 범위나 상한을 실제 분석값으로 오인하지 않도록 하였다. 10월 24일 확장 라운드에서는 시험온도 및 RE 미보고 항목을 임의로 채우지 않았으며, 단계별 처리 규칙을 전체 자료에 소급하여 동일하게 적용한 것으로 기술하지 않았다.')
p('조성 보완 검토본에는 유사 강종과 관측 조성을 이용한 donor 중앙값 대치를 적용하였다. 공통 관측 원소가 두 개 이상인 후보를 IQR 정규화 거리로 정렬하고 서로 다른 논문 3–5개의 참조값을 사용하였다. 이는 유사 관측치 기반 대치의 발상과 연결되지만 [6], 해당 문헌의 가중 KNNimpute와 동일하지 않으며 거리 및 donor 제한은 본 연구의 규칙이다. 신규 33행에서 108개 조성 셀을 보완하고 추정값은 다시 donor로 사용하지 않았다.')
p('신규 pH 24개는 원문값을 유지하였다. 나머지 9개는 단순 3.5% NaCl·20–30 °C 조건에서 참조 문헌 3편의 중앙값 6.5를 검토용 대리값으로 사용하였다. 이 단계는 제로샷 추출이 아닌 별도 대치이며, 원문값과 보완본을 분리하였다. 평가용 전처리는 데이터 분리 후 학습자료 내부에서 결정하도록 하여 전역 보완 검토본과 구분한다 [8].')
h('4.1. 통합 데이터 및 추적성')
p('2026년 10월 24일 확장 기록에서는 문헌 후보 14개 중 3개를 편입하여 33개 관측치를 추가하였고, 통합 검토본은 352개에서 385개로 증가하였다. 부식전류밀도 확인 자료는 377개이며 기존 미확인 8개는 평가에서 제외하였다. 신규 RE 함량 확인 자료는 없으므로 기존 RE 양성 41개는 유지되었다. 모든 필수 입력을 요구한 완전 관측치는 0개로, 377개는 완전 실측 입력 자료의 수를 뜻하지 않는다.')
p('원문값, 보완 검토본, 문헌 선정 기록, 필드별 출처 및 대치 이력을 별도로 보관하였다. 이 체계는 API를 통한 문헌 확보의 효율성과 원문 근거에 기반한 검증을 결합하여, 후속 부식 예측에 사용할 수 있는 추적 가능한 데이터를 구성하기 위한 것이다.')
page()
h('참고문헌')
refs=[
('[1]','Kononova, O. et al. (2021). Opportunities and challenges of text mining in materials research. iScience, 24, 102155.','https://doi.org/10.1016/j.isci.2021.102155'),
('[2]','Swain, M. C. & Cole, J. M. (2016). ChemDataExtractor: A Toolkit for Automated Extraction of Chemical Information from the Scientific Literature. Journal of Chemical Information and Modeling, 56, 1894–1904.','https://doi.org/10.1021/acs.jcim.6b00207'),
('[3]','Polak, M. P. & Morgan, D. (2024). Extracting accurate materials data from research papers with conversational language models and prompt engineering. Nature Communications, 15, 1569.','https://doi.org/10.1038/s41467-024-45914-8'),
('[4]','Nyby, C. et al. (2021). Electrochemical metrics for corrosion resistant alloys. Scientific Data, 8, 58.','https://doi.org/10.1038/s41597-021-00840-y'),
('[5]','Sasidhar, K. et al. (2023). Enhancing corrosion-resistant alloy design through natural language processing and deep learning. Science Advances, 9, eadg7992.','https://doi.org/10.1126/sciadv.adg7992'),
('[6]','Troyanskaya, O. et al. (2001). Missing value estimation methods for DNA microarrays. Bioinformatics, 17, 520–525.','https://doi.org/10.1093/bioinformatics/17.6.520'),
('[7]','Elsevier. Text Mining / Article Retrieval API. DOI 기반 원문 요청과 API 인증에 관한 기술 문서. 확인일: 2026-10-27.','https://dev.elsevier.com/tecdoc_text_mining.html'),
('[8]','Kapoor, S. & Narayanan, A. (2023). Leakage and the reproducibility crisis in machine-learning-based science. Patterns, 4, 100804.','https://doi.org/10.1016/j.patter.2023.100804'),
]
for n,t,u in refs:p(f'{n} {t}<br/><link href="{u}" color="#17618A">{u}</link>','small')
h('작성 근거 및 재현 정보')
p('실제 수행 기록: 문헌데이터_수집과정_정리.pdf(2026-10-22 작성, 10월 21일 현황), literature_expansion_methods_20261024.pdf 및 현 저장소의 README.md. 초기 API·LLM 사용은 첫 보고서의 기록에 근거하며 현재 남아 있는 원 추출 코드나 호출 로그를 재실행하여 확인한 것은 아니다. 집계는 날짜별 스냅샷으로 구분하였다.','small')
p('투고 시 보완 항목: 검색 기간·플랫폼별 검색식, 실제 LLM 호출 식별자·실행일·전체 프롬프트·정답 시범 여부, 실행별 적용 범위, pH donor 3편 및 최종 사용 데이터 버전. 원래 수집의 직접 참고문헌과 본 문서에서 사후 연결한 방법론적 근거를 구분한다. API 인증 키의 실제 값은 보고하지 않는다.','small')

def footer(c,d):
 c.setStrokeColor(colors.HexColor('#CBD8E0'));c.line(48,802,547,802)
 c.setFont('MG',8);c.setFillColor(colors.HexColor('#5A6C79'))
 c.drawString(48,814,'REE_AL  /  API-based literature data collection')
 c.drawString(48,27,'방법론 개정본 · 2026.10.27');c.drawRightString(547,27,str(d.page))
doc=SimpleDocTemplate(str(OUT),pagesize=(595.28,841.89),rightMargin=48,leftMargin=48,topMargin=56,bottomMargin=47,title='API 기반 문헌 데이터 수집 및 구조화 방법론',author='REE_AL')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
d=pymupdf.open(OUT)
print('PAGES',len(d))
for i,pg in enumerate(d):
 print(i+1,len(pg.get_text()))
 pg.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(str(ROOT/f'tmp/pdfs/api_methods_page_{i+1}.png'))
print(OUT)
