"""Audit the user's complete-input requirement; never fabricate predictions."""
import json,hashlib,sys
from pathlib import Path
import numpy as np,pandas as pd,joblib,pymupdf
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak,Spacer
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'results/feature_requirements_20261024';OUT.mkdir(parents=True,exist_ok=True)
TMP=ROOT/'tmp/pdfs/feature_requirements_20261024';TMP.mkdir(parents=True,exist_ok=True)
raw=pd.read_csv(ROOT/'data/al_expanded_20261024/expanded_source_only.csv',float_precision='round_trip')
train=pd.read_csv(ROOT/'data/training.csv',float_precision='round_trip')
CORE='C Si Mn P S Cr Ni Mo Cu N'.split()
REQUIRED=CORE+['RE_ppm','temperature_C','pH','exposure_h','scan_rate_mV_s','ocp_stabilization_min','heat_treatment_temperature_C','heat_treatment_time_min','electrolyte_condition_cat']
# This is the current model's conservative no-imputation admission rule, not a
# universal claim that each trace element is indispensable to every corrosion model.
missing=raw[REQUIRED].isna()
audit=raw[['record_id','source_paper_id','source_sample_id','target_verified']].copy()
audit['missing_count']=missing.sum(axis=1)
audit['missing_fields']=['; '.join(np.array(REQUIRED)[r]) for r in missing.to_numpy()]
audit['RE_species_missing_when_positive']=raw.RE_ppm.gt(0)&raw.RE_element_cat.isna()
audit['full_current_model_inputs_observed']=audit.missing_count.eq(0)&~audit.RE_species_missing_when_positive
audit['prediction_permitted']=audit.full_current_model_inputs_observed&audit.target_verified.fillna(False).astype(bool)
audit.to_csv(OUT/'paper_input_completeness.csv',index=False,encoding='utf-8-sig')
by_paper=audit.groupby('source_paper_id').agg(rows=('record_id','size'),minimum_missing_fields=('missing_count','min'),eligible_rows=('prediction_permitted','sum')).reset_index()
by_paper.to_csv(OUT/'paper_summary.csv',index=False,encoding='utf-8-sig')
field_rows=[dict(field=c,observed_rows=int(raw[c].notna().sum()),missing_rows=int(raw[c].isna().sum()),missing_pct=float(raw[c].isna().mean()*100)) for c in REQUIRED]
pd.DataFrame(field_rows).to_csv(OUT/'required_feature_coverage.csv',index=False,encoding='utf-8-sig')
thermal=train[['heat_treatment_temperature_C','heat_treatment_time_min']].dropna()
b=joblib.load(ROOT/'models/svr.joblib');numeric=b.named_steps['preprocessor'].transformers_[0][2];scaler=b.named_steps['preprocessor'].named_transformers_['num'].named_steps['standardscaler'];idx=numeric.index('heat_treatment_temperature_C')
sd=float(scaler.scale_[idx]);shift=abs(480-float(scaler.mean_[idx]))/sd
screen=[
 dict(doi='10.1016/j.prostr.2025.08.043',decision='reject_complete_input_external_test',reason='Missing pH, corrosion test temperature, N, RE, exposure; 480 C is far outside operating-model thermal training support.'),
 dict(doi='10.1155/2014/951471',decision='reject_complete_input_external_test',reason='Bulk composition reports only Fe/Cr/C/Ni/Mn/Si; P/S/Mo/Cu/N/RE and pH not fully reported. Table current is A, requiring explicit 0.22 cm2 area normalization; never treat it as A/cm2.'),
 dict(doi='10.3390/met12091443',decision='reject_numeric_target_validation',reason='Primary page 7 states Tafel fitting was not conducted; no eligible scalar icorr table. Do not substitute Rct or digitize as a reported target.'),
 dict(doi='10.1016/j.jmrt.2023.12.189',decision='reject_complete_input_external_test',reason='Primary Table 1 gives upper bounds/ranges for several composition fields, not measured point compositions. 0.2Y label differs from table Y=0.3 wt.%; do not assume 0.2 wt.% or convert bounds to measurements.'),
 dict(doi='10.1155/ijco/5531986',decision='closest_process_environment_complete_candidate_not_full_model_complete',reason='40 rows have C/Si/Mn/P/S, thermal pair, test temperature, pH, scan and OCP, but Cr/Ni/Mo/Cu/N/RE are not reported. Quench medium must be retained to distinguish rows. Already in expanded corpus; not in operating training.'),
]
pd.DataFrame(screen).to_csv(OUT/'candidate_screening.csv',index=False,encoding='utf-8-sig')
summary=dict(task='Required feature identification and complete-input paper search',date='2026-10-24',criterion='Conservative admission for the CURRENT model with source-observed numeric inputs; optional bounds and missingness flags are not treated as physical measurements.',rows_screened=len(raw),papers_screened=int(raw.source_paper_id.nunique()),complete_rows=int(audit.prediction_permitted.sum()),required_fields=REQUIRED,model_thermal_observed_rows=len(thermal),model_thermal_temperature_min=float(thermal.heat_treatment_temperature_C.min()),model_thermal_temperature_max=float(thermal.heat_treatment_temperature_C.max()),model_thermal_temperature_scale=sd,previous_480C_scaled_shift=shift,source_only_data_hash=hashlib.sha256((ROOT/'data/al_expanded_20261024/expanded_source_only.csv').read_bytes()).hexdigest(),new_predictions_generated=False,new_external_R2=None,status='Not completed: no paper meeting complete current-model-input and target verification requirements found. No invalid substitute prediction produced.')
(OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
assert len(raw)==385 and int(audit.prediction_permitted.sum())==0 and len(thermal)==76
for n,f in [('KR','malgun.ttf'),('KRB','malgunbd.ttf')]:pdfmetrics.registerFont(TTFont(n,'C:/Windows/Fonts/'+f))
pdfmetrics.registerFontFamily('KR',normal='KR',bold='KRB')
styles={k:ParagraphStyle(k,fontName='KRB' if k in ['title','h'] else 'KR',fontSize=size,leading=lead,textColor=colors.HexColor('#163B58'),spaceAfter=9,wordWrap='CJK') for k,size,lead in [('title',20,29),('h',12,20),('body',9.6,16),('small',8,12)]}
W=A4[0]-88;story=[]
def p(t,k='body'):story.append(Paragraph(t,styles[k]))
def page(t):
 if story:story.append(PageBreak())
 p(t,'title')
def table(rows,widths):
 t=Table([[Paragraph(str(v),styles['small']) for v in row] for row in rows],colWidths=widths,repeatRows=1)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DDECF1')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F5F7')]),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(t);story.append(Spacer(1,9))
page('icorr 예측에 필요한 피처와<br/>완전 입력 문헌의 선정 기준')
p('2026-10-24 | 이번 문서는 피처·자료 적합성 감사이며 새 예측 성능 보고서가 아님','small')
p('먼저 확인된 모델의 적용 범위 문제','h')
p(f'운영 SVR의 279행 중 열처리 온도·시간이 관측된 행은 76행뿐이다. 온도 범위는 1150~1200 °C이며 대부분 1200 °C이다. 전처리 후 온도 표준편차 척도는 {sd:.2f} °C여서, 앞선 480 °C 입력은 중심에서 약 {shift:.1f} 척도만큼 벗어났다. 열처리 정보가 있다는 사실만으로 이 모델이 시효 실험을 학습했다고 볼 수 없다.')
p('480 °C 논문 외부 검증은 결측치와 큰 조건 외삽을 함께 포함한다. 따라서 앞선 실패를 “새 논문이면 예측이 안 된다” 또는 “icorr 자체가 예측 불가능하다”로 일반화하면 안 된다. 이 논문은 완전 입력 사례를 원한 현재 요청의 검증 자료로 부적합하다.')
p('필요한 물리적 입력 - 연구 설계 우선순위','h')
table([['구분','확인할 피처','역할'],['재료 조성','벌크 주 합금 조성, RE 종류·실제 함량; 관련 미량원소','재료 간 차이와 RE 첨가 효과 구분'],['공정·재료 상태','열처리 단계별 온도·시간, 냉각방식, 압연/용접/적층 상태','같은 최종 온도·시간이라도 다른 미세조직을 구분'],['부식환경','전해질 전체 조성·농도, pH, 시험온도, 사전 노출시간','반응 및 물질전달 조건 구분'],['시험 프로토콜','주사속도, OCP 안정화시간, 표면연마, 통기/탈기','논문별 측정조건 차이 통제'],['가능하면 추가','시험 전 결정립 크기·상분율·개재물 지표','RE·공정의 미세조직 경로 설명. 제조 전 설계에서는 미지일 수 있음']],[85,245,W-330])
p('이 표는 물리적 후보 피처와 수집 기준이다. 통계적으로 최적 피처를 확정한 결과가 아니며, 한 가지 보편적 필수 목록만으로 정확도가 보장되지 않는다. 각 피처의 유효성은 학습자료 안의 검증으로 비교해야 한다.','small')
page('1. 피처 사용 원칙과 완전성 점검')
p('실험 전 예측에서 사용 가능한 정보','h')
p('원소 조성·계획한 공정·시험환경·프로토콜은 입력으로 사용할 수 있다. 실제 제조 후 미세조직은 측정된 경우에만 사용하고, 실험 전에 알 수 없다면 별도 미세조직 예측 또는 공정 대리변수가 필요하다. icorr·부식속도·같은 분극곡선에서 얻은 Tafel slope·실측 Ecorr를 실험 전 입력으로 넣어 결과를 누설하지 않는다.')
p('현재 모델에 대해 적용한 무대치 문헌 선정 기준','h')
p('현재 모델의 10개 조성(C·Si·Mn·P·S·Cr·Ni·Mo·Cu·N), RE 함량, 시험온도, pH, 사전 노출시간, 주사속도, OCP 시간, 열처리 온도·시간, 전해질을 원문에서 확인하는 보수적 기준을 적용했다. RE가 양수이면 종류도 확인한다. 이는 현재 피처 체계를 결측치 없이 적용하기 위한 기준이며, 모든 부식 모델에서 10개 원소가 항상 필수라는 뜻은 아니다.')
p(f'현재 원문값 자료 385행 / {raw.source_paper_id.nunique()}개 논문을 검사한 결과, 이 기준을 모두 만족하는 타깃 확인 행은 <b>0행</b>이다. 평균값·범위 중간값·상한의 절반으로 채워 만든 자료는 완전 실측 자료로 집계하지 않았다.')
table([['핵심 항목','원문값 존재 /385','결측 /385']]+[[r['field'],r['observed_rows'],r['missing_rows']] for r in field_rows if r['field'] in ['RE_ppm','pH','temperature_C','exposure_h','scan_rate_mV_s','ocp_stabilization_min','heat_treatment_temperature_C','heat_treatment_time_min']],[250,128,W-378])
p('냉각방식은 현재 수치 공정 피처에 포함되지 않는다. 같은 입력으로 보였던 서로 다른 담금질 실험을 구분하려면 이를 수집·코딩하고, 냉각방식이 달라지는 학습자료를 확보한 뒤 새 모델을 학습해야 한다. 시험조건을 더 기록하는 것과 모델이 그 효과를 학습한 것은 다르다.')
page('2. 원문 후보 검토와 예측 실행 여부')
table([['후보 논문','원문 확인 내용','선정 결과'],['17-4PH 시효시간<br/>10.1016/j.prostr.2025.08.043','시효 480 °C; pH·시험온도·N·RE·노출시간 미보고','완전 입력 사례에서 제외'],['Mn·용체화<br/>10.1155/2014/951471','조성·공정·25 °C·용액·주사속도는 있으나 다수 조성·pH 미보고. 타깃은 A, 면적 0.22 cm² 정규화 필요','완전 입력 사례에서 제외'],['30CrMnSiNi2A<br/>10.3390/met12091443','pH·온도·프로토콜 상세하지만 p.7에 Tafel fitting을 수행하지 않았다고 명시','정량 icorr 검증 대상 제외'],['Y 첨가 해양강<br/>10.1016/j.jmrt.2023.12.189','조성표 다수가 상한·범위. 0.2Y 표기와 Table 1의 Y 0.3 wt.% 차이 주의','실측 단일 조성 완전 사례에서 제외'],['중탄소강 나노유체 담금질<br/>10.1155/ijco/5531986','40행의 C·Si·Mn·P·S, 열처리쌍, pH·온도·주사·OCP가 존재. 나머지 모델 조성·RE 미보고','공정·환경이 상세한 후보이나 전체 피처 완비 아님']],[160,245,W-405])
p('이번 요청의 처리 상태','h')
p('<b>피처 기준 및 원문 적합성 감사는 완료했지만, 필수 입력이 모두 있는 새 논문 실험의 예측은 아직 완료하지 못했다.</b> 조건을 만족하는 논문을 확보하지 못했기 때문에 새 외부 R²를 계산하지 않았다. 기존 논문을 새 논문처럼 부르거나, 같은 논문 일부를 학습해 놓고 논문 전체 외부 검증으로 제시하지 않았다.')
p('현실적인 다음 데이터 확보 우선순위','h')
p('RE 첨가 철강의 실제 벌크 분석값과 무첨가 대조군, 명시된 열처리·냉각조건, pH·시험온도·전해질·분극 프로토콜을 함께 확보해야 한다. 현재 모델을 시효·담금질까지 적용하려면 해당 공정 범위를 포함하는 학습자료와 냉각방식 표현도 필요하다. 실험조건이 없는 문헌은 저자 보충자료·원시데이터 없이는 완전 입력 사례로 복구할 수 없다.')
p('기록: results/feature_requirements_20261024/의 paper_input_completeness.csv, paper_summary.csv, required_feature_coverage.csv, candidate_screening.csv, summary.json. 운영 모델과 데이터는 이 감사로 변경하지 않았다.','small')
page('3. 근거 문헌과 재현')
links=[('부식전류와 시험조건의 관계','https://www.gamry.com/application-notes/corrosion-coatings/basics-of-electrochemical-corrosion-measurements/'),('Mn 함량·용체화 논문','https://doi.org/10.1155/2014/951471'),('30CrMnSiNi2A 논문','https://doi.org/10.3390/met12091443'),('Y 첨가 해양강 논문','https://doi.org/10.1016/j.jmrt.2023.12.189'),('중탄소강 나노유체 담금질 논문','https://doi.org/10.1155/ijco/5531986')]
for label,url in links:p(f'<link href="{url}" color="#147D85">{label}: {url}</link>','small')
p('원문 접근과 해석','h')
p('Mn 함량·용체화 원문은 Wiley TDM으로 PDF를 확보했고, 30CrMnSiNi2A는 출판사 공개 PDF를 확인했다. Y 첨가 논문은 출판사 API/PDF 직접 접근이 제한되어 출판사 페이지의 공개 검색 인덱스에 제공된 Table 1과 실험절을 확인했다. 검색 인덱스만으로 모호한 시편 조건을 완결하지 않았고 주 학습자료에 추가하지 않았다. 나노유체 논문은 기존 확보 원문 및 검토 이력을 사용했다.')
p('최적 피처를 검증하려면','h')
p('물리적 후보를 먼저 정한 뒤, 학습자료 내부에서 조성만 / 조성+공정 / 조성+공정+환경 / 추가 미세조직의 모델을 동일한 분할로 비교해야 한다. 외부 논문의 점수를 보고 피처나 하이퍼파라미터를 고르는 방식은 외부 검증의 독립성을 훼손한다. 이번 감사에서는 그러한 선택을 수행하지 않았다.')
p('재현: 프로젝트 루트에서 python scripts/audit_prediction_requirements_20261024.py','small')
p('원문값 자료 SHA256: '+summary['source_only_data_hash'],'small')
def footer(c,doc):c.setFont('KR',8);c.drawString(44,27,'REE_AL | Feature and source readiness audit | 2026-10-24');c.drawRightString(A4[0]-44,27,str(doc.page))
path=ROOT/'output/pdf/feature_requirements_and_source_audit_20261024.pdf';SimpleDocTemplate(str(path),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=43,bottomMargin=46,title='icorr 피처와 완전 입력 문헌 감사').build(story,onFirstPage=footer,onLaterPages=footer)
doc=pymupdf.open(path);assert len(doc)==4
for i,page in enumerate(doc):page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(str(TMP/f'page-{i+1}.png'))
print(json.dumps(summary,ensure_ascii=False,indent=2));print(path)
