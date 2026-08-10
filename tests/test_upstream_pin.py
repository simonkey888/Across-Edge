import subprocess,pytest
from across_edge.upstream import verify_upstream_checkout
def git(path,*args):subprocess.run(['git','-C',str(path),*args],check=True,capture_output=True)
def test_pin_and_repo_identity_fail_closed(tmp_path):
 r=tmp_path/'r';r.mkdir();git(r,'init');git(r,'config','user.email','x@y.z');git(r,'config','user.name','x');(r/'x').write_text('x');git(r,'add','x');git(r,'commit','-m','x');git(r,'remote','add','origin','https://github.com/across-protocol/relayer.git')
 with pytest.raises(RuntimeError,match='HEAD mismatch'):verify_upstream_checkout(r)
 git(r,'remote','set-url','origin','https://github.com/evil/relayer.git')
 with pytest.raises(RuntimeError,match='repository identity'):verify_upstream_checkout(r)
