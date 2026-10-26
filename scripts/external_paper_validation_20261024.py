"""Retrospective external-paper validation of the untouched operating SVR."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import joblib,numpy as np,pandas as pd,pymupdf
from corrosion_ml.data import NUM,PROCESS_NUM,CAT,PROCESS_CAT
from corrosion_ml.experiments import metrics,predict_without_target
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak,Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
DOI='10.1016/j.prostr.2025.08.043'
TITLE='Effect of Aging Duration on the Microstructure and Corrosion Characteristics of 17-4 PH Stainless Steel'
OUT=ROOT/'results/external_paper_20261024';OUT.mkdir(exist_ok=True,parents=True)
SOURCE=ROOT/'outputs/external_paper_20261024';TMP=ROOT/'tmp/pdfs/external_paper_20261024';TMP.mkdir(exist_ok=True,parents=True)
training=pd.read_csv(ROOT/'data/training.csv');expanded=pd.read_csv(ROOT/'data/al_expanded_20261024/expanded_source_only.csv')
assert DOI not in set(training.source_paper_id) and DOI not in set(expanded.source_paper_id)
modelpath=ROOT/'models/svr.joblib';mh=hashlib.sha256(modelpath.read_bytes()).hexdigest()
bundle=joblib.load(modelpath)
assert set(bundle.training_record_ids_)==set(training.record_id)
assert DOI not in bundle.named_steps['composition'].training_papers_
assert len(bundle.training_record_ids_)==279
plan=dict(doi=DOI,title=TITLE,selection='New paper not in operating training or expanded 385-row corpus; tabulated bulk composition, aging temperature/time, and Tafel means.',primary_conditions='All four reported ST+aging conditions: 480 C, 1/4/8/32 h',secondary='As-received control, no thermal pair; never fabricate 0 C/0 min',model_sha256=mh,model_training_rows=279,no_retraining=True,no_tuning=True,no_new_source_donors=True,missing_policy='Unreported N, RE, pH, test temperature, exposure left missing. Apply only saved training-fitted transforms.',evaluation='Retrospective external-paper evaluation, not blinded prospective experiment',source_urls=[f'https://fis.cld.bz/Issue-711/{i}/' for i in [109,110,111,115]])
(OUT/'evaluation_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
# Table 1 Cr entry is line-wrapped as 15.39 + 8 in the primary HTML text.
# Preserve its reported 15.398 value; sensitivity below quantifies the wrap ambiguity.
composition=dict(C=.043,Si=.458,Mn=.65,P=.021,S=.035,Cr=15.398,Ni=4.211,Mo=.223,Cu=3.518)
rows=[]
for label,hours,target in [('ST+Aging 1h',1,1.726e-7),('ST+Aging 4h',4,1.131e-7),('ST+Aging 8h',8,1.273e-7),('ST+Aging 32h',32,3.649e-7),('AR',None,3.334e-7)]:
 row={c:np.nan for c in NUM+PROCESS_NUM};row.update({c:'missing' for c in CAT+PROCESS_CAT});row.update(composition)
 row.update(record_id='EXT_PROSTR_2025_08043_'+('AR' if hours is None else str(hours)+'h'),source_paper_id=DOI,source_sample_id=label,source_url='https://doi.org/'+DOI,steel_family='스테인리스강',electrolyte_condition_cat='3.5 wt.% NaCl',scan_rate_mV_s=1.,ocp_stabilization_min=60.,icorr_A_cm2=target,evaluation_role='primary_aged' if hours else 'secondary_as_received',heat_treatment_temperature_C=480. if hours else np.nan,heat_treatment_time_min=hours*60. if hours else np.nan,heat_history_note='Solution 1040 C /60 min water quench; age 480 C; air cool.' if hours else 'As-received rolled sheet; prior thermal pair unreported',sample_process_cat='missing',sample_region_cat='missing')
 rows.append(row)
d=pd.DataFrame(rows);d.to_csv(OUT/'source_inputs.csv',index=False,encoding='utf-8-sig')
# Supply no target, Ecorr, or response-derived fields to prediction.
inputs=d.drop(columns=['icorr_A_cm2','evaluation_role'])
pred=predict_without_target(bundle,inputs);d['predicted_log10']=pred;d['observed_log10']=np.log10(d.icorr_A_cm2);d['predicted_A_cm2']=10.**pred;d['absolute_fold_error']=10.**abs(d.predicted_log10-d.observed_log10)
primary=d[d.evaluation_role.eq('primary_aged')]
summary=dict(**plan,primary=metrics(primary.observed_log10,primary.predicted_log10),all_five_secondary=metrics(d.observed_log10,d.predicted_log10),target_span_factor=float(primary.icorr_A_cm2.max()/primary.icorr_A_cm2.min()),unreported_fields=['N','RE_ppm','pH','temperature_C','exposure_h','RE_element_cat'],unreported_categorical_fields=['sample_process_cat','sample_region_cat','temperature_condition_cat'],process_category_note='Heat history documented numerically; no asserted mapping of combined solution-plus-aging route to an existing category.',Cr_linewrap_note='Primary Table 1 text wraps 15.398 into 15.39 + 8; both numeric interpretations evaluated as sensitivity, no choice by score.')
alt=inputs.copy();alt['Cr']=15.39
summary['max_log10_prediction_change_Cr_15_398_vs_15_39']=float(np.max(abs(predict_without_target(bundle,alt)-pred)))
z=bundle[:-1].transform(inputs);central=bundle.named_steps['model'].central_
distance=((z[:,None,:]-central.support_vectors_[None,:,:])**2).sum(axis=2)
kernel_max=np.exp(-central._gamma*distance).max(axis=1)
summary['max_RBF_similarity_to_training_support_vectors']=kernel_max.tolist()
summary['central_SVR_intercept_log10']=float(central.intercept_[0])
summary['aged_predictions_equal_intercept']=bool(np.all(pred[:4]==central.intercept_[0]))
# Assert that predicting without any targets equals prior predictions; model bytes unchanged.
assert np.array_equal(predict_without_target(bundle,inputs),pred)
assert hashlib.sha256(modelpath.read_bytes()).hexdigest()==mh
assert set(d.record_id).isdisjoint(set(training.record_id))
d.to_csv(OUT/'predictions.csv',index=False,encoding='utf-8-sig')
(OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
proof=[]
for field,page,location,note in [('composition',110,'Table 1, journal page 318','Bulk OES composition, wt.%; Cr line-wrapped; N and RE unreported'),('heat_treatment',111,'Table 2, journal page 319','480 C, 1/4/8/32 h; solution stage 1040 C/1 h'),('test_protocol',111,'Experimental, journal page 319','3.5 wt.% NaCl; OCP 1 h; scan 1 mV/s; no numeric corrosion-test temperature or pH'),('icorr_A_cm2',115,'Table 3, journal page 323','Central means multiplied by 1e-7 A/cm2; SD not separate samples')]:
 txt=(SOURCE/f'page_{page}.txt').read_text(encoding='utf-8');assert ('Table 3' in txt if page==115 else True);proof.append(dict(field=field,location=location,note=note,source_url=f'https://fis.cld.bz/Issue-711/{page}/',source_file=str(SOURCE/f'page_{page}.html')))
pd.DataFrame(proof).to_csv(OUT/'provenance.csv',index=False,encoding='utf-8-sig')
fig,ax=plt.subplots(figsize=(7,3.5));x=np.array([1,4,8,32]);ax.plot(x,primary.icorr_A_cm2,'o-',label='Reported',color='#147D85');ax.plot(x,primary.predicted_A_cm2,'s--',label='Frozen SVR',color='#D07D3A');ax.set(xscale='log',yscale='log',xlabel='Aging duration at 480 C (h)',ylabel='icorr (A/cm²)');ax.set_xticks(x,labels=['1','4','8','32']);ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(TMP/'comparison.png',dpi=190);plt.close(fig)
for name,file in [('KR','malgun.ttf'),('KRB','malgunbd.ttf')]:pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('KR',normal='KR',bold='KRB')
styles={k:ParagraphStyle(k,fontName='KRB' if k in ['title','h'] else 'KR',fontSize=size,leading=lead,spaceAfter=9,textColor=colors.HexColor('#163B58'),wordWrap='CJK') for k,size,lead in [('title',20,29),('h',12,20),('body',9.6,16),('small',8,12)]}
story=[];W=A4[0]-88
def p(t,k='body'):story.append(Paragraph(t,styles[k]))
def page(t):
 if story:story.append(PageBreak())
 p(t,'title')
def table(rows,widths):
 t=Table([[Paragraph(str(v),styles['small']) for v in row] for row in rows],colWidths=widths,repeatRows=1);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DDECF1')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F5F7')]),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(t)
page('새 논문 실험값을 이용한<br/>고정 모델 외부 검증')
p('2026-10-24 | 새 논문 전체를 평가에 사용 | 재학습 없음','small')
p('평가 논문','h');p(TITLE+'<br/>G. Narasinga Rao et al., Procedia Structural Integrity 71 (2025), 317-324.','small');p('<link href="https://doi.org/'+DOI+'" color="#147D85">DOI: '+DOI+'</link>','small')
p('기존 279행 운영 학습자료와 385행 확장 자료에 없는 논문을 선정했다. 저장된 SVR의 학습 ID와 조성 donor의 논문 목록에서도 해당 DOI가 없음을 확인했다. 새 논문의 타깃이나 조성을 재학습·donor 확장에 사용하지 않았다.')
p('검증 대상과 주 결과','h')
p('주 평가는 열처리 온도·시간이 명확한 480 °C 시효 1·4·8·32시간의 4조건이다. 원상태 AR은 열처리 이력이 불명확하므로 별도 보조 평가에만 포함했다. 논문에 정량 icorr가 없는 ST 단독 조건의 값을 만들지 않았다.')
a=summary['primary'];table([['지표','새 논문 4조건'],['R² - log10(icorr)',f'{a["r2_log10"]:.4f}'],['R² - 원척도 A/cm²',f'{a["r2_A_cm2"]:.4f}'],['MAE - log10',f'{a["mae_log10"]:.4f}'],['기하평균 배수 오차',f'{a["geometric_mean_fold_error"]:.2f}배'],['2배 오차 이내',f'{int(round(a["fraction_within_factor2"]*4))}/4조건']],[260,W-260])
p('이 검증은 공개된 문헌의 이미 알려진 실험값을 사용한 후향적 외부 검증이다. 논문 발표 이후에 미래 실험을 사전 예측한 맹검 검증으로 표현하지 않는다. 논문은 점수 계산 전에 선정했고, 평가 후 모델 설정을 조정하지 않았다.','small')
page('1. 관측값과 모델 예측의 비교')
table([['시효시간','실측 icorr<br/>(A/cm²)','예측 icorr<br/>(A/cm²)','배수 오차']]+[[f'{int(v.heat_treatment_time_min/60)} h',f'{v.icorr_A_cm2:.3e}',f'{v.predicted_A_cm2:.3e}',f'{v.absolute_fold_error:.2f}'] for v in primary.itertuples()],[80,145,145,W-370])
story.append(Image(str(TMP/'comparison.png'),width=W,height=W/2))
p('실측값의 범위와 R²의 해석','h')
p(f'이 논문의 4조건 실측 icorr는 최대/최소 약 {summary["target_span_factor"]:.2f}배 범위이다. R²의 분모인 관측값 분산이 작아 절대값 차이가 크지 않아도 R²가 매우 낮거나 음수가 될 수 있다. 음수는 해당 4조건의 실측 평균을 고정 예측하는 것보다 제곱오차가 크다는 뜻이다. 따라서 R²와 배수 오차를 함께 해석한다.')
p('보조 결과: AR을 포함한 5조건','h');b=summary['all_five_secondary'];p(f'R²(log10)={b["r2_log10"]:.4f}, 기하평균 배수 오차={b["geometric_mean_fold_error"]:.2f}배. AR 실측 {d.iloc[-1].icorr_A_cm2:.3e}, 예측 {d.iloc[-1].predicted_A_cm2:.3e} A/cm². AR을 추가해 점수가 바뀌더라도 4조건 주 결과를 대체하지 않는다.')
page('2. 입력 근거·결측치·재현')
p('원문에서 가져온 입력','h')
p('Table 1의 벌크 조성 9개(C·Si·Mn·P·S·Cr·Ni·Mo·Cu), Table 2의 시효 온도·시간, 실험절의 NaCl 3.5 wt.%·주사속도 1 mV/s·OCP 안정화 60 min을 사용했다. 정답은 Table 3의 icorr 열 중심값에 10^-7 A/cm² 배율을 적용했다. [1]')
p('미보고값과 한계','h')
p('N·RE·pH·부식시험 온도·노출시간은 빈칸으로 두고 저장된 모델의 학습 시 적합된 대치기만 적용했다. 미세경도 시험의 ambient temperature를 부식시험 온도로 옮기지 않았다. 미보고 RE를 0 ppm으로 두지 않았다. 복합 열처리를 기존 공정 범주에 임의 대응시키지 않고 수치 온도·시간과 이력으로 기록했다.')
p(f'Cr 조성은 원문 HTML의 줄바꿈 “15.39”와 “8”을 이어 15.398 wt.%로 읽었다. 15.39로 바꾼 민감도 확인에서 최대 log10 예측 변화는 {summary["max_log10_prediction_change_Cr_15_398_vs_15_39"]:.4g}였다. 이는 주 결과를 보고 유리한 값을 선택한 것이 아니다.','small')
p('현재 결론','h')
p('시효 4조건 모두 1.584×10^-6 A/cm²로 동일하게 예측했다. 각 입력과 학습 support vector의 RBF 유사도 최대값은 약 1.2×10^-42 이하로, 중앙 SVR의 절편값을 출력한 상태였다. 즉 이 입력 조건에서는 학습 패턴과 연결되지 않아 절대값과 시간별 변화를 재현하지 못했다. 미보고 조건과 공정 표현 한계가 영향을 줄 수 있으며 다른 논문 전체의 성능으로 일반화하지 않는다. RE 미보고 자료이므로 RE 첨가 효과의 검증도 아니다.')
p('출처와 보관 파일','h')
p('<link href="https://fis.cld.bz/Issue-711/110/" color="#147D85">[1] 원문 Table 1: journal p.318</link><br/><link href="https://fis.cld.bz/Issue-711/111/" color="#147D85">열처리 Table 2 및 시험법: journal p.319</link><br/><link href="https://fis.cld.bz/Issue-711/115/" color="#147D85">실험값 Table 3: journal p.323</link>','small')
p('results/external_paper_20261024/: source_inputs.csv(입력), predictions.csv(관측·예측), provenance.csv(원문 위치), evaluation_plan.json(평가 기준), summary.json(지표·모델 해시). 재생성: python scripts/external_paper_validation_20261024.py','small')
p('운영 모델 SHA256: '+mh,'small')
def footer(c,doc):c.setFont('KR',8);c.drawString(44,27,'REE_AL | New-paper external validation | 2026-10-24');c.drawRightString(A4[0]-44,27,str(doc.page))
pdfpath=ROOT/'output/pdf/external_new_paper_validation_20261024.pdf';SimpleDocTemplate(str(pdfpath),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=43,bottomMargin=46,title='새 논문 실험값 기반 외부 검증').build(story,onFirstPage=footer,onLaterPages=footer)
doc=pymupdf.open(pdfpath)
for i,page in enumerate(doc):page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(str(TMP/f'page-{i+1}.png'))
assert len(doc)==3
print(json.dumps(summary,indent=2));print(d[['source_sample_id','icorr_A_cm2','predicted_A_cm2','absolute_fold_error']].to_string(index=False));print(pdfpath)
