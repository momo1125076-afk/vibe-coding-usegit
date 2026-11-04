#!/usr/bin/env python3
"""Replay sanitized plan records in a fresh temporary project; no network."""
import json,subprocess,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 with tempfile.TemporaryDirectory(prefix='usegit-replay-') as tmp:
  root=Path(tmp);cli=ROOT/'tools/usegit.py';records=[]
  def run(*args):
   r=subprocess.run([sys.executable,str(cli),*args,'--project',tmp],text=True,capture_output=True,timeout=20)
   if r.returncode:raise RuntimeError(r.stdout+r.stderr)
   records.append({'arguments':list(args),'exit_code':r.returncode});return json.loads(r.stdout)
  run('init','--mode','plan');shutil.copytree(ROOT/'examples/miniprogram-plan/artifacts',root/'.usegit/artifacts',dirs_exist_ok=True)
  for stage in ['discover','find-skills','find-repos','evaluate']:run('record',stage,'--artifact','.usegit/artifacts/'+stage+'.json')
  status=run('status');run('audit')
  assert status['stages']['discover']=='complete' and status['stages']['find-skills']=='complete'
  assert status['stages']['find-repos']=='blocked' and status['stages']['evaluate']=='blocked' and not status['complete_for_mode']
  print(json.dumps({'scope':'Replay of recorded planning artifacts, not live search or product verification','records':records,'final_status':status},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
