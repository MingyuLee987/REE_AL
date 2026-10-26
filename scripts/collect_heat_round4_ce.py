"""Restore sample assignments from the publisher's rowspan-bearing table."""
import json,re
from html.parser import HTMLParser
import collect_heat_round4_extra as m
from collect_grain_size import request,key,save_json

class TableRows(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.cell=None;self.row=[]
 def handle_starttag(self,tag,attrs):
  if tag=='tr':self.row=[]
  if tag in ('td','th'):self.cell=[dict(attrs),[]]
 def handle_data(self,data):
  if self.cell is not None:self.cell[1].append(data)
 def handle_endtag(self,tag):
  if tag in ('td','th') and self.cell is not None:self.row.append((self.cell[0],' '.join(''.join(self.cell[1]).split())));self.cell=None
  if tag=='tr' and self.row:self.rows.append(self.row)

def main():
 doi='10.1007/s11663-025-03817-z';m.ROUND=m.ROOT/'outputs/heat_expansion_round4_ce_20261023';m.ROUND.mkdir(parents=True,exist_ok=True)
 source=m.ROOT/'outputs/heat_expansion_round4_20261023/sources'/f'{key(doi)}.json';paper=json.loads(source.read_text(encoding='utf-8'))
 url='https://link.springer.com/article/'+doi+'/tables/4';status,raw=request(url,timeout=45);assert status==200
 path=m.ROUND/'table4.html';path.write_bytes(raw);match=re.search(r'<table[\s\S]*?</table>',raw.decode());assert match
 parser=TableRows();parser.feed(match.group(0));expanded=[];spans={}
 for row in parser.rows:
  vals={};col=0;newspans={}
  for attrs,txt in row:
   while col in spans:vals[col]=spans[col][0];col+=1
   vals[col]=txt
   if int(attrs.get('rowspan','1'))>1:newspans[col]=(txt,int(attrs['rowspan'])-1)
   col+=int(attrs.get('colspan','1'))
  for c,(txt,left) in spans.items():
   vals[c]=txt
   if left>1:newspans[c]=(txt,left-1)
  spans=newspans;expanded.append(' | '.join(vals[c] for c in sorted(vals)))
 text='Table IV. Publisher table with HTML rowspan values mechanically carried into their covered rows. Source: '+url+'\n'+'\n'.join(expanded)
 paper['blocks'].append(dict(location='publisher_table_IV_rowspan_expanded',section='Table IV',text=text,source_path=str(path),source_url=url))
 save_json(m.ROUND/'sources'/f'{key(doi)}.json',paper)
 m.CANDIDATE_FILE='round4_ce_candidates.csv';m.SPECS=[(doi,paper['title'],None,None,None)];m.DIRECT=[];m.ADDITIONAL=[]
 # Replace the incomplete extraction for this paper; old candidates are retained in the audit file only.
 for folder in ['extractions','reviews']:
  p=m.OUT/folder/f'{key(doi)}.json'
  if p.exists():save_json(m.ROUND/f'previous_{folder}.json',json.loads(p.read_text(encoding='utf-8')));p.unlink()
 m.main()
if __name__=='__main__':main()
