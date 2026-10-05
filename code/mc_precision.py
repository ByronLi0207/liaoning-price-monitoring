from pathlib import Path
import json,math,re,base64,struct,hashlib
from scipy.stats import beta
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'
def inert(p):return json.loads(re.search(r'<script\b[^>]*type=[\"\']application/json[\"\'][^>]*>([\s\S]*?)</script>',p.read_text(encoding='utf-8')).group(1))
def uncertainty(k,n):
 if not n:return {'raw_probability':None,'MCSE':None,'binomial_95':None}
 p=k/n
 if k==0:ci=[0,1-0.05**(1/n)];kind='one-sided 95% exact upper bound'
 elif k==n:ci=[0.05**(1/n),1];kind='one-sided 95% exact lower bound'
 else:ci=[float(beta.ppf(.025,k,n-k+1)),float(beta.ppf(.975,k+1,n-k))];kind='two-sided 95% Clopper-Pearson'
 return {'raw_probability':p,'MCSE':math.sqrt(n*p*(1-p))/(n+1) if 0<k<n else None,'binomial_95':ci,'binomial_definition':kind,'resolution':1/(n+1)}
summary=json.loads((OUT/'precision/precision_summary.json').read_text(encoding='utf-8'))
for s in summary:
 s['tail_uncertainty']=uncertainty(s['fixed_tail_count'],s['fixed_valid'])
 s['positive_uncertainty']=uncertainty(s['positive_count'],s['paired_valid'])
 s['positive_uncertainty']['MCSE']=math.sqrt(s['positive_fraction']*(1-s['positive_fraction'])/s['paired_valid']) if 0<s['positive_count']<s['paired_valid'] else None
 s['positive_uncertainty']['resolution']=1/s['paired_valid'] if s['paired_valid'] else None
(OUT/'precision/precision_summary_with_MC_error.json').write_text(json.dumps(summary,indent=2)+'\n', encoding='utf-8')
core=ROOT/'inputs/reference_experiments'
original=inert(core/'figure_export/inputs/T1_summary.html')['summary']
t4=inert(core/'figure_export/inputs/T4b_complete_sets_summary.html')['summary']
rows=[]
for b in ['B0','B1','B2','B3','B4']:
 packets=[]
 for p in sorted((core/'T1_records').glob(f'T1_{b}_L6_rep*.html')):
  x=inert(p);packets.append(x)
 packets.sort(key=lambda x:x['metadata']['rep_start']);decoded=[]
 for x in packets:
  a=base64.b64decode(x['counts_u16_le_base64']);nums=struct.unpack('<'+'H'*(len(a)//2),a)
  decoded.extend([nums[i:i+21] for i in range(0,len(nums),21)])
 t=inert(core/f'T4b_records/T4b_{b}_rep1_1999.html');a=base64.b64decode(t['counts_u16_le_base64']);nums=struct.unpack('<'+'H'*(len(a)//2),a);tdecoded=[nums[i:i+21] for i in range(0,len(nums),21)]
 for label,name,c,sr in [('Full12','all12',0,None),('U10','without_Jianping_Qingyuan10',2,None),('S6','complete_set_3',2,tdecoded)]:
  s=dict(next(x for x in (t4 if label=='S6' else original) if x['benchmark']==b and x['L']==6 and x.get('set_id',x.get('cohort'))==name))
  z=[r[c*7:c*7+7] for r in (sr or decoded)]
  K=sum(r[5]>=s['observed_low_count'] for r in z if r[5]!=65535);valid=sum(r[5]!=65535 for r in z);pos=sum(r[1]>r[2] for r in z if r[0]>0 and r[2]!=65535);zero=sum(r[1]==r[2] for r in z if r[0]>0 and r[2]!=65535)
  s.update(label=label,fixed_tail_count=K,fixed_valid=valid,fixed_p=(K+1)/(valid+1),positive_count=pos,zero_count=zero,negative_count=1999-pos-zero,tail_uncertainty=uncertainty(K,valid),positive_uncertainty=uncertainty(pos,1999),primary_draws=1999)
  s['positive_uncertainty']['MCSE']=math.sqrt((pos/1999)*(1-pos/1999)/1999) if 0<pos<1999 else None
  s['positive_uncertainty']['resolution']=1/1999
  if abs(s['fixed_p']-s['fixed_reference_p'])>1e-15:raise AssertionError('primary p')
  rows.append(s)
(OUT/'primary_15_L6.json').write_text(json.dumps(rows,indent=2)+'\n', encoding='utf-8')
print(json.dumps({'status':'PASS','precision':summary,'primary_rows':len(rows)}))
