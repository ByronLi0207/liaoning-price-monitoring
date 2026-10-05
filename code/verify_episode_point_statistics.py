"""Reproduce B0 quotation-episode counts directly from the unchanged county CSV."""
from pathlib import Path
from decimal import Decimal
import csv,math,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
ids=['210111000000','210124000000','210283000000','210423000000','210882000000','210922000000','211121000000','211322000000','211381000000','211081000000','211224000000','211282000000']
# Cohort order is sourced from the frozen scientific implementation, rather than name matching.
import re
core=(ROOT/'code/reference_core.js').read_text(encoding='utf-8')
ids=json.loads(re.search(r'const MAIN12=(\[[^;]+\])',core).group(1))
raw=(ROOT/'inputs/normalized_prices.csv').read_bytes();assert hashlib.sha256(raw).hexdigest()=='f5536401160dc415b33ee7934081484a208aaefc1fa7fd7c6eff6a8b822a906b'
rows=list(csv.DictReader(raw.decode('utf-8-sig').splitlines()));dates=sorted({r['date'] for r in rows});lookup={(r['date'],r['region_id'],r['product_id']):r for r in rows}
episodes=[]
for region in ids:
 vals=[]
 for date in dates:
  c=lookup[(date,region,'maize_purchase_mixed')];u=lookup[(date,region,'urea_domestic')]
  good=bool(c['value']) and bool(u['value']) and Decimal(c['value'])>0 and Decimal(u['value'])>0 and c['source_id']==u['source_id']
  vals.append(None if not good else {'date':date,'c':Decimal(c['value']),'u':Decimal(u['value']),'source':c['source_id'],'x':math.log(float(c['value']))-math.log(float(u['value']))})
 b=sum(v['x'] for v in vals[:108])/108;run=[]
 def close():
  if run:
   mu=sum(a['c']!=z['c'] for a,z in zip(run,run[1:]));uu=sum(a['u']!=z['u'] for a,z in zip(run,run[1:]));any_u=sum(a['c']!=z['c'] or a['u']!=z['u'] for a,z in zip(run,run[1:]))
   episodes.append({'region_id':region,'start':run[0]['date'],'end':run[-1]['date'],'observations':len(run),'internal_edges':len(run)-1,'maize_updates':mu,'urea_updates':uu,'any_updates':any_u})
 for t,v in enumerate(vals[108:],108):
  if v is None or not v['x']-b < -1e-12:
   close();run=[];continue
  if run and v['source']!=run[-1]['source']:
   close();run=[]
  run.append(v)
 close()
summary=[]
for label,remove in [('all12',set()),('without_J',{'211322000000'}),('without_J_Q',{'211322000000','210423000000'})]:
 e=[x for x in episodes if x['region_id'] not in remove];ge3=[x for x in e if x['observations']>=3]
 summary.append({'cohort':label,'episodes':len(e),'ge2':sum(x['observations']>=2 for x in e),'ge3':len(ge3),'zero_ge2':sum(x['observations']>=2 and x['any_updates']==0 for x in e),'zero_ge3':sum(x['any_updates']==0 for x in ge3),'internal_edges':sum(x['internal_edges'] for x in e),'any_updates':sum(x['any_updates'] for x in e)})
assert [(r['episodes'],r['ge2'],r['ge3'],r['zero_ge3'],r['internal_edges'],r['any_updates']) for r in summary]==[(74,55,45,4,540,204),(71,52,42,4,362,187),(66,47,37,3,300,179)],summary
out={'status':'PASS','summary':summary,'episodes':episodes};dest=ROOT/'review/episode_point_reproduction.json';dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(out,indent=2)+'\n', encoding='utf-8');print(json.dumps({'status':'PASS','summary':summary}))
