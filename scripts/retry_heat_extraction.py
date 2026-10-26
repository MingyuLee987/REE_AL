"""Retry transient/oversized extraction failures in smaller candidate batches."""
import concurrent.futures as cf
import json
import sys
from expand_heat_treatment_data import OUT,SCHEMA,INSTRUCTIONS,api_json
from collect_grain_size import env,norm,save_json

def main():
    sys.stdout.reconfigure(encoding='utf-8');e=env()
    failed=[]
    for f in (OUT/'extractions').glob('*.json'):
        d=json.loads(f.read_text(encoding='utf-8'))
        if 'error' in d:failed.append((f,d))
    jobs=[]
    for f,d in failed:
        inp=json.loads((OUT/'inputs'/f.name).read_text(encoding='utf-8'))
        for start in range(0,len(inp['candidates']),4):
            jobs.append((f,d,start,{**inp,'candidates':inp['candidates'][start:start+4]}))
    def one(job):
        f,d,start,inp=job;cache=OUT/'retry_chunks'/f'{f.stem}_{start}.json'
        if cache.exists():r=json.loads(cache.read_text(encoding='utf-8'))
        else:
            r=api_json(e,e['OPENAI_MODEL'],INSTRUCTIONS,inp,SCHEMA,'heat_corrosion_extraction_retry',max_tokens=18000);save_json(cache,r)
        print(json.dumps(dict(doi=d['doi'],batch=start,records=len(r.get('records',[])),error=r.get('error'))),flush=True)
        return f,r
    results={}
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        for f,r in pool.map(one,jobs):results.setdefault(f,[]).append(r)
    for f,parts in results.items():
        old=json.loads(f.read_text(encoding='utf-8'));inp=json.loads((OUT/'inputs'/f.name).read_text(encoding='utf-8'));cids={x['record_id'] for x in inp['candidates']}
        records=[]
        for part in parts:
            for r in part.get('records',[]):
                r['candidate_exists']=r['candidate_id'] in cids
                r['target_quote_verified']=bool(norm(r['target_quote']) and any(norm(r['target_quote']) in norm(b['text']) for b in inp['source_blocks']))
                for a in r['attributes']:a['quote_verified']=bool(norm(a['quote']) and any(norm(a['quote']) in norm(b['text']) for b in inp['source_blocks']))
                records.append(r)
        save_json(OUT/'failed_attempts'/f.name,old)
        save_json(f,dict(doi=old['doi'],title=old['title'],records=records,retry_partial_failure=any('error' in p for p in parts),model=e['OPENAI_MODEL'],usage_parts=[p.get('usage') for p in parts],exclusion_note='Retried source candidates in groups of four.'))
        review=OUT/'reviews'/f.name
        if review.exists():review.unlink()

if __name__=='__main__':main()
