"""Additional primary PDFs, including yttrium-alloyed H13 steel."""
import concurrent.futures as cf
import json
import sys
import pandas as pd
from urllib.parse import quote
from collect_grain_size import env,key,save_json,request
from collect_more_heat_papers import ROUND,one
from expand_heat_treatment_data import OUT,extract_one

def main():
    sys.stdout.reconfigure(encoding='utf-8');e=env();papers=[]
    for doi in ['10.3390/met15090935','10.3390/met15010085','10.3390/ma14123254']:
        p=ROUND/'sources'/f'{key(doi)}.json';d=json.loads(p.read_text(encoding='utf-8'))
        s,b=request('https://api.crossref.org/works/'+quote(doi,safe=''))
        if s==200:d['title']=json.loads(b)['message']['title'][0]
        else:d['title']='Primary steel corrosion study '+doi
        save_json(p,d);papers.append(d)
    pdf=ROUND/'frontiers_pdf_source.json'
    if pdf.exists():
        d=json.loads(pdf.read_text(encoding='utf-8'));papers.append(d)
        cache=ROUND/'target_discovery'/f'{key(d["doi"])}.json'
        if cache.exists() and not json.loads(cache.read_text(encoding='utf-8')).get('targets'):
            save_json(ROUND/'metadata_only_discovery'/cache.name,json.loads(cache.read_text(encoding='utf-8')));cache.unlink()
    with cf.ThreadPoolExecutor(max_workers=3) as pool:parts=list(pool.map(lambda p:one(p,e),papers))
    rows=[r for rr in parts for r in rr]
    prior=pd.read_csv(OUT/'round2_candidates.csv',float_precision='round_trip')
    pd.concat([prior,pd.DataFrame(rows)],ignore_index=True).drop_duplicates('record_id').to_csv(OUT/'round2_candidates.csv',index=False,encoding='utf-8-sig')
    def extract(p):
        rr=[r for r in rows if r['source_paper_id']==p['doi']]
        if not rr:return
        r=extract_one(dict(doi=p['doi'],title=p['title'],candidates=rr,blocks=p['blocks']),e)
        print(json.dumps(dict(doi=p['doi'],records=len(r.get('records',[])),error=r.get('error'))),flush=True)
    with cf.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(extract,papers))

if __name__=='__main__':main()
