#!/usr/bin/env python3
"""Portable native PDF/PNG export with an isolated LibreOffice profile."""
from pathlib import Path
import os,shutil,subprocess,tempfile,json,hashlib
import fitz
ROOT=Path(__file__).resolve().parents[1]
exe=os.environ.get('SOFFICE') or shutil.which('soffice')
if not exe:raise SystemExit('Install LibreOffice or set SOFFICE to its executable.')
records=[]
for role in ['manuscript','supplement','supplement_methods','supplement_validation','project_brief']:
 docx=ROOT/'native'/f'{role}.docx';out=ROOT/'native'/f'render_{role}_reproduced';out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='document_export_') as temporary:
  profile=Path(temporary)/'profile';home=Path(temporary)/'home';home.mkdir();profile.mkdir()
  env=os.environ.copy();env['FONTCONFIG_FILE']=str(ROOT/'assets/fonts/fontconfig.conf');env.update(HOME=str(home),XDG_CONFIG_HOME=str(home/'config'),XDG_CACHE_HOME=str(home/'cache'))
  cmd=[exe,'-env:UserInstallation='+profile.as_uri(),'--headless','--norestore','--convert-to','pdf','--outdir',str(out),str(docx)]
  p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',env=env);assert p.returncode==0,p.stderr
 pdf=out/(docx.stem+'.pdf');assert pdf.exists();d=fitz.open(pdf)
 for i,page in enumerate(d):
  target=out/f'page-{i+1}.png';data=page.get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False).tobytes('png');tmp=target.with_suffix('.tmp');tmp.write_bytes(data);tmp.replace(target)
 records.append({'role':role,'command':cmd,'exit_code':p.returncode,'stdout':p.stdout,'pages':len(d),'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()})
print(json.dumps(records,indent=2))
