#!/usr/bin/env python3
"""Check source bundle completeness, source-helper parity, and local Markdown links."""
from pathlib import Path
import re,json,sys
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'vibe-coding-usegit','usegit-discover','usegit-find-skills','usegit-find-repos','usegit-evaluate','usegit-run','usegit-adapt','usegit-deploy','usegit-verify'}
def check():
 errors=[];seen=set()
 for p in (ROOT/'skills').glob('*/SKILL.md'):
  text=p.read_text();match=re.match(r'---\n(.*?)\n---\n',text,re.S)
  if not match:errors.append(str(p)+': missing frontmatter');continue
  meta=match.group(1);n=re.search(r'^name: (.+)$',meta,re.M);d=re.search(r'^description: (.+)$',meta,re.M)
  if not n or not d:errors.append(str(p)+': metadata missing');continue
  name=n.group(1).strip('"\'');seen.add(name)
  if name!=p.parent.name:errors.append(str(p)+': name mismatch')
  if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',name):errors.append(str(p)+': invalid name')
  if re.search(r'allowed-tools:|hooks:',meta):errors.append(str(p)+': unexpected permission field')
 if seen!=EXPECTED:errors.append('Expected nine skill names')
 for p in ROOT.rglob('*.md'):
  if any(part.startswith('.') for part in p.relative_to(ROOT).parts):continue
  for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' in target or target.startswith('#'):continue
   target=target.split('#')[0]
   if target and not (p.parent/target).is_file():errors.append(str(p.relative_to(ROOT))+': missing link '+target)
 for skill,name in [('vibe-coding-usegit','usegit.py'),('usegit-find-repos','search_repos.py'),('usegit-evaluate','rank_candidates.py')]:
  a=ROOT/'tools'/name;b=ROOT/'skills'/skill/'scripts'/name
  if not a.is_file() or not b.is_file() or a.read_bytes()!=b.read_bytes():errors.append('Helper missing or stale: '+name)
 for p in ROOT.rglob('*.json'):
  if '.git' not in p.parts:
   try:json.loads(p.read_text())
   except (ValueError,OSError):errors.append('Invalid JSON '+str(p))
 print(json.dumps({'skill_count':len(seen),'errors':errors},ensure_ascii=False,indent=2));return bool(errors)
if __name__=='__main__':sys.exit(check())
