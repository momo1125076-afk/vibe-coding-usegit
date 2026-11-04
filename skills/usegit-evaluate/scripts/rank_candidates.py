#!/usr/bin/env python3
"""Offline evidence-aware comparison. References are validated, not verified."""
import argparse, json, math, os, tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, parse_qsl
from datetime import datetime, timezone
WEIGHTS = dict(fit=30, runnability=20, adaptability=15, maintenance=15, license=10, deployment_cost=10)

def read_json(path):
    with Path(path).open('rb') as handle: raw=handle.read(8*1024*1024+1)
    if len(raw)>8*1024*1024: raise ValueError('input exceeds 8 MiB')
    return json.loads(raw)

def atomic_json(path,data):
    if path=='-': print(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)); return
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=p.parent,prefix='.'+p.name)
    try:
        with os.fdopen(fd,'w') as f: json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def references(value):
    if not isinstance(value,list) or len(value)>30: raise ValueError('invalid evidence references')
    for ref in value:
        if not isinstance(ref,str) or not ref.strip() or '\\' in ref: raise ValueError('invalid reference')
        u=urlsplit(ref)
        if u.scheme:
            if u.scheme not in ('http','https') or not u.hostname or u.username or u.password: raise ValueError('unsafe evidence URL')
            if any(k.lower() == 'auth' or any(w in k.lower() for w in ('token','secret','password','credential','signature','api_key','apikey','authorization','access_key')) for k,v in parse_qsl(u.query)): raise ValueError('credential query rejected')
        elif u.netloc or ref.startswith('/') or '..' in PurePosixPath(u.path).parts or ':' in u.path: raise ValueError('unsafe evidence path')
    return value

def compare(source,assessment):
    if not isinstance(source,(dict,list)): raise ValueError('candidate input must be an object or array')
    candidates=source if isinstance(source,list) else source.get('candidates')
    if not isinstance(candidates,list) or len(candidates)>2000: raise ValueError('invalid candidate list')
    ids=set()
    for c in candidates:
        if not isinstance(c,dict) or not isinstance(c.get('id'),str) or not c['id'].strip() or c['id'].lower() in ids: raise ValueError('invalid or duplicate candidate ID')
        ids.add(c['id'].lower());s=c.get('stars')
        if s is not None and (type(s) is not int or s<0): raise ValueError('invalid stars')
    if not isinstance(assessment,dict): raise ValueError('assessment must be object')
    hard=assessment.get('hard_requirements',[])
    if not isinstance(hard,list) or any(not isinstance(x,str) or not x for x in hard): raise ValueError('invalid hard requirements')
    hard=list(dict.fromkeys(['license-fit','platform-fit']+hard))
    rows=assessment.get('assessments',[])
    if not isinstance(rows,list): raise ValueError('assessments must be array')
    amap={}
    for a in rows:
        if not isinstance(a,dict): raise ValueError('invalid assessment')
        key=a.get('candidate_id')
        if not isinstance(key,str) or key.lower() not in ids or key.lower() in amap: raise ValueError('unknown or duplicate assessment')
        amap[key.lower()]=a
    result={k:[] for k in ('ranked','needs_review','excluded')}
    for c in candidates:
        a=amap.get(c['id'].lower(),{});hc=a.get('hard_checks',{});sc=a.get('scores',{})
        if not isinstance(hc,dict) or set(hc)-set(hard): raise ValueError('unknown hard check')
        if not isinstance(sc,dict) or set(sc)-set(WEIGHTS): raise ValueError('unknown score dimension')
        checks={};scores={};total=0.;coverage=0;failed=[];unresolved=[];missing=[]
        for key in hard:
            x=hc.get(key,{});
            if not isinstance(x,dict): raise ValueError('invalid hard check')
            status=x.get('status','unknown');ev=references(x.get('evidence',[]))
            if status not in ('pass','fail','unknown'): raise ValueError('invalid hard status')
            if not ev: status='unknown'
            checks[key]=dict(status=status,evidence=ev,note=x.get('note',''))
            if status=='fail':failed.append(key)
            if status=='unknown':unresolved.append(key)
        for key,weight in WEIGHTS.items():
            x=sc.get(key,{})
            if not isinstance(x,dict): raise ValueError('invalid score')
            score=x.get('score');ev=references(x.get('evidence',[]))
            if score is not None and (type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=5): raise ValueError('score must be finite 0..5')
            if not ev:score=None
            if score is None:missing.append(key)
            else:total+=score/5*weight;coverage+=weight
            scores[key]=dict(score=score,evidence=ev,note=x.get('note',''))
        category='excluded' if failed else 'needs_review' if unresolved or missing else 'ranked'
        result[category].append(dict(candidate=c,score_total=round(total,6),evidence_coverage_weight=coverage,scores=scores,hard_checks=checks,failed_requirements=failed,unresolved_requirements=unresolved,missing_scores=missing,classification=category,assessment_note=a.get('note','')))
    for rows in result.values():
        rows.sort(key=lambda r:(-r['score_total'],-r['evidence_coverage_weight'],-(r['candidate'].get('stars') if r['candidate'].get('stars') is not None else -1),r['candidate']['id'].lower()))
        for n,r in enumerate(rows,1):r['position_within_category']=n
    return dict(schema_version=1,report_type='candidate-comparison',stage='evaluate',evaluated_at=datetime.now(timezone.utc).isoformat(),weights=WEIGHTS,score_scale=[0,5],hard_requirements=hard,**result,counts={k:len(v) for k,v in result.items()},search_coverage=source.get('coverage',[]) if isinstance(source,dict) else [],source_errors=source.get('errors',[]) if isinstance(source,dict) else [],notes=['Reference syntax was checked; evidence truth, licenses and runnability require human/agent review.'])

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--assessments',required=True);p.add_argument('--out',default='.usegit/artifacts/comparison.json');a=p.parse_args(argv)
    try: atomic_json(a.out,compare(read_json(a.input),read_json(a.assessments)));return 0
    except (OSError,ValueError,TypeError,KeyError) as e: print(json.dumps({'error':str(e)},ensure_ascii=False));return 2
if __name__=='__main__':raise SystemExit(main())
