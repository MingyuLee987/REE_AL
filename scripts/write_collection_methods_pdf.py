"""A source-traceable Korean methods report for the actual 352-row artifact."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
import pandas as pd
import pymupdf
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/al_RE_more_confirmed_20261023'
OUT=ROOT/'output/pdf/REE_실험데이터_수집및보완방법_352행_정리.pdf'
TMP=ROOT/'tmp/pdfs/collection_methods_352'
NAVY=colors.HexColor('#163B58');TEAL=colors.HexColor('#147D85');INK=colors.HexColor('#243747');GRAY=colors.HexColor('#657887')

def main():
 OUT.parent.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
 df=pd.read_csv(DATA/'al_RE_expanded_review.csv');missing=pd.read_csv(DATA/'missingness.csv');re=df[df.RE_ppm.gt(0)]
 assert len(df)==352 and len(re)==41 and int(re.target_verified.sum())==34 and int(re.checked_heat_label_available.sum())==22
 for name,file in [('KR','malgun.ttf'),('KRB','malgunbd.ttf')]:pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
 pdfmetrics.registerFontFamily('KR',normal='KR',bold='KRB',italic='KR',boldItalic='KRB')
 styles={
 'title':ParagraphStyle('title',fontName='KRB',fontSize=22,leading=32,textColor=NAVY,spaceAfter=15,wordWrap='CJK'),
 'sub':ParagraphStyle('sub',fontName='KRB',fontSize=15,leading=23,textColor=NAVY,spaceAfter=13,wordWrap='CJK'),
 'h':ParagraphStyle('h',fontName='KRB',fontSize=11,leading=17,textColor=TEAL,spaceBefore=12,spaceAfter=7,wordWrap='CJK'),
 'body':ParagraphStyle('body',fontName='KR',fontSize=9.7,leading=16,textColor=INK,spaceAfter=8,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='KR',fontSize=8.2,leading=13,textColor=GRAY,spaceAfter=7,wordWrap='CJK'),
 'cell':ParagraphStyle('cell',fontName='KR',fontSize=8.5,leading=13,textColor=INK,wordWrap='CJK'),
 'head':ParagraphStyle('head',fontName='KRB',fontSize=8.6,leading=13,textColor=colors.white,wordWrap='CJK')}
 story=[];W=A4[0]-88
 def para(text,kind='body'):return Paragraph(text,styles[kind])
 def p(text,kind='body'):story.append(para(text,kind))
 def h(text):p(text,'h')
 def table(rows,widths):
  t=Table([[para(escape(str(v)),'head' if i==0 else 'cell') for v in row] for i,row in enumerate(rows)],colWidths=widths,repeatRows=1,hAlign='LEFT')
  t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#EEF4F6'),colors.white]),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#D1DCE2'))]));story.extend([t,Spacer(1,8)])
 def page(title):
  if story:story.append(PageBreak())
  p(title,'sub')

 p('희토류 첨가 철강의<br/>부식 실험데이터 수집 방법','title')
 p('문헌 검색 · 시편 연결 · 단위 환산 · 결측 보완 · 검증 기록','h')
 p('<b>작성 기준일: 2026-10-23</b> | 현재 통합 검토본 352행 / 63개 출처','small')
 p('본 보고서는 REE_AL 작업에서 실제 수행한 문헌 기반 데이터 준비 과정을 정리한다. 새 실험을 직접 실시한 보고서가 아니라, 출판 논문의 실험값을 시편·처리·시험조건별로 연결해 CSV로 구성한 기록이다. 목표 타깃은 log10(icorr [A/cm2])이며 공정 피처는 열처리 온도와 유지시간 두 개로 한정하였다.')
 table([['현재 집계','행 수','정확한 의미'],['전체 통합 검토본','352','일반강·스테인리스강·희토류 첨가강을 포함'],['타깃 + 열처리 쌍 확인','321','다른 조성·환경 피처가 모두 완비됐다는 뜻은 아님'],['RE 함량 수치 기입','52','무첨가 비교군 0 ppm 11행 포함'],['RE 양성 (RE_ppm > 0)','41','13개 출처; 명목 배합/보고 분석값의 근거는 별도 확인'],['RE 양성 중 타깃 검증 표시','34','기존 7행의 미검증 타깃은 검토본에만 보존'],['RE 양성 중 타깃 + 열처리 확인','22','41행 전체를 완전 학습자료로 부르지 않음']],[159,49,W-208])
 h('352행과 41행이 다른 이유')
 p('352행은 전체 부식 실험 관측 수이고, 41행은 그 안에서 RE 첨가량이 양수로 기입된 부분집합이다. 52행은 0 ppm 비교군도 포함한 함량 기입 수다. 논문 수, 시편 수, 독립 반복측정 수는 서로 같지 않으며, 보고된 평균과 표준편차를 별도 실험행으로 나누지 않았다.')
 p('이 보고서의 숫자는 data/al_RE_more_confirmed_20261023/의 현재 CSV를 다시 읽어 산출하였다. 과거 279·317·336행 등의 집계는 버전 이력이며 현재 자료와 합산하지 않는다.','small')

 page('1. 검색 범위와 원문 확보')
 h('검색 대상과 조합')
 p('steel / stainless steel / low-alloy steel에 rare earth, cerium, lanthanum, yttrium, Ce, La, Y와 corrosion current density, icorr, Tafel, potentiodynamic polarization을 조합해 후보를 찾았다. 공정 자료가 필요할 때 annealing, solution treatment, aging, tempering, temperature, holding time을 함께 확인했다. 희토류 함량이 실제로 합금 시편에 속하는지 확인하기 위해 microalloying·bulk composition·ICP-MS·chemical composition 표도 추적했다.')
 table([['확보 경로','실제 사용과 한계'],['기존 로컬 원문·보충표','이전에 확보한 PDF/XML/본문/표 캐시를 우선 재활용. 캐시가 있다는 이유만으로 수치 포함을 승인하지 않음.'],['공개 원문','Europe PMC XML, MDPI PDF, J-STAGE, 학술기관 공개 원고 및 출판사 HTML 표를 확보.'],['출판사 API','Elsevier 검색, Wiley TDM 등 접근 가능한 경로 사용. Elsevier 일부 원문 및 Springer API는 접근 제한이 있어 검색 성공과 원문 확보를 구분.'],['OpenAI 보조 추출·검토','확보한 본문을 구조화하고 별도 호출로 일부 수치를 검토. 호출 성공 자체가 실험값의 진실성을 증명하지 않음.'],['직접 원문 대조','OpenAI 잔액 소진 후 확보된 원문의 표·본문을 직접 대조. 최신 RE 양성 8행은 직접 대조 방식으로 기록.']],[112,W-112])
 h('후보 선별')
 p('같은 철강 시편의 조성 또는 RE 첨가량과 실험 icorr가 연결되는 연구를 우선한다. 희토류를 용액에 넣은 억제제 실험, 희토류 코팅, 비철 합금의 실험을 RE 첨가 철강으로 집계하지 않는다. 원문 없이 초록만 있는 경우, 부동태·임계·공식 전류를 icorr로 바꿔 넣는 경우, 부식률만 제공된 경우도 구분한다.')
 h('검색 완료 범위의 표현')
 p('본 작업은 접근 가능한 문헌의 반복 확장 수집이다. 데이터베이스 전체의 재현 가능한 단일 검색식·검색일별 총 검색 건수·모든 중복 제거 건수를 고정한 체계적 문헌고찰이나 PRISMA 보고서로 주장하지 않는다. 접근 실패·단위 충돌·열처리 부족 등의 이유는 가능한 범위에서 후보·검토 기록에 남겼다.')

 page('2. 한 행을 만드는 기준과 수치 검증')
 h('관측 단위')
 p('<b>한 행 = 논문 출처 + 시편/재료 상태 + 열처리 이력 + 부식시험 조건의 조합</b>이다. 같은 시편이라도 전해질, 시험온도, 침지시간 등이 다르면 다른 조건의 관측이 될 수 있다. 반대로 같은 기준 시편이 여러 표나 본문에 반복 등장한 것은 중복으로 늘리지 않는다.')
 table([['단계','수행한 확인'],['시편 매칭','표의 행·열, 본문의 시편명, 공통 실험 절, 보충자료를 대조. 시편명이 없는 숫자는 함부로 다른 시편과 연결하지 않음.'],['타깃 확인','실험 분극곡선의 Tafel/분극 적합 icorr를 확인. 부식률, EIS 저항, ip, ic, Ipit와 구분.'],['인용문 검사','추출 인용문이 확보한 원문 블록에 실제 존재하는지 코드로 검사. 이 검사만으로 열·시편 매칭이 맞다고 판단하지 않음.'],['단위·열 위치 대조','원래 단위, 지수 배율, 해당 열을 재확인. PDF의 기하 텍스트 블록과 필요시 표 렌더를 함께 확인.'],['최종 상태 기록','target_verified, target_review_status, 열처리 확인 여부와 원문 위치를 남김. 미검증 기존 행은 보존하되 확인본에서 제외.']],[104,W-104])
 h('숫자 재구성과 반복 측정')
 p('원문 표 또는 본문에 직접 보고된 중심값을 사용하였다. 표준편차·오차막대는 독립 타깃으로 만들지 않았다. 새로 포함한 값에 대해 곡선을 임의로 읽어 행 수를 늘리지 않았고, 보고되지 않은 시험조건을 복제해 새로운 실험으로 세지 않았다. 기존 8행의 타깃 미검증 상태는 그대로 보존되므로 전체 352행이 모두 동일한 수준으로 검증된 것은 아니다.')
 h('출처 기록 항목')
 p('record_id, source_paper_id(DOI 등), source_sample_id, source_url, 원문 인용문, 표/쪽/블록 위치, 원 단위, 환산 방법, 실측·명목·proxy·통계 대치 여부를 기록한다. 기존 행의 출처는 해당 이전 버전의 provenance도 함께 참조한다.')

 page('3. 단위 통일과 희토류 함량의 처리')
 table([['항목','표준 단위 / 규칙','예시'],['부식전류밀도','A/cm2로 통일','250 microA/cm2 = 2.50 × 10^-4 A/cm2'],['표 머리의 지수','명시된 지수를 먼저 반영','icorr ×10^-7 A/cm2 열의 2.592 → 2.592 ×10^-7'],['RE 함량','벌크 wt.% × 10000 = ppm','Ce 0.0095 wt.% → 95 ppm'],['혼합 RE','같은 시편의 RE 원소만 합산','La 0.002 + Ce 0.003 wt.% → 합계 50 ppm'],['온도','K - 273.15 = °C','1333 K → 1059.85 °C'],['유지시간','h ×60, s ÷60 → min','1 h → 60 min, 2 s → 0.03333 min'],['원자 조성','전체 원자 배합이 있을 때만 wt.% 환산','w_i = 100 x_i M_i / Σ(x_j M_j)']],[82,177,W-259])
 h('투입량, 실제 벌크 함량, 국부 EDS를 구분')
 p('명목 배합 또는 시편 라벨을 실제 잔류 분석값으로 부르지 않는다. 예를 들어 La 0.5 wt.%라는 라벨과 벌크 분석값 0.49 wt.%가 함께 있으면 후자는 4900 ppm으로 기록하고 기준을 명시한다. 개재물·석출물·부식생성물 EDS의 RE 비율은 강재 전체 조성이 아니므로 RE_ppm에 넣지 않는다. 미보고 RE는 0 ppm으로 채우지 않는다.')
 h('직접 검토한 신규 RE 관측 8행')
 table([['출처','시편 / RE','icorr (A/cm2)','열처리 쌍'],['[1]','Al 및 Ti/Zr 탈산강 / La+Ce 50 ppm','4.60×10^-5 / 2.93×10^-5','미보고'],['[2]','교량강 / Ce 6, 10 ppm','3.30×10^-4 / 3.19×10^-4','유지시간 미보고'],['[3]','FSS2/3/4 / Ce 480, 560, 530 ppm','2.50×10^-4 / 2.35×10^-4 / 1.72×10^-4','1000 °C / 1 min'],['[4]','CE190 / Ce 190 ppm','1.024×10^-4','1059.85 °C / 30 min']],[38,151,151,W-340])
 p('이 8행은 RE 양성 33행에서 41행으로 확장한 최신 추가분이다. RE로 icorr가 낮아진 사례만 골라 넣지 않았다. 원문의 열 이름과 수치를 보존하며, [4]에서는 RE 첨가 시편의 icorr가 기준 시편보다 높아도 배제하지 않았다.','small')

 page('4. 열처리 온도·시간의 추출 기준')
 h('추가 공정 피처는 두 개')
 p('<b>heat_treatment_temperature_C</b>: 해당 등온 유지단계의 온도.<br/><b>heat_treatment_time_min</b>: 같은 단계의 유지시간. 결정립 크기·상분율·냉각매체·용접 파라미터 등은 이번 추가 공정 피처로 사용하지 않았다.')
 table([['원문 상황','현재 처리'],['여러 단계가 명시됨','신규 자료는 마지막 명시적 등온 유지단계를 기본으로 택하고 앞선 이력을 heat_history_note로 보존.'],['FSS: 소둔 10 min → 냉간압연 → 재결정 소둔 1 min','최종 1000 °C / 1 min을 사용. 앞선 10 min을 최종 유지시간으로 연결하지 않음.'],['Ce-316L: 1200 °C / 2 h → 단조 → 1050 °C 용체화','최종 온도 1050 °C만 확인. 시간은 결측. 앞선 2 h와 섞지 않음.'],['압연 온도·냉각속도만 보고','등온 유지시간을 역산하지 않음. 상온 냉각을 0 °C·0 min으로 표현하지 않음.'],['시험온도·OCP·침지시간','열처리 온도·시간과 다른 피처로 관리. 세척·건조시간을 열처리로 대입하지 않음.']],[169,W-169])
 h('기존 버전과의 일관성')
 p('기존 자료에는 용체화·시효·소결·빌릿 재가열 등 서로 다른 대표 단계가 남아 있다. 예를 들어 기존 SASS 자료 일부는 용체화 쌍을 보존하고 이후 시효를 메타데이터에 남겼다. 따라서 현재 352행을 하나의 동일한 최종 처리단계로 통일했다고 주장하지 않는다. heat_treatment_stage와 thermal_history_incomplete를 함께 확인해야 한다.')
 h('표현하지 못하는 공정·조성의 효과')
 p('두 숫자로 다단계 이력과 냉각매체의 차이를 모두 설명할 수 없다. 또한 신규 FSS3/FSS4/CE190의 W 0.58/1.12/3.40 wt.%는 메타데이터로 보존했으나 현재 핵심 조성 피처에는 W가 없다. 열처리 쌍이 확인되었다는 이유만으로 이 자료를 그대로 AL 설계공간에 넣을 수 있는 것은 아니다.')
 p('온도·시간과 icorr는 다른 논문의 중앙값이나 모델 예측으로 채우지 않았다. 현재 온도 결측은 28/352행(7.95%), 시간 결측은 31/352행(8.81%)이다.','small')

 page('5. 조성 결측과 pH 보완')
 h('제공된 조성 보완 PDF에서 적용한 원칙')
 p('원문·보충자료에서 직접 복구 → 동일 논문 모재/원료 proxy 또는 명목 배합 → 명시된 범위의 대표값 가정 → 제한적인 다른 논문 참고 순으로 근거 수준을 구분했다. 제조사 대표값이나 원료 조성은 해당 제조 후 강재의 벌크 실측값이 아님을 표시한다. 상한 U의 U/2, 범위 중간값도 프로젝트 가정이지 측정값이 아니다.')
 p('남은 핵심 조성 C·Si·Mn·P·S·Cr·Ni·Mo·Cu·N은 같은 강종 계열에서 관측 원소가 2개 이상 겹치는 후보를 IQR 정규화 거리로 비교한다. 논문당 하나씩 최소 3개·최대 5개 출처를 골라 중앙값을 사용하며, 참고 논문이 부족하면 빈칸을 유지한다. 추정 조성을 다시 donor로 쓰거나 icorr를 조성 추정 입력으로 쓰지 않는다.')
 h('pH는 별도 확장 규칙')
 p('제공 PDF는 조성 보완 문서이며 pH 전용 대치식을 제시하지 않는다. pH 보완은 원문 우선·방법 표시·논문 간 참고 원칙을 확장한 프로젝트 규칙이다. 조성의 U/2를 pH에 그대로 적용하지 않았다.')
 table([['현재 pH 상태','행 수','처리 의미'],['기존 원문 보고값 보존','69','pH_reported에 보존. 값의 신규 재측정을 뜻하지 않음.'],['같은 전해질 3개 논문 중앙값','98','단순 3.5% NaCl, 실온 또는 20-30 °C만 대상. 5.9·6.5·7.4의 논문별 중앙값 → 6.5.'],['같은 논문 용액 proxy','4','0.1 M H2S 응력부식 용액의 pH 3.0을 전기화학 용액 proxy로 표시. 직접 Tafel pH 보고와 구분.'],['하한만 보고','3','알칼리 해수 pH >14. 부등호를 보존하며 pH=14로 대입하지 않음.'],['원문값·추정값 모두 없음','178','그대로 결측 유지. 하한만 있는 3행까지 합치면 수치 결측 181행.']],[148,40,W-188])
 p('pH 수치 기입은 171/352행, 결측률은 51.42%이다. 그중 102행은 대리값/추정값이다. 산·알칼리·CO2·해수·탈기 조건으로 중앙값을 확대하지 않았고, 세척용 PBS pH를 부식시험 pH로 옮기지 않았다. 5.9-7.4는 참고값 범위이며 신뢰구간이 아니다. pH가 실제로 복원됐거나 예측성능이 향상됐다고 주장하지 않는다.','small')

 page('6. 품질 관리와 AL 사용 범위')
 h('별도 보관한 자료')
 table([['분리 자료','행 수','이유'],['희토류 플럭스 첨가 용접금속 [5]','4','REE-Si-Fe의 플럭스 첨가율만 보고. 강재 잔류 RE ppm으로 변환하지 않음. 전체 352행·RE 양성 41행에 합산하지 않음.'],['EH36 La/Ce/Pr 후보 [6]','3','±5 mV 주사범위와 Tafel 설명 충돌, Ce 함량의 표/서론 불일치. 확인 전 주 자료에 넣지 않음.'],['기존 타깃 미검증','8','전체 검토본에 상태를 남겨 보존. RE 양성 7행 포함. 타깃+열처리 확인본에서 제외.']],[139,37,W-176])
 h('검증과 누출 방지')
 p('양의 타깃, record_id 중복, 이전 행 타깃·pH 값 보존, 온도·시간 확인 상태, 단위 환산, 운영 CSV·모델 해시 보존을 점검했다. 이는 데이터 구조·출처 검증이며 모델 성능 검증은 아니다. 같은 논문의 서로 다른 행을 무작위로 학습/검증에 나누면 논문 특성이 공유될 수 있어 source_paper_id 단위 분리가 필요하다.')
 p('독립 평가에서는 원래 결측 자료를 먼저 논문별로 분리한 뒤, 조성 donor·IQR와 pH donor 선택을 학습 fold에서만 수행해야 한다. 이전 344행 버전에서 5개 논문 그룹 fold를 만들었으나, 이 파일을 현재 352행 버전의 fold 결과로 부르지 않는다. pH 보고 donor가 3개뿐이어서 한 논문이 검증군에 들어가면 최소 donor 기준을 만족하지 못해 결측이 다시 남는다.')
 h('현재 데이터로 할 수 있는 해석')
 p('희토류 첨가·조성·열처리·환경과 icorr의 관계를 탐색할 수 있으나, 문헌 간 차이와 추정값을 포함한 상관관계를 희토류의 독립적인 인과효과로 해석하지 않는다. 실제 AL은 같은 강종·처리단계·선행 이력·시험환경으로 범위를 좁히고, 제조 전에 알 수 있는 명목 배합과 제조 후 잔류 분석값을 구분해야 한다.')
 p('현재 모든 선택 피처가 완비된 행은 0행이다. 전체 검토본의 전역 대치값은 검토용이며, 원문값만 사용한 경우와 추정값을 허용한 경우의 민감도 비교가 필요하다. 모델 재학습, 독립 성능 평가 및 새로운 실험 검증은 이번 수집 작업에서 수행하지 않았다.','small')

 page('7. 재현 파일과 출처')
 table([['현재 폴더: data/al_RE_more_confirmed_20261023/','용도'],['al_RE_expanded_review.csv','전체 352행. 기존 미검증 타깃·대치값 상태 포함.'],['al_heat_checked_RE_expanded.csv','타깃+열처리 쌍 확인 321행. 다른 피처 결측은 남음.'],['RE_positive_quantified.csv','RE 양성 41행. 검증 수준은 행별 상태 확인.'],['new_RE_positive_rows.csv','최신 RE 양성 추가 8행.'],['new_source_provenance.csv / missingness.csv','새 값의 원문 위치·방법 / 현재 결측 집계.'],['RE_flux_addition_only_separate.csv / RE_protocol_unresolved_separate.csv','주 자료와 분리한 4행 / 3행.']],[282,W-282])
 p('이전 보완 근거: data/al_RE_pH_enriched_20261023/의 pH_imputation_log.csv, new_RE_source_provenance.csv 및 이전 버전 provenance. 재생성 코드: scripts/add_confirmed_RE_experiments.py, enrich_RE_pH.py, build_heat_expansion.py, verify_heat_round4_primary.py. 원문·표 렌더: outputs/RE_more_20261023/ 및 기존 문헌 캐시.','small')
 h('원문 근거와 대조 위치')
 refs=[
 ('[1] RE 개재물과 미세합금강의 초기 해양 부식','10.3390/ma12203359','Tables 1-2, 실험 절: ICP-MS 조성, 분극 icorr, NaCl 조건.'),
 ('[2] Ce 미량 첨가 고강도 내후성 교량강','10.3390/met15010085','Tables 1, 7 / 3.4.1절: Ce 분석값, 분극 icorr, 9일 조건.'),
 ('[3] Ce·W 첨가 444형 페라이트계 강의 부동태 거동','10.20964/2019.03.31','Tables 1-2, PDF 3-4쪽: 최종 소둔 1 min, icorr 최우측 열.'),
 ('[4] Ce 첨가 하이퍼 듀플렉스강의 황산 중 부동태 거동','10.2320/matertrans.M2015145','Tables 1-2, 실험 절: Ce 190 ppm, K 온도, 분극 icorr.'),
 ('[5] RE 첨가 10CrNi3MoV FCAW 용접금속','10.1155/2018/4071352','Tables 1-2, 6, 10: 플럭스 첨가량과 강재 벌크 함량의 구분.'),
 ('[6] RE 첨가 EH36 해양 플랫폼강','10.3390/coatings14040413','Table 2, 2.4절, Figure 5 본문: 함량·주사범위 충돌 검토.'),
 ('[7] pH 중앙값 donor 3개 원문','10.3390/ma17235687 ; 10.1155/ijco/5531986 ; 10.3390/ma14247863','각 실험 절의 3.5% NaCl pH 5.9 / 6.5 / 7.4. 실험용액 조정의 차이는 남음.')]
 for title,doi,note in refs:
  p('<b>'+escape(title)+'</b><br/>'+escape(doi)+'<br/>'+escape(note),'small')
 p('방법 기준 문서: 사용자가 제공한 「문헌데이터_수집과정_정리_조성보완_개정본.pdf」, 특히 4-5쪽. 조성 보완의 배경 문헌을 현재 pH 대치식의 직접 근거로 전용하지 않았다.','small')

 def footer(c,doc):
  c.saveState();c.setStrokeColor(colors.HexColor('#C9D9E1'));c.line(44,A4[1]-39,A4[0]-44,A4[1]-39);c.setFont('KR',8);c.setFillColor(GRAY);c.drawString(44,A4[1]-29,'REE RESEARCH  |  문헌 실험데이터 수집·보완 기록');c.drawString(44,27,'2026-10-23  ·  352행 버전  ·  데이터 준비와 성능 검증을 구분');c.drawRightString(A4[0]-44,27,str(doc.page));c.restoreState()
 doc=SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=57,bottomMargin=47,title='희토류 첨가 철강의 부식 실험데이터 수집 방법',author='REE_AL research data preparation')
 doc.build(story,onFirstPage=footer,onLaterPages=footer)
 pdf=pymupdf.open(OUT);assert len(pdf)==8,len(pdf)
 texts=[]
 for i,page in enumerate(pdf):
  texts.append(page.get_text());page.get_pixmap(matrix=pymupdf.Matrix(1.25,1.25)).save(str(TMP/f'page-{i+1}.png'))
 for token in ['352','321','41','34','22','51.42','102']:assert token in '\n'.join(texts),token
 (TMP/'extracted.txt').write_text('\n\n'.join(texts),encoding='utf-8')
 (TMP/'validation.json').write_text(json.dumps(dict(pages=len(pdf),source_rows=len(df),RE_positive=len(re),RE_target_verified=34,RE_target_and_heat_checked=22,pH_reported=69,pH_estimated=102,rendered_pages=8),indent=2),encoding='utf-8')
 print(OUT);print('8 pages rendered')

if __name__=='__main__':main()
