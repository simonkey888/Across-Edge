from __future__ import annotations
import json,subprocess,tempfile,time,unittest
from pathlib import Path
from across_edge_worker.rpc import ReadOnlyRpcClient
from across_edge_worker.security import assert_endpoint_allowed,prepare_isolated_target,run_bounded_process,scan_text_for_secrets,scrub_environment,validate_relative_path,validate_target_repository
from helpers import make_repo
class FakeResponse:
 def __init__(self,payload,url="https://rpc.example"):self.payload=json.dumps(payload).encode();self.url=url
 def __enter__(self):return self
 def __exit__(self,*args):return False
 def read(self):return self.payload
 def geturl(self):return self.url
class FakeOpener:
 def __init__(self,responses):self.responses=list(responses)
 def open(self,request,timeout=0):return self.responses.pop(0)
class SecurityTests(unittest.TestCase):
 def test_path_traversal_and_symlink_escape_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)/"root";root.mkdir();(root/"safe").mkdir();(root/"safe/a.txt").write_text("ok");outside=Path(td)/"outside";outside.mkdir();(root/"safe/link").symlink_to(outside,target_is_directory=True)
   with self.assertRaisesRegex(ValueError,"path_escape"):validate_relative_path(root,"../outside/x",["safe"])
   with self.assertRaisesRegex(ValueError,"symlink"):validate_relative_path(root,"safe/link/x",["safe"])
 def test_environment_scrubs_sensitive_names(self):
  clean=scrub_environment({"PATH":"/bin","AWS_SECRET_ACCESS_KEY":"x","CLOUDFLARE_API_TOKEN":"x","STRIPE_SECRET_KEY":"x","PRIVATE_KEY":"x","WALLET_SEED":"x"},home="/tmp/clean");self.assertNotIn("PRIVATE_KEY",clean);self.assertNotIn("WALLET_SEED",clean)
 def test_secret_scanner(self):
  pem="-----BEGIN "+"PRIVATE"+" KEY-----\nabc";self.assertTrue(scan_text_for_secrets(pem));self.assertFalse(scan_text_for_secrets("public evidence only"))
 def test_endpoint_exact_allowlist_and_credential_query_policy(self):
  assert_endpoint_allowed("https://rpc.example",["https://rpc.example"])
  with self.assertRaisesRegex(ValueError,"endpoint_not_allowlisted"):assert_endpoint_allowed("https://evil.example",["https://rpc.example"])
  with self.assertRaisesRegex(ValueError,"query_forbidden"):assert_endpoint_allowed("https://rpc.example?token=secret",["https://rpc.example?token=secret"])
  credential_url="https://"+"user"+":"+"pass"+"@"+"rpc.example"
  with self.assertRaisesRegex(ValueError,"invalid_url"):assert_endpoint_allowed(credential_url,[credential_url])
 def test_target_repository_remote_policy(self):
  credential_remote="https://"+"user"+":"+"token"+"@"+"example.com/repo.git"
  for value in ("ssh://example.com/repo.git","git://example.com/repo.git",credential_remote,"https://example.com/repo.git?token=x"):
   with self.subTest(value=value):
    with self.assertRaisesRegex(ValueError,"target_repository_remote_policy_forbidden"):validate_target_repository(value)
  validate_target_repository("https://github.com/example/repo")
 def test_rpc_is_read_only_and_chain_bound(self):
  c=ReadOnlyRpcClient("https://rpc.example",("https://rpc.example",),(42161,));c._opener=FakeOpener([FakeResponse({"jsonrpc":"2.0","id":1,"result":"0xa4b1"}),FakeResponse({"jsonrpc":"2.0","id":2,"result":"0x10"}),FakeResponse({"jsonrpc":"2.0","id":3,"result":{"number":"0x10","hash":"0x"+"11"*32}})]);self.assertEqual(c.provenance().chain_id,42161)
  with self.assertRaisesRegex(PermissionError,"forbidden"):c.call("eth_sendRawTransaction",["0xdead"])
 def test_rpc_redirect_fails_closed(self):
  class R:
   def open(self,request,timeout=0):raise ValueError("rpc_redirect_forbidden")
  c=ReadOnlyRpcClient("https://rpc.example",("https://rpc.example",),(42161,));c._opener=R()
  with self.assertRaisesRegex(ValueError,"rpc_redirect_forbidden"):c.chain_id()
 def test_rpc_spoofed_chain_and_host_fail_closed(self):
  c=ReadOnlyRpcClient("https://rpc.example",("https://rpc.example",),(42161,));c._opener=FakeOpener([FakeResponse({"jsonrpc":"2.0","id":1,"result":"0x1"})])
  with self.assertRaisesRegex(ValueError,"chain_id_not_allowlisted"):c.chain_id()
  c=ReadOnlyRpcClient("https://rpc.example",("https://rpc.example",),(42161,));c._opener=FakeOpener([FakeResponse({"jsonrpc":"2.0","id":1,"result":"0xa4b1"},url="https://other.example")])
  with self.assertRaisesRegex(ValueError,"rpc_host_changed"):c.chain_id()
 def test_git_hooks_not_executed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);repo,sha=make_repo(root/"repo");marker=root/"hook-ran";hook=repo/".git/hooks/post-checkout";hook.write_text(f"#!/bin/sh\necho bad > {marker}\n");hook.chmod(0o755);target=prepare_isolated_target(str(repo),sha,root/"work");self.assertFalse(marker.exists());self.assertEqual(subprocess.check_output(["git","-C",str(target),"config","core.hooksPath"],text=True).strip(),"/dev/null")
 def test_bounded_process_kills_process_group_and_honors_cancel_marker(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);script=root/"spawn.py";pid_file=root/"child.pid";script.write_text("import subprocess,time,pathlib\np=subprocess.Popen(['python3','-c','import time;time.sleep(30)'])\npathlib.Path("+repr(str(pid_file))+").write_text(str(p.pid))\ntime.sleep(30)\n")
   with self.assertRaisesRegex(TimeoutError,"bounded_process_timeout"):run_bounded_process(["python3",str(script)],cwd=root,timeout=.5)
   time.sleep(.2);self.assertFalse(Path(f"/proc/{int(pid_file.read_text())}").exists())
   marker=root/"cancel";marker.write_text("1")
   with self.assertRaisesRegex(InterruptedError,"worker_cancelled"):run_bounded_process(["python3","-c","import time;time.sleep(30)"],cwd=root,timeout=5,cancel_marker=marker)
if __name__=="__main__":unittest.main()
