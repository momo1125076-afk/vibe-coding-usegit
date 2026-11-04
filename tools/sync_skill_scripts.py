#!/usr/bin/env python3
"""Copy reviewed canonical helpers into standalone skill bundles."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
MAPPING={'vibe-coding-usegit':['usegit.py'],'usegit-find-repos':['search_repos.py'],'usegit-evaluate':['rank_candidates.py']}
def main():
 for skill,files in MAPPING.items():
  dest=ROOT/'skills'/skill/'scripts';dest.mkdir(parents=True,exist_ok=True)
  for name in files:
   source=ROOT/'tools'/name
   if not source.is_file():raise SystemExit('Missing canonical helper: '+name)
   shutil.copy2(source,dest/name)
 print('Synchronized 3 standalone helpers.')
if __name__=='__main__':main()
