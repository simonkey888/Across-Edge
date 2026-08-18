from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from across_edge_worker.security import scan_tree_for_secrets
root=Path(__file__).resolve().parents[1]
allowed_exact={"tests/fixtures/secret_scanner_placeholders.txt"}
findings=[]
for finding in scan_tree_for_secrets(root):
 relative=finding.split(":secret_pattern_",1)[0]
 if relative in allowed_exact:continue
 findings.append(finding)
if findings:
 print("\n".join(findings));raise SystemExit(1)
print("WORKER_SECRET_SCAN=PASS")
