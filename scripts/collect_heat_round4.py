"""Collect enough source-verified steel experiments for the 300-row milestone."""
import concurrent.futures as cf
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote
import pandas as pd
from collect_grain_size import ROOT,OUT as GOUT,key,norm,env,request,save_json
import collect_more_heat_papers as collect
from expand_heat_treatment_data import OUT,SCHEMA,INSTRUCTIONS,api_json

ROUND=ROOT/'outputs/heat_expansion_round4_20261023'
SPECS=[
 ('10.3390/met14040391','Effect of Nitrogen on the Corrosion Resistance of 6Mo Super Austenitic Stainless Steel','metals',14,391),
 ('10.3390/met15111249','Effect of Aluminum Content on the Corrosion Behavior of Fe-Mn-Al-C Structural Steels in Marine Environments','metals',15,1249),
 ('10.3390/coatings15060649','Corrosion and Wear Behavior of 17-4PH Stainless Steel Manufactured by Selective Laser Melting and Bulk Material After Solution Treatment','coatings',15,649),
 ('10.3390/met13101700','Analysis of a Double Aging Process in a Maraging 300 Steel Fabricated by Selective Laser Melting, Using the Design of Experiments Technique','metals',13,1700),
 ('10.3390/coatings14040413','Effect of Doping Trace Rare Earth Elements on Corrosion Behavior of EH36 Offshore Platform Steel','coatings',14,413),
]
LEGACY=[
 '10.1038/s41529-025-00682-8','10.1007/s11663-025-03817-z','10.1007/s11663-026-04267-x',
 '10.1002/adem.202402545','10.1002/maco.201911150','10.1002/maco.202213672',
 '10.1038/s41598-024-67799-9','10.3390/ma18010069','10.3390/ma17184467',
 '10.1007/s42243-025-01553-x','10.1038/s41598-018-23273-x',
]
DIRECT=[
 ('n80','10.22399/ijcesen.4161','Effect of temperature on Microstructure and Corrosion Behavior of Carbon Steel: Experimental study and modeling'),
 ('ca6nm','10.17675/2305-6894-2022-11-4-15','Effect of single and double tempering on corrosion behavior of modified CA6NM steel in 3.5% NaCl solution'),
 ('co2','10.1016/j.corsci.2019.03.009','Effect of tempering heat treatment on the CO2 corrosion resistance of quench-hardened Cr-Mo low-alloy steels for oil and gas applications'),
 ('hcr','10.20964/2022.08.24','Effects of Austenitizing Temperature on Microstructure Evolution and Corrosion Resistance of High Cr Ferritic/Martensitic Steel'),
]

def extract_batches(paper,rows,e):
    """Keep calls small enough to avoid the earlier large-output timeouts."""
    doi=paper['doi'];rr=[r for r in rows if r['source_paper_id']==doi]
    inp=dict(doi=doi,title=paper['title'],candidates=rr,source_blocks=paper['blocks'])
    save_json(OUT/'inputs'/f'{key(doi)}.json',inp)
    return [(paper,start,{**inp,'candidates':rr[start:start+4]}) for start in range(0,len(rr),4)]

def main():
    sys.stdout.reconfigure(encoding='utf-8');ROUND.mkdir(parents=True,exist_ok=True);e=env();collect.ROUND=ROUND
    collect.DISCOVER=collect.DISCOVER.replace('tabulated experimental','tabulated or explicitly numerically stated prose experimental').replace('eligible tabulated rows','eligible tabulated or explicitly numerically reported prose values')+' Source paper may include models; only actual measured experimental numbers are eligible. A labelled current in A or microA may be normalized only if the exact exposed geometric area of that same test is explicitly reported; document its factor, not an assumed 1 cm2.'
    with cf.ThreadPoolExecutor(max_workers=3) as pool:papers=list(pool.map(collect.retrieve,SPECS))
    for doi in LEGACY:
        path=GOUT/'papers'/f'{key(doi)}.json'
        if not path.exists():continue
        paper=json.loads(path.read_text(encoding='utf-8'))
        title=paper.get('title','')
        if not title or str(title)=='nan':
            status,raw=request('https://api.crossref.org/works/'+quote(doi,safe=''))
            if status==200:title=json.loads(raw)['message']['title'][0]
            else:title=next((b['text'][:220] for b in paper['blocks'] if len(b['text'])>20),'Primary steel paper '+doi)
        paper.update(doi=doi,title=title,access=[dict(provider='Previously retrieved primary fulltext',http_status=200)])
        save_json(ROUND/'sources'/path.name,paper);papers.append(paper)
    for tag,doi,title in DIRECT:
        path=ROUND/f'{tag}_source.json'
        if not path.exists():continue
        src=json.loads(path.read_text(encoding='utf-8'));paper=dict(doi=doi,title=title,blocks=src['blocks'],source_paths=[src['path']],access=[dict(provider='Public primary PDF',url=src['url'],http_status=200)])
        # Read the DOI from the manuscript rather than trusting a guessed identifier.
        if tag=='co2':
            text=' '.join(b['text'] for b in paper['blocks'][:45])
            found=re.search(r'10\.1016/j\.corsci\.2019\.\d+\.\d+',text)
            if found:paper['doi']=found.group(0)
            else:
                status,raw=request('https://api.crossref.org/works?query.title='+quote(title)+'&rows=1')
                if status==200:
                    hit=json.loads(raw)['message']['items'][0]
                    if 'tempering heat treatment' in hit['title'][0].lower():paper['doi']=hit['DOI']
                assert paper['doi']!='10.1016/j.corsci.2019.03.009','DOI requires source verification'
        save_json(ROUND/'sources'/f'{key(paper["doi"])}.json',paper);papers.append(paper)
    unique={p['doi']:p for p in papers};papers=list(unique.values())
    current=set(pd.read_csv(ROOT/'data/al_heat_expanded_round3_20261023/al_labeled_heat_treatment_expanded.csv').source_paper_id)
    papers=[p for p in papers if p['doi'] not in current]
    save_json(ROUND/'screened_sources.json',[{k:v for k,v in p.items() if k!='blocks'} for p in papers])
    with cf.ThreadPoolExecutor(max_workers=3) as pool:parts=list(pool.map(lambda p:collect.one(p,e),papers))
    rows=[r for part in parts for r in part]
    pd.DataFrame(rows).to_csv(OUT/'round4_candidates.csv',index=False,encoding='utf-8-sig')
    print('Discovered eligible candidate rows:',len(rows),flush=True)
    jobs=[]
    for paper in papers:
        rr=[r for r in rows if r['source_paper_id']==paper['doi']]
        target=OUT/'extractions'/f'{key(paper["doi"])}.json'
        if not rr:
            if not target.exists():
                discovery=ROUND/'target_discovery'/target.name
                notes=json.loads(discovery.read_text(encoding='utf-8')).get('notes','') if discovery.exists() else 'No primary text.'
                save_json(target,dict(doi=paper['doi'],title=paper['title'],records=[],exclusion_note=notes))
            continue
        if target.exists() and json.loads(target.read_text(encoding='utf-8')).get('records'):continue
        jobs+=extract_batches(paper,rows,e)
    def one(job):
        paper,start,inp=job;cache=ROUND/'extraction_chunks'/f'{key(paper["doi"])}_{start}.json'
        if cache.exists():result=json.loads(cache.read_text(encoding='utf-8'))
        else:
            instructions=INSTRUCTIONS+' Explicit sample-linked numerical reports in prose are valid; do not digitize figures. Exact known current and exposed area can establish a density only with explicit documented normalization. Do not infer a missing final-stage hold from an earlier stage; an earlier reported pair may be retained only with its correct stage name and unknown later stage clearly recorded.'
            result=api_json(e,e['OPENAI_MODEL'],instructions,inp,SCHEMA,'round4_steel_heat_attributes',max_tokens=14000);save_json(cache,result)
        print(json.dumps(dict(doi=paper['doi'],batch=start,records=len(result.get('records',[])),error=result.get('error'))),flush=True)
        return paper,result
    grouped={}
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        for paper,result in pool.map(one,jobs):grouped.setdefault(paper['doi'],[]).append(result)
    for paper in papers:
        if paper['doi'] not in grouped:continue
        records=[];cids={r['record_id'] for r in rows if r['source_paper_id']==paper['doi']}
        for part in grouped[paper['doi']]:
            for r in part.get('records',[]):
                r['candidate_exists']=r['candidate_id'] in cids
                r['target_quote_verified']=bool(norm(r['target_quote']) and any(norm(r['target_quote']) in norm(b['text']) for b in paper['blocks']))
                for a in r['attributes']:a['quote_verified']=bool(norm(a['quote']) and any(norm(a['quote']) in norm(b['text']) for b in paper['blocks']))
                records.append(r)
        save_json(OUT/'extractions'/f'{key(paper["doi"])}.json',dict(doi=paper['doi'],title=paper['title'],records=records,retry_partial_failure=any('error' in p for p in grouped[paper['doi']]),usage_parts=[p.get('usage') for p in grouped[paper['doi']]],exclusion_note='Small-batch primary extraction.'))
        stale=OUT/'reviews'/f'{key(paper["doi"])}.json'
        if stale.exists():stale.unlink()
    print('Round 4 extraction complete.',flush=True)

if __name__=='__main__':main()
