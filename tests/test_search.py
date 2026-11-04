import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('search',Path(__file__).resolve().parents[1]/'tools/search_repos.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class SearchTests(unittest.TestCase):
 def args(self,*extra):return m.parse(['--provider','github','--query','test',*extra])
 def item(self):return {'html_url':'https://github.com/A/B','stargazers_count':3}
 def test_success(self):
  r=m.search(self.args(),lambda *x:({'items':[self.item()],'total_count':1},{}),{});self.assertTrue(r['coverage_complete']);self.assertIsNone(r['candidates'][0]['archived']);self.assertTrue(r['coverage'][0]['exhaustive'])
 def test_dedup_queries(self):
  r=m.search(self.args('--query','other'),lambda *x:({'items':[self.item()],'total_count':1},{}),{});self.assertEqual(len(r['candidates']),1);self.assertEqual(r['candidates'][0]['matched_queries'],['test','other'])
 def test_rate_limit_skips(self):
  def fail(*x):raise m.FetchError('http_error',429,20)
  r=m.search(self.args('--query','other'),fail,{});self.assertEqual([x['status'] for x in r['coverage']],['error','skipped']);self.assertFalse(r['coverage_complete'])
 def test_tokens_not_in_output(self):
  def fake(url,headers,*x):self.assertIn('SECRET',headers['Authorization']);return {'items':[self.item()],'total_count':1},{}
  r=m.search(self.args(),fake,{'GH_TOKEN':'SECRET'});self.assertNotIn('SECRET',str(r))
 def test_gitee_token_redacted(self):
  def fake(url,*x):self.assertIn('SECRET',url);return [{'html_url':'https://gitee.com/a/b'}],{}
  r=m.search(self.args('--provider','gitee'),fake,{'GITEE_TOKEN':'SECRET'});self.assertNotIn('SECRET',str(r));self.assertFalse(r['coverage'][0]['exhaustive'])
 def test_incomplete(self):
  r=m.search(self.args(),lambda *x:({'items':[],'total_count':0,'incomplete_results':True},{}),{});self.assertEqual(r['coverage'][0]['status'],'partial')
 def test_page_budget(self):
  r=m.search(self.args('--max-pages','1','--page-size','1'),lambda *x:({'items':[self.item()],'total_count':50},{}),{});self.assertFalse(r['coverage_complete'])
 def test_filter(self):
  r=m.search(self.args('--min-stars','5'),lambda *x:({'items':[self.item()],'total_count':1},{}),{});self.assertEqual(r['candidates'],[])
 def test_bad_urls(self):
  for url in ['https://evil.test/a/b','https://user:pass@github.com/a/b','http://github.com/a/b','https://github.com/a/b/issues']:
   with self.subTest(url=url):self.assertIsNone(m.normalize({'html_url':url},'github','url','date','q'))
 def test_malformed_url_preserves_valid_items(self):
  r=m.search(self.args(),lambda *x:({'items':[self.item(),{'html_url':'https://[bad/a/b'}],'total_count':2},{}),{})
  self.assertEqual(len(r['candidates']),1);self.assertEqual(r['coverage'][0]['invalid_items'],1);self.assertEqual(r['coverage'][0]['status'],'partial')
 def test_partial_results_preserved(self):
  calls=[]
  def fake(*x):
   calls.append(1)
   if len(calls)>1:raise m.FetchError('network_error')
   return {'items':[self.item()],'total_count':2},{}
  r=m.search(self.args('--page-size','1'),fake,{});self.assertEqual(len(r['candidates']),1);self.assertEqual(r['coverage'][0]['status'],'partial')
if __name__=='__main__':unittest.main()
