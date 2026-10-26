import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from collect_grain_size import ROOT,key,request,blocks,save_json
OUT=ROOT/'outputs/expansion_20261024'
doi='10.1007/s13369-024-09647-6'
url='https://link.springer.com/content/pdf/'+doi+'.pdf'
s,raw=request(url,timeout=45)
bb=[];paths=[]
if s==200 and raw.startswith(b'%PDF'):
 p=OUT/'fulltext'/f'{key(doi)}.pdf';p.write_bytes(raw);bb=blocks(p);paths=[str(p)]
save_json(OUT/'sources'/f'{key(doi)}.json',dict(doi=doi,title='Effect of Heat Treatment on Corrosion Behavior of S275 Mild Steel Using Accelerated DC Voltage, LPR, and EIS',blocks=bb,source_paths=paths,access=[dict(provider='publisher public PDF',status=s,url=url)]))
print(s,len(bb))
