"""Explicit prose-reported values are measurements, not figure digitization."""
import json
import sys
import pandas as pd
from collect_grain_size import key,env,save_json
import collect_more_heat_papers as collect
from expand_heat_treatment_data import OUT,extract_one

def main():
    sys.stdout.reconfigure(encoding='utf-8');doi='10.3390/met15090935';e=env()
    p=collect.ROUND/'sources'/f'{key(doi)}.json';paper=json.loads(p.read_text(encoding='utf-8'))
    cache=collect.ROUND/'target_discovery'/p.name
    if cache.exists() and not json.loads(cache.read_text(encoding='utf-8')).get('targets'):
        save_json(collect.ROUND/'table_only_discovery'/p.name,json.loads(cache.read_text(encoding='utf-8')));cache.unlink()
    collect.DISCOVER=collect.DISCOVER.replace('tabulated experimental','tabulated or explicitly numerically stated prose experimental').replace('eligible tabulated rows','eligible tabulated or explicitly numerically stated prose values')+' Explicit text provides Q, YQ, QT, YQT icorr values in page10_block5. These reported scalar values are allowed; do not digitize the plotted curves. A text location may be used instead of a table location.'
    rows=collect.one(paper,e)
    prior=pd.read_csv(OUT/'round2_candidates.csv',float_precision='round_trip')
    pd.concat([prior,pd.DataFrame(rows)],ignore_index=True).drop_duplicates('record_id').to_csv(OUT/'round2_candidates.csv',index=False,encoding='utf-8-sig')
    if rows:
        r=extract_one(dict(doi=doi,title=paper['title'],candidates=rows,blocks=paper['blocks']),e)
        print(json.dumps(dict(doi=doi,records=len(r.get('records',[])),error=r.get('error'))),flush=True)

if __name__=='__main__':main()
