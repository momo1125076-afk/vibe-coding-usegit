import importlib.util, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('rank',Path(__file__).resolve().parents[1]/'tools/rank_candidates.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class RankingTests(unittest.TestCase):
 def data(self):
  return [{'id':'github:a/b','stars':10}],{'assessments':[{'candidate_id':'github:a/b','hard_checks':{k:{'status':'pass','evidence':['review.md']} for k in ['license-fit','platform-fit']},'scores':{k:{'score':5,'evidence':['review.md']} for k in r.WEIGHTS}}]}
 def test_wrong_top_level(self):
  for source in [None,3,'text',True]:
   with self.subTest(source=source),self.assertRaises(ValueError):r.compare(source,{})
 def test_full(self):
  c,a=self.data();x=r.compare(c,a);self.assertEqual(x['ranked'][0]['score_total'],100)
 def test_hard_fail(self):
  c,a=self.data();a['assessments'][0]['hard_checks']['license-fit']['status']='fail';self.assertEqual(r.compare(c,a)['counts']['excluded'],1)
 def test_missing_evidence(self):
  c,a=self.data();a['assessments'][0]['scores']['fit']['evidence']=[];x=r.compare(c,a)['needs_review'][0];self.assertEqual(x['score_total'],70);self.assertEqual(x['evidence_coverage_weight'],70)
 def test_no_assessment(self):self.assertEqual(r.compare([{'id':'x','stars':None}],{})['counts']['needs_review'],1)
 def test_bad_score(self):
  for score in [True,float('nan'),float('inf'),-1,6,'5']:
   c,a=self.data();a['assessments'][0]['scores']['fit']['score']=score
   with self.subTest(score=score),self.assertRaises(ValueError):r.compare(c,a)
 def test_bad_refs(self):
  for ref in ['../secret','/etc/passwd','https://x/?token=a','https://u:p@x/','file:///x','C:/x','//host/x','x\\..\\s']:
   with self.subTest(ref=ref),self.assertRaises(ValueError):r.references([ref])
 def test_author_reference_allowed(self):self.assertEqual(r.references(['https://example.test/?author=alice']),['https://example.test/?author=alice'])
 def test_auth_reference_rejected(self):
  with self.assertRaises(ValueError):r.references(['https://example.test/evidence?authorization=Bearer_SYNTHETIC_SECRET'])
 def test_unknown_candidate(self):
  c,a=self.data();a['assessments'][0]['candidate_id']='missing'
  with self.assertRaises(ValueError):r.compare(c,a)
 def test_duplicates(self):
  c,a=self.data()
  with self.assertRaises(ValueError):r.compare(c+c,a)
 def test_unknown_dimensions(self):
  c,a=self.data();a['assessments'][0]['scores']['speed']={}
  with self.assertRaises(ValueError):r.compare(c,a)
 def test_evidenceless_fail_unknown(self):
  c,a=self.data();a['assessments'][0]['hard_checks']['license-fit']={'status':'fail','evidence':[]};self.assertEqual(r.compare(c,a)['counts']['needs_review'],1)
if __name__=='__main__':unittest.main()
