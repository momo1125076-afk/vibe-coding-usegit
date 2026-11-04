#!/usr/bin/env python3
"""Thirty file-installation/Python smoke checks, NOT host runtime certification."""
import argparse,json,subprocess,sys,tempfile,zipfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
HOSTS={'codex':'.agents/skills','claude-code':'.claude/skills','deepseek-harness':'.dsh/skills','openclaw':'skills','workbuddy':'dist/workbuddy'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',default='evidence/distribution-smoke.json');a=p.parse_args();records=[]
 with tempfile.TemporaryDirectory(prefix='usegit-smoke-') as tmp:
  base=Path(tmp)
  def run(host,case,command):
   r=subprocess.run(command,capture_output=True,text=True,timeout=30)
   records.append(dict(host=host,case=case,command=command,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
   if r.returncode:raise RuntimeError(f'{host}/{case}: {r.returncode}')
  for host,sub in HOSTS.items():
   project=base/host;cmd=[sys.executable,str(ROOT/'tools/install_skills.py'),'--host',host,'--project',str(project),'--source',str(ROOT/'skills'),'--apply']
   if host=='workbuddy':cmd+=['--version','0.2.0','--author','UseGit test fixture (not a release attribution)']
   run(host,'install',cmd)
   skill=project/sub/'vibe-coding-usegit'
   if host=='workbuddy':
    target=base/'workbuddy-extracted'
    with zipfile.ZipFile(str(skill)+'.zip') as z:
     for n in z.namelist():
      if Path(n).is_absolute() or '..' in Path(n).parts:raise RuntimeError('Unsafe generated ZIP')
     z.extractall(target)
    skill=target/'vibe-coding-usegit'
   cli=skill/'scripts/usegit.py';customer=base/(host+'-customer')
   for case,args in [('help',['--help']),('init',['init','--project',str(customer),'--name','预约','--idea','场地预约','--platform','wechat-miniprogram','--mode','plan']),('doctor',['doctor']),('status',['status','--project',str(customer)]),('template',['template','discover','--project',str(customer),'--out','.usegit/artifacts/discover.json'])]:run(host,case,[sys.executable,str(cli)]+args)
 report=dict(observed_at=datetime.now(timezone.utc).isoformat(),verification='observed',scope=__doc__,checks=len(records),passed=sum(r['exit_code']==0 for r in records),records=records)
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'checks':len(records),'passed':report['passed'],'report':str(out)}))
if __name__=='__main__':main()
