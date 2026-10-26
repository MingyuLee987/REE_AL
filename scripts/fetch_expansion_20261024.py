"""Retrieve primary fulltexts without exposing publisher credentials."""
import sys,json,concurrent.futures as cf
from urllib.parse import quote
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from collect_grain_size import ROOT,key,env,request,blocks,save_json
import collect_more_heat_papers as c
OUT=ROOT/'outputs/expansion_20261024';OUT.mkdir(parents=True,exist_ok=True)
c.ROUND=OUT
SPECS=[
 ('10.3390/met15030232','Influence of Selective Laser Melting Process and Heat Treatment Parameters on the Corrosion Resistance of 17-4 Precipitation Hardening Stainless Steel','metals',15,232),
 ('10.3390/met15020137','Characterization of Microstructure and Localized Corrosion Resistance of Heat-Treated 17-4 PH Stainless Steel Fabricated by Material Extrusion','metals',15,137),
 ('10.3390/met12081386','Effect of Microstructure on Electrochemical Properties of the EN S275 Mild Steel under Chlorine-Rich and Chlorine-Free Media at Different pHs','metals',12,1386),
 ('10.3390/met15080880','Electrochemical Behavior of Thermomechanically Processed UNS S41003 Steel in Acidic Chloride Media','metals',15,880),
 ('10.3390/met16050464','Effect of H1150M Heat Treatment on Functional Properties of 15-5 PH Stainless Steel Produced by Additive Manufacturing','metals',16,464),
 ('10.3390/ma15010024','Effect of Annealing on Microstructure and Corrosion Behavior of Interstitial Free Steel','materials',15,24),
 ('10.3390/ma15051746','Long-Term Corrosion Behavior of Strong and Ductile High Mn-Low Cr Steel in Acidic Aqueous Environments','materials',15,1746),
 ('10.3390/ma18112443','Effect of the Rare Earth Element Cerium on the Corrosion Resistance of Steel for an Offshore Platform in a Simulated Marine Atmospheric Environment','materials',18,2443),
 ('10.3390/ma16020876','Local Corrosion Behaviors in the Coarse-Grained Heat-Affected Zone in a Newly Developed Zr–Ti–Al–RE Deoxidized High-Strength Low-Alloy Steel','materials',16,876),
 ('10.3390/ma14010123','Effect of Different Austempering Heat Treatments on Corrosion Properties of High Silicon Steel','materials',14,123),
]
def other(doi,title):
 path=OUT/'sources'/f'{key(doi)}.json'
 if path.exists():return json.loads(path.read_text(encoding='utf-8'))
 e=env();bb=[];paths=[];access=[]
 if doi.startswith('10.1002/'):
  url='https://api.wiley.com/onlinelibrary/tdm/v1/articles/'+quote(doi,safe='');heads={'Wiley-TDM-Client-Token':e.get('WILEY_TDM_TOKEN','')}
 else:
  url='https://api.elsevier.com/content/article/doi/'+doi+'?view=FULL';heads={'X-ELS-APIKey':e.get('ELSEVIER_API_KEY',''),'Accept':'application/xml'}
 status,raw=request(url,heads,timeout=55);access.append(dict(provider='publisher API',status=status,bytes=len(raw)))
 if status==200:
  suf='.pdf' if raw.startswith(b'%PDF') else '.xml';p=OUT/'fulltext'/f'{key(doi)}{suf}';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);bb=blocks(p);paths=[str(p)]
 result=dict(doi=doi,title=title,blocks=bb,source_paths=paths,access=access);save_json(path,result);print(doi,len(bb),access,flush=True);return result
if __name__=='__main__':
 with cf.ThreadPoolExecutor(max_workers=4) as pool:papers=list(pool.map(c.retrieve,SPECS))
 with cf.ThreadPoolExecutor(max_workers=2) as pool:papers+=list(pool.map(lambda a:other(*a),[
 ('10.1002/adem.202402545','Exploring the Effect of Lanthanum on Corrosion Resistance of Stainless Steel in Seawater'),
 ('10.1016/j.jmrt.2023.12.189','Corrosion mechanism and microstructure evolution of yttrium-doped marine steel'),
 ('10.1016/j.jmrt.2025.01.207','Rare earth corrosion steel candidate'),
 ]))
 save_json(OUT/'inventory.json',[{k:v for k,v in p.items() if k!='blocks'} for p in papers])
