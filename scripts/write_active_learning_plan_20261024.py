"""Korean closed-loop corrosion research plan with primary-source references."""
from pathlib import Path
import json
import pymupdf
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Spacer, Flowable

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf/active_learning_experimental_pipeline_20261024.pdf'
TMP=ROOT/'tmp/pdfs/active_learning_pipeline';TMP.mkdir(parents=True,exist_ok=True)
OUT.parent.mkdir(parents=True,exist_ok=True)
for name,file in [('KR','malgun.ttf'),('KRB','malgunbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('KR',normal='KR',bold='KRB')
INK=colors.HexColor('#15394C');TEAL=colors.HexColor('#087F8C');LIGHT=colors.HexColor('#EDF4F6')
W=A4[0]-88
styles={k:ParagraphStyle(k,fontName='KRB' if k in ['title','h','lead'] else 'KR',fontSize=size,leading=lead,
    wordWrap='CJK',spaceAfter=space,textColor=INK) for k,size,lead,space in
    [('title',20,29,15),('lead',12,20,12),('h',11.5,18,8),('body',9.5,15.5,9),('small',8.1,12.5,7)]}
story=[]
def p(text,style='body'):story.append(Paragraph(text,styles[style]))
def page(title,sub):
    if story:story.append(PageBreak())
    p(title,'title');p(sub,'small');story.append(Spacer(1,5))
def table(rows,widths=None):
    t=Table([[Paragraph(str(v),styles['small']) for v in row] for row in rows],colWidths=widths or [W/len(rows[0])]*len(rows[0]),repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCEBF0')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.7,TEAL)]))
    story.append(t);story.append(Spacer(1,10))

class PipelineFigure(Flowable):
    def __init__(self):Flowable.__init__(self);self.width=W;self.height=210
    def draw(self):
        c=self.canv;bw=145;bh=57;xs=[0,(W-bw)/2,W-bw];ys=[135,39]
        texts=[('문헌 + 초기 직접실험','초기 학습자료 구성'),('조건·단위 정리','입력 / 정답 / 출처 구분'),('모델 학습','예측값 + 불확실성'),('측정값 검증·추가','자료·모델 버전 저장'),('직접 실험 수행','재학습 전 예측오차 평가'),('다음 실험 선택','불확실성 + 다양성')]
        for j,(a,b) in enumerate(texts):
            row=j//3;col=j%3;x=xs[col];y=ys[row]
            c.setFillColor(LIGHT);c.setStrokeColor(TEAL);c.roundRect(x,y,bw,bh,7,fill=1,stroke=1)
            c.setFillColor(INK);c.setFont('KRB',10);c.drawCentredString(x+bw/2,y+34,a)
            c.setFont('KR',8);c.drawCentredString(x+bw/2,y+15,b)
        def arrow(x1,y1,x2,y2):
            c.setStrokeColor(TEAL);c.setLineWidth(1.4);c.line(x1,y1,x2,y2)
            if x2>x1:c.line(x2,y2,x2-5,y2+3);c.line(x2,y2,x2-5,y2-3)
            elif x2<x1:c.line(x2,y2,x2+5,y2+3);c.line(x2,y2,x2+5,y2-3)
            elif y2<y1:c.line(x2,y2,x2-3,y2+5);c.line(x2,y2,x2+3,y2+5)
            else:c.line(x2,y2,x2-3,y2-5);c.line(x2,y2,x2+3,y2-5)
        for i in [0,1]:arrow(xs[i]+bw+3,163,xs[i+1]-3,163)
        arrow(xs[2]+bw/2,132,xs[2]+bw/2,99)
        for i in [2,1]:arrow(xs[i]-3,67,xs[i-1]+bw+3,67)
        arrow(bw/2,99,bw/2,132)
        c.setFillColor(INK);c.setFont('KR',8);c.drawCentredString(W/2,13,'고정 평가자료는 학습·후보 선택에서 제외 | 실험 예산 안에서 반복')

page('직접 실험을 넣어 발전시키는\n부식 예측 Active Learning','연구 설계안 | 2026-10-24 | 문헌 초기화 → 직접 측정 → 재학습 → 다음 실험 추천')
p('이 방식은 적절하다. 핵심은 데이터 추가와 함께 다음 실험을 선택하는 규칙을 만드는 것이다.','lead')
p('문헌 자료로 만든 초기 모델에 연구자가 측정한 icorr를 추가해 모델을 갱신하는 접근은 합리적이다. 특히 동일 실험실의 제조·시험조건이 쌓이면 목표 실험 범위에 맞는 모델을 개발할 수 있다. 다만 정확도 향상은 실제 평가로 확인해야 하며, 자료를 넣기만 하면 보장되지는 않는다. [2,3]')
story.append(PipelineFigure())
table([['구분','실제로 하는 일'],['순차 재학습','연구자가 정한 실험값을 추가하고 다시 학습한다.'],['Active learning','현재 모델이 미측정 후보의 정보 가치를 평가해 다음 실험을 선택하고, 측정값을 추가한 뒤 반복한다.'],['베이지안 최적화','가장 낮은 icorr 등 목표 성능을 찾도록 후보를 선택한다. 예측 정확도를 높이는 목표와 구별해 설정한다.']],[105,W-105])
p('첨부 그림과의 관계','h')
p('첨부 그림의 제작·부식시험·분석·ML 구조는 Wang et al.의 통합 고처리량 연구 도식과 대응한다. 본 보고서는 이를 참고해 위 순환도를 새로 그렸다. 원 연구의 용융염 부식 분석값을 수용액 icorr와 동일한 정답으로 합치지는 않는다. [1]','small')

page('1. 어떤 데이터를 넣어야 하나','관측 한 행 = 특정 배치·공정·환경에서 측정한 하나의 시편 또는 명시된 조건 평균')
table([['항목','기록 내용','모델에서의 용도'],['식별·출처','record / batch / condition / replicate ID, 논문 DOI 또는 실험일지, acquisition round','분리·추적용. 임의의 ID는 예측 피처로 쓰지 않음'],['조성·제조','실측 조성, RE 원소·함량, 압연/주조/SLM 등 제조법','실험 전에 아는 입력'],['단계별 열처리','용체화·시효·뜨임 각각의 온도/시간/냉각, 필요한 선행 단계','실험 전에 아는 입력'],['환경·측정조건','pH, 실제 시험온도, 염 농도, 탈기, 표면처리, 침지시간, 주사속도, OCP 안정시간, 면적','조건을 맞추거나 입력으로 사용'],['정답','실측 icorr(A/cm²), 추출 방법, 반복수·표준편차','log10(icorr)를 주 예측 대상으로 사용'],['추가 결과','Ecorr와 기준전극, EIS·조직·경도 등','보조 정답 또는 별도 모델 입력 후보']],[82,255,W-337])
p('결측과 단위 처리','h')
p('미보고 RE·N·pH를 0으로 만들지 않는다. 보고되지 않은 온도와 “열처리 미실시”는 다르다. A와 A/cm²를 구별하고 노출면적이 확인될 때만 전환한다. OCP 안정시간을 침지시간과 같은 값으로 복사하지 않는다. 통계적 대치는 학습 자료에서만 적합하고 원문값과 구별한다.')
p('Ecorr와 사후 분석값은 언제 사용할 수 있나','h')
p('새 시편의 분극시험 전에 icorr를 예측하려면 같은 시험에서 얻는 Ecorr를 필수 입력으로 요구하면 안 된다. icorr와 Ecorr를 함께 출력하는 다중 출력 모델은 별도 비교할 수 있다. 실험 후 XRD/SEM 결과도 다음 후보에서 측정 전 알 수 없다면 해당 예측의 입력으로 직접 사용할 수 없다. 계산으로 미리 얻는 물성이나 사전에 측정하는 조직 정보는 출처·오차를 명시해 후보 피처로 검토한다. [1,6]')

page('2. 한 번의 Active Learning 반복','학습자료 D(t), 미측정 후보 U(t), 모델 M(t)를 매 반복마다 별도로 저장')
table([['단계','실행 내용'],['① 후보 정의','실제로 만들 수 있는 조성·공정·환경 조합을 생성. 정답은 빈칸. 제조 불가능·시험 불가능 후보를 제외.'],['② 모델 학습','문헌 + 현재까지 측정된 개발용 직접 실험으로 학습. 전처리·모델 선택은 학습 내부에서 수행.'],['③ 예측·선택','후보의 log icorr 예측값, 불확실성, 학습범위와의 거리를 계산하고 규칙에 따라 batch를 선택.'],['④ 사전 기록','측정 전 모델 버전·예측값·불확실성·선택 사유·예측 시각을 저장.'],['⑤ 실험·평가','동일 프로토콜로 실제 icorr 측정. 저장된 사전 예측과 먼저 비교.'],['⑥ 추가·재학습','검증된 실측값만 학습자료에 추가하고 후보에서 제거. 반복시편은 조건·배치로 연결.']],[80,W-80])
p('처음 적용할 후보 선택 규칙','h')
p('예측 정확도 개선이 목표라면 불확실성과 후보 다양성을 함께 사용하는 단순 규칙부터 시작한다. 예를 들어 학습 피처 공간에서 불확실성 순위와 기존 실험에서의 거리 순위를 같은 가중치로 더하고, 하나를 고를 때마다 나머지 후보의 중복을 줄인다. 이 0.5/0.5 가중치는 본 프로젝트의 시작 예시이며 선행논문의 보편 최적값이 아니다. [2,3]')
p('u(x) = bootstrap 모델들의 log icorr 예측 표준편차<br/>예시 점수 A(x) = 0.5 × rank[u(x)] + 0.5 × rank[거리(x, 기존 관측)]','small')
p('현재 코드의 15개 bootstrap SVR 분산은 후보 순위를 만드는 휴리스틱이다. 이를 95% 신뢰구간이나 검증된 오차확률이라고 부르지 않는다. 입력이 학습범위에서 멀면 모델들이 모두 틀리면서 서로 비슷한 값을 낼 수도 있다. 같은 시편의 중복 선택을 막고, 측정 잡음을 확인할 반복실험도 별도로 배정한다. Gaussian process는 비교 후보이며 불확실성 역시 실측 오차로 점검한다.')

page('3. 구체적인 시작 예시','아래는 측정 전 설계 예시다. 실제 사용자의 합금·RE 범위·장비 조건을 확인한 후 수치 설정')
p('우선 하나의 질문을 고정한다','h')
p('예: “같은 강종·같은 시험환경에서 RE 함량과 시효조건이 바뀔 때 icorr를 얼마나 정확히 예측할 수 있는가?” 처음부터 강종·염 종류·pH·조성·열처리를 전부 자유롭게 바꾸지 말고, 연구의 핵심 변수를 제외한 조건을 고정한다. RE를 연구한다면 실제 측정한 RE 함량을 사용하고 원소 종류와 제조 배치를 함께 기록한다.')
table([['시점','실행 예시','남길 결과'],['초기 준비','사용 가능한 직접 실험은 개발용 초기 데이터로 사용. 별도 평가할 조건은 사전에 분리. 문헌 자료는 조건별로 선별.','문헌/직접 자료 구분, 배치·조건 ID'],['후보 구성','실행 가능한 조성·RE 함량·열처리 조합으로 후보표 작성. 수치 범위는 연구자가 확정.','미측정 후보 목록; icorr는 빈칸'],['1회차 예시','서로 다른 후보 3조건을 모델이 선택. 조건당 독립 시편 3개면 총 9시편. 예산 예시이며 최소 요건 아님.','측정 전 예측 3개, 조건별 3개 실측'],['반복','측정값을 검증한 뒤 재학습하고 다음 후보 선택. 기존 조건의 재현성 확인도 별도 배정.','round별 사전 예측 오차와 모델 버전']],[82,260,W-342])
p('왜 앞서 480°C가 등장했나','h')
p('그 값은 예시 외부 논문에서 사용한 17-4PH의 시효온도다. 해당 논문은 1040°C·60분 용체화 → 수냉 → 480°C에서 1/4/8/32시간 시효 → 공냉이다. 사용자의 RE 강 연구에 480°C를 그대로 권하는 뜻이 아니다. 실제 연구의 열처리 범위를 별도로 정해야 한다. [8]')
p('기존 12시편 표의 위치','h')
p('앞서 만든 480°C·4시간조건 × 3시편 표는 이 논문 조건을 재현하기 위한 고정 실험계획이다. 모델이 그 조건을 선택한 기록이 없으므로 그 자체가 active learning 결과는 아니다. 초기 실험 또는 재현성 확인용으로 쓰고, 그 뒤 후보 선택을 모델에 연결하면 된다.')

page('4. 정확도가 좋아졌다는 것을 어떻게 보이나','주장은 “데이터를 넣었다”가 아니라 “같은 측정 예산으로 예측 오차가 줄었다”')
table([['평가','방법','주의점'],['초기 내부 평가','문헌/초기 데이터의 무작위 80:20 test와 학습 내부 CV','기존 seed42 test는 이미 반복 확인한 개발 비교 자료'],['직접 실험 사전 예측','M(t)로 예측 저장 → 실험 → 오차 계산 → 그 후 학습 추가','측정 후 재학습한 모델로 같은 관측을 맞춘 값은 신규 예측 성능이 아님'],['고정 평가자료','목표 실험 범위에서 대표 조건을 사전 지정하고 학습·후보 선택에서 제외','각 round 뒤 성능 추적 가능. 추적으로 모델을 조정했다면 최종 미관측 검증을 따로 확보'],['전략 비교','같은 초기 데이터·후보·실험 budget에서 random 선택과 AL 선택 비교','서로 다른 조건을 같은 round에 측정하므로 사전 예측 오차만으로 AL 우위 단정 금지'],['최종 확인','추가 미관측 조건·별도 배치 또는 새 논문에서 모델 고정 후 검증','외부 논문 R²는 필수 형식은 아니지만, 다른 환경까지 예측한다는 주장은 그 범위에서 검증']],[82,240,W-322])
p('보고할 지표와 그림','h')
p('주 지표는 log10(icorr) R²·RMSE·MAE, 기하평균 배수 오차와 2배 이내 비율이다. 가로축을 추가 측정한 고유 조건 수 또는 실제 시편·비용으로 두고, 세로축은 동일 고정 평가자료의 오차로 그린다. 반복시편 3개를 서로 다른 3조건으로 세지 않는다. 조건·배치가 같은 반복은 평가와 학습 양쪽에 나누지 않는다.')
p('R²가 불안정한 경우','h')
p('직접 실험 수가 적거나 icorr 범위가 좁으면 큰 음수 R²가 나올 수 있다. 실제값과 예측값, 배수 오차를 함께 보여준다. 새 실험값을 학습에 넣는 것은 정상 절차지만, 넣은 후 그 값으로 계산한 높은 R²를 독립 예측 결과라고 보고하면 안 된다. [5,7]')

page('5. 현재 결과와 다음 실행 순서','지금까지 확인한 개발 결과와 아직 하지 않은 직접 실험 기반 AL을 분리')
table([['현재 자료/실행','확인된 상태'],['문헌 확장 자료','385행 중 icorr 검증된 377행. 사용자의 신규 실측 자료를 이 작업에서 식별·병합한 것은 아님.'],['기존 SVR','무작위 test log R²=0.7597, 기하평균 배수 오차=2.28배.'],['학습 내부 CV 선정 RF','같은 test log R²=0.7848, 배수 오차=2.48배. 모든 지표가 개선된 것은 아님.'],['17-4PH 외부 개발 사례','기존 SVR의 4조건 배수 오차=7.75배. 조건과 공정이 다른 문헌 적용의 한계 사례.'],['단계별 피처 추가 예시','같은 외부 사례에서 49.46배로 악화. 단계 정보 확보·대상 영역 확인 없이 피처 증가만으로 해결되지 않음.']],[130,W-130])
p('원하는 연구의 다음 순서','h')
p('1. 사용자가 실제로 측정한 자료를 원문값 그대로 표준 입력표에 연결하고, 합금·RE·공정·시험환경과 반복구조를 확인한다.<br/>2. 기존 직접 실험 중 학습에 사용할 부분과 평가용 조건을 먼저 결정한다. 다음 실험의 가능 범위를 후보표로 만든다.<br/>3. 문헌만 사용 / 직접 실험만 사용 / 문헌+직접 실험을 비교해 문헌 혼합이 도움이 되는지 확인한다. 조건 불일치가 크면 무조건 전체 문헌을 합치지 않는다.<br/>4. 초기 모델과 후보 선택 규칙을 고정하고 다음 batch를 추천한다. 실험 전 예측을 저장한다.<br/>5. 측정 후 사전 예측 오차를 기록하고 재학습한다. random 기준과 같은 예산으로 학습곡선을 비교한다.')
p('현재 코드와의 연결','h')
p('corrosion_ml/model.py에는 random / uncertainty / diverse_uncertainty 선택 로직과 bootstrap SVR이 있다. experiments.py에는 정답을 제외한 예측·측정값 비교 기능이 있다. 다만 현 평가 CLI의 기준 모델은 기존 운영 모델이므로, 최신 학습자료 및 직접 실험을 사용하는 별도 버전의 학습·예측·query 기록을 연결해야 한다. 이 PDF 작성만으로 그 운영 연결이나 실제 AL 실험이 완료된 것은 아니다.','small')
p('연구 설명 문장 예시','h')
p('“문헌 기반 초기 회귀모델을 구축한 후, 예측 불확실성과 후보 다양성을 이용해 후속 실험조건을 선정하였다. 직접 측정한 부식전류밀도를 순차적으로 추가하여 모델을 갱신하고, 동일한 실험 예산의 무작위 선택 기준 및 별도 평가자료에 대해 예측 성능을 비교하였다.” 실제 반복실험을 수행한 뒤에 사용할 문장이다. [2,3,4]','small')

refs=[
('1','Wang, Y., et al. (2022). Integrated High-Throughput and Machine Learning Methods to Accelerate Discovery of Molten Salt Corrosion-Resistant Alloys. Advanced Science, 9, 2200370.','10.1002/advs.202200370','첨부 도식과 대응하는 제작·용융염 시험·자동 분석·물리 descriptor·ML 통합 연구. 이를 직접적인 icorr active learning 검증으로 인용하지 않는다. 용융염 결과와 수용액 icorr는 구별한다.'),
('2','Lookman, T.; Balachandran, P. V.; Xue, D.; Yuan, R. (2019). Active learning in materials science with emphasis on adaptive sampling using uncertainties for targeted design. npj Computational Materials, 5, 21.','10.1038/s41524-019-0153-8','불확실성·utility function을 이용한 순차 후보 선택의 방법론 근거. 예측 학습과 목표 물성 최적화의 선택 목적을 구별할 때 참고.'),
('3','Venkatraman, A., et al. (2024). An active learning framework for the rapid assessment of galvanic corrosion. npj Materials Degradation, 8, 54.','10.1038/s41529-024-00476-4','부식 분야의 acquisition 기반 순차 학습 사례. FE 시뮬레이션과 실험 경계조건을 사용한 갈바닉 전류 모델로, 사용자의 직접 Tafel icorr 실험과 동일한 측정 체계는 아니다.'),
('4','Cai et al. (2025). A process-synergistic active learning framework for high-strength Al-Si alloys design. npj Computational Materials, 11, 228.','10.1038/s41524-025-01721-3','후보 합금 선택·실험 검증·데이터 반영을 반복하는 실험 연계 사례. 목표는 Al-Si 강도이며 부식 성능의 직접 증거는 아니다. 본 계획의 3조건 batch와 동일 설계라고 주장하지 않는다.'),
('5','Dong, Z., et al. (2024). Machine learning-based corrosion rate prediction of steel embedded in soil. Scientific Reports, 14, 18194.','10.1038/s41598-024-68562-w','1428건 무작위 80:20 분리와 RF/SVR/MLP 비교 사례. 외부 논문 검증이 모든 부식 AI 연구의 필수 형식은 아니라는 구분에 사용. 토양/LPR 조건은 본 수용액 자료와 다르다.'),
('6','Ghorbani, M.; Li, Z.; Pasquini, A.; Vasa, R.; Birbilis, N. (2025). Supervised machine learning for corrosion assessment of multi-principal element alloys using experimental and generative datasets. npj Materials Degradation, 9, 155.','10.1038/s41529-025-00700-9','문헌 기반 부식 물성과 여러 회귀모델의 train/test 비교 사례. icorr·Ecorr·Epit를 다룬다고 Ecorr를 측정 전 icorr의 필수 입력으로 써야 한다는 뜻은 아니다. GAN은 본 계획에 적용하지 않음.'),
('7','Chen, Q.; Cai, Y.; Zhu, Y.; Ji, H.; Ma, X.; Wang, H. (2025). An Integrated Approach Using GA-XGBoost and GMM-RegGAN for Marine Corrosion Prediction Under Small Sample Size. Materials, 18, 3760.','10.3390/ma18163760','80:20 평가와 최적화 중 5fold CV/RMSE의 구분에 참고. 합성 자료 증강과 직접 실험을 추가하는 active learning은 다른 절차다. 본 보고서는 GA·GAN을 실행하지 않음.'),
('8','G. Narasinga Rao et al. (2025). Effect of Aging Duration on the Microstructure and Corrosion Characteristics of 17-4 PH Stainless Steel. Procedia Structural Integrity, 71, 317-324.','10.1016/j.prostr.2025.08.043','기존 외부 개발 검증의 원문. Table 2의 1040도 용체화/480도 시효, Table 3의 icorr 평균 사용. 이미 결과를 확인한 자료이며 사용자의 새 실험 결과가 아님.'),
('9','Kerbout et al. (2025). Influence of Selective Laser Melting Process and Heat Treatment Parameters on the Corrosion Resistance of 17-4 Precipitation Hardening Stainless Steel. Metals, 15, 232.','10.3390/met15030232','현재 문헌 자료의 9조건 출처. 용체화/시효와 레이저 출력·속도가 달라지는 SLM 실험이므로, 압연재와 같은 공정 자료로 취급하지 않는다.'),
('10','Szewczyk-Nykiel et al. (2017). Effect of Aging Temperature on Corrosion Behavior of Sintered 17-4 PH Stainless Steel in Dilute Sulfuric Acid Solution. Journal of Materials Engineering and Performance, 26, 3450-3456.','10.1007/s11665-017-2778-4','현재 단계별 정리 자료의 6조건 출처. 분말소결·황산 환경이며 NaCl 압연재와 구별.')]
for block_index,block in enumerate([refs[:5],refs[5:]],1):
    page(f'참고문헌과 적용 범위 {block_index}/2','원문 DOI 링크 | 방법론 근거와 기존 데이터 출처를 구분해 기재')
    for number,citation,doi,note in block:
        p('['+number+'] '+citation,'small')
        p('<link href="https://doi.org/'+doi+'" color="#087F8C">https://doi.org/'+doi+'</link>','small')
        p('본 연구에 적용: '+note,'small');story.append(Spacer(1,9))

def footer(c,doc):
    c.setStrokeColor(colors.HexColor('#C9DADF'));c.line(44,39,A4[0]-44,39)
    c.setFont('KR',7.5);c.setFillColor(INK);c.drawString(44,26,'REE_AL | Experimental active learning plan | 2026-10-24')
    c.drawRightString(A4[0]-44,26,str(doc.page))
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=40,bottomMargin=51,
    title='직접 실험 기반 부식 예측 Active Learning 파이프라인',author='REE_AL').build(story,onFirstPage=footer,onLaterPages=footer)
doc=pymupdf.open(OUT)
for i,pag in enumerate(doc):pag.get_pixmap(matrix=pymupdf.Matrix(1.1,1.1)).save(TMP/f'page-{i+1}.png')
assert len(doc)==8, len(doc)
assert all(len(pag.get_text().strip())>100 for pag in doc)
(TMP/'reference_map.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2),encoding='utf-8')
print(str(OUT));print('Pages:',len(doc));print('References:',len(refs))
