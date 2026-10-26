"""Preserve the original six pages and add four source-traceable methods pages."""
import hashlib
import io
import json
from pathlib import Path
from xml.sax.saxutils import escape

import pymupdf
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.pdfgen import canvas

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf'
TMP=ROOT/'tmp/pdfs/heat_treatment_revision'
NAME='문헌데이터_수집과정_정리_조성보완_열처리추가_개정본.pdf'
NAVY=colors.HexColor('#173C66');INK=colors.HexColor('#293C50');MUTED=colors.HexColor('#59728C')

def main():
    OUT.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
    source=Path(json.loads((ROOT/'data/literature/manifest.json').read_text(encoding='utf-8'))['input_guideline'])
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    summary=json.loads((ROOT/'data/al_heat_expanded_round2_20261023/summary.json').read_text(encoding='utf-8'))
    pdfmetrics.registerFont(TTFont('Korean','C:/Windows/Fonts/malgun.ttf'))
    pdfmetrics.registerFont(TTFont('KoreanBold','C:/Windows/Fonts/malgunbd.ttf'))
    pdfmetrics.registerFontFamily('Korean',normal='Korean',bold='KoreanBold',italic='Korean',boldItalic='KoreanBold')
    styles={
        'title':ParagraphStyle('title',fontName='KoreanBold',fontSize=16,leading=23,textColor=NAVY,spaceAfter=13,wordWrap='CJK'),
        'h':ParagraphStyle('h',fontName='KoreanBold',fontSize=11.1,leading=17,textColor=NAVY,spaceBefore=10,spaceAfter=6,wordWrap='CJK'),
        'body':ParagraphStyle('body',fontName='Korean',fontSize=9.8,leading=15.6,textColor=INK,spaceAfter=8,wordWrap='CJK'),
        'small':ParagraphStyle('small',fontName='Korean',fontSize=8.5,leading=13.2,textColor=INK,spaceAfter=6,wordWrap='CJK'),
        'cell':ParagraphStyle('cell',fontName='Korean',fontSize=8.8,leading=13.5,textColor=INK,wordWrap='CJK'),
        'headcell':ParagraphStyle('headcell',fontName='KoreanBold',fontSize=8.9,leading=13.5,textColor=colors.white,wordWrap='CJK'),
    }
    story=[]
    def para(s,kind='body'):return Paragraph(s,styles[kind])
    def p(s,kind='body'):story.append(para(s,kind))
    def h(s):p(s,'h')
    def table(rows,widths):
        cells=[[para(escape(str(x)),'headcell' if i==0 else 'cell') for x in row] for i,row in enumerate(rows)]
        t=Table(cells,colWidths=widths,hAlign='LEFT',repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#F1F5F9'),colors.white]),('LINEBELOW',(0,0),(-1,0),.5,NAVY),('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#CFDAE5'))]))
        story.append(t);story.append(Spacer(1,8))
    width=A4[0]-92

    p('10. 열처리 온도·시간의 문헌 수집 방법','title')
    p('<b>추가 개정 2026-10-23.</b> 앞 1-6쪽은 2026-10-22 조성 보완 이력으로 보존한다. 5쪽의 RF 및 과거 R²는 개발 당시 기록이며, 현재 확장 CSV의 학습·검증 결과가 아니다. 이번 추가 절은 사전에 정할 수 있는 열처리 입력을 실제로 수집한 방법을 설명한다.')
    h('10.1 피처의 정의와 수집 대상')
    p('공정 입력은 <b>heat_treatment_temperature_C</b>(유지 온도, ℃)와 <b>heat_treatment_time_min</b>(해당 온도에서의 유지시간, min) 두 항목으로 한정하였다. 동일 시편의 조성, 재료 상태, 계획된 전기화학 시험조건과 i_corr를 연결한다. 결정립 크기·측정 상분율은 제조 전 입력에서 제외하였다.')
    h('10.2 원문에서 값을 회수하는 순서')
    for text in [
        '<b>① 시편 식별:</b> DOI, 시편명, 처리 상태, 전해질·시험온도·침지 조건으로 한 행을 식별한다. 같은 논문의 다른 시편이나 다른 부식시험 조건을 섞지 않는다.',
        '<b>② 원출처 확인:</b> Experimental/Materials and Methods의 처리 설명, 열처리 표, 보충자료, 수치가 명시된 공정도·캡션을 대조한다. 승온 종료 온도만으로 유지 온도·시간을 만들어 넣지 않는다.',
        '<b>③ 온도-시간 쌍 연결:</b> 동일한 등온 유지단계의 두 값을 함께 기록한다. 용체화 온도와 시효 시간을 조합하거나, 시험온도와 열처리 시간을 연결하지 않는다.',
        '<b>④ 시편별 분기:</b> 공통 처리와 시편별 변경 조건을 구분한다. “모든 시편에 적용”이라는 근거가 있을 때만 공통 조건을 여러 행에 연결한다.',
        '<b>⑤ 단위 통일·검증:</b> 원래 수치·단위와 환산식을 남기고 ℃ 및 min으로 통일한다. API 추출값은 원문 인용문과 시편 연결을 재검토한다. 구체적인 감사 기록은 12절에 정리하였다.',
    ]:p(text)
    table([['보고 형식','기록 방법'],['1 h / 4 h / 2 s','60 min / 240 min / 0.03333 min으로 환산'],['482 ± 3 ℃','명시된 중심 설정값 482 ℃를 기록하고 ±3 ℃ 허용범위를 근거에 보존'],['온도 또는 유지시간 미보고','해당 항목은 결측으로 유지. 미처리를 0 ℃·0 min으로 대입하지 않음']],[121,width-121])
    p('<b>조성 보완과의 차이:</b> 다른 논문의 중앙값, 제조사 강종 대표값, 조성 유사도 또는 i_corr로 열처리 온도·시간을 추정하지 않았다. 범위만 있고 대표 설정값이 없는 열처리 조건도 임의의 중간값으로 완성하지 않는다.','small')
    story.append(PageBreak())

    p('11. 다단계 열처리의 기록 기준과 예시','title')
    p('다단계 이력을 온도·시간 두 숫자로 모두 표현할 수는 없다. <b>이번 신규 추출은 마지막으로 명시된 등온 유지단계를 기본으로 선택</b>하고, 이전 단계는 heat_history_note에 남겼다. 기존 자료는 앞서 확인한 대표 단계를 보존했으므로 용체화·시효·빌릿 재가열·소결이 섞여 있다. 현재 CSV가 하나의 동일한 처리단계로 통일됐다는 뜻은 아니다.')
    table([
        ['시편 / 출처','온도 (℃)','시간 (min)','선택한 단계와 보존한 이력'],
        ['SASS T30 [5]','1200','30','기존 자료의 용체화 단계. 이후 수냉 → 900 ℃/30 min 시효 → 공랭 이력을 별도 보존.'],
        ['17-4PH A480 [6]','480','60','최종 시효 단계. 선행 1040 ℃/60 min 용체화 및 수냉은 이력으로 기록.'],
        ['17-4PH F620 [6]','620','240','최종 시효 단계. 4 h를 240 min으로 환산.'],
        ['H13 Q / YQ [7]','1080','30','담금질 전 유지. 이후 유냉. 뜨임을 거친 QT/YQT와 구분.'],
        ['H13 QT / YQT [7]','580','120','최종 뜨임. 앞선 1080 ℃/30 min 유지 및 유냉 이력을 보존.'],
        ['A100 steel [8]','482','360','최종 뜨임. 원문 설정값 (482 ± 3) ℃/6 h. 앞선 담금질·심냉 이력은 별도 기록.'],
    ],[111,58,63,width-232])
    h('11.1 입력과 감사 메타데이터를 구분')
    p('<b>heat_treatment_stage</b>는 어떤 단계의 쌍을 택했는지, <b>heat_history_note</b>는 선행 처리와 냉각 이력을 설명한다. 이 컬럼들은 감사·층화용 메타데이터이며 현재 모델의 추가 공정 피처가 아니다. 다단계 이력의 일부만 입력에 반영된 경우 thermal_history_incomplete도 확인한다.')
    h('11.2 포함·보류의 경계')
    p('시험 중 용액 온도, OCP 안정화 시간, 부식 침지시간, 세척·건조시간은 열처리 유지조건과 구분한다. 승온속도·냉각속도·자연 발생한 용접 최고온도만으로 유지시간을 추정하지 않는다. 명시적 온도와 유지시간이 있는 제어된 Gleeble 모사 열사이클은 후보가 될 수 있지만, 대응 i_corr의 단위·시편 연결까지 확인해야 포함한다.')
    p('실제로 [9]의 CGHAZ는 1320 ℃에서 2 s 유지한 조건이 확인되었다. 그러나 Table 4의 전류 단위가 A·cm²로 표기되어 재검토에서 보류하였다. 열처리 두 값의 확보만으로 해당 부식행의 타당성이 자동 확보되지는 않는다.','small')
    p('<b>AL 적용 범위:</b> 온도·시간 두 피처를 사용할 때는 같은 강종, 같은 처리단계, 같은 선행 이력과 부식환경으로 범위를 좁히는 것이 바람직하다. 서로 다른 제조 이력을 두 숫자만으로 구별하거나, 관찰된 상관관계를 열처리의 독립적인 인과효과로 해석하지 않는다.','small')
    story.append(PageBreak())

    p('12. API 검증·출처 기록과 현재 집계','title')
    h('12.1 실제 수행한 검증 흐름')
    p('설정된 API 키를 사용해 문헌 메타데이터와 접근 가능한 원문을 조회하고, 이미 확보한 원문 및 공개 PDF도 함께 활용하였다. Elsevier 검색 API는 사용했으나 일부 원문은 접근 거부되었고 Springer API도 접근 제한이 있었다. 원문을 확보하지 못한 논문의 수치를 추측해 추가하지 않았다.')
    p('OpenAI API로 원문을 구조화하고, <b>인용문이 확보한 원문 블록에 그대로 존재하는지 코드로 확인</b>하였다. 이어 별도 모델 호출로 시편명, 열처리 단계, 온도·시간, 전류밀도 열과 단위 환산을 재검토하였다. 이는 API 보조 검증으로, 사람이 모든 원문을 독립적으로 검토했다거나 오류율 0%를 입증했다는 뜻은 아니다.')
    p('i_corr는 실험에서 보고된 Tafel/동전위분극 전류밀도를 우선하였다. 표와 본문에 명시된 수치는 허용했지만 그래프를 보고 임의의 숫자를 만들지 않았다. 예를 들어 [7]의 Q/YQ/QT/YQT 수치는 PDF 10쪽 본문에 직접 보고되어 있다. 부식률·부동태전류·공식전류 및 단위가 불명확한 후보는 별도로 보류하였다.')
    h('12.2 보존한 근거')
    p('record_id, source_paper_id, 시편명, 출처 URL, 원문 위치, 짧은 인용문, 원래 단위와 환산계수, 선택한 처리단계, 시편 대응 판단, 포함·보류 사유를 보존하였다. 새 값은 new_source_provenance.csv, 보류 후보는 rejected_or_unresolved.csv, 입력 목록은 feature_schema.json에서 확인할 수 있다.')
    table([
        ['집계 항목 (2026-10-23)','확인된 결과'],
        ['데이터 확장 이력','45행 → 142행 → 179행'],
        ['현재 전체 검토본','179행 / 39개 출처'],
        ['i_corr와 열처리 온도·시간 확인','160행. 다른 조성·시험조건의 결측은 남아 있음'],
        ['온도·시간 각각의 결측','19/179행, 10.61%'],
        ['핵심 조성 10개 + 주요 시험조건 충족','56행 / 11개 출처. 조성 추정 포함; 모든 피처 완비를 뜻하지 않음'],
        ['현재 남은 주요 결측','N: 81/179 (45.25%), pH: 157/179 (87.71%)'],
    ],[218,width-218])
    p('이번 마지막 추가분은 7개 출처의 37행이다. 이 중 Y 첨가 H13강 2행은 원문의 0.014 wt.%를 140 ppm으로 환산했다. 원문의 nominal 표기를 제조 후 잔류량 실측으로 단정하지 않는다. La·Ce·Y의 미보고 함량을 일괄 0으로 채우지 않았다.','small')
    p('<b>검증 범위:</b> 기존 142행의 i_corr를 보존했고, 논문 단위 5개 분할에서 검증 논문이 조성 donor와 IQR 산정에 들어가지 않도록 확인했다. 이는 데이터 준비 검증이며 새 모델 성능 평가 또는 실제 AL 실험 수행 결과가 아니다. 운영 학습자료와 모델은 재학습하지 않았다.','small')
    story.append(PageBreak())

    p('13. Methods 기술문·재현 자료','title')
    h('13.1 논문에 사용할 수 있는 열처리 수집 기술문')
    p('제조 전에 설정할 수 있는 공정변수로 열처리 유지 온도와 유지시간을 선정하였다. 각 문헌의 실험 방법, 열처리 표 및 보충자료에서 동일 시편의 온도-시간 쌍을 회수하고, 조성·재료 상태·전기화학 시험조건 및 부식전류밀도와 연결하였다. 온도와 시간은 각각 ℃와 min으로 통일하였으며, 원래 수치·단위와 환산 근거를 보존하였다. 열처리 온도·시간이 보고되지 않은 경우 다른 문헌이나 조성 유사도에 기반해 대치하지 않고 결측으로 유지하였다.')
    p('다단계 열처리에서는 신규 추출 자료의 마지막 명시적 등온 유지단계를 대표 입력으로 선택하고, 선행 처리와 냉각 이력 및 선택한 단계는 감사용 메타데이터로 기록하였다. 기존 자료에 보존된 대표 단계는 별도로 구분하였으며, 모든 관측이 동일한 열처리 단계에 해당한다고 가정하지 않았다. API를 이용한 구조화 결과는 원문 인용문 존재 여부와 시편·단위 대응을 재검토하였다. 미확정 타깃·단위 또는 열처리 대응 관계를 가진 관측은 학습 후보에서 보류하였다.')
    p('조성의 통계적 보완을 허용한 파일은 검토용으로 구분하였다. 독립 모델 평가에서는 논문 단위로 자료를 분리한 뒤 학습 분할에서만 조성 대치기와 척도를 산정한다. 열처리 온도·시간 및 i_corr 자체에는 통계적 대치를 적용하지 않는다. 현재 자료 준비 결과를 대치 후 성능 향상이나 능동학습 최적화의 실증 결과로 해석하지 않는다.')
    h('13.2 추가 근거 문헌')
    refs=[
        ('[5] 용체화 시간·온도를 변화시킨 SASS 부식시험 (2022).','10.3390/ma15248780'),
        ('[6] 17-4PH강 시효 처리와 부식거동 (2025).','10.3390/ma18081823'),
        ('[7] Y 첨가 H13강의 담금질·뜨임과 부식거동 (2025).','10.3390/met15090935'),
        ('[8] A100강의 초기 염무-SO2 부식거동; 482 ± 3 ℃ 뜨임.','10.1039/d5ra08480f'),
        ('[9] Zr-Ti-Al-RE 탈산 HSLA강의 CGHAZ 부식시험 (2023).','10.3390/ma16020876'),
    ]
    for label,doi in refs:p(escape(label)+'<br/><link href="https://doi.org/'+doi+'" color="#245A88">https://doi.org/'+doi+'</link>','small')
    h('13.3 파일과 재현 경로')
    p('현재 결과 폴더: <b>data/al_heat_expanded_round2_20261023/</b><br/>전체 검토본: al_labeled_heat_treatment_expanded.csv<br/>타깃·열처리 확인본: al_heat_checked_labels.csv<br/>이번 추가분: new_rows_this_round.csv<br/>원문 대조·조성 이력: new_source_provenance.csv / composition_imputation_log.csv<br/>집계·결측·검증: summary.json / missingness.csv / validation.json','small')
    p('수집·재검토 코드는 scripts/collect_more_heat_papers.py, recover_yttrium_text_targets.py, review_heat_expansion.py에 있고, 누적 결과 생성은 build_heat_expansion.py --round2로 수행했다. 전체 검토본의 조성 대치값을 독립 평가에 그대로 재사용하지 않고, paper_group_fold_*.csv의 분할별 보완 이력을 확인한다.','small')

    def decoration(c,doc):
        c.setStrokeColor(colors.HexColor('#BFCFE0'));c.setLineWidth(.5)
        c.line(46,A4[1]-36,A4[0]-46,A4[1]-36);c.line(46,35,A4[0]-46,35)
        c.setFont('Korean',7.6);c.setFillColor(NAVY)
        c.drawString(46,A4[1]-28,'REE RESEARCH | 문헌 수집·조성 보완·열처리 조건')
        c.setFillColor(MUTED);c.drawString(46,23,'추가 개정 2026-10-23 · 원문 회수와 조성 대치를 구분')
        c.drawRightString(A4[0]-46,23,str(doc.page+6))
    supplement=TMP/'heat_treatment_methods_appendix.pdf'
    doc=SimpleDocTemplate(str(supplement),pagesize=A4,rightMargin=46,leftMargin=46,topMargin=55,bottomMargin=51,title='열처리 온도·시간 문헌 수집 방법',author='REE_AL')
    doc.build(story,onFirstPage=decoration,onLaterPages=decoration)
    appendix=pymupdf.open(supplement)
    assert len(appendix)==4, f'Unexpected appendix pagination: {len(appendix)}'
    original=pymupdf.open(source);final=pymupdf.open();final.insert_pdf(original)
    # Original body stays intact; date label disambiguates the historical model/version statements.
    overlay=io.BytesIO();c=canvas.Canvas(overlay,pagesize=A4);c.setFillColor(MUTED);c.setFont('Korean',7)
    c.drawString(46,48,'2026-10-22 조성 보완 이력 | 열처리 조건 추가 개정: 7-10쪽 (2026-10-23)');c.save()
    label=pymupdf.open(stream=overlay.getvalue(),filetype='pdf')
    for page in final:page.show_pdf_page(page.rect,label,0)
    final.insert_pdf(appendix)
    final.set_metadata(dict(title='문헌데이터 수집·조성 보완 및 열처리 조건 수집 방법',author='REE_AL',subject='2026-10-23 열처리 온도·시간 수집 및 검증 방법 추가'))
    final.set_toc([[1,'조성 보완 이력 (2026-10-22)',1],[1,'10. 열처리 온도·시간 수집',7],[1,'11. 다단계 열처리와 예시',8],[1,'12. API 검증과 현재 데이터',9],[1,'13. Methods 기술문과 재현 자료',10]])
    target=OUT/NAME;final.save(target,garbage=4,deflate=True)
    assert source_hash==hashlib.sha256(source.read_bytes()).hexdigest()
    check=pymupdf.open(target);assert len(check)==10
    text='\n'.join(page.get_text() for page in check)
    for required in ['heat_treatment_temperature_C','heat_treatment_time_min','179','160','10.61','482','1320','0.03333']:
        assert required in text,required
    assert '\ufffd' not in text
    (TMP/'revised_extracted_text.txt').write_text(text,encoding='utf-8')
    report=dict(source=str(source),source_sha256=source_hash,output=str(target),pages=len(check),original_pages=6,added_pages=4,original_file_unchanged=True,data_version='al_heat_expanded_round2_20261023')
    (TMP/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))

if __name__=='__main__':main()
