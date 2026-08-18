from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from across_edge_worker.security import scan_tree_for_secrets
root=Path(__file__).resolve().parents[1];findings=scan_tree_for_secrets(root)
if findings:
 print("\n".join(findings));raise SystemExit(1)
print("WORKER_SECRET_SCAN=PASS")
