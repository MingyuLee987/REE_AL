"""Further ordinary-steel experimental data, using the existing evidence pipeline."""
import concurrent.futures as cf
import json
import sys
from urllib.parse import quote
import pandas as pd
from collect_grain_size import ROOT,key,env,request,save_json,blocks
import collect_more_heat_papers as collect
import expand_heat_treatment_data as expand

ROUND=ROOT/'outputs/heat_expansion_round3_20261023'
SPECS=[
 ('10.3390/met15030319','Electrochemical and Tribological Behavior of Dual-Phase Steels Obtained from a Commercial-Grade API 5CT Steel','metals',15,319),
 ('10.3390/ma19132728','Effect of Heat Treatments on the Corrosion Resistance of a TRIP Steel and Its Evaluation by Non-Destructive Testing','materials',19,2728),
 ('10.3390/ma16030899','Influence of Cryogenic Treatment on the Corrosion Properties of 42CrMo Low Alloy Steel','materials',16,899),
 ('10.3390/met14030322','Effect of Tempering Time on the Microstructure and Properties of Martensitic Stainless Steel','metals',14,322),
 ('10.3390/met12030425','Effect of Solution Temperature on the Microstructure and Properties of 17-4PH High-Strength Steel Samples Formed by Selective Laser Melting','metals',12,425),
 ('10.3390/ma11122404','Enhancing Corrosion Resistance and Hardness Properties of Carbon Steel through Modification of Microstructure','materials',11,2404),
]

def main():
    sys.stdout.reconfigure(encoding='utf-8');e=env();ROUND.mkdir(parents=True,exist_ok=True)
    collect.ROUND=ROUND
    collect.DISCOVER=collect.DISCOVER.replace('tabulated experimental','tabulated or explicitly numerically stated prose experimental').replace('eligible tabulated rows','eligible tabulated or explicitly numerically reported prose values')+' Directly stated numerical Tafel values in prose are valid, without digitizing graphs. Untreated means no additional treatment but an explicitly stated prior solution anneal may establish a legitimate known thermal pair.'
    with cf.ThreadPoolExecutor(max_workers=3) as pool:papers=list(pool.map(collect.retrieve,SPECS))
    for tag,doi,title in [
        ('jstm','10.57131/jstm.2022.2.4','Influence of Sigma Phase on General Corrosion of Austenitic Stainless Steel'),
        ('amm','10.24425/amm.2026.158827','Corrosion Behavior of Mild Steel in Aqueous Solutions of Ammonium Nitrate')]:
        src=json.loads((ROUND/f'{tag}_source.json').read_text(encoding='utf-8'))
        paper=dict(doi=doi,title=title,blocks=src['blocks'],source_paths=[src['path']],access=[dict(provider='Journal public primary PDF',http_status=200,url=src['url'])])
        save_json(ROUND/'sources'/f'{key(doi)}.json',paper);papers.append(paper)
    for doi,title,provider,url,headers in [
        ('10.1002/srin.202200455','Resistance against Abrasive Wear and Corrosion of Laser Powder Bed Alloyed High Chromium Tool Steels','Wiley TDM','https://api.wiley.com/onlinelibrary/tdm/v1/articles/'+quote('10.1002/srin.202200455',safe=''),{'Wiley-TDM-Client-Token':e['WILEY_TDM_TOKEN']}),
        ('10.1080/23311916.2022.2045675','Comparative evaluation of the oxidation resistance of untreated, annealed and quenched 434 ferritic stainless steels in corrosive electrolytes','Taylor and Francis public PDF','https://www.tandfonline.com/doi/pdf/10.1080/23311916.2022.2045675',{})]:
        path=ROUND/'sources'/f'{key(doi)}.json'
        if path.exists():paper=json.loads(path.read_text(encoding='utf-8'))
        else:
            status,raw=request(url,headers,timeout=70);bb=[];paths=[]
            if status==200 and raw.startswith(b'%PDF'):
                p=ROUND/'fulltext'/f'{key(doi)}.pdf';p.write_bytes(raw);bb=blocks(p);paths=[str(p)]
            paper=dict(doi=doi,title=title,blocks=bb,source_paths=paths,access=[dict(provider=provider,http_status=status)])
            save_json(path,paper)
        print(json.dumps(dict(doi=doi,access=paper['access'],blocks=len(paper['blocks']))),flush=True);papers.append(paper)
    with cf.ThreadPoolExecutor(max_workers=3) as pool:parts=list(pool.map(lambda p:collect.one(p,e),papers))
    rows=[r for rr in parts for r in rr]
    pd.DataFrame(rows).to_csv(expand.OUT/'round3_candidates.csv',index=False,encoding='utf-8-sig')
    save_json(ROUND/'screened_sources.json',[{k:v for k,v in p.items() if k!='blocks'} for p in papers])
    def extract(p):
        rr=[r for r in rows if r['source_paper_id']==p['doi']]
        if not rr:
            target=expand.OUT/'extractions'/f'{key(p["doi"])}.json'
            if not target.exists():
                discovery=ROUND/'target_discovery'/target.name
                notes=json.loads(discovery.read_text(encoding='utf-8')).get('notes','') if discovery.exists() else 'Primary full text unavailable.'
                save_json(target,dict(doi=p['doi'],title=p['title'],records=[],exclusion_note=notes))
            return
        result=expand.extract_one(dict(doi=p['doi'],title=p['title'],candidates=rr,blocks=p['blocks']),e)
        print(json.dumps(dict(doi=p['doi'],records=len(result.get('records',[])),error=result.get('error'))),flush=True)
    with cf.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(extract,papers))
    print('Round 3 extraction complete.',flush=True)

if __name__=='__main__':main()
