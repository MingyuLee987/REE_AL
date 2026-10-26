"""Build a reviewed, additive dataset; never fit or overwrite the production model."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from collect_grain_size import ROOT, OUT, DATA, blocks, key, norm, save_json

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    original_path=ROOT/'data/training.csv'
    original_hash=hashlib.sha256(original_path.read_bytes()).hexdigest()
    training=pd.read_csv(original_path,float_precision='round_trip')
    decisions=json.loads((ROOT/'docs/grain_review_decisions.json').read_text(encoding='utf-8'))
    accepted=[];all_candidates=[]
    for p in (OUT/'llm').glob('*.json'):
        d=json.loads(p.read_text(encoding='utf-8'))
        for r in d['records']:
            r=dict(r);r['candidate_id']=key(json.dumps([r['source_paper_id'],r['sample_label'],r['grain_size_value_reported'],r['lower_reported'],r['upper_reported']],ensure_ascii=False))
            all_candidates.append(r)
            rule=decisions['papers'].get(r['source_paper_id'])
            if not rule or r['sample_label'] not in rule['accepted_samples']:continue
            assert r['quote_verified'] and r['is_current_experiment']
            assert r['unit'] in ('μm','µm','um')
            source_blocks=blocks(Path(r['source_path']))
            assert any(norm(r['evidence_quote']) in b['text'] for b in source_blocks)
            ids=rule.get('record_mapping_override',{}).get(r['sample_label'],r['training_record_ids'])
            assert ids, 'Reviewed mapping required'
            for rid in ids:
                matches=training.loc[training.record_id.eq(rid)]
                assert len(matches)==1 and matches.source_paper_id.iloc[0]==r['source_paper_id']
            r['training_record_ids']=ids
            r['grain_region']=rule['region']
            if r['sample_label'] in rule.get('group_samples',[]):scope='reported_group'
            elif r['grain_size_value_reported'] is None:scope='reported_bound'
            else:scope='reported_individual'
            r['measurement_scope']=scope
            r['reported_uncertainty_um']=rule.get('reported_uncertainty_by_sample',{}).get(r['sample_label'],rule.get('reported_uncertainty_um'))
            r['review_note']=rule['review_note']
            r['review_status']='source_checked'
            r['source_url']='https://doi.org/'+r['source_paper_id']
            r['measurement_id']='grain_'+r['candidate_id']
            accepted.append(r)
    # Explicit numeric figure-label transcription, not pixel-scale estimation.
    figpath=OUT/'fulltext/ma19122685_visual.pdf'
    assert figpath.exists()
    mid={
        'source_paper_id':'10.3390/ma19122685','sample_label':'0.03LaCe',
        'grain_size_value_reported':1.28,'lower_reported':None,'upper_reported':None,'unit':'μm',
        'statistic':'Paper-described average; printed Xc distribution label',
        'grain_definition':'EBSD grain-size distribution; phase and boundary threshold unspecified',
        'measurement_method':'EBSD; directly transcribed printed Figure 2(b3) label',
        'condition':'Same 0.03LaCe material state as existing corrosion record',
        'evidence_quote':'Xc = 1.28 μm','evidence_location':'PDF page 6, Figure 2(b3)',
        'source_path':str(figpath.resolve()),'training_record_ids':['65d1ab55f2759442c5d6'],
        'grain_region':'EBSD_bulk_microstructure','measurement_scope':'reported_individual',
        'reported_uncertainty_um':None,'review_status':'figure_label_visually_checked',
        'quote_verified':False,'figure_label_visually_verified':True,'is_current_experiment':True,
        'review_note':decisions['papers']['10.3390/ma19122685']['review_note'],
        'source_url':'https://doi.org/10.3390/ma19122685','measurement_id':'grain_ma19122685_fig2b3'
    }
    accepted.append(mid)
    measurements=pd.DataFrame(accepted)
    assert measurements.measurement_id.is_unique
    for col in ['grain_size_value_reported','lower_reported','upper_reported']:
        assert (pd.to_numeric(measurements[col],errors='coerce').dropna()>0).all()
    measurements['training_record_ids']=measurements.training_record_ids.map(json.dumps)
    measurements.to_csv(DATA/'grain_measurements_reviewed.csv',index=False,encoding='utf-8-sig')
    new=training.copy()
    numeric=['grain_size_um','grain_size_group_um','grain_size_lower_bound_um','grain_size_upper_bound_um','grain_size_uncertainty_um']
    for c in numeric:new[c]=np.nan
    metadata=['grain_size_measurement_id','grain_size_definition','grain_size_region','grain_size_method','grain_size_statistic','grain_size_source_url','grain_size_source_location','grain_size_scope','grain_size_review_note','grain_size_bound_operator']
    for c in metadata:new[c]=''
    new['grain_size_review_status']='not_recovered'
    links=[]
    for r in accepted:
        for rid in r['training_record_ids']:
            idx=new.index[new.record_id.eq(rid)][0]
            links.append({'record_id':rid,'measurement_id':r['measurement_id'],'source_paper_id':r['source_paper_id'],'measurement_scope':r['measurement_scope']})
            value=r['grain_size_value_reported'];scope=r['measurement_scope']
            if value is not None:
                target='grain_size_um' if scope=='reported_individual' else 'grain_size_group_um'
                assert pd.isna(new.loc[idx,target])
                new.loc[idx,target]=value
                new.loc[idx,'grain_size_uncertainty_um']=r['reported_uncertainty_um']
            if r['lower_reported'] is not None:new.loc[idx,'grain_size_lower_bound_um']=r['lower_reported']
            if r['upper_reported'] is not None:new.loc[idx,'grain_size_upper_bound_um']=r['upper_reported']
            if scope=='reported_bound':new.loc[idx,'grain_size_bound_operator']='>'
            # Range-only records supplement their group's central descriptor.
            if value is not None or scope=='reported_bound':
                for c,v in {'grain_size_measurement_id':r['measurement_id'],'grain_size_definition':r['grain_definition'],'grain_size_region':r['grain_region'],'grain_size_method':r['measurement_method'],'grain_size_statistic':r['statistic'],'grain_size_source_url':r['source_url'],'grain_size_source_location':r['evidence_location'],'grain_size_scope':scope,'grain_size_review_note':r['review_note'],'grain_size_review_status':r['review_status']}.items():new.loc[idx,c]=v
    pd.DataFrame(links).to_csv(DATA/'grain_record_links.csv',index=False,encoding='utf-8-sig')
    target_path=ROOT/'data/training_with_grain_size.csv'
    new.to_csv(target_path,index=False,encoding='utf-8-sig')
    roundtrip=pd.read_csv(target_path,float_precision='round_trip')
    pd.testing.assert_frame_equal(training,roundtrip[training.columns],check_dtype=False)
    assert len(new)==len(training) and new.record_id.is_unique
    assert new.loc[new.grain_size_scope.isin(['reported_group','reported_bound']),'grain_size_um'].isna().all()
    assert hashlib.sha256(original_path.read_bytes()).hexdigest()==original_hash
    production=json.loads((ROOT/'models/manifest.json').read_text(encoding='utf-8'))
    assert original_hash==production['training_sha256']
    # External candidates are a review queue, not labelled alloy training examples.
    ext=[r for r in all_candidates if r['source_paper_id'] not in set(training.source_paper_id)]
    c=pd.read_csv(ROOT/'data/literature/icorr_candidates.csv')
    screen=pd.read_csv(DATA/'paper_screen.csv')
    queue=[]
    for doi in sorted({r['source_paper_id'] for r in ext}):
        sr=screen[screen.source_paper_id.eq(doi)]
        queue.append({'source_paper_id':doi,'title':sr.title.iloc[0] if len(sr) else '', 'grain_candidates':sum(r['source_paper_id']==doi for r in ext),'icorr_table_candidates':int(c.source_paper_id.eq(doi).sum()),'admission_status':'not_merged_requires_sample_and_target_verification','source_url':'https://doi.org/'+doi})
    pd.DataFrame(queue).to_csv(DATA/'external_paper_queue.csv',index=False,encoding='utf-8-sig')
    summary={
        'date':'2026-10-23','original_rows':len(training),'original_papers':training.source_paper_id.nunique(),
        'screened_sources':len(screen),'training_sources_with_substantial_text':int((screen.in_training & (screen.text_chars>8000)).sum()),
        'publisher_fulltexts_downloaded':sum(bool(r.get('path')) for r in json.loads((OUT/'retrieved.json').read_text(encoding='utf-8'))),
        'llm_extraction_sources':len(list((OUT/'llm').glob('*.json'))),'llm_candidate_measurements':len(all_candidates),
        'reviewed_measurement_records':len(accepted),'reviewed_papers':measurements.source_paper_id.nunique(),
        'rows_with_individual_numeric_grain_size':int(new.grain_size_um.notna().sum()),
        'individual_material_measurements':int(measurements.measurement_scope.eq('reported_individual').sum()),
        'rows_with_group_only_grain_size':int(new.grain_size_group_um.notna().sum()),
        'rows_with_bound_only_grain_size':int(new.grain_size_scope.eq('reported_bound').sum()),
        'external_candidate_measurements':len(ext),'external_candidate_papers':len(queue),
        'original_training_sha256':original_hash,'enriched_sha256':hashlib.sha256(target_path.read_bytes()).hexdigest(),
        'model_changed':False,'validation':'279 original records and all 82 original fields round-trip identically; reviewed evidence and same-paper mapping checked; group/bounds never populate individual grain_size_um',
        'limitations':['No imputation of missing grain size','Not all 43 sources accessible','Definitions/regions differ across papers','Shared grain measurement across exposure rows is not an independent replicate','No grain-size model trained; production SVR ignores added fields']
    }
    save_json(DATA/'summary.json',summary)
    plot(new)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

def plot(d):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    titles={
        '10.3390/met13010066':'Q235: rolled microstructure',
        '10.1002/srin.202400576':'75Cr1: EBSD crystallographic grains',
        '10.3390/ma19122685':'0.4Sb low-alloy steel: EBSD grains',
        '10.1016/j.isci.2025.113319':'Ce-SASS weld: HAZ intercept size',
        '10.1007/s10853-025-11514-0':'La-SASS weld: fusion-zone grains',
    }
    fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    colors=['#176b87','#bc5b22']
    for ax,(doi,title) in zip(axes.flat,titles.items()):
        s=d[d.source_paper_id.eq(doi)&d.grain_size_um.notna()]
        groups=list(s.groupby('exposure_h',dropna=False))
        for j,(exposure,g) in enumerate(groups):
            g=g.sort_values('grain_size_um')
            label=f'{exposure:g} h exposure' if pd.notna(exposure) else 'Exposure not specified'
            ax.plot(g.grain_size_um,g.icorr_A_cm2*1e6,'o-',color=colors[j%2],label=label,lw=1.5)
            for r in g.itertuples():
                name=r.source_sample_id.split('_')[0].replace('UCS-','')
                at_right=r.grain_size_um==g.grain_size_um.max()
                ax.annotate(name,(r.grain_size_um,r.icorr_A_cm2*1e6),xytext=(-4 if at_right else 4,5),ha='right' if at_right else 'left',textcoords='offset points',fontsize=7)
        ax.set(title=title,xlabel='Reported grain size (um)',ylabel='i_corr (uA/cm2; log scale)');ax.set_yscale('log');ax.grid(alpha=.2)
        if len(groups)>1:ax.legend(fontsize=8)
        ax.margins(x=.2,y=.35)
    axes.flat[-1].axis('off')
    measured=d[d.grain_size_um.notna()]
    note=f'{len(measured)} existing corrosion-test rows\n{measured.grain_size_measurement_id.nunique()} individual material measurements\n{measured.source_paper_id.nunique()} source papers\n\nWithin-paper connections only.\nRE content and microstructure co-vary.\nNo causal grain-size effect is inferred.\n\nGroup values and >150 um bound excluded.\nBefore/after rows share the starting\ngrain descriptor.'
    axes.flat[-1].text(0,.95,note,va='top',fontsize=11,linespacing=1.6)
    fig.suptitle('Source-checked grain size versus existing corrosion current density',fontsize=15)
    fig.savefig(DATA/'grain_size_icorr_by_paper.png',dpi=180)
    plt.close(fig)

if __name__=='__main__':main()
