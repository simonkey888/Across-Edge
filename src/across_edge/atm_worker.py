from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlsplit
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from .safety import SafetyViolation, assert_read_only_rpc_method, sanitize_endpoint, sanitize_text
WORKER_ID = 'across-edge'
WORKER_PROTOCOL_VERSION = 'atm-worker/v1'
WORKER_CAPABILITIES = frozenset({'event_log_decoding', 'chain_provenance', 'sdk_client_repair', 'unsigned_transaction_validation', 'relayer_reconciliation', 'fee_logic_verification', 'external_mutation_refusal'})
TERMINAL_LEASE_STATES = frozenset({'expired', 'cancelled', 'completed', 'failed', 'revoked', 'terminal'})
FORBIDDEN_EXTERNAL_ACTIONS = frozenset({'broadcast', 'send_transaction', 'send_raw_transaction', 'claim', 'submit', 'register', 'nominate', 'swap', 'rebalance', 'withdraw', 'transfer', 'sign'})
_SHA40 = re.compile('^[0-9a-f]{40}$')
_SECRET_NAME = re.compile('(?i)(secret|token|password|private|mnemonic|seed|credential|aws_|gcp_|google_|azure_|stripe|paypal|wallet|key$|key_)')
_SECRET_CONTENT_PATTERNS = (re.compile('gh[pousr]_[A-Za-z0-9_]{20,}'), re.compile('(?i)authorization\\s*:\\s*bearer\\s+[A-Za-z0-9._~+\\-/=]{8,}'), re.compile('https?://[^\\s/@:]+:[^\\s/@]+@'), re.compile('(?i)(?:private[_ -]?key|mnemonic|seed phrase)\\s*[=:]\\s*[\'\\"]?(?:0x)?[0-9a-f]{64}'), re.compile('(?i)(?:api[_-]?key|access[_-]?token|password)\\s*[=:]\\s*[\'\\"]?[A-Za-z0-9._~+\\-/=]{20,}'))

class WorkerContractError(ValueError):
    """The frozen ATM job contract is invalid or exceeds worker authority."""

class WorkerExecutionError(RuntimeError):
    """A bounded worker operation could not be completed safely."""

class WorkerCannotHandle(WorkerExecutionError):
    """The requested work is outside the worker's current authority/capability."""

class InjectedCrash(WorkerExecutionError):
    """Deterministic qualification-only crash injection."""

class WorkerCancelled(WorkerExecutionError):
    """The durable cancel marker was observed at a safe boundary."""

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def _parse_time(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except Exception as exc:
        raise WorkerContractError(f'invalid RFC3339 timestamp: {value!r}') from exc

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def _safe_relative_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise WorkerContractError('allowed path must be a non-empty string')
    value = raw.replace('\\', '/')
    p = PurePosixPath(value)
    if p.is_absolute() or any((part in {'', '.', '..'} for part in p.parts)):
        raise WorkerContractError(f'unsafe relative path: {raw!r}')
    return str(p)

def _normalize_endpoint(raw: str) -> str:
    if not isinstance(raw, str):
        raise WorkerContractError('read endpoint must be a string')
    p = urlsplit(raw)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.fragment:
        raise WorkerContractError(f'unsafe read endpoint: {sanitize_endpoint(raw)}')
    if p.query:
        raise WorkerContractError('read endpoint query strings are prohibited')
    return raw.rstrip('/')

def _scope_payload(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {'job_id': raw.get('job_id'), 'canonical_opportunity_id': raw.get('canonical_opportunity_id'), 'worker_id': raw.get('worker_id'), 'work_lease_id': raw.get('work_lease_id'), 'target_repository': raw.get('target_repository'), 'target_base_sha': raw.get('target_base_sha'), 'allowed_paths': sorted(raw.get('allowed_paths') or []), 'required_capabilities': sorted(raw.get('required_capabilities') or []), 'frozen_acceptance_criteria': raw.get('frozen_acceptance_criteria'), 'structured_requirements': raw.get('structured_requirements'), 'expected_deliverable': raw.get('expected_deliverable'), 'deterministic_checks': raw.get('deterministic_checks'), 'allowed_chain_ids': sorted(raw.get('allowed_chain_ids') or []), 'allowed_read_endpoints': raw.get('allowed_read_endpoints') or {}, 'max_spend_usd': str(raw.get('max_spend_usd'))}

def compute_scope_hash(raw: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(_scope_payload(raw)))

@dataclass(frozen=True)
class WorkerJob:
    job_id: str
    canonical_opportunity_id: str
    worker_id: str
    work_lease_id: str
    scope_hash: str
    lease_state: str
    lease_expires_at: str
    frozen_acceptance_criteria: tuple[str, ...]
    target_repository: str
    target_base_sha: str
    allowed_paths: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    structured_requirements: Mapping[str, Any]
    expected_deliverable: Mapping[str, Any]
    deterministic_checks: tuple[Mapping[str, Any], ...]
    allowed_chain_ids: tuple[int, ...]
    allowed_read_endpoints: Mapping[int, tuple[str, ...]]
    max_spend_usd: Decimal

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any], *, now: float | None=None) -> 'WorkerJob':
        if not isinstance(raw, Mapping):
            raise WorkerContractError('job must be an object')
        required = ('job_id', 'canonical_opportunity_id', 'worker_id', 'work_lease_id', 'scope_hash', 'lease_state', 'lease_expires_at', 'frozen_acceptance_criteria', 'target_repository', 'target_base_sha', 'allowed_paths', 'required_capabilities', 'structured_requirements', 'expected_deliverable', 'deterministic_checks', 'allowed_chain_ids', 'allowed_read_endpoints', 'max_spend_usd')
        missing = [name for name in required if name not in raw]
        if missing:
            raise WorkerContractError('missing required fields: ' + ','.join(missing))
        if raw['worker_id'] != WORKER_ID:
            raise WorkerContractError('worker_id mismatch')
        for name in ('job_id', 'canonical_opportunity_id', 'work_lease_id', 'scope_hash', 'target_repository'):
            if not isinstance(raw[name], str) or not raw[name].strip():
                raise WorkerContractError(f'{name} must be non-empty')
        lease_state = str(raw['lease_state']).strip().lower()
        if lease_state in TERMINAL_LEASE_STATES or lease_state != 'active':
            raise WorkerContractError(f'lease is not active: {lease_state}')
        expires = str(raw['lease_expires_at'])
        if _parse_time(expires) <= (time.time() if now is None else now):
            raise WorkerContractError('lease expired')
        base_sha = str(raw['target_base_sha']).lower()
        if not _SHA40.fullmatch(base_sha):
            raise WorkerContractError('target_base_sha must be a full 40-char lowercase git SHA')
        try:
            spend = Decimal(str(raw['max_spend_usd']))
        except InvalidOperation as exc:
            raise WorkerContractError('max_spend_usd must be numeric') from exc
        if spend != 0:
            raise WorkerContractError('nonzero spend is outside worker authority')
        if not isinstance(raw['allowed_paths'], list):
            raise WorkerContractError('allowed_paths must be a list')
        paths = tuple(sorted({_safe_relative_path(v) for v in raw['allowed_paths']}))
        if not paths:
            raise WorkerContractError('allowed_paths cannot be empty')
        if not isinstance(raw['required_capabilities'], list):
            raise WorkerContractError('required_capabilities must be a list')
        capabilities = tuple(sorted(set(map(str, raw['required_capabilities']))))
        unsupported = sorted(set(capabilities) - WORKER_CAPABILITIES)
        if unsupported:
            raise WorkerContractError('unsupported capability: ' + ','.join(unsupported))
        if not isinstance(raw['frozen_acceptance_criteria'], list) or not all((isinstance(v, str) and v for v in raw['frozen_acceptance_criteria'])):
            raise WorkerContractError('frozen_acceptance_criteria must be a non-empty string list')
        if not raw['frozen_acceptance_criteria']:
            raise WorkerContractError('frozen_acceptance_criteria cannot be empty')
        if not isinstance(raw['structured_requirements'], Mapping):
            raise WorkerContractError('structured_requirements must be an object')
        if not isinstance(raw['expected_deliverable'], Mapping):
            raise WorkerContractError('expected_deliverable must be an object')
        if not isinstance(raw['deterministic_checks'], list) or not all((isinstance(v, Mapping) for v in raw['deterministic_checks'])):
            raise WorkerContractError('deterministic_checks must be an object list')
        try:
            chain_ids = tuple(sorted(set((int(v) for v in raw['allowed_chain_ids']))))
        except Exception as exc:
            raise WorkerContractError('allowed_chain_ids must contain integers') from exc
        if any((v <= 0 for v in chain_ids)):
            raise WorkerContractError('allowed_chain_ids must be positive')
        endpoints_raw = raw['allowed_read_endpoints']
        if not isinstance(endpoints_raw, Mapping):
            raise WorkerContractError('allowed_read_endpoints must be an object')
        endpoints: dict[int, tuple[str, ...]] = {}
        for chain_key, values in endpoints_raw.items():
            chain_id = int(chain_key)
            if chain_id not in chain_ids:
                raise WorkerContractError(f'endpoint chain {chain_id} not in chain allowlist')
            if not isinstance(values, list) or not values:
                raise WorkerContractError(f'chain {chain_id} endpoints must be a non-empty list')
            endpoints[chain_id] = tuple(sorted({_normalize_endpoint(v) for v in values}))
        if set(endpoints) != set(chain_ids):
            raise WorkerContractError('every allowed chain must have explicit read endpoints')
        expected_scope = compute_scope_hash(raw)
        if raw['scope_hash'] != expected_scope:
            raise WorkerContractError('scope_hash mismatch')
        actions = raw['structured_requirements'].get('actions', [])
        if not isinstance(actions, list):
            raise WorkerContractError('structured_requirements.actions must be a list')
        for action in actions:
            if not isinstance(action, Mapping):
                raise WorkerContractError('every action must be an object')
            operation = str(action.get('operation') or '').lower()
            if operation in FORBIDDEN_EXTERNAL_ACTIONS or action.get('external_mutation') is True:
                raise WorkerCannotHandle('CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY')
        return cls(job_id=str(raw['job_id']), canonical_opportunity_id=str(raw['canonical_opportunity_id']), worker_id=WORKER_ID, work_lease_id=str(raw['work_lease_id']), scope_hash=str(raw['scope_hash']), lease_state=lease_state, lease_expires_at=expires, frozen_acceptance_criteria=tuple(raw['frozen_acceptance_criteria']), target_repository=str(raw['target_repository']), target_base_sha=base_sha, allowed_paths=paths, required_capabilities=capabilities, structured_requirements=dict(raw['structured_requirements']), expected_deliverable=dict(raw['expected_deliverable']), deterministic_checks=tuple((dict(v) for v in raw['deterministic_checks'])), allowed_chain_ids=chain_ids, allowed_read_endpoints=endpoints, max_spend_usd=spend)

    def endpoint_allowed(self, chain_id: int, endpoint: str) -> bool:
        return endpoint.rstrip('/') in self.allowed_read_endpoints.get(chain_id, ())

@dataclass(frozen=True)
class WorkerResult:
    worker_id: str
    worker_protocol_version: str
    worker_source_sha: str
    job_id: str
    work_lease_id: str
    scope_hash: str
    status: str
    started_at: str
    finished_at: str
    artifact_hashes: Mapping[str, str]
    patch_sha256: str | None
    target_commit_sha: str | None
    test_results: tuple[Mapping[str, Any], ...]
    chain_evidence_refs: tuple[Mapping[str, Any], ...]
    limitations: tuple[str, ...]
    error_class: str | None
    outgoing_spend_usd: str = '0'
    financial_authority: int = 0
    claim_authority: int = 0
    submission_authority: int = 0
    external_protocol_mutation_authority: int = 0

    def to_dict(self) -> dict[str, Any]:
        result = {'worker_id': self.worker_id, 'worker_protocol_version': self.worker_protocol_version, 'worker_source_sha': self.worker_source_sha, 'job_id': self.job_id, 'work_lease_id': self.work_lease_id, 'scope_hash': self.scope_hash, 'status': self.status, 'started_at': self.started_at, 'finished_at': self.finished_at, 'artifact_hashes': dict(self.artifact_hashes), 'patch_sha256': self.patch_sha256, 'target_commit_sha': self.target_commit_sha, 'test_results': list(self.test_results), 'chain_evidence_refs': list(self.chain_evidence_refs), 'limitations': list(self.limitations), 'error_class': self.error_class, 'outgoing_spend_usd': self.outgoing_spend_usd, 'financial_authority': self.financial_authority, 'claim_authority': self.claim_authority, 'submission_authority': self.submission_authority, 'external_protocol_mutation_authority': self.external_protocol_mutation_authority}
        forbidden = {'paid', 'withdrawable', 'realized_profit', 'external_accepted', 'executed_onchain', 'payout_success'}
        if forbidden & result.keys():
            raise WorkerExecutionError('forbidden authority-bearing result fields')
        return result

class ExecutionJournal:
    """Small durable state machine. Every receipt is source/lease/scope bound and content hashed."""

    def __init__(self, root: str | Path, job: WorkerJob, source_sha: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.job = job
        self.source_sha = source_sha
        if not _SHA40.fullmatch(source_sha):
            raise WorkerExecutionError('worker source SHA must be exact')
        self.binding = sha256_text(canonical_json({'job_id': job.job_id, 'work_lease_id': job.work_lease_id, 'scope_hash': job.scope_hash, 'source_sha': source_sha, 'worker_id': WORKER_ID}))
        existing = self.root / 'binding.json'
        if existing.exists():
            payload = json.loads(existing.read_text())
            if payload.get('binding_sha256') != self.binding:
                raise WorkerExecutionError('durable execution binding mismatch')
        else:
            self._atomic_json(existing, {'worker_id': WORKER_ID, 'source_sha': source_sha, 'job_id': job.job_id, 'work_lease_id': job.work_lease_id, 'scope_hash': job.scope_hash, 'binding_sha256': self.binding, 'created_at': _utc_now()})

    def _atomic_json(self, path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                handle.write(json.dumps(payload, sort_keys=True, indent=2) + '\n')
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def append_event(self, event: str, **data: Any) -> Mapping[str, Any]:
        payload = {'event': event, 'at': _utc_now(), 'binding_sha256': self.binding, 'data': data}
        line = canonical_json(payload)
        with (self.root / 'events.jsonl').open('a', encoding='utf-8') as handle:
            handle.write(line + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        return payload

    def ack(self) -> Mapping[str, Any]:
        path = self.root / 'ack.json'
        if path.exists():
            payload = json.loads(path.read_text())
            if payload.get('binding_sha256') != self.binding:
                raise WorkerExecutionError('ACK binding mismatch')
            return payload
        payload = {'status': 'ACK', 'worker_id': WORKER_ID, 'source_sha': self.source_sha, 'job_id': self.job.job_id, 'work_lease_id': self.job.work_lease_id, 'scope_hash': self.job.scope_hash, 'binding_sha256': self.binding, 'ack_at': _utc_now()}
        self._atomic_json(path, payload)
        self.append_event('ACK', ack_sha256=sha256_file(path))
        return payload

    def progress(self, stage: str, **data: Any) -> Mapping[str, Any]:
        payload = self.append_event('PROGRESS', stage=stage, **data)
        return payload

    def action_receipt(self, operation_id: str) -> Mapping[str, Any] | None:
        path = self.root / 'actions' / f'{operation_id}.json'
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        if payload.get('binding_sha256') != self.binding:
            raise WorkerExecutionError('action receipt binding mismatch')
        return payload

    def record_action(self, operation_id: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        record = {**dict(payload), 'operation_id': operation_id, 'binding_sha256': self.binding, 'recorded_at': _utc_now()}
        path = self.root / 'actions' / f'{operation_id}.json'
        self._atomic_json(path, record)
        self.append_event('ACTION_RECEIPT', operation_id=operation_id, receipt_sha256=sha256_file(path))
        return record

    def request_cancel(self) -> None:
        marker = self.root / 'cancel.requested'
        marker.write_text(_utc_now() + '\n', encoding='utf-8')

    def cancellation_requested(self) -> bool:
        return (self.root / 'cancel.requested').exists()

    def final_result(self) -> Mapping[str, Any] | None:
        path = self.root / 'result.json'
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        if payload.get('scope_hash') != self.job.scope_hash or payload.get('worker_source_sha') != self.source_sha:
            raise WorkerExecutionError('terminal result binding mismatch')
        return payload

    def write_result(self, result: WorkerResult) -> Mapping[str, Any]:
        payload = result.to_dict()
        self._atomic_json(self.root / 'result.json', payload)
        self.append_event('FINALIZE_RESULT', result_sha256=sha256_file(self.root / 'result.json'), status=result.status)
        return payload

def sanitized_worker_env(base: Mapping[str, str] | None=None, *, home: str | Path | None=None) -> dict[str, str]:
    source = dict(os.environ if base is None else base)
    allow = {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TMP', 'TEMP', 'TMPDIR', 'LANG', 'LC_ALL'}
    env = {k: v for k, v in source.items() if k in allow and (not _SECRET_NAME.search(k))}
    env['HOME'] = str(home or tempfile.gettempdir())
    env['GIT_TERMINAL_PROMPT'] = '0'
    env['GIT_CONFIG_COUNT'] = '1'
    env['GIT_CONFIG_KEY_0'] = 'core.hooksPath'
    env['GIT_CONFIG_VALUE_0'] = os.devnull
    env['ACROSS_EDGE_ATM_WORKER_MODE'] = '1'
    env['SEND_RELAYS'] = 'false'
    env['SEND_TRANSACTIONS'] = 'false'
    return env

def _git(repo: Path, *args: str, env: Mapping[str, str] | None=None, timeout: int=30) -> str:
    proc = subprocess.run(['git', '-C', str(repo), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(env or sanitized_worker_env(home=repo)), timeout=timeout, check=False)
    if proc.returncode != 0:
        raise WorkerExecutionError('git command failed: ' + sanitize_text(proc.stderr.strip()))
    return proc.stdout.strip()

def _reject_symlinks(root: Path) -> None:
    for path in root.rglob('*'):
        if path.is_symlink():
            raise WorkerExecutionError(f'symlink target surface rejected: {path.relative_to(root)}')

def _normalize_repository_identity(value: str) -> str:
    raw = value.strip().rstrip('/')
    if raw.startswith('fixture://'):
        return raw
    if raw.startswith('git@github.com:'):
        raw = 'https://github.com/' + raw.split(':', 1)[1]
    if raw.endswith('.git'):
        raw = raw[:-4]
    parsed = urlsplit(raw)
    if parsed.scheme != 'https' or parsed.hostname != 'github.com' or (not parsed.path.strip('/')):
        raise WorkerContractError('target_repository must be fixture:// or canonical https://github.com/owner/repo')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise WorkerContractError('target_repository contains unsafe URL components')
    return 'https://github.com/' + parsed.path.strip('/')

def _verify_target_repository(job: WorkerJob, source: Path) -> None:
    expected = _normalize_repository_identity(job.target_repository)
    if expected.startswith('fixture://'):
        return
    try:
        actual = _git(source, 'remote', 'get-url', 'origin')
    except WorkerExecutionError as exc:
        raise WorkerContractError('target checkout has no verifiable origin remote') from exc
    if _normalize_repository_identity(actual) != expected:
        raise WorkerContractError('target_repository does not match checkout origin')

def prepare_isolated_target(job: WorkerJob, source_checkout: str | Path, workspace_root: str | Path, *, canonical_checkout: str | Path | None=None) -> Path:
    source = Path(source_checkout).resolve()
    if not source.is_dir() or not (source / '.git').exists():
        raise WorkerExecutionError('target source must be a git checkout')
    if canonical_checkout is not None and source == Path(canonical_checkout).resolve():
        raise WorkerExecutionError('target source cannot be the Across-Edge canonical checkout')
    _reject_symlinks(source)
    _verify_target_repository(job, source)
    head = _git(source, 'rev-parse', 'HEAD')
    if head != job.target_base_sha:
        raise WorkerContractError(f'target SHA mismatch: expected {job.target_base_sha}, got {head}')
    root = Path(workspace_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f'target-{job.job_id}'
    if destination.exists():
        existing = _git(destination, 'rev-parse', 'HEAD')
        if existing != job.target_base_sha:
            raise WorkerExecutionError('existing isolated target has wrong base')
        return destination
    shutil.copytree(source, destination, symlinks=False)
    _reject_symlinks(destination)
    hooks = destination / '.git' / 'hooks'
    if hooks.exists():
        shutil.rmtree(hooks)
        hooks.mkdir()
    return destination

def resolve_allowed_path(root: str | Path, relative: str, allowed_paths: Iterable[str]) -> Path:
    rel = _safe_relative_path(relative)
    root_path = Path(root).resolve()
    target = (root_path / rel).resolve()
    try:
        target.relative_to(root_path)
    except ValueError as exc:
        raise WorkerContractError('path escapes target checkout') from exc
    allowed = tuple((_safe_relative_path(v) for v in allowed_paths))
    if not any((rel == prefix or rel.startswith(prefix.rstrip('/') + '/') for prefix in allowed)):
        raise WorkerContractError(f'path outside allowed scope: {rel}')
    current = root_path
    for part in PurePosixPath(rel).parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise WorkerContractError('symlink traversal rejected')
    return target

def idempotent_replace(job: WorkerJob, journal: ExecutionJournal, target_root: str | Path, *, path: str, old: str, new: str) -> Mapping[str, Any]:
    if old == new or not old:
        raise WorkerContractError('replace_text requires distinct non-empty old/new strings')
    operation_id = sha256_text(canonical_json({'op': 'replace_text', 'path': path, 'old': old, 'new': new}))
    existing = journal.action_receipt(operation_id)
    target = resolve_allowed_path(target_root, path, job.allowed_paths)
    if existing is not None:
        if not target.exists() or sha256_file(target) != existing.get('after_sha256'):
            raise WorkerExecutionError('previous action receipt no longer matches target')
        return existing
    if not target.is_file():
        raise WorkerExecutionError(f'target file missing: {path}')
    text = target.read_text(encoding='utf-8')
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1:
        before_hash = sha256_text(text)
        updated = text.replace(old, new, 1)
        target.write_text(updated, encoding='utf-8')
    elif old_count == 0 and new_count >= 1:
        before_hash = 'RECOVERED_ALREADY_APPLIED'
        updated = text
    else:
        raise WorkerExecutionError(f'replace_text expected exactly one old occurrence, found {old_count}')
    payload = {'operation': 'replace_text', 'path': path, 'before_sha256': before_hash, 'after_sha256': sha256_text(updated)}
    return journal.record_action(operation_id, payload)

def capture_patch(target_root: str | Path, out_path: str | Path) -> Mapping[str, Any]:
    root = Path(target_root)
    patch = _git(root, 'diff', '--binary', '--no-ext-diff')
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(patch + ('\n' if patch and (not patch.endswith('\n')) else ''), encoding='utf-8')
    return {'path': str(out), 'sha256': sha256_file(out), 'bytes': out.stat().st_size}

def validate_unsigned_transaction(job: WorkerJob, tx: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(tx, Mapping):
        raise WorkerContractError('unsigned transaction must be an object')
    forbidden = {'raw', 'rawTransaction', 'raw_signed_tx', 'signature', 'r', 's', 'v', 'private_key', 'mnemonic'}
    present = sorted((key for key in forbidden if tx.get(key) not in (None, '', '0x')))
    if present:
        raise WorkerContractError('signed/secret transaction material rejected: ' + ','.join(present))
    required = {'chain_id', 'to', 'data', 'value'}
    missing = sorted(required - tx.keys())
    if missing:
        raise WorkerContractError('unsigned transaction missing: ' + ','.join(missing))
    chain_id = int(tx['chain_id'])
    if chain_id not in job.allowed_chain_ids:
        raise WorkerContractError('unsigned transaction chain is not allowed')
    to = str(tx['to'])
    data = str(tx['data'])
    if not re.fullmatch('0x[0-9a-fA-F]{40}', to):
        raise WorkerContractError('unsigned transaction to address malformed')
    if not re.fullmatch('0x(?:[0-9a-fA-F]{2})*', data):
        raise WorkerContractError('unsigned transaction data malformed')
    try:
        value = int(str(tx['value']), 0) if isinstance(tx['value'], str) else int(tx['value'])
    except Exception as exc:
        raise WorkerContractError('unsigned transaction value malformed') from exc
    if value < 0:
        raise WorkerContractError('unsigned transaction value cannot be negative')
    canonical = {'chain_id': chain_id, 'to': to.lower(), 'data': data.lower(), 'value': value}
    return {'status': 'VALID_UNSIGNED_STRUCTURE', 'structure_sha256': sha256_text(canonical_json(canonical)), 'external_execution': False, 'signature_present': False}

def verify_fee_logic(inputs: Mapping[str, Any]) -> Mapping[str, Any]:
    names = ('gross_relayer_fee_usd', 'gas_usd', 'bridge_fee_usd', 'slippage_usd')
    try:
        values = {name: Decimal(str(inputs[name])) for name in names}
    except (KeyError, InvalidOperation) as exc:
        raise WorkerContractError('fee inputs are incomplete or non-numeric') from exc
    if any((value < 0 for value in values.values())):
        raise WorkerContractError('fee inputs must be non-negative')
    net = values['gross_relayer_fee_usd'] - values['gas_usd'] - values['bridge_fee_usd'] - values['slippage_usd']
    return {'gross_relayer_fee_usd': str(values['gross_relayer_fee_usd']), 'gas_usd': str(values['gas_usd']), 'bridge_fee_usd': str(values['bridge_fee_usd']), 'slippage_usd': str(values['slippage_usd']), 'net_ev_usd': str(net), 'profitable': net > 0, 'realized_profit_claimed': False, 'input_sha256': sha256_text(canonical_json(dict(inputs)))}

def reconcile_relayer_fixture(deposits: Sequence[Mapping[str, Any]], fills: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    def key(row: Mapping[str, Any]) -> tuple[int, str]:
        return (int(row['origin_chain_id']), str(row['deposit_id']))
    deposit_map: dict[tuple[int, str], Mapping[str, Any]] = {}
    for row in deposits:
        k = key(row)
        if k in deposit_map and canonical_json(deposit_map[k]) != canonical_json(row):
            raise WorkerContractError(f'ambiguous duplicate deposit: {k}')
        deposit_map[k] = row
    filled: set[tuple[int, str]] = set()
    duplicate_fills = 0
    for row in fills:
        k = key(row)
        if k in filled:
            duplicate_fills += 1
        filled.add(k)
    unknown_fills = sorted((k for k in filled if k not in deposit_map))
    if unknown_fills:
        raise WorkerContractError('fill references unknown deposit')
    unfilled = sorted((k for k in deposit_map if k not in filled))
    return {'deposit_count': len(deposit_map), 'unique_fill_count': len(filled), 'duplicate_fill_count': duplicate_fills, 'unfilled': [{'origin_chain_id': chain, 'deposit_id': dep} for chain, dep in unfilled], 'fixture_sha256': sha256_text(canonical_json({'deposits': list(deposits), 'fills': list(fills)})), 'external_execution': False}

def _decode_word(type_name: str, word: bytes) -> Any:
    if len(word) != 32:
        raise WorkerContractError('ABI word must be 32 bytes')
    if type_name == 'address':
        return '0x' + word[-20:].hex()
    if type_name.startswith('uint'):
        return int.from_bytes(word, 'big')
    if type_name == 'bool':
        value = int.from_bytes(word, 'big')
        if value not in (0, 1):
            raise WorkerContractError('invalid ABI bool')
        return bool(value)
    if type_name == 'bytes32':
        return '0x' + word.hex()
    raise WorkerCannotHandle(f'unsupported fixture ABI type: {type_name}')

def decode_event_fixture(schema: Mapping[str, Any], log: Mapping[str, Any]) -> Mapping[str, Any]:
    inputs = schema.get('inputs')
    topics = log.get('topics')
    data = log.get('data')
    if not isinstance(inputs, list) or not isinstance(topics, list) or (not isinstance(data, str)):
        raise WorkerContractError('event fixture malformed')
    if not re.fullmatch('0x(?:[0-9a-fA-F]{64})*', data):
        raise WorkerContractError('event data malformed')
    topic_bytes = []
    for topic in topics:
        if not isinstance(topic, str) or not re.fullmatch('0x[0-9a-fA-F]{64}', topic):
            raise WorkerContractError('event topic malformed')
        topic_bytes.append(bytes.fromhex(topic[2:]))
    indexed_words = iter(topic_bytes[1:])
    data_bytes = bytes.fromhex(data[2:])
    if len(data_bytes) % 32:
        raise WorkerContractError('event data is not ABI-word aligned')
    data_words = iter((data_bytes[i:i + 32] for i in range(0, len(data_bytes), 32)))
    decoded: dict[str, Any] = {}
    for item in inputs:
        if not isinstance(item, Mapping) or not item.get('name') or (not item.get('type')):
            raise WorkerContractError('event input schema malformed')
        try:
            word = next(indexed_words if item.get('indexed') else data_words)
        except StopIteration as exc:
            raise WorkerContractError('event log has insufficient ABI words') from exc
        decoded[str(item['name'])] = _decode_word(str(item['type']), word)
    return {'event': str(schema.get('name') or 'UNKNOWN'), 'decoded': decoded, 'log_sha256': sha256_text(canonical_json(dict(log))), 'schema_sha256': sha256_text(canonical_json(dict(schema)))}

def verify_rpc_response(job: WorkerJob, *, chain_id: int, endpoint: str, method: str, response: Mapping[str, Any], block_number: int, block_hash: str, observed_at: str | None=None) -> Mapping[str, Any]:
    if chain_id not in job.allowed_chain_ids or not job.endpoint_allowed(chain_id, endpoint):
        raise WorkerContractError('RPC chain/endpoint outside frozen allowlist')
    assert_read_only_rpc_method(method)
    if response.get('jsonrpc') != '2.0' or 'error' in response or 'result' not in response:
        raise WorkerExecutionError('malformed/spoofed JSON-RPC response')
    if block_number < 0 or not re.fullmatch('0x[0-9a-fA-F]{64}', block_hash):
        raise WorkerExecutionError('invalid block provenance')
    return {'chain_id': chain_id, 'endpoint': sanitize_endpoint(endpoint), 'method': method, 'block_number': block_number, 'block_hash': block_hash.lower(), 'as_of': observed_at or _utc_now(), 'response_sha256': sha256_text(canonical_json(dict(response))), 'read_only': True}

class _NoRedirect(urllib_request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class ReadOnlyRpcClient:
    """Policy-bound JSON-RPC client. It has no write-method path and rejects redirects."""

    def __init__(self, job: WorkerJob, chain_id: int, endpoint: str, *, transport: Callable[[str, Sequence[Any]], tuple[Mapping[str, Any], str]] | None=None):
        if chain_id not in job.allowed_chain_ids or not job.endpoint_allowed(chain_id, endpoint):
            raise WorkerContractError('RPC chain/endpoint outside frozen allowlist')
        self.job = job
        self.chain_id = chain_id
        self.endpoint = endpoint.rstrip('/')
        self.transport = transport or self._http_transport

    def _http_transport(self, method: str, params: Sequence[Any]) -> tuple[Mapping[str, Any], str]:
        assert_read_only_rpc_method(method)
        payload = canonical_json({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}).encode('utf-8')
        req = urllib_request.Request(self.endpoint, data=payload, headers={'Content-Type': 'application/json', 'User-Agent': 'across-edge-atm-worker/1'}, method='POST')
        opener = urllib_request.build_opener(_NoRedirect)
        try:
            with opener.open(req, timeout=15) as response:
                final_url = response.geturl().rstrip('/')
                body = response.read(2 * 1024 * 1024 + 1)
                if len(body) > 2 * 1024 * 1024:
                    raise WorkerExecutionError('RPC response exceeds 2MiB limit')
        except (HTTPError, URLError, TimeoutError) as exc:
            raise WorkerExecutionError('read-only RPC request failed: ' + sanitize_text(exc)) from exc
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise WorkerExecutionError('RPC returned malformed JSON') from exc
        if not isinstance(parsed, Mapping):
            raise WorkerExecutionError('RPC returned non-object JSON')
        return (parsed, final_url)

    def _call(self, method: str, params: Sequence[Any]) -> Mapping[str, Any]:
        assert_read_only_rpc_method(method)
        response, final_url = self.transport(method, params)
        if final_url.rstrip('/') != self.endpoint:
            raise WorkerExecutionError('RPC redirect/host change rejected')
        if response.get('jsonrpc') != '2.0' or 'error' in response or 'result' not in response:
            raise WorkerExecutionError('malformed/spoofed JSON-RPC response')
        return response

    def query(self, method: str, params: Sequence[Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        assert_read_only_rpc_method(method)
        chain = self._call('eth_chainId', [])
        try:
            observed_chain = int(str(chain['result']), 16)
        except Exception as exc:
            raise WorkerExecutionError('RPC chainId response malformed') from exc
        if observed_chain != self.chain_id:
            raise WorkerExecutionError(f'RPC chain mismatch: expected {self.chain_id}, got {observed_chain}')
        response = self._call(method, params)
        block = self._call('eth_getBlockByNumber', ['latest', False])
        block_result = block.get('result')
        if not isinstance(block_result, Mapping):
            raise WorkerExecutionError('RPC latest block response malformed')
        try:
            block_number = int(str(block_result['number']), 16)
            block_hash = str(block_result['hash'])
        except Exception as exc:
            raise WorkerExecutionError('RPC block provenance malformed') from exc
        evidence = verify_rpc_response(self.job, chain_id=self.chain_id, endpoint=self.endpoint, method=method, response=response, block_number=block_number, block_hash=block_hash)
        return (response, evidence)

def operation_id(action: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(dict(action)))

def execute_actions(job: WorkerJob, journal: ExecutionJournal, target_root: str | Path, artifacts_root: str | Path, *, crash_at: str | None=None, deadline_monotonic: float | None=None) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    artifacts = Path(artifacts_root)
    artifacts.mkdir(parents=True, exist_ok=True)
    results: list[Mapping[str, Any]] = []
    chain_refs: list[Mapping[str, Any]] = []
    actions = list(job.structured_requirements.get('actions') or [])
    for index, action in enumerate(actions):
        if journal.cancellation_requested():
            journal.append_event('CANCELLED', boundary=f'before_action:{index}')
            raise WorkerCancelled('worker cancellation requested')
        if deadline_monotonic is not None and time.monotonic() > deadline_monotonic:
            journal.append_event('TIMEOUT', boundary=f'before_action:{index}')
            raise WorkerExecutionError('worker timeout exceeded')
        capability = str(action.get('capability') or '')
        if capability not in job.required_capabilities:
            raise WorkerContractError(f'action capability not frozen in required_capabilities: {capability}')
        op_id = operation_id(action)
        cached = journal.action_receipt(op_id)
        if cached is not None and cached.get('operation') != 'replace_text':
            results.append(cached)
            continue
        if crash_at == f'before_action:{index}':
            raise InjectedCrash(crash_at)
        if capability == 'sdk_client_repair':
            if action.get('operation') != 'replace_text':
                raise WorkerCannotHandle('sdk_client_repair currently supports bounded replace_text only')
            result = idempotent_replace(job, journal, target_root, path=str(action['path']), old=str(action['old']), new=str(action['new']))
            if crash_at == f'after_target_write:{index}':
                receipt_path = journal.root / 'actions' / f'{op_id}.json'
                if receipt_path.exists():
                    receipt_path.unlink()
                raise InjectedCrash(crash_at)
        elif capability == 'unsigned_transaction_validation':
            result = {'operation_id': op_id, 'operation': 'unsigned_transaction_validation', **validate_unsigned_transaction(job, action['transaction'])}
            journal.record_action(op_id, result)
        elif capability == 'fee_logic_verification':
            result = {'operation_id': op_id, 'operation': 'fee_logic_verification', **verify_fee_logic(action['inputs'])}
            journal.record_action(op_id, result)
        elif capability == 'relayer_reconciliation':
            result = {'operation_id': op_id, 'operation': 'relayer_reconciliation', **reconcile_relayer_fixture(action.get('deposits', []), action.get('fills', []))}
            journal.record_action(op_id, result)
        elif capability == 'event_log_decoding':
            result = {'operation_id': op_id, 'operation': 'event_log_decoding', **decode_event_fixture(action['schema'], action['log'])}
            journal.record_action(op_id, result)
        elif capability == 'chain_provenance':
            result = {'operation_id': op_id, 'operation': 'chain_provenance', **verify_rpc_response(job, chain_id=int(action['chain_id']), endpoint=str(action['endpoint']), method=str(action['method']), response=action['response'], block_number=int(action['block_number']), block_hash=str(action['block_hash']), observed_at=str(action.get('observed_at') or _utc_now()))}
            journal.record_action(op_id, result)
            chain_refs.append(result)
        elif capability == 'external_mutation_refusal':
            requested = str(action.get('requested_operation') or '').lower()
            if requested not in FORBIDDEN_EXTERNAL_ACTIONS:
                raise WorkerContractError('external_mutation_refusal fixture must name a prohibited operation')
            result = {'operation_id': op_id, 'operation': 'external_mutation_refusal', 'requested_operation': requested, 'status': 'CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY', 'external_mutation_performed': False}
            journal.record_action(op_id, result)
        else:
            raise WorkerCannotHandle(f'unsupported action capability: {capability}')
        if crash_at == f'after_action_receipt:{index}':
            raise InjectedCrash(crash_at)
        results.append(result)
        journal.progress('ACTION_COMPLETE', index=index, capability=capability, operation_id=op_id)
    patch_meta = capture_patch(target_root, artifacts / 'worker.patch')
    (artifacts / 'action-results.json').write_text(json.dumps(results, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    journal.progress('ARTIFACTS_CREATED', patch_sha256=patch_meta['sha256'], action_results=len(results))
    if crash_at == 'after_result_artifact':
        raise InjectedCrash(crash_at)
    return (results, chain_refs)

def scan_generated_artifacts(root: str | Path) -> Mapping[str, Any]:
    base = Path(root)
    scanned = 0
    for path in sorted((p for p in base.rglob('*') if p.is_file())):
        scanned += 1
        data = path.read_bytes()
        if b'\x00' in data:
            continue
        text = data.decode('utf-8', errors='ignore')
        for pattern in _SECRET_CONTENT_PATTERNS:
            if pattern.search(text):
                raise WorkerExecutionError(f'generated artifact secret scan rejected {path.relative_to(base)}')
    return {'status': 'PASS', 'files_scanned': scanned}

def build_artifact_hashes(root: str | Path) -> dict[str, str]:
    base = Path(root)
    hashes: dict[str, str] = {}
    for path in sorted((p for p in base.rglob('*') if p.is_file())):
        hashes[str(path.relative_to(base)).replace('\\', '/')] = sha256_file(path)
    return hashes

def run_worker_job(raw_job: Mapping[str, Any], *, worker_source_sha: str, target_source_checkout: str | Path, run_root: str | Path, canonical_checkout: str | Path | None=None, crash_at: str | None=None) -> Mapping[str, Any]:
    started_at = _utc_now()
    started_monotonic = time.monotonic()
    job = WorkerJob.from_mapping(raw_job)
    max_runtime = job.structured_requirements.get('max_runtime_seconds', 300)
    try:
        max_runtime_seconds = float(max_runtime)
    except (TypeError, ValueError) as exc:
        raise WorkerContractError('max_runtime_seconds must be numeric') from exc
    if not 0 < max_runtime_seconds <= 3600:
        raise WorkerContractError('max_runtime_seconds must be >0 and <=3600')
    deadline_monotonic = started_monotonic + max_runtime_seconds
    root = Path(run_root)
    journal = ExecutionJournal(root / 'state', job, worker_source_sha)
    existing = journal.final_result()
    if existing is not None:
        return existing
    journal.append_event('RECEIVE')
    journal.append_event('VALIDATE', status='PASS')
    journal.ack()
    if journal.cancellation_requested():
        journal.append_event('CANCELLED', boundary='after_ack')
        raise WorkerCancelled('worker cancellation requested')
    if time.monotonic() > deadline_monotonic:
        journal.append_event('TIMEOUT', boundary='after_ack')
        raise WorkerExecutionError('worker timeout exceeded')
    if crash_at == 'after_ack':
        raise InjectedCrash(crash_at)
    target = prepare_isolated_target(job, target_source_checkout, root / 'workspace', canonical_checkout=canonical_checkout)
    journal.progress('PREPARE_ISOLATED_TARGET', target_base_sha=job.target_base_sha)
    if crash_at == 'during_protocol_work':
        raise InjectedCrash(crash_at)
    action_results, chain_refs = execute_actions(job, journal, target, root / 'artifacts', crash_at=crash_at, deadline_monotonic=deadline_monotonic)
    checks: list[Mapping[str, Any]] = []
    for check in job.deterministic_checks:
        kind = str(check.get('kind') or '')
        if kind == 'file_contains':
            target_file = resolve_allowed_path(target, str(check['path']), job.allowed_paths)
            expected = str(check['text'])
            passed = target_file.is_file() and expected in target_file.read_text(encoding='utf-8')
            checks.append({'kind': kind, 'path': str(check['path']), 'passed': passed})
        elif kind == 'artifact_exists':
            artifact = (root / 'artifacts' / str(check['path'])).resolve()
            artifact_root = (root / 'artifacts').resolve()
            try:
                artifact.relative_to(artifact_root)
            except ValueError as exc:
                raise WorkerContractError('artifact check path escapes artifact root') from exc
            checks.append({'kind': kind, 'path': str(check['path']), 'passed': artifact.is_file()})
        else:
            raise WorkerCannotHandle(f'unsupported deterministic check: {kind}')
    if not all((item['passed'] for item in checks)):
        raise WorkerExecutionError('deterministic acceptance check failed')
    secret_scan = scan_generated_artifacts(root / 'artifacts')
    journal.progress('ARTIFACT_SECRET_SCAN', status=secret_scan['status'], files_scanned=secret_scan['files_scanned'])
    journal.progress('RESULT_READY', deterministic_checks=len(checks), action_results=len(action_results))
    patch_path = root / 'artifacts' / 'worker.patch'
    target_commit = _git(target, 'rev-parse', 'HEAD')
    result = WorkerResult(worker_id=WORKER_ID, worker_protocol_version=WORKER_PROTOCOL_VERSION, worker_source_sha=worker_source_sha, job_id=job.job_id, work_lease_id=job.work_lease_id, scope_hash=job.scope_hash, status='RESULT_READY', started_at=started_at, finished_at=_utc_now(), artifact_hashes=build_artifact_hashes(root / 'artifacts'), patch_sha256=sha256_file(patch_path) if patch_path.exists() else None, target_commit_sha=target_commit, test_results=tuple(checks), chain_evidence_refs=tuple(chain_refs), limitations=('read-only external protocol authority', 'no claim/submission/payment authority', 'target commands are not executed by the qualification worker; deterministic checks are worker-owned'), error_class=None)
    return journal.write_result(result)
