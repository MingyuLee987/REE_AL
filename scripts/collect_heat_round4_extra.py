"""Additional public primary papers for the 300-row collection."""
import concurrent.futures as cf
import json
import sys
from urllib.parse import quote
import pandas as pd
from collect_grain_size import ROOT,key,env,request,save_json,blocks,norm
import collect_more_heat_papers as collect
from collect_heat_round4 import extract_batches
from expand_heat_treatment_data import OUT,SCHEMA,INSTRUCTIONS,api_json

ROUND=ROOT/'outputs/heat_expansion_round4_extra_20261023'
CANDIDATE_FILE='round4_extra_candidates.csv'
ADDITIONAL=[('10.1155/ijco/5531986','Corrosion Rate of Medium-Carbon Steel Quenched in Nanofluids (Al2O3 and CuO) at Different Temperatures'),('10.1016/j.corcom.2022.06.004','Effect of rare earth on corrosion of GCr15 steel'),('10.1016/j.jmrt.2025.01.207','Effect of rare earth on corrosion resistance of low-alloy steel')]
SPECS=[
 ('10.3390/ma14133759','Effect of Sub-Zero Treatments and Tempering on Corrosion Behaviour of Vanadis 6 Tool Steel','materials',14,3759),
 ('10.3390/ma15051746','Long-Term Corrosion Behavior of Strong and Ductile High Mn-Low Cr Steel in Acidic Aqueous Environments','materials',15,1746),
 ('10.3390/ma18174125','Effect of Back-Tempering on the Wear and Corrosion Properties of Multiple-Pass Friction Stir Processed High-Speed Steel','materials',18,4125),
 ('10.3390/ma12203359','Mechanism Understanding of the Role of Rare Earth Inclusions in the Initial Marine Corrosion Process of Microalloyed Steels','materials',12,3359),
 ('10.1038/s41598-023-31803-5','Effect of heat treatment atmospheres on microstructure evolution and corrosion resistance of 2205 duplex stainless steel weldments',None,None,None),
 ('10.1038/s41598-026-53108-z','Corrosion resistance behavior of additively manufactured 316L stainless steel in nuclear environments',None,None,None),
 ('10.3390/ma15010252','Production, Mechanical Properties and Biomedical Characterization of ZrTi-Based Bulk Metallic Glasses in Comparison with 316L Stainless Steel and Ti6Al4V Alloy','materials',15,252),
 ('10.3390/ma12060987','Corrosion Resistance of Stainless Steels Intended to Come into Direct or Prolonged Contact with the Skin','materials',12,987),
 ('10.3390/ma15072560','Effects of Temperature and Applied Potential on the Stress Corrosion Cracking of X80 Steel in a Xinzhou Simulated Soil Solution','materials',15,2560),
]
DIRECT=[
 ('10.17222/mit.2021.014','Corrosion behaviour of tempered 42CrMo4 steel','https://mater-tehnol.si/ojs-3.1.2-4/index.php/MatTech/article/download/14/63'),
 ('10.1016/S1452-3981(23)05063-0','Electrochemical corrosion behavior and prediction of corrosion rate for low alloy steel after tempering treatment','https://www.electrochemsci.org/papers/vol10/100201169.pdf'),
 ('10.1007/s40962-024-01543-x','Effect of Different Heat Treatment Procedures on the Corrosion Behavior of High-Manganese Austenitic Steels','https://link.springer.com/content/pdf/10.1007/s40962-024-01543-x.pdf'),
 ('10.3934/matersci.2023004','Effect of sub-zero treatments on hardness and corrosion properties of low-alloy nickel steel','https://www.aimspress.com/aimspress-data/aimsmates/2023/1/PDF/matersci-10-01-004.pdf'),
 ('10.2320/matertrans.MRA2008252','A Study on Corrosion Behavior of DP-Type and TRIP-Type Cold Rolled Steel Sheet','https://www.jstage.jst.go.jp/article/matertrans/50/6/50_MRA2008252/_pdf'),
 ('10.1016/j.jelechem.2023.117207','Heat treatment and corrosion of steel','https://digibuo.uniovi.es/dspace/bitstream/handle/10651/67922/1-s2.0-S157266572300067X-main.pdf?sequence=1'),
 ('10.1016/j.corsci.2024.112027','CO2 corrosion resistance of low-alloy steel subjected to different tempering treatments','https://backend.orbit.dtu.dk/ws/portalfiles/portal/357331072/1-s2.0-S0010938X24002117-main.pdf'),
]
def direct(spec,e):
 doi,title,url=spec;p=ROUND/'sources'/f'{key(doi)}.json'
 if p.exists():return json.loads(p.read_text(encoding='utf-8'))
 status,raw=request(url,timeout=55);bb=[];paths=[]
 if status==200 and raw.startswith(b'%PDF'):
  path=ROUND/'fulltext'/f'{key(doi)}.pdf';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);bb=blocks(path);paths=[str(path)]
 paper=dict(doi=doi,title=title,blocks=bb,source_paths=paths,access=[dict(provider='Public primary manuscript',url=url,http_status=status)])
 save_json(p,paper);print(json.dumps(dict(doi=doi,blocks=len(bb),status=status)),flush=True);return paper
def main():
 sys.stdout.reconfigure(encoding='utf-8');e=env();ROUND.mkdir(parents=True,exist_ok=True);collect.ROUND=ROUND
 collect.DISCOVER=collect.DISCOVER.replace('tabulated experimental','tabulated or explicitly numerically stated prose experimental').replace('eligible tabulated rows','eligible tabulated or explicitly numerically reported prose values')+' Exact known current and exposed area permit explicit documented normalization; do not assume an area. Earlier heat stages may be retained only with explicit stage labeling and unknown later stages flagged.'
 with cf.ThreadPoolExecutor(max_workers=4) as pool:
  papers=list(pool.map(collect.retrieve,SPECS))+list(pool.map(lambda s:direct(s,e),DIRECT))
 for doi,title in ADDITIONAL:
  if doi.startswith(('10.1155','10.1002')):
   url='https://api.wiley.com/onlinelibrary/tdm/v1/articles/'+quote(doi,safe='');status,raw=request(url,{'Wiley-TDM-Client-Token':e['WILEY_TDM_TOKEN']},timeout=65)
   if status==200 and raw.startswith(b'%PDF'):
    path=ROUND/'fulltext'/f'{key(doi)}.pdf';path.write_bytes(raw);paper=dict(doi=doi,title=title,blocks=blocks(path),source_paths=[str(path)],access=[dict(provider='Wiley TDM',http_status=status)]);save_json(ROUND/'sources'/f'{key(doi)}.json',paper);papers.append(paper)
  else:papers.append(collect.retrieve((doi,title,None,None,None)))
 old=set(pd.read_csv(ROOT/'data/al_heat_expanded_round3_20261023/al_labeled_heat_treatment_expanded.csv').source_paper_id)
 papers=[p for p in papers if p['doi'] not in old]
 save_json(ROUND/'screened_sources.json',[{k:v for k,v in p.items() if k!='blocks'} for p in papers])
 with cf.ThreadPoolExecutor(max_workers=3) as pool:parts=list(pool.map(lambda p:collect.one(p,e),papers))
 rows=[r for part in parts for r in part];pd.DataFrame(rows).to_csv(OUT/CANDIDATE_FILE,index=False,encoding='utf-8-sig');print('Extra candidate rows: '+str(len(rows)),flush=True)
 jobs=[]
 for paper in papers:
  rr=[r for r in rows if r['source_paper_id']==paper['doi']]
  if rr:jobs+=extract_batches(paper,rows,e)
 def extract(job):
  paper,start,inp=job;cache=ROUND/'extraction_chunks'/f'{key(paper["doi"])}_{start}.json'
  result=json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else api_json(e,e['OPENAI_MODEL'],INSTRUCTIONS+' Explicit numerical prose is eligible. Preserve the exact heat stage; never infer an unreported hold. Document earlier stages and later unknown holds.',inp,SCHEMA,'extra_heat_attributes',max_tokens=14000)
  save_json(cache,result);print(json.dumps(dict(doi=paper['doi'],batch=start,records=len(result.get('records',[])),error=result.get('error'))),flush=True);return paper,result
 grouped={}
 with cf.ThreadPoolExecutor(max_workers=3) as pool:
  for paper,result in pool.map(extract,jobs):grouped.setdefault(paper['doi'],[]).append(result)
 for paper in papers:
  if paper['doi'] not in grouped:continue
  records=[];cids={r['record_id'] for r in rows if r['source_paper_id']==paper['doi']}
  for part in grouped[paper['doi']]:
   for r in part.get('records',[]):
    r['candidate_exists']=r['candidate_id'] in cids;r['target_quote_verified']=bool(norm(r['target_quote']) and any(norm(r['target_quote']) in norm(b['text']) for b in paper['blocks']))
    for a in r['attributes']:a['quote_verified']=bool(norm(a['quote']) and any(norm(a['quote']) in norm(b['text']) for b in paper['blocks']))
    records.append(r)
  save_json(OUT/'extractions'/f'{key(paper["doi"])}.json',dict(doi=paper['doi'],title=paper['title'],records=records,retry_partial_failure=any('error' in p for p in grouped[paper['doi']]),exclusion_note='Primary evidence, small batch extraction.'))
  stale=OUT/'reviews'/f'{key(paper["doi"])}.json'
  if stale.exists():stale.unlink()
 print('Extra extraction complete.',flush=True)
if __name__=='__main__':main()
