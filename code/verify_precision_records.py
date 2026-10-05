from pathlib import Path
import json,csv,base64,struct,hashlib
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
reports=[];fields_total=0;rows_total=0
for p in sorted((ROOT/'inputs/accepted_counts').glob('B*.json')):
 s=json.loads(p.read_text(encoding='utf-8'));a=base64.b64decode(s['base64']);assert sha(a)==s['raw_sha256'];assert len(a)==s['raw_bytes']==9999*7*2
 counts=list(struct.iter_unpack('<7H',a));f=ROOT/'results/precision'/(s['file_id']+'.csv');raw=f.read_bytes();rows=list(csv.DictReader(raw.decode().splitlines()));assert len(rows)==9999
 errors=0
 for i,(old,row) in enumerate(zip(counts,rows),1):
  assert int(row['rep'])==i and int(row['N'])==s['N'] and int(row['fixed_T'])==s['fixed_T']
  for k,v in zip(s['count_fields'],old):
   expected=None if v==65535 else v;actual=None if row[k]=='' else int(row[k]);assert actual==expected,(s['file_id'],i,k);fields_total+=1
 csv_exact=sha(raw)==s['csv_sha256'];assert csv_exact,('CSV byte identity',s['file_id'],sha(raw),s['csv_sha256'])
 rows_total+=len(rows);reports.append({'configuration':s['file_id'],'rows':len(rows),'integer_fields':len(rows)*7,'mismatches':0,'csv_bytes':len(raw),'csv_sha256':sha(raw),'original_csv_sha256':s['csv_sha256'],'csv_byte_identity':csv_exact})
assert rows_total==59994 and fields_total==419958
out={'status':'PASS','actual_rows':rows_total,'actual_integer_fields':fields_total,'mismatches':0,'all_six_CSV_byte_SHA_identical':True,'groups':reports,'script_sha256':sha(Path(__file__).read_bytes())}
f=ROOT/'review/precision_full_actual_comparison.json';f.parent.mkdir(exist_ok=True);f.write_text(json.dumps(out,indent=2)+'\n', encoding='utf-8');print(json.dumps(out))
