"""Two Korean reports: random evaluation protocol and audited collection record."""
import json,sys,hashlib
from pathlib import Path
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1]
import pandas as pd,numpy as np,pymupdf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak,Image,Spacer
DEST=ROOT/'data/al_expanded_20261024';RES=ROOT/'results/random_protocol_20261024';TMP=ROOT/'tmp/pdfs/random_and_collection_20261024';TMP.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'output/pdf';OUT.mkdir(parents=True,exist_ok=True)
s=json.loads((DEST/'summary.json').read_text());e=json.loads((RES/'summary.json').read_text());m=pd.read_csv(RES/'metrics.csv');pred=pd.read_csv(RES/'predictions.csv');new=pd.read_csv(DEST/'new_rows_source_only.csv');missing=pd.read_csv(DEST/'missingness.csv');review=pd.read_csv(DEST/'expanded_review.csv');raw=pd.read_csv(DEST/'expanded_source_only.csv');screen=pd.read_csv(DEST/'screening_log.csv')
for name,f in [('KR','malgun.ttf'),('KRB','malgunbd.ttf')]:pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+f))
pdfmetrics.registerFontFamily('KR',normal='KR',bold='KRB')
NAVY=colors.HexColor('#163B58');TEAL=colors.HexColor('#147D85');GREY=colors.HexColor('#607585')
styles={k:ParagraphStyle(k,fontName='KRB' if k in ['title','h'] else 'KR',fontSize=size,leading=lead,textColor=NAVY,wordWrap='CJK',spaceAfter=8) for k,size,lead in [('title',21,29),('h',12,20),('body',9.5,16),('small',8,12),('cell',8.1,12)]}
W=A4[0]-88
class Report:
 def __init__(self,name,label):self.name=name;self.label=label;self.story=[]
 def p(self,t,kind='body'):self.story.append(Paragraph(t,styles[kind]))
 def h(self,t):self.p(t,'h')
 def page(self,t):
  if self.story:self.story.append(PageBreak())
  self.p(t,'title')
 def table(self,rows,widths):
  t=Table([[Paragraph(escape(str(v)),styles['cell']) for v in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
  t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DDECF1')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F5F7')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),5)]));self.story.append(t);self.story.append(Spacer(1,8))
 def link(self,url,label):self.p(f'<link href="{escape(url)}" color="#147D85">{escape(label)}</link>','small')
 def save(self):
  def foot(c,d):
   c.setFont('KR',7.5);c.setFillColor(GREY);c.drawString(44,27,'REE_AL | '+self.label+' | 2026-10-24');c.drawRightString(A4[0]-44,27,str(d.page))
  path=OUT/self.name;SimpleDocTemplate(str(path),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=43,bottomMargin=45,title=self.label,author='REE_AL').build(self.story,onFirstPage=foot,onLaterPages=foot)
  pdf=pymupdf.open(path);folder=TMP/path.stem;folder.mkdir(exist_ok=True)
  for i,p in enumerate(pdf):p.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(str(folder/f'page-{i+1}.png'))
  text='\n'.join(p.get_text() for p in pdf);(folder/'text.txt').write_text(text,encoding='utf-8');print(path,len(pdf),flush=True);return dict(path=str(path),pages=len(pdf),text=text)
def main_report():
 r=Report('icorr_random_split_method_20261024.pdf','Random split evaluation')
 r.page('icorr 예측 모델<br/>무작위 분리 평가 방법')
 r.p('주 평가: 무작위 80:20 holdout | 보조 평가: 무작위 5-fold | 2026-10-24','small')
 r.h('이번에 실제로 실행한 방식')
 r.p('행 기준 무작위 분리를 주 평가로 사용했다. 확장 자료에서 icorr 확인 상태가 유효한 377행을 골라 학습 301행과 테스트 76행으로 분리했다. 논문 ID는 출처 추적용이며 예측 입력으로 사용하지 않았다. 이번 보고서의 주 성능은 논문 단위 분리가 아니라 아래의 무작위 holdout 결과이다.')
 r.table([['평가 자료','Train / Test','Test R² (log10)'],['기존 운영 자료 279행','223 / 56',f'{e["main_evaluation"][0]["r2_log10"]:.4f}'],['확장 확인 자료 377행 - 주 결과','301 / 76',f'{e["main_evaluation"][1]["r2_log10"]:.4f}'],['열처리·타깃 확인 342행 - 보조','273 / 69',f'{e["main_evaluation"][2]["r2_log10"]:.4f}']],[235,110,W-345])
 r.p('전체 검토본 385행 중 기존 icorr 미확인 8행은 평가에서 제외했다. 342행은 377행 중 열처리 온도·시간과 타깃 확인 조건을 만족하는 부분집합이며, 모든 입력이 원문 실측으로 완비된 집합이라는 뜻은 아니다.')
 r.h('icorr를 목표로 정한 이유')
 r.p('연구 목적은 조성·공정·환경에 따른 부식 반응 속도를 예측하고 낮은 부식전류밀도를 보이는 후보를 찾는 것이다. icorr는 전기화학적 부식속도와 연결되므로 주 목표로 설정했다. 균일부식의 침투속도는 icorr × 당량 / 밀도에 비례하며, 재료별 당량과 밀도가 다르면 같은 icorr가 같은 침투속도를 뜻하지 않는다. [1]')
 r.p('Ecorr는 양극·음극 부분전류가 균형을 이루는 혼합전위이다. 전위의 양의 이동만으로 속도 저감을 단정하지 않으므로, Ecorr는 공동 예측의 보조 목표로 추후 비교할 수 있다. 이번 모델은 icorr 단일 출력이며 Ecorr 공동 학습의 효과를 검증한 결과가 아니다.')
 r.h('다른 AI 논문과의 방법상 관계')
 r.p('부식 예측에서도 무작위 70:30 또는 80:20 분리를 사용하는 실제 사례가 있다. 따라서 무작위 분리를 주 평가로 보고할 수 있다. 다만 전체 분야에서 어느 방식이 다수인지 계량 조사한 것은 아니다. [2, 3]')
 r.page('1. 자료 준비부터 test 평가까지')
 steps=[['순서','실행 내용'],['1. 정답 확인','385행 중 target_verified=True, icorr>0인 377행 선택. 미확인 8행 제외'],['2. 정답 변환','y = log10(icorr / (A/cm²)). 원래 단위는 A/cm²로 통일'],['3. 무작위 분리','train_test_split(test_size=0.2, shuffle=True, random_state=42). 분리 ID를 CSV로 저장'],['4. 학습 내부 보완','원문값 CSV에서 분리. 조성 donor 선택·중앙값 대치·스케일링·범주 인코딩은 train에만 적합'],['5. 고정 모델 학습','RBF SVR, C=10, epsilon=0.15, gamma=scale. 이번에 test 점수를 보고 설정을 바꾸지 않음'],['6. 테스트 예측','학습된 전처리를 test에 적용하고 중앙 SVR로 예측. Ecorr·icorr·논문 ID는 설명변수에서 제외'],['7. 성능 계산','log10 척도의 R²·RMSE·MAE와 역변환 원척도 R²를 별도 산출'],['8. 보조 확인','확장 377행 무작위 5-fold 결과와 열처리 확인 342행 holdout 결과를 구분해 보고']]
 r.table(steps,[90,W-90])
 r.h('입력과 공정 피처 범위')
 r.p('핵심 조성은 C·Si·Mn·P·S·Cr·Ni·Mo·Cu·N이며, RE 정보, 강종, 시험 온도·pH·노출시간·주사속도·전해질 및 기존 프로토콜 항목을 사용한다. 신규 열처리 수치 피처는 온도와 유지시간 두 개이다. SLM 출력·스캔속도, W, 검토 상태, Ecorr 등의 추가 열은 메타데이터로 보존하며 자동으로 피처에 추가하지 않았다.')
 r.p('평가용 bootstrap 위원 수는 2개이다. 최종 점예측은 전체 train 자료로 학습한 중앙 SVR이 수행하므로 운영 15개 위원과 중앙 예측 방식이 같다. 이번 평가는 불확실성의 보정 정확도나 active learning의 실험 절감 효과를 검증하지 않는다.','small')
 r.h('실측과 추정의 구분')
 r.p('원문값은 expanded_source_only.csv, 전역 조성·pH 보완본은 expanded_review.csv에 저장했다. 보완본은 검토용이다. 평가에는 원문값 CSV를 사용하고, 결측치 대치기는 분리 후 학습자료에서만 적합했다. 결측 입력을 처리했다는 사실이 실험에서 그 값을 측정했다는 뜻은 아니다.')
 r.page('2. 실제 test 성능과 그래프')
 r.table([['자료','R² log10','RMSE log10','MAE log10','R² 원척도']]+[[label]+[f'{a[k]:.4f}' for k in ['r2_log10','rmse_log10','mae_log10','r2_raw']] for label,a in zip(['기존 279행','확장 377행','열처리 342행'],e['main_evaluation'])],[110,95,105,105,W-415])
 fig,axs=plt.subplots(1,2,figsize=(9,3.5))
 for ax,cohort,title in zip(axs,['operating_279','expanded_verified'],['Operating data: 279 rows','Expanded verified data: 377 rows']):
  a=pred[pred.cohort.eq(cohort)&pred.method.eq('random_holdout_80_20')];v=np.r_[a.observed_log10,a.predicted_log10];lo=v.min()-.25;hi=v.max()+.25;ax.scatter(a.observed_log10,a.predicted_log10,color='#147D85',s=20,alpha=.75);ax.plot([lo,hi],[lo,hi],ls='--',color='gray');ax.set(title=title,xlabel='Observed log10(icorr / A cm^-2)',ylabel='Predicted log10(icorr / A cm^-2)',xlim=(lo,hi),ylim=(lo,hi));ax.grid(alpha=.15)
 fig.tight_layout();fig.savefig(TMP/'holdout_parity.png',dpi=190);plt.close(fig);r.story.append(Image(str(TMP/'holdout_parity.png'),width=W,height=W*3.5/9));r.p('그림. 고정 seed 42의 무작위 80:20 test set. 점선은 완전 일치선.','small')
 r.h('이전 0.8178과 이번 숫자가 다른 이유')
 r.p(f'이전 0.8178은 279행의 무작위 5-fold 평균이다. 이번 기존 279행의 80:20 holdout R²는 {e["main_evaluation"][0]["r2_log10"]:.4f}이다. 분리·집계가 다르므로 같은 수치가 아니다. 확장 377행의 무작위 5-fold 평균은 {e["cv_mean_r2"]:.4f} ± {e["cv_sd_r2"]:.4f}, pooled OOF R²는 {e["cv_pooled"]["r2_log10"]:.4f}이다.')
 r.h('서로 다른 데이터셋의 점수 비교')
 r.p('279행과 377행은 test set 구성과 자료 범위가 다르다. R² 차이를 “33행 추가가 정확도를 그만큼 향상시켰다”는 인과적 근거로 사용하지 않는다. 342행의 높은 점수도 결과를 보고 고른 최종 성능으로 바꾸지 않고 부분집합 보조 결과로 제시한다.')
 r.page('3. 결과 표기·보조 검증·재현')
 r.h('확장 377행 무작위 5-fold')
 cv=m[m.method.eq('random_5fold')]
 r.table([['Fold','Train / Test','R² (log10)']]+[[int(a.fold),f'{int(a.n_train)} / {int(a.n_test)}',f'{a.r2_log10:.4f}'] for a in cv.itertuples()]+[['평균 ± SD','5개 fold',f'{e["cv_mean_r2"]:.4f} ± {e["cv_sd_r2"]:.4f}']],[70,160,W-230])
 r.h('논문·보고서에 사용할 수 있는 결과 문장')
 r.p(f'“부식속도와의 물리적 연관성을 고려하여 log10(icorr / (A/cm²))를 예측 목표로 설정하였다. 문헌 실험자료 385행 중 타깃 확인 자료 377행을 대상으로, 무작위 80:20 분리(random_state=42)를 적용하였다. 결측치 보완 및 표준화는 학습자료에서만 적합했으며, 고정 RBF-SVR의 test R²는 {e["main_evaluation"][1]["r2_log10"]:.4f}였다. 무작위 5-fold 평균 R²는 {e["cv_mean_r2"]:.4f}였다.”')
 r.h('해석 범위')
 r.p('무작위 분리는 현재 자료 분포 안의 행 수준 예측 성능을 나타낸다. 같은 논문의 여러 시편이 양쪽에 들어갈 수 있다는 조건을 방법에 밝힌다. 독립 신규 실험 성능, RE 첨가의 인과효과, 장기수명 예측, active learning의 라벨 절감 효과는 별도 검증 대상이다. 기존 SVR 설정의 과거 선택 이력과 문헌 잡음을 포함하므로, 완전히 새 자료에 대한 확증 시험으로 표현하지 않는다.')
 r.h('재현 파일')
 r.p('scripts/evaluate_random_20261024.py 실행 결과는 results/random_protocol_20261024/의 metrics.csv, predictions.csv, splits.csv, summary.json에 저장했다. 기존 운영 모델 파일은 이번 평가로 덮어쓰지 않았다.','small')
 r.h('참고 근거')
 r.link('https://www.gamry.com/application-notes/corrosion-coatings/basics-of-electrochemical-corrosion-measurements/','[1] Gamry: Basics of Electrochemical Corrosion Measurements')
 r.link('https://pmc.ncbi.nlm.nih.gov/articles/PMC7435615/','[2] 저합금강 대기부식 Random Forest 연구: 무작위 70:30 분리')
 r.link('https://doi.org/10.1515/corrrev-2023-0162','[3] Model construction of corrosion resistance of alloying elements: 무작위 80:20 분리')
 return r.save()
def collection_report():
 r=Report('literature_expansion_methods_20261024.pdf','Literature collection and missingness')
 r.page('실험데이터 추가 수집과<br/>결측치 보완 기록')
 r.p('기존 문헌 수집·원문 대조 절차의 연속 작업 | 2026-10-24','small')
 r.h('확장 결과와 실제 확인 범위')
 r.table([['항목','결과'],['전체 검토 자료','352 → 385행, 신규 33행 / 3개 논문'],['원문 및 접근 상태 검토','14개 문헌 후보, 3개 문헌 편입'],['icorr 타깃 확인','신규 33/33행. 전체 확인 377행, 기존 미확인 8행 평가 제외'],['신규 pH 원문값','24/33행. 나머지 9행은 기존 pH donor 규칙으로 추정'],['신규 시험온도 원문값','15/33행. S275의 18행은 미보고로 유지'],['신규 주사속도 / OCP 안정화','각각 33/33행 원문 확인'],['신규 열처리 온도·시간 쌍','21/33행 원문 확인'],['신규 RE 함량 확인','0행. 기존 RE 양성 총 41행 유지'],['신규 핵심 조성 통계 보완','108개 셀. 실측과 구분하여 로그 저장']],[235,W-235])
 r.p('<b>완전 무결측 자료를 확보한 것은 아니다.</b> 이번 신규 자료는 pH와 전기화학 시험법 정보가 비교적 잘 갖춰진 실험을 우선 선정했다. 조성 10개·RE·시험온도·pH·주사속도·OCP·열처리 2개·전해질을 모두 요구하면 기존 및 확장 자료의 완전행은 0행이다. RE와 시험온도 등의 미보고 항목을 임의로 채워 이 수치를 늘리지 않았다.')
 r.h('추가한 관측치의 의미')
 r.p('33행은 논문이 보고한 시편·열처리·용액·pH 조건별 실험 중심값이다. 반복 측정의 평균±표준편차를 여러 행으로 분해하지 않았다. 검토본 385행과 모델 평가 377행, 열처리 확인 부분집합 342행은 서로 다른 기준이므로 혼용하지 않는다.')
 r.page('1. 검색·확보·편입 절차')
 r.table([['단계','실행한 작업'],['1. 검색','steel / stainless steel와 Ce·La·Y·rare earth, corrosion current density·Tafel·heat treatment·pH 등을 조합. 기존 352행의 논문 ID와 대조'],['2. 원문 확보','기존 원문 캐시, 출판사 공개 PDF, Europe PMC, Wiley TDM, Elsevier API를 사용. 토큰·키는 출력하지 않음'],['3. 타깃 확인','원문 표의 icorr 열, 단위·지수·행 머리글을 대조. Ecorr·수동태전류·공식전류·부식속도와 구분'],['4. 시편 연결','같은 논문의 조성표·열처리·전해질·pH·온도·주사속도를 해당 시편에 연결'],['5. 단위 통일','microA/cm² × 10^-6 → A/cm², mV ÷ 1000 → V. 마지막 등온 유지 단계의 온도·시간 기록'],['6. 중복·추정 구분','신규 3개 DOI는 기존 352행에 없음. 출처·표·위치·변환법 기록. 미보고값은 빈칸 유지'],['7. 보완본 작성','기존 유사 조성 donor 중앙값 및 제한된 pH 규칙 적용. 원문값 CSV와 보완 검토본 분리'],['8. 검증','33개 정답 양수·ID 유일성·원문 인용 위치·기존 352개 정답 보존 확인. 원문 표 7개 페이지 렌더 대조']],[90,W-90])
 r.h('수집 범위의 정확한 표현')
 r.p('이번은 14개 후보를 점검한 추가 수집 라운드이며, 전 세계 문헌을 빠짐없이 조사한 체계적 문헌고찰은 아니다. 접근 실패·타깃 미보고·식별자 불일치 등의 이유를 screening_log.csv에 저장했다. AI 추출 API를 호출해 검증했다고 주장하지 않으며 이번 편입값은 직접 원문 표와 프로토콜을 대조했다.')
 r.h('희토류 자료가 늘지 않은 이유')
 r.p('La 첨가 스테인리스 문헌 원문을 확보했지만 정량 icorr 표와 열처리 유지조건을 확인하지 못했다. Y 첨가 해양강 논문은 출판사 API 접근이 제한됐고 검색 요약만으로 조성·시편·열처리 매칭을 완결할 수 없었다. RE가 다른 첨가물과 묶인 총량은 개별 RE ppm으로 환산하지 않았다. 이 후보들을 신규 RE 양성 자료로 합산하지 않았다.')
 r.page('2. 신규 문헌별 데이터 추출 상세')
 r.h('[A] S275 mild steel - 18행')
 r.p('DOI 10.3390/met12081386. 원문 Table 6·7에서 O(원상태), Q(담금질), T(뜨임) × pH 4·7·10 × 3.5% NaCl/Na2SO4의 18조건을 추출했다. icorr는 microA/cm²로 보고되어 10^-6배했다. Table 1의 C 0.16, Mn 0.40, Si 0.03, P 0.11, S 0.10, Cu 0.05 wt.%를 보존했다.')
 r.p('본문에서 HT2만 부식시험에 사용했다고 확인했다. Q는 1000 °C/45 min, T는 최종 600 °C/30 min으로 기록했다. 원상태 O에는 열처리 0 °C/0 min을 만들지 않았다. pH·주사속도 1 mV/s·OCP 60 min은 원문값이다. 열처리 냉각 과정의 “실온”을 시험온도 25 °C로 바꾸지 않았다.')
 r.p('P 0.11 및 S 0.10 wt.%는 일반적 기대보다 높지만 표에 실제로 인쇄된 값이다. 임의로 소수점을 이동하지 않았으며 current_model_scope_note에 기록했다.','small')
 r.link('https://doi.org/10.3390/met12081386','원문 [A] / Tables 1, 6, 7; Sections 2.2, 2.5, 3.1')
 r.h('[B] SLM 17-4 PH steel - 9행')
 r.p('DOI 10.3390/met15030232. Table 3의 L9 직교실험 9행을 사용했다. 최종 시효온도 480·550·620 °C, 유지시간 60·150·240 min을 각 행과 연결했다. 앞선 응력제거 650 °C/60 min 및 소둔 1040 °C/30 min은 이력으로 남겼다. Table 2 조성의 “-”는 0이 아닌 결측으로 처리했다.')
 r.p('시험은 3.5 wt.% NaCl, 20±1 °C, 1 mV/s, OCP 1 h이다. 표준편차는 복제 행으로 만들지 않고 중심값만 썼다. 레이저 출력과 스캔속도도 변하므로 메타데이터에 기록했다. 이 자료만으로 열처리의 독립적 효과를 추정했다고 해석하지 않는다.')
 r.link('https://doi.org/10.3390/met15030232','원문 [B] / Tables 2, 3; Sections 2.2, 2.3')
 r.h('[C] UNS S41003 steel - 6행')
 r.p('DOI 10.3390/met15080880. Table 5에서 410F·410T × pH 5.8·4.0·2.0의 6조건을 추출했다. 25 °C, 1 mV/s, OCP 60 min이며 pH는 측정값이다. HCl 첨가에 따른 최종 Cl 농도 500·504·853 ppm을 구분했다. 열처리 상세는 산업 기밀로 미공개여서 빈칸으로 남기고 열처리 확인 342행 평가에서는 제외했다.')
 r.link('https://doi.org/10.3390/met15080880','원문 [C] / Tables 1, 5; Sections 2.1, 2.3')
 r.page('3. 결측치 보완 원칙과 남은 결측')
 r.h('조성 보완: 기존 규칙을 이어서 적용')
 r.p('강종 계열과 관측 조성이 비슷한 다른 논문을 후보로 정하고, 두 개 이상 원소가 겹치는 경우 IQR로 정규화한 거리로 정렬했다. 원소별로 서로 다른 논문 3개 이상, 최대 5개의 donor 중앙값을 사용했다. 관측값은 고정하고 추정값을 다시 donor로 사용하지 않았다. 신규 33행에서 108개 조성 셀을 보완했으며 출처·거리·값·범위를 composition_imputation_log.csv에 저장했다.')
 r.h('pH 보완: 원문값과 제한된 대리값 구분')
 r.p('S275 및 S41003의 24개 pH는 원문값 그대로 유지했다. SLM의 9행은 기존 함수 ph_fill의 단순 3.5% NaCl·20~30 °C 조건에 해당하여 참고 3개 논문의 중앙값 6.5로 보완했다. pH_basis·pH_is_estimated·donor 정보를 보존했으며, 실측 pH 33행이라고 표현하지 않는다. 이 전역 pH 보완본은 검토용이다.')
 r.h('신규 33행의 결측 수: 원문 → 보완 검토본')
 cols=['C','Si','Mn','P','S','Cr','Ni','Mo','Cu','N','RE_ppm','temperature_C','pH','exposure_h','scan_rate_mV_s','ocp_stabilization_min','heat_treatment_temperature_C','heat_treatment_time_min']
 label={'temperature_C':'시험온도','exposure_h':'노출시간','scan_rate_mV_s':'주사속도','ocp_stabilization_min':'OCP 안정화','heat_treatment_temperature_C':'열처리 온도','heat_treatment_time_min':'열처리 시간'}
 mm=missing.set_index('field')
 r.table([['항목','원문 결측 /33','보완본 결측 /33']]+[[label.get(c,c),int(mm.loc[c].new_source_missing),int(mm.loc[c].new_prepared_missing)] for c in cols],[235,125,W-360])
 r.p('미보고 RE는 무첨가 0 ppm과 다르다. 미보고 노출시간도 0 h가 아니며, OCP 안정화 60 min과 같다고 두지 않았다. 열처리쌍 21행과 모든 조건 완전행 0행을 구분했다.','small')
 r.page('4. 보관 파일·검증·재현')
 r.table([['data/al_expanded_20261024/ 파일','용도'],['expanded_source_only.csv','385행. 이번 평가의 원문값 입력'],['expanded_review.csv','385행. 기존 보완값 및 신규 보완값 검토용'],['new_rows_source_only.csv','신규 33행의 원문값'],['new_rows_prepared_review.csv','신규 33행의 조성/pH 보완 검토본'],['new_source_provenance.csv','행·필드별 원문 위치, 값, 단위 변환, 원문 인용'],['composition_imputation_log.csv','108개 신규 조성 보완 셀의 donor와 추정 근거'],['pH_imputation_audit.csv','기존 pH 규칙 적용 이력'],['missingness.csv','이전·신규·통합 자료의 열별 결측 수'],['screening_log.csv','14개 후보의 편입 여부와 미편입 이유'],['feature_schema.json / summary.json','피처 및 완전성 정의 / 집계'],['validation.json','ID 유일성, 정답 보존, 운영 파일 해시 검증']],[260,W-260])
 r.h('완전성 정의와 모델 투입')
 r.p('full_required_fields_complete는 조성 10개, RE_ppm, 전해질, 시험온도, pH, 주사속도, OCP 안정화, 열처리 온도·시간이 모두 존재하는지 검사한다. 이번 정의의 완전행은 0행이다. 빈 complete_required_fields CSV도 이 결과를 그대로 나타낸다. 결측 허용 모델에는 377개 확인 타깃을 투입할 수 있으나, 완전 실측 자료 377개를 확보한 것은 아니다.')
 r.h('이번에 확인한 보존 조건')
 r.p('기존 352행의 icorr를 바꾸지 않았고, 새 ID 33개와 통합 ID 385개는 중복이 없다. 신규 타깃은 모두 양수이며 원문 위치에 연결했다. 운영 data/training.csv 및 models/svr.joblib의 SHA256은 변경 전과 같다. 새 결과는 운영 모델의 재배포가 아닌 별도 평가 결과이다.')
 r.h('재현 순서')
 r.p('1. python scripts/fetch_expansion_20261024.py<br/>2. python scripts/fetch_s275_followup.py<br/>3. python scripts/expand_data_20261024.py<br/>4. python scripts/evaluate_random_20261024.py<br/>5. python scripts/write_random_and_collection_reports_20261024.py','small')
 r.p('추가 수집 원문은 outputs/expansion_20261024/에 저장했다. 후속 평가는 무작위 분리 후 train 내부 대치 원칙을 따른다. 문헌을 더 확보하면 같은 원문 대조·단위 확인·중복 검사·결측 로그 절차로 이어갈 수 있다.','small')
 return r.save()
if __name__=='__main__':
 results=[main_report(),collection_report()]
 for a in results:assert '385' in a['text'] and '377' in a['text']
 (TMP/'validation.json').write_text(json.dumps([{k:v for k,v in a.items() if k!='text'} for a in results],ensure_ascii=False,indent=2),encoding='utf-8')
