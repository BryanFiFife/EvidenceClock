import json,tempfile,unittest,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
from evidenceclock.core import *
from evidenceclock.cli import main
BASE=datetime(2026,8,30,0,0,tzinfo=timezone.utc)
def node(i,ttl=60,deps=None,obs=BASE): return {"id":i,"observed_at":fmt_time(obs),"max_age_seconds":ttl,"depends_on":deps or []}
def manifest(nodes,roots=None): return {"decision_id":"d","nodes":nodes,"roots":roots or [nodes[-1]['id']]}
class Tests(unittest.TestCase):
 def test_fresh(self): self.assertTrue(verify_manifest(manifest([node('a')]),BASE+timedelta(seconds=30),False).fresh)
 def test_boundary_fresh(self): self.assertTrue(verify_manifest(manifest([node('a')]),BASE+timedelta(seconds=60),False).fresh)
 def test_after_boundary_stale(self): self.assertFalse(verify_manifest(manifest([node('a')]),BASE+timedelta(seconds=61),False).fresh)
 def test_transitive_expiry(self):
  r=verify_manifest(manifest([node('a',10),node('b',100,['a'])]),BASE+timedelta(seconds=11),False); self.assertFalse(r.fresh); self.assertEqual(r.nodes[1].expires_at,fmt_time(BASE+timedelta(seconds=10)))
 def test_three_level(self): self.assertFalse(verify_manifest(manifest([node('a',5),node('b',50,['a']),node('c',500,['b'])]),BASE+timedelta(seconds=6),False).fresh)
 def test_missing_dep(self):
  with self.assertRaises(EvidenceClockError): verify_manifest(manifest([node('a',deps=['x'])]),BASE,False)
 def test_cycle(self):
  with self.assertRaises(EvidenceClockError): verify_manifest(manifest([node('a',deps=['b']),node('b',deps=['a'])]),BASE,False)
 def test_duplicate(self):
  with self.assertRaises(EvidenceClockError): verify_manifest(manifest([node('a'),node('a')]),BASE,False)
 def test_bad_ttl(self):
  n=node('a'); n['max_age_seconds']=-1
  with self.assertRaises(EvidenceClockError): verify_manifest(manifest([n]),BASE,False)
 def test_bool_ttl(self):
  n=node('a'); n['max_age_seconds']=True
  with self.assertRaises(EvidenceClockError): verify_manifest(manifest([n]),BASE,False)
 def test_future_clock(self): self.assertFalse(verify_manifest(manifest([node('a',obs=BASE+timedelta(seconds=31))]),BASE,False).fresh)
 def test_future_within_skew(self): self.assertTrue(verify_manifest(manifest([node('a',obs=BASE+timedelta(seconds=30))]),BASE,False).fresh)
 def test_timezone_required(self):
  with self.assertRaises(EvidenceClockError): parse_time('2026-01-01T00:00:00')
 def test_file_capture_verify(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'x'; p.write_text('abc'); n=capture_file(p,'f',60,BASE); self.assertTrue(verify_manifest(manifest([n]),BASE).fresh)
 def test_file_tamper(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'x'; p.write_text('abc'); n=capture_file(p,'f',60,BASE); p.write_text('changed'); self.assertFalse(verify_manifest(manifest([n]),BASE).fresh)
 def test_missing_file(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'x'; p.write_text('abc'); n=capture_file(p,'f',60,BASE); p.unlink(); self.assertFalse(verify_manifest(manifest([n]),BASE).fresh)
 def test_symlink_rejected(self):
  if not hasattr(os,'symlink'): self.skipTest('no symlink')
  with tempfile.TemporaryDirectory() as td:
   a=Path(td)/'a'; b=Path(td)/'b'; a.write_text('x'); b.symlink_to(a)
   with self.assertRaises(EvidenceClockError): hash_file(b)
 def test_bad_sha(self):
  n=node('a'); n['sha256']='abc'
  with self.assertRaises(EvidenceClockError): verify_manifest(manifest([n]),BASE)
 def test_all_nodes_checked_hidden_cycle(self):
  m=manifest([node('root'),node('a',deps=['b']),node('b',deps=['a'])],['root'])
  with self.assertRaises(EvidenceClockError): verify_manifest(m,BASE,False)
 def test_roots_validation(self):
  with self.assertRaises(EvidenceClockError): verify_manifest(manifest([node('a')],['x']),BASE,False)
 def test_capture_bad_ttl(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'x'; p.write_text('x')
   with self.assertRaises(EvidenceClockError): capture_file(p,'x',-1,BASE)
 def test_cli_stale_exit(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'m.json'; p.write_text(json.dumps(manifest([node('a',1)]))); self.assertEqual(main(['verify',str(p),'--at',fmt_time(BASE+timedelta(seconds=2)),'--no-file-check']),2)
 def test_cli_invalid_exit(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'m.json'; p.write_text('{'); self.assertEqual(main(['verify',str(p)]),3)
 def test_sources_transitive(self):
  r=verify_manifest(manifest([node('a'),node('b',deps=['a'])]),BASE,False); self.assertEqual(r.nodes[1].effective_sources,('a','b'))
if __name__=='__main__': unittest.main()
