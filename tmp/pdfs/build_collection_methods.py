from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT
import pymupdf

ROOT=Path.cwd()
OUT=ROOT/'output/pdf/REE_AL_data_collection_methodology_20261027.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('MG','C:/Windows/Fonts/malgun.ttf'))
pdfmetrics.registerFont(TTFont('MGB','C:/Windows/Fonts/malgunbd.ttf'))
styles={
 'title':ParagraphStyle('title',fontName='MGB',fontSize=25,leading=36,textColor=colors.HexColor('#13334B'),spaceAfter=16,wordWrap='CJK'),
 'h':ParagraphStyle('h',fontName='MGB',fontSize=15,leading=22,textColor=colors.HexColor('#13334B'),spaceBefore=13,spaceAfter=9,wordWrap='CJK'),
 'sub':ParagraphStyle('sub',fontName='MGB',fontSize=10.5,leading=17,spaceBefore=9,spaceAfter=5,wordWrap='CJK'),
 'body':ParagraphStyle('body',fontName='MG',fontSize=10,leading=17,spaceAfter=9,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='MG',fontSize=8.5,leading=14,spaceAfter=6,wordWrap='CJK'),
 'cell':ParagraphStyle('cell',fontName='MG',fontSize=8.4,leading=13,wordWrap='CJK'),
}
story=[]
def p(t,s='body'): story.append(Paragraph(t,styles[s]))
def h(t): p(t,'h')
def table(rows,widths):
 t=Table([[Paragraph(str(c),styles['cell']) for c in r] for r in rows],colWidths=widths,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E7EFF4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#7693A8')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#D8E0E6')),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
 story.append(t);story.append(Spacer(1,10))
def page(): story.append(PageBreak())

p('REE_AL · METHODS NOTE · 2026.10.27','small')
p('문헌 기반 부식 데이터 수집<br/>및 제로샷 정보 추출 방법론','title')
p('희토류 첨가 저탄소 저합금강의 부식 예측을 위한 데이터 구축','sub')
h('문서의 범위')
p('문헌 검색과 선정, 제로샷 기반 정보 추출, 시편별 조건 연결, 원문 검증, 단위 표준화 및 결측치 처리를 하나의 데이터 수집 체계로 정리하였다. 실제 수집 현황은 2026년 10월 24일 기록에 근거하며, 제로샷의 방법론적 근거는 선행연구와 연결하였다.')
table([['구분','현재 확인된 내용'],['수집 확장','기존 352개 관측치에 3개 문헌의 33개 조건을 추가하여 총 385개'],['타깃 확인','부식전류밀도 확인 377개, 기존 미확인 8개는 평가 제외'],['RE 자료','기존 RE 양성 41개 유지. 신규 33개에서는 RE 함량 확인 없음'],['완전성','정의된 모든 필수 입력을 갖춘 완전 관측치 0개'],['제로샷 수행 근거','모델·프롬프트·대화 로그는 본 문서의 근거 자료에서 확인되지 않음']],[94,405])
h('수행 범위와 방법론의 구분')
p('첨부 기록은 이번 추가 수집에서 원문 표와 프로토콜을 직접 대조했다고 명시하며, AI 추출 API를 호출하여 검증했다고 주장하지 않는다. API 미사용 자체가 제로샷을 배제하지는 않지만, 전체 자료를 제로샷으로 추출했다고 확정할 근거도 아니다. 이에 본 문서는 원문 검증과 데이터 처리의 수행 사실을 기술하고, 제로샷은 적용 조건과 재현 가능한 절차를 별도로 제시한다.')
p('권장 방법명: 원문 검증을 결합한 문헌 기반 부식 데이터 큐레이션. 제로샷 적용 로그를 확보한 범위에 대해서는 “제로샷 LLM 보조 추출 및 원문 검증”으로 구체화할 수 있다.','small')
page()
h('1. 문헌 검색 및 관측치 구성')
p('희토류 및 열처리 조건과 부식전류밀도의 관계를 분석하기 위해 문헌 기반 데이터베이스를 확장하였다. 검색에는 steel 및 stainless steel과 Ce, La, Y, rare earth, corrosion current density, Tafel, heat treatment 및 pH 등의 용어를 조합하였다. 원문은 기존 확보 자료, 출판사 공개 PDF, Europe PMC, Wiley TDM 및 Elsevier API를 통해 확보하였다.')
p('추가 수집 라운드에서는 문헌 후보 14개를 검토하고 3개 문헌을 편입하였다. 이는 기존 데이터베이스를 확장하기 위한 목적 지향적 수집이며, 관련 문헌 전체를 포괄한 체계적 문헌고찰로 정의하지 않는다. 원문 접근 제한, 타깃 미보고 및 식별자 불일치 등의 미편입 사유는 별도 기록으로 관리하였다.')
p('하나의 관측치는 원문에서 구분한 시편과 열처리·시험환경의 조합으로 정의하였다. 반복 측정이 평균과 표준편차로 보고된 경우 중심값을 한 관측치로 기록하였으며, 표준편차나 반복 횟수를 이용하여 행을 추가 생성하지 않았다.')
table([['신규 문헌','추출 범위','수량'],['S275 연강 [5]','원상태·담금질·뜨임, pH 4·7·10, NaCl 또는 Na₂SO₄ 용액','18'],['SLM 17-4 PH 강 [6]','L9 직교실험의 제조·최종 시효 조건','9'],['UNS S41003 강 [7]','시편 410F·410T 및 pH 5.8·4.0·2.0','6']],[112,346,41])
h('1.1. 데이터 스키마와 시편 연결')
p('각 관측치에는 조성 10개 원소(C, Si, Mn, P, S, Cr, Ni, Mo, Cu, N), 보고된 RE 정보, 열처리 온도·시간, 전해질, pH, 시험온도, 주사속도, OCP 안정화 시간 및 부식전류밀도를 연결하였다. DOI, 시편명, 표·절 위치, 원문 단위 및 변환 내역을 함께 보존하였다.')
p('이 구성은 합금 조성에 시험환경·열처리·주사속도 등을 연결한 Nyby et al. [2]의 부식 데이터베이스와 같은 원칙을 따른다. 단, 본 연구의 변수 선택과 시편 연결 규칙은 연구 목적에 맞추어 구성한 것이다.')
page()
h('2. 제로샷 기반 문헌 정보 추출')
p('제로샷은 추출 과제의 입력–정답 시범을 프롬프트에 제공하지 않고, 과제 특화 미세조정 없이 지시문과 원문으로 정보를 추출하는 설정이다. 원문, 변수 정의 및 출력 스키마를 제공하는 것은 제로샷과 양립한다. 반면 추출 정답이 포함된 시범을 제공하면 few-shot 설정에 해당한다. 추가 학습을 하지 않았다는 사실만으로 제로샷을 확정할 수는 없다.')
p('Polak과 Morgan [1]은 ChatExtract에서 관련 문장 식별, 재료–값–단위 추출 및 후속 질문을 통한 확인을 결합하였다. 본 연구에 적용할 때에는 이러한 기본 구조를 시편–부식값–시험조건의 관계 추출로 확장한다. 여러 번 질문하더라도 정답 시범을 제공하지 않으면 제로샷으로 구성할 수 있다. 원문에서 근거를 찾는 것과 모델의 일반 지식으로 결측값을 추정하는 것은 구분한다.')
table([['단계','적용 절차'],['① 입력 준비','표의 제목·머리글·각주와 관련 Methods 문맥을 함께 제공한다.'],['② 관련성 판단','정량 i_corr와 시편 대응 정보가 있는지 확인한다.'],['③ 구조화 추출','시편, 조성, RE, 열처리, 시험조건, 값·단위 및 근거 위치를 반환한다.'],['④ 관계 재확인','수치가 해당 시편의 i_corr인지, 열처리와 시험온도를 혼동하지 않았는지 확인한다.'],['⑤ 최종 편입','원문 대조를 통과한 항목을 편입하고 불명확한 필드는 결측으로 유지한다.']],[91,408])
p('추출 지시문 예시 · 제안 템플릿','sub')
p('“제공한 원문만 근거로 시편별 부식전류밀도와 조성, 희토류 함량, 열처리 및 시험조건을 추출하라. i_corr를 E_corr, 수동태전류 또는 공식전류와 구분하라. 각 값의 원문 단위와 근거 위치를 포함하라. 없는 값은 null로 기록하고, 미보고를 0으로 해석하지 말라. 동일 시편 여부를 확인할 수 없으면 연결을 보류하라.”','small')
p('위 절차와 프롬프트는 제로샷 적용을 위한 방법 설계이며, 과거 수집에 동일하게 사용했다는 기록은 아니다. 원 논문의 문장 중심 ChatExtract를 표·복수 절 간 연결로 확장한 성능은 별도로 검증해야 한다. 재현을 위해 실제 모델 식별자, 실행일, 전체 프롬프트, 예시 제공 여부 및 원출력을 보관한다.','small')
page()
h('3. 원문 검증 및 표준화')
p('목표 변수는 원문 표의 i_corr 열, 단위, 지수 및 행·열 머리글을 대조하여 확인하였다. 조성표와 열처리·시험방법을 시편 ID로 연결하였다. 신규 33개 관측치는 원문 위치에 연결하였고, 관련 표 7개 페이지의 렌더링 결과와 대조하였다. DOI 중복 및 통합 관측치 ID의 유일성을 검사하고 기존 352개 타깃의 보존 여부를 확인하였다.')
p('부식전류밀도는 A/cm²로 통일하였다. μA/cm² 값에는 10⁻⁶을 곱하고, 필요한 전위값은 mV에서 V로 변환하였다. 원문값과 표준화값 및 변환 근거를 구분하여 보존하였다. 일반적인 기대와 다른 값도 전사 오류의 근거가 없으면 임의로 수정하지 않았다. S275의 P 및 S 함량은 원문 표기값을 유지하고 주의사항을 기록하였다.')
p('복수 단계 열처리에서는 마지막 등온 유지 단계의 온도·시간을 대표 변수로 기록하고 이전 단계는 이력으로 보존하였다. 원상태 시편을 0 °C·0 min으로 코딩하지 않았으며, 냉각 과정의 “실온”을 시험온도 25 °C로 간주하지 않았다. 제조조건이 함께 변화한 SLM 자료로부터 열처리의 독립적인 인과효과를 단정하지 않았다.')
h('3.1. 결측값과 원문값의 구분')
p('미보고 조성은 0이 아닌 결측으로 유지하였다. RE 미보고와 명시적 무첨가 0 ppm을 구분하고, 혼합 첨가물 총량을 개별 RE 함량으로 역산하지 않았다. OCP 안정화 시간을 부식 노출시간으로 대신 입력하지 않았다. 이는 Nyby et al. [2]이 제시한 미보고 조성의 NA 보존 및 시험환경 구분 원칙과 부합한다.')
h('3.2. 추출 성능과 데이터 검증의 구분')
p('원문 대조를 마친 최종 데이터의 정확성과 LLM 초벌 추출의 정확도는 다른 평가 대상이다. 제로샷 성능을 보고하려면 수정 전 출력을 독립 정답 자료와 비교하고, 시편–값–단위 일치 및 조건 연결의 정밀도·재현율 등을 산정해야 한다. ChatExtract의 보고 성능을 본 부식 데이터의 성능으로 인용하지 않는다.')
page()
h('4. 결측치 처리와 평가용 데이터 구성')
p('원문값 데이터와 추정값을 포함한 검토본을 분리하였다. 조성 결측치는 강종 계열과 관측 조성이 유사한 타 문헌 자료를 참조하여 보완하였다. 공통 관측 원소가 두 개 이상인 후보를 IQR 정규화 조성 거리로 정렬하고, 원소별로 서로 다른 논문에서 확보한 최소 3개, 최대 5개 참조값의 중앙값을 사용하였다. 추정값을 다시 donor로 사용하지 않았다. 신규 자료에서는 108개 조성 셀을 보완하고 출처·거리·추정값·범위를 기록하였다.')
p('이 방법은 유사한 관측치를 이용하는 이웃 기반 대치 [3]와 개념적으로 연결된다. 그러나 기존 가중 KNNimpute와 동일하지 않으며, IQR 거리, 논문 수 제한 및 중앙값 집계는 본 연구의 규칙이다. 따라서 “유사 조성 기반 donor 중앙값 대치”로 명명하고, 성능이 검증된 표준 알고리즘의 직접 적용으로 표현하지 않는다.')
p('신규 24개 pH는 원문값을 유지하였다. 나머지 9개는 단순 3.5% NaCl·20–30 °C 조건에 제한하여 참고 문헌 3편의 중앙값 6.5로 검토용 보완하였다. 이는 제로샷 추출이 아닌 별도 대리값 부여이며, 실측 pH로 취급하지 않는다. 최종 논문에는 donor 3편과 선택 근거를 보완 로그에서 확인하여 추가해야 한다.')
table([['데이터 범위','관측치 수','의미'],['통합 검토본','385','조건별 문헌 관측치 전체'],['확인 타깃','377','i_corr 확인 자료. 완전 입력 자료라는 의미는 아님'],['열처리 확인 부분집합','342','별도 기준으로 정의된 평가 범위'],['전체 필수 입력 완전행','0','조성·RE·환경·시험법·열처리 모두 요구 시']],[153,62,284])
p('평가에서는 데이터 분리 후 학습 데이터 내부에서 대치 규칙을 결정하는 원칙을 사용한다. 검토용 전역 보완본을 그대로 평가에 사용하면 정보 누출이 생길 수 있으므로 구분한다 [4]. 새로운 문헌에 대한 일반화 검증을 위해 DOI 단위 분리 평가를 추가할 수 있으나, 이는 현재 기록에서 완료가 확인된 절차와 구분되는 후속 제안이다.')
p('문헌 데이터 구축은 후속 active learning의 초기 자료 준비 단계이다. 문헌 수집이나 제로샷 추출 자체를 순차 실험이 완료된 것으로 기술하지 않는다.','small')
page()
h('5. 보관·재현 및 최종 기술 기준')
p('원문값, 보완 검토본, 행·필드별 출처, 문헌 선정 사유, 결측 현황 및 대치 이력을 분리하여 보관하였다. 기록상 운영 데이터와 모델은 변경하지 않고 별도 평가를 수행하였다. 자료 확대와 제로샷 적용 여부는 수집 라운드별로 기록하여, 수행 방식이 다른 관측치를 모두 동일한 추출 방식으로 묶지 않는다.')
p('최종 Methods에는 검색 플랫폼별 검색식·기간, 제로샷 적용 문헌과 관측치 범위, 모델·프롬프트·정답 예시 여부, 검증 담당과 판정 기준, donor 문헌 및 실제 평가 분할·대치 설정을 추가한다. 수행 로그가 확인되기 전에는 “모든 자료를 제로샷으로 자동 추출하였다”는 표현을 사용하지 않는다.')
h('참고문헌')
refs=[
('[1]','Polak, M. P. & Morgan, D. (2024). Extracting accurate materials data from research papers with conversational language models and prompt engineering. Nature Communications, 15, 1569.','https://doi.org/10.1038/s41467-024-45914-8'),
('[2]','Nyby, C. et al. (2021). Electrochemical metrics for corrosion resistant alloys. Scientific Data, 8, 58.','https://doi.org/10.1038/s41597-021-00840-y'),
('[3]','Troyanskaya, O. et al. (2001). Missing value estimation methods for DNA microarrays. Bioinformatics, 17, 520–525. 유사 관측치 기반 대치의 개념적 근거이며 부식 자료의 성능 검증 근거는 아님.','https://doi.org/10.1093/bioinformatics/17.6.520'),
('[4]','Kapoor, S. & Narayanan, A. (2023). Leakage and the reproducibility crisis in machine-learning-based science. Patterns, 4, 100804.','https://doi.org/10.1016/j.patter.2023.100804'),
('[5]','S275 신규 수집 원문. Metals (2022). 원문 표 1·6·7 및 절 2.2·2.5·3.1을 수집 기록에서 지정.','https://doi.org/10.3390/met12081386'),
('[6]','SLM 17-4 PH 신규 수집 원문. Metals (2025). 원문 표 2·3 및 절 2.2·2.3을 수집 기록에서 지정.','https://doi.org/10.3390/met15030232'),
('[7]','UNS S41003 신규 수집 원문. Metals (2025). 원문 표 1·5 및 절 2.1·2.3을 수집 기록에서 지정.','https://doi.org/10.3390/met15080880'),
]
for num,txt,url in refs:p(f'{num} {txt}<br/><link href="{url}" color="#17618A">{url}</link>','small')
p('수행 사실의 근거: literature_expansion_methods_20261024.pdf, 2026-10-24, 총 5쪽. [5]–[7]의 추출 범위와 수량은 해당 기록에 근거한다. 본 문서는 원문 재추출이나 LLM 성능 평가를 새로 수행한 보고서가 아니다.','small')

def footer(c,d):
 c.setStrokeColor(colors.HexColor('#CBD8E0'));c.line(48,802,547,802)
 c.setFont('MG',8);c.setFillColor(colors.HexColor('#5A6C79'))
 c.drawString(48,814,'REE_AL  /  Literature data collection methodology')
 c.drawString(48,27,'수집 현황 2026.10.24 · 문서 작성 2026.10.27')
 c.drawRightString(547,27,str(d.page))
doc=SimpleDocTemplate(str(OUT),pagesize=(595.28,841.89),rightMargin=48,leftMargin=48,topMargin=56,bottomMargin=47,title='문헌 기반 부식 데이터 수집 및 제로샷 정보 추출 방법론',author='REE_AL')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
d=pymupdf.open(OUT)
print('PDF',OUT,'PAGES',len(d))
for i,pg in enumerate(d):
 print(i+1,len(pg.get_text()),'blocks',len(pg.get_text('blocks')))
 pg.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(str(ROOT/f'tmp/pdfs/methods_page_{i+1}.png'))
