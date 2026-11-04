#!/usr/bin/env python3
"""Bounded read-only GitHub/Gitee search; no cloning, execution, or retries."""
import argparse,json,os,tempfile,urllib.request,urllib.error
from urllib.parse import urlencode,urlsplit
from pathlib import Path
from datetime import datetime,timezone
ENDPOINTS={'github':'https://api.github.com/search/repositories','gitee':'https://gitee.com/api/v5/search/repositories'}
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return None
class FetchError(Exception):
 def __init__(self,code,status=None,retry=None): self.code,self.status,self.retry=code,status,retry

def fetch(url,headers,timeout):
 req=urllib.request.Request(url,headers=headers)
 try:
  with urllib.request.build_opener(NoRedirect()).open(req,timeout=timeout) as response:
   data=response.read(2*1024*1024+1)
   if len(data)>2*1024*1024:raise FetchError('response_too_large')
   try: body=json.loads(data)
   except (ValueError,UnicodeError): raise FetchError('invalid_json')
   return body,dict(response.headers)
 except urllib.error.HTTPError as e:
  retry=e.headers.get('Retry-After','')
  raise FetchError('redirect_blocked' if 300<=e.code<400 else 'http_error',e.code,int(retry) if retry.isdigit() else None) from None
 except (urllib.error.URLError,TimeoutError,OSError):raise FetchError('network_error') from None

def integer(x):return x if type(x) is int and x>=0 else None

def normalize(item,provider,source,now,query):
 if not isinstance(item,dict):return None
 raw=item.get('html_url') or item.get('web_url')
 try:u=urlsplit(raw) if isinstance(raw,str) else None
 except ValueError:return None
 if not u or u.scheme!='https' or u.hostname!=('github.com' if provider=='github' else 'gitee.com') or u.username or u.password:return None
 parts=u.path.strip('/').split('/')
 if len(parts)!=2 or any(not p or p in ('.','..') for p in parts):return None
 fullname='/'.join(parts);license=item.get('license')
 if isinstance(license,str):license={'spdx_id':None,'name':license,'key':None,'url':None}
 elif isinstance(license,dict):
  license={k:license.get(k) for k in ['spdx_id','name','key','url']}
  if str(license.get('spdx_id')).upper() in ('NOASSERTION','UNKNOWN','NONE'):license['spdx_id']=None
 else:license=None
 fork=item.get('fork') if type(item.get('fork')) is bool else None
 mirror=item.get('mirror_url')
 return dict(id=provider+':'+fullname.lower(),provider=provider,full_name=fullname,url='https://'+u.hostname+'/'+fullname,description=item.get('description') if isinstance(item.get('description'),str) else None,stars=integer(item.get('stargazers_count')),forks=integer(item.get('forks_count')),archived=item.get('archived') if type(item.get('archived')) is bool else None,license=license,language=item.get('language'),pushed_at=item.get('pushed_at'),source_api=source,retrieved_at=now,provider_repository_id=item.get('id'),is_fork=fork,mirror_url=mirror,upstream_url=None,origin_status='fork' if fork else 'mirror' if mirror else 'unverified',metadata_warnings=['API metadata does not verify origin, license suitability, or runtime behavior.'],matched_queries=[query])

def search(args,fetcher=fetch,environ=None):
 env=os.environ if environ is None else environ;now=datetime.now(timezone.utc).isoformat();queries=list(dict.fromkeys(args.query));candidates={};coverage=[];errors=[]
 providers=['github','gitee'] if args.provider=='both' else [args.provider]
 for provider in providers:
  token=(env.get('GH_TOKEN') or env.get('GITHUB_TOKEN')) if provider=='github' else env.get('GITEE_TOKEN');disabled=False
  for query in queries:
   c=dict(provider=provider,query=query,status='ok',pages_requested=0,raw_items=0,accepted_items=0,filtered_items=0,invalid_items=0,total_count=None,exhaustive=False,incomplete_results=False,stop_reason=None,source_urls=[],authenticated=bool(token));coverage.append(c);seen=set()
   if disabled:c.update(status='skipped',stop_reason='provider_unavailable');continue
   for page in range(1,args.max_pages+1):
    params={'q':query,'page':page,'per_page':args.page_size,'sort':'stars','order':'desc'};safe_url=ENDPOINTS[provider]+'?'+urlencode(params);headers={'User-Agent':'UseGit/0.2','Accept':'application/json'}
    if token:
     if provider=='github':headers['Authorization']='Bearer '+token
     else:params['access_token']=token
    actual_url=ENDPOINTS[provider]+'?'+urlencode(params);c['source_urls'].append(safe_url);c['pages_requested']+=1
    try:
     body,response_headers=fetcher(actual_url,headers,args.timeout)
     if provider=='github':
      if not isinstance(body,dict) or not isinstance(body.get('items'),list):raise FetchError('invalid_response')
      items=body['items'];c['total_count']=integer(body.get('total_count'));c['incomplete_results']=c['incomplete_results'] or body.get('incomplete_results') is True
     else:
      if not isinstance(body,list):raise FetchError('invalid_response')
      items=body
     c['rate_limit']={k:v for k,v in response_headers.items() if k.lower() in ('x-ratelimit-remaining','x-ratelimit-reset')}
    except FetchError as e:
     errors.append(dict(provider=provider,query=query,page=page,code=e.code,message='Provider request failed; no request secrets or response body recorded.',http_status=e.status,retry_after_seconds=e.retry));c.update(status='partial' if seen else 'error',stop_reason=e.code)
     if e.status in (401,403,429) or e.code=='network_error':disabled=True
     break
    c['raw_items']+=len(items)
    for item in items:
     row=normalize(item,provider,safe_url,now,query)
     if row is None:c['invalid_items']+=1;continue
     if (row['archived'] is True and not args.include_archived) or (args.min_stars>0 and (row['stars'] is None or row['stars']<args.min_stars)):c['filtered_items']+=1;continue
     key=row['id']
     if key not in seen and len(seen)>=args.limit:continue
     seen.add(key)
     if key in candidates:
      if query not in candidates[key]['matched_queries']:candidates[key]['matched_queries'].append(query)
     else:candidates[key]=row
    c['accepted_items']=len(seen)
    total=c['total_count'];exhausted=(provider=='github' and total is not None and page*args.page_size>=total) or (not items) or (total is None and len(items)<args.page_size)
    if len(seen)>=args.limit:c['stop_reason']='candidate_limit';break
    if exhausted:c['stop_reason']='results_exhausted';c['exhaustive']=provider=='github' and not c['incomplete_results'];break
    if page==args.max_pages:c.update(status='partial',stop_reason='page_budget')
   if c['status']=='ok' and c['incomplete_results']:c.update(status='partial',stop_reason='provider_incomplete')
   if c['status']=='ok' and not seen:c['status']='empty'
   if c['invalid_items'] and c['status'] in ('ok','empty'):c['status']='partial';c['stop_reason']='invalid_items'
 complete=all(c['status'] in ('ok','empty') for c in coverage)
 return dict(schema_version=1,report_type='repository-discovery',stage='find-repos',retrieved_at=now,queries=queries,parameters={k:getattr(args,k) for k in ['provider','limit','min_stars','max_pages','page_size','timeout','include_archived']},coverage=coverage,errors=errors,candidates=list(candidates.values()),notes=['Bounded API search only; not an exhaustive website search. Gitee has no verified total count.'],coverage_complete=complete)

def save(path,data):
 if path=='-':print(json.dumps(data,ensure_ascii=False,indent=2));return
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=p.parent,prefix='.'+p.name)
 try:
  with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

def parse(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--provider',choices=['github','gitee','both'],default='both');p.add_argument('--query',action='append',required=True);p.add_argument('--limit',type=int,default=20);p.add_argument('--min-stars',type=int,default=0);p.add_argument('--max-pages',type=int,default=3);p.add_argument('--page-size',type=int,default=50);p.add_argument('--timeout',type=float,default=10);p.add_argument('--include-archived',action='store_true');p.add_argument('--out',default='.usegit/artifacts/repos.json');a=p.parse_args(argv)
 if not 1<=len(a.query)<=8 or any(not q.strip() or len(q)>256 for q in a.query) or not 1<=a.limit<=100 or a.min_stars<0 or not 1<=a.max_pages<=10 or not 1<=a.page_size<=100 or not 0<a.timeout<=30:p.error('parameters outside supported bounds')
 return a

def main(argv=None):
 a=parse(argv)
 try:
  report=search(a);save(a.out,report);return 0 if report['coverage_complete'] else 1
 except (OSError,ValueError,TypeError):print(json.dumps({'error':'Invalid input or output could not be written.'}));return 2
if __name__=='__main__':raise SystemExit(main())
