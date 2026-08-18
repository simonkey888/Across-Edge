from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
from .atm_worker import WORKER_CAPABILITIES, WORKER_ID, WORKER_PROTOCOL_VERSION, WorkerCannotHandle, WorkerContractError, WorkerExecutionError, WorkerJob, run_worker_job

def _source_sha(repo: Path) -> str:
    proc = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise WorkerExecutionError('cannot resolve worker source SHA')
    value = proc.stdout.strip().lower()
    if len(value) != 40:
        raise WorkerExecutionError('worker source SHA is not exact')
    return value

def main(argv: list[str] | None=None) -> int:
    parser = argparse.ArgumentParser(prog='across-edge-worker')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('capabilities')
    cancel = sub.add_parser('cancel')
    cancel.add_argument('--run-root', required=True)
    validate = sub.add_parser('validate')
    validate.add_argument('job_json')
    run = sub.add_parser('run')
    run.add_argument('job_json')
    run.add_argument('--target-checkout', required=True)
    run.add_argument('--run-root', required=True)
    run.add_argument('--worker-checkout', default='.')
    run.add_argument('--canonical-checkout')
    args = parser.parse_args(argv)
    if args.command == 'cancel':
        marker = Path(args.run_root) / 'state' / 'cancel.requested'
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text('requested\n', encoding='utf-8')
        print(json.dumps({'status': 'CANCEL_REQUESTED', 'run_root': str(Path(args.run_root))}, sort_keys=True))
        return 0
    if args.command == 'capabilities':
        print(json.dumps({'worker_id': WORKER_ID, 'worker_protocol_version': WORKER_PROTOCOL_VERSION, 'capabilities': sorted(WORKER_CAPABILITIES), 'outgoing_spend_usd': 0, 'financial_authority': 0, 'claim_authority': 0, 'submission_authority': 0, 'external_protocol_mutation_authority': 0}, sort_keys=True))
        return 0
    raw = json.loads(Path(args.job_json).read_text(encoding='utf-8'))
    try:
        job = WorkerJob.from_mapping(raw)
        if args.command == 'validate':
            print(json.dumps({'status': 'VALID', 'worker_id': job.worker_id, 'job_id': job.job_id, 'work_lease_id': job.work_lease_id, 'scope_hash': job.scope_hash, 'outgoing_spend_usd': 0}, sort_keys=True))
            return 0
        worker_checkout = Path(args.worker_checkout).resolve()
        result = run_worker_job(raw, worker_source_sha=_source_sha(worker_checkout), target_source_checkout=args.target_checkout, run_root=args.run_root, canonical_checkout=args.canonical_checkout or worker_checkout)
        print(json.dumps(result, sort_keys=True))
        return 0
    except WorkerCannotHandle as exc:
        print(json.dumps({'status': 'CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY', 'error': str(exc)}, sort_keys=True))
        return 3
    except (WorkerContractError, WorkerExecutionError) as exc:
        print(json.dumps({'status': 'FAILED_CLOSED', 'error_class': type(exc).__name__, 'error': str(exc)}, sort_keys=True))
        return 2
if __name__ == '__main__':
    raise SystemExit(main())
