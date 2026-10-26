"""Recompute held-out scores and write a Korean target-selection report."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np,pandas as pd,pymupdf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from corrosion_ml.data import training_data,labels,score,validation_splits
from corrosion_ml.model import fitted
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak,Image,Spacer
OUT=ROOT/'output/pdf/icorr_target_and_test_r2.pdf'
RES=ROOT/'results/icorr_report';RES.mkdir(parents=True,exist_ok=True)
TMP=ROOT/'tmp/pdfs/icorr_report';TMP.mkdir(parents=True,exist_ok=True)
d=training_data();y=labels(d)
metrics=[];predictions=[]
for mode in ['random','paper']:
 for fold,(tr,te) in enumerate(validation_splits(d,5,mode),1):
  model,_=fitted(d.iloc[tr],y[tr],n_members=2,seed=42)
  p=model.predict(d.iloc[te].drop(columns=['icorr_A_cm2']))
  overlap=len(set(d.iloc[tr].source_paper_id)&set(d.iloc[te].source_paper_id))
  metrics.append(dict(split=mode,fold=fold,n_train=len(tr),n_test=len(te),paper_overlap=overlap,**score(y[te],p)))
  for idx,pred in zip(te,p):predictions.append(dict(split=mode,fold=fold,record_id=d.record_id.iloc[idx],observed_log10=y[idx],predicted_log10=pred))
  print(mode,fold,metrics[-1]['r2_log10'],flush=True)
m=pd.DataFrame(metrics);pr=pd.DataFrame(predictions)
old=pd.read_csv(ROOT/'results/training/predictions.csv')
check=pr[pr.split.eq('random')].merge(old,on=['fold','record_id'],suffixes=('_new','_old'))
assert len(check)==279
delta=float(abs(check.predicted_log10_new-check.predicted_log10_old).max())
assert delta<1e-9,delta
m.to_csv(RES/'metrics.csv',index=False);pr.to_csv(RES/'predictions.csv',index=False)
summary={mode:dict(mean_r2=float(m[m.split.eq(mode)].r2_log10.mean()),std_r2=float(m[m.split.eq(mode)].r2_log10.std()),pooled=score(pr[pr.split.eq(mode)].observed_log10,pr[pr.split.eq(mode)].predicted_log10)) for mode in ['random','paper']}
summary.update(records=len(d),papers=int(d.source_paper_id.nunique()),prior_prediction_max_difference=delta,data_sha256=hashlib.sha256((ROOT/'data/training.csv').read_bytes()).hexdigest())
(RES/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
fig,axs=plt.subplots(1,2,figsize=(9,3.65))
for ax,mode,title in zip(axs,['random','paper'],['Random-row 5-fold','Paper-group 5-fold']):
 a=pr[pr.split.eq(mode)];ax.scatter(a.observed_log10,a.predicted_log10,s=15,alpha=.65,color='#147d85');lo=min(a.observed_log10.min(),a.predicted_log10.min())-.2;hi=max(a.observed_log10.max(),a.predicted_log10.max())+.2;ax.plot([lo,hi],[lo,hi],color='#666666',ls='--');ax.set(xlim=(lo,hi),ylim=(lo,hi),xlabel='Observed log10(icorr / A cm^-2)',ylabel='Predicted log10(icorr / A cm^-2)',title=title+'\nPooled OOF R² = %.4f'%summary[mode]['pooled']['r2_log10']);ax.grid(alpha=.15)
fig.tight_layout();fig.savefig(TMP/'parity.png',dpi=190);plt.close(fig)
for name,file in [('KR','malgun.ttf'),('KRB','malgunbd.ttf')]:pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('KR',normal='KR',bold='KRB')
navy=colors.HexColor('#163B58');teal=colors.HexColor('#147D85')
styles={k:ParagraphStyle(k,fontName='KRB' if k in ['title','h'] else 'KR',fontSize=size,leading=lead,textColor=navy,spaceAfter=9,wordWrap='CJK') for k,size,lead in [('title',22,31),('h',13,21),('body',10,17),('small',8,12)]}
story=[]
def p(t,k='body'):story.append(Paragraph(t,styles[k]))
def page(t):
 if story:story.append(PageBreak())
 p(t,'title')
def table(rows,widths):
 t=Table([[Paragraph(str(v),styles['small']) for v in row] for row in rows],colWidths=widths,repeatRows=1)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCECF0')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F5F7')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.append(t);story.append(Spacer(1,10))
page('icorr 예측 목표 선정 근거와\ntest-set R² 검증'.replace('\n','<br/>'))
p('REE_AL 연구 기록 | 2026-10-24','small')
p('핵심 결과','h')
p(f'<b>log10(icorr)의 무작위 5-fold 평균 test R² = {summary["random"]["mean_r2"]:.4f}</b><br/>논문 단위 5-fold 평균 test R² = {summary["paper"]["mean_r2"]:.4f}')
p('평가 대상은 현재 운영 SVR의 학습 원본인 279행·43개 논문이다. 최신 352행 문헌 수집본을 재학습한 결과가 아니며, 독립적인 신규 실험 test set에 대한 성능도 아니다.')
p('1. 왜 icorr를 주 예측 대상으로 정하는가','h')
p('<b>연구 목표와 직접 연결된다.</b> 동일하거나 비교 가능한 부식시험 조건에서 작은 부식전류밀도는 낮은 전기화학적 부식속도를 나타낸다. Faraday 법칙에 따라 균일부식 침투속도는 icorr × 당량 / 밀도에 비례하므로, 내식성 향상 후보를 정량적으로 비교하는 데 적합하다. 재료별 당량·밀도가 다르면 icorr만으로 침투속도를 동일시하면 안 된다. [1, 2]')
p('<b>Ecorr와 역할이 다르다.</b> Ecorr는 양극·음극 부분전류가 균형을 이루는 혼합전위이다. 외부 순전류가 0이어도 부식 반응은 진행된다. 전위가 더 양의 방향으로 이동했다는 사실만으로 부식속도가 낮아졌다고 판정할 수 없으므로, 속도 저감이 목표인 본 연구에서는 icorr를 주 지표로 삼는 것이 타당하다. [1]')
p('<b>문헌과 후속 실험을 연결할 수 있다.</b> 현재 코드의 정답은 icorr_A_cm2이며, 조성·열처리·환경 정보로 이를 예측한다. 실험 전 후보 선택에는 아직 측정하지 않은 Ecorr가 필요하지 않다. Ecorr는 향후 공동 예측의 보조 목표로 검증할 수 있다.')
p('선정 근거의 해석 범위','h')
p('위 설명은 현 연구 목표와 구현에 대한 과학적 정당화이다. icorr가 Ecorr보다 예측하기 쉽다는 비교 실험이나, 두 값을 함께 학습하면 성능이 개선된다는 검증을 수행한 것은 아니다. 또한 icorr는 공식·틈부식·장기 노출수명을 단독으로 대표하지 않는다. 부동태계의 Tafel 적합 신뢰성도 별도로 확인해야 한다.')
page('2. 예측값과 검증 방법')
p('예측 목표: y = log10(icorr / (A/cm²))','h')
p(f'관측 icorr 범위는 {d.icorr_A_cm2.min():.3g} - {d.icorr_A_cm2.max():.3g} A/cm²이다. 로그 변환은 여러 자릿수에 걸친 값을 다루고, 큰 전류값이 손실을 과도하게 지배하는 효과를 완화하기 위한 선택이다. 유사한 부식 ML 연구에서도 넓은 목표 범위를 다루기 위해 로그 변환을 사용한다. [2]')
table([['구분','이번 평가 설정'],['모델','RBF SVR: C=10, epsilon=0.15, gamma=scale'],['입력','조성·RE 정보·열처리·부식환경에서 생성한 설명변수. icorr·Ecorr·논문 ID는 예측 입력에서 제외'],['전처리','조성 donor 보완, 수치 중앙값 대치, 표준화, 범주 인코딩을 각 train fold에만 적합'],['무작위 분리','KFold(5, shuffle=True, random_state=42). 같은 논문의 서로 다른 행이 train/test에 들어갈 수 있음'],['논문 단위 분리','GroupKFold(5), source_paper_id 기준. 각 fold의 train/test 논문 중복 0'],['평가의 성격','고정 SVR의 교차검증. 최종 모델의 전체 자료 재학습 후 training R²를 test 성능으로 사용하지 않음']],[92,415])
p('R² 계산과 두 집계값의 차이','h')
p('R² = 1 - Σ(y - ŷ)² / Σ(y - 평균(y_test))²<br/>각 test fold 안에서 평균을 계산한다. R²=1은 완전 일치, 0은 해당 test set 평균 예측과 같은 오차이며 음수도 가능하다. R²=0.82를 “82%의 시편을 맞혔다”로 해석하면 안 된다.')
p('<b>평균 test R²</b>는 5개 fold R²의 산술평균이다. <b>Pooled OOF R²</b>는 각 행이 자신을 학습에 포함하지 않은 모델에서 얻은 예측 279개를 모아 한 번 계산한다. 분모와 집계 방식이 달라 두 값이 일치할 필요는 없다.')
p('재현 확인','h')
p(f'이번 재계산의 무작위 분리 예측은 기존 results/training/predictions.csv의 279개 예측과 최대 절대차 {delta:.2g}로 일치했다. 중앙 SVR 예측만 평가하므로 계산량을 줄이기 위해 bootstrap 위원 수는 2개로 설정했다. 운영 15개 위원과 중앙 예측은 동일하며, 이번 보고서는 불확실성의 보정 성능을 평가하지 않는다.','small')
page('3. Test-set R² 결과')
for mode,title in [('random','A. 행 기준 무작위 5-fold'),('paper','B. 논문 기준 5-fold')]:
 p(title,'h');a=m[m.split.eq(mode)]
 table([['Fold','Train / Test','R² (log10)','R² (원척도)']]+[[int(r.fold),f'{int(r.n_train)} / {int(r.n_test)}',f'{r.r2_log10:.4f}',f'{r.r2_raw:.4f}'] for r in a.itertuples()]+[['평균 ± SD','5개 fold',f'{a.r2_log10.mean():.4f} ± {a.r2_log10.std():.4f}',f'{a.r2_raw.mean():.4f} ± {a.r2_raw.std():.4f}']],[58,110,170,169])
p('OOF 전체 예측을 모은 지표','h')
table([['분리 방법','R² (log10)','RMSE (log10)','MAE (log10)','R² (원척도)']]+[[mode,f'{summary[mode]["pooled"]["r2_log10"]:.4f}',f'{summary[mode]["pooled"]["rmse_log10"]:.4f}',f'{summary[mode]["pooled"]["mae_log10"]:.4f}',f'{summary[mode]["pooled"]["r2_raw"]:.4f}'] for mode in ['random','paper']],[87,105,105,105,105])
p('SD는 5개 fold 사이의 표본 표준편차이며 신뢰구간이 아니다. 원척도 R²는 10^ŷ로 복원한 A/cm² 값에 대해 계산했다. 로그척도 성능과 원척도 성능을 혼용하면 안 된다.','small')
page('4. 결과 해석과 연구 적용')
story.append(Image(str(TMP/'parity.png'),width=507,height=206))
p('그림. 두 분리 방법의 out-of-fold 관측값-예측값 비교. 점선은 완전 일치선이다.','small')
p('현재 수치로 말할 수 있는 것','h')
p(f'현재 고정 SVR은 279행 자료의 무작위 분리에서 평균 test R² {summary["random"]["mean_r2"]:.4f}를 재현했다. 새로운 논문에 대한 일반화는 논문 단위 평균 R² {summary["paper"]["mean_r2"]:.4f}를 함께 제시해야 한다. 무작위 결과만으로 신규 합금·신규 실험실에 대한 정확도를 보장할 수 없다.')
p('icorr + Ecorr 모델과 active learning의 다음 검증','h')
p('icorr 단일 모델과 icorr·Ecorr 공동 모델을 같은 논문 분리 및 같은 실험 예산에서 비교한다. Ecorr는 기준전극과 단위를 통일하고, 시험 전에는 모르는 실측 Ecorr를 icorr 모델의 입력에 넣지 않는다. 주 목적이 icorr 정확도라면 평가와 획득함수도 icorr 오차 감소를 중심으로 설계한다.')
p('이번 test R²는 일반 지도학습 예측 모델의 평가이다. Active learning 자체의 효율은 별도의 초기 학습 집합·후보 풀·고정 test set을 두고, 동일한 라벨 수에서 무작위 선택과 비교한 학습곡선으로 검증해야 한다.')
p('보고서·논문용 결과 문장','h')
p(f'“부식속도와의 물리적 연관성을 고려하여 log10(icorr / (A/cm²))를 주 예측 목표로 설정하였다. 고정 RBF-SVR에 대해 279개 관측치, 43개 논문을 평가한 결과, 행 기준 무작위 5-fold 교차검증의 평균 test R²는 {summary["random"]["mean_r2"]:.4f}, 논문 단위 5-fold 교차검증에서는 {summary["paper"]["mean_r2"]:.4f}였다. 이 결과는 독립 신규 실험에 대한 외부 검증과 구분하였다.”')
page('5. 근거 자료와 재현 기록')
p('외부 근거','h')
p('[1] Gamry Instruments. Basics of Electrochemical Corrosion Measurements. 혼합전위, Tafel 해석, 부식전류와 속도 설명.<br/><link href="https://www.gamry.com/application-notes/corrosion-coatings/basics-of-electrochemical-corrosion-measurements/" color="#147D85">gamry.com / Basics of Electrochemical Corrosion Measurements</link>','small')
p('[2] Machine-learning-guided descriptor selection for predicting corrosion resistance in multi-principal element alloys. npj Materials Degradation (2021). 전류밀도에서 부식속도 환산 및 넓은 목표 범위의 로그 변환 사례.<br/><link href="https://www.nature.com/articles/s41529-021-00208-y" color="#147D85">doi:10.1038/s41529-021-00208-y</link>','small')
p('프로젝트 내 근거','h')
table([['파일','보고서에서 사용한 내용'],['data/training.csv','279개 정답 및 논문 그룹, 학습 입력 원본'],['models/manifest.json','운영 모델 SVR 설정 및 데이터 규모'],['corrosion_ml/data.py','log10 정답, R² 정의, KFold·GroupKFold'],['corrosion_ml/model.py','전처리 적합과 중앙 SVR 예측 구현'],['results/training/predictions.csv','기존 무작위 OOF 예측 재현 비교'],['results/icorr_report/metrics.csv','이번 평가의 fold별 수치 및 논문 중복 수'],['results/icorr_report/predictions.csv','두 분리 방법의 행별 OOF 관측·예측값'],['results/icorr_report/summary.json','집계 성능, 입력 SHA256 및 예측 일치 검증'],['scripts/report_icorr.py','본 보고서 재생성 스크립트']],[235,272])
p('재생성: 프로젝트 루트에서 python scripts/report_icorr.py','small')
p('데이터 SHA256: '+summary['data_sha256'],'small')
p('평가 한계','h')
p('고정 SVR의 과거 모델 선택에 본 자료가 관여했을 가능성을 배제하는 중첩 교차검증은 수행하지 않았다. 논문 분리는 출처 공유 효과를 줄이지만 독립 실험을 대체하지 않는다. 조성 보완 가정, 문헌별 측정법 및 부동태·용액 조건 차이도 잔여 오차의 원인이 될 수 있다. Ecorr 공동 학습의 성능 향상은 이번에 검증하지 않았다.')
def footer(c,doc):
 c.setFont('KR',8);c.setFillColor(navy);c.drawString(44,28,'REE_AL | icorr target selection and held-out evaluation | 2026-10-24');c.drawRightString(A4[0]-44,28,str(doc.page))
OUT.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=43,bottomMargin=46,title='icorr 예측 목표 선정과 test-set R² 검증').build(story,onFirstPage=footer,onLaterPages=footer)
pdf=pymupdf.open(OUT)
for i,page in enumerate(pdf):page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(str(TMP/f'page-{i+1}.png'))
print(json.dumps(summary,indent=2));print('PDF pages',len(pdf));print(OUT)
