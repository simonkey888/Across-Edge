#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';

const ENTRYPOINT = 'tools/atm-worker-entrypoint.mjs';
const WORKER_ID = 'across-edge';
const WORKER_PROTOCOL = 'across-edge-worker/v1';
const CHAIN_ID = 8453;
let leaseExpiresMs = 0;

function required(name) {
  const value = String(process.env[name] || '').trim();
  if (!value) throw new Error(`missing_${name}`);
  return value;
}
function normalize(value) {
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === 'object') {
    const out = {};
    for (const key of Object.keys(value).sort()) out[key] = normalize(value[key]);
    return out;
  }
  return value;
}
function canonicalJson(value) { return JSON.stringify(normalize(value)); }
function sha256Text(value) { return createHash('sha256').update(value).digest('hex'); }
function sha256Json(value) { return sha256Text(canonicalJson(value)); }
function fail(message, code = 30) { process.stderr.write(String(message) + '\n'); process.exit(code); }
function remainingMs(capMs) {
  const remaining = leaseExpiresMs - Date.now();
  if (!Number.isFinite(remaining) || remaining <= 0) fail('atm_work_lease_expired', 18);
  return Math.max(1, Math.min(Number(capMs), Math.floor(remaining)));
}
function boundedSpawn(command, args, options, capMs) {
  const run = spawnSync(command, args, { ...options, timeout: remainingMs(capMs) });
  if (run.error?.code === 'ETIMEDOUT') fail('atm_work_lease_expired_or_subprocess_timeout', 18);
  if (Date.now() >= leaseExpiresMs) fail('atm_work_lease_expired_after_subprocess', 18);
  return run;
}
function normalizeRepo(value) {
  let text = String(value || '').trim();
  if (text.endsWith('.git')) text = text.slice(0, -4);
  return text.replace(/\/$/, '');
}
function git(args, cwd) {
  const p = boundedSpawn('git', args, { cwd, env: process.env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }, 180000);
  if (p.status !== 0) fail(String(p.stderr || p.stdout || 'git_failed'), 29);
  return String(p.stdout || '').trim();
}
function targetStaticCheck(spec) {
  const rows = Array.isArray(spec.deterministic_checks) ? spec.deterministic_checks : [];
  const raw = rows.find((value) => String(value).startsWith('target_json_parse:'));
  if (!raw) fail('target_json_parse_check_required', 30);
  const path = String(raw).slice('target_json_parse:'.length).trim();
  if (!path || !Array.isArray(spec.allowed_paths) || !spec.allowed_paths.includes(path)) fail('target_json_parse_outside_allowed_paths', 31);
  return { kind: 'json_parse', path };
}

try {
  const specPath = required('ATM_JOB_SPEC_PATH');
  const resultPath = required('ATM_TASK_RESULT_PATH');
  const executionJobId = required('ATM_EXECUTION_JOB_ID');
  const workLeaseId = required('ATM_WORK_LEASE_ID');
  const leaseExpiresAt = required('ATM_WORK_LEASE_EXPIRES_AT');
  const atmScopeHash = required('ATM_SCOPE_HASH');
  const atmJobSpecHash = required('ATM_JOB_SPEC_HASH');
  const sourceSha = required('ATM_WORKER_SOURCE_SHA');
  leaseExpiresMs = Date.parse(leaseExpiresAt);
  if (!Number.isFinite(leaseExpiresMs) || leaseExpiresMs <= Date.now()) fail('invalid_or_expired_atm_work_lease', 18);
  if (process.env.ATM_MAX_SPEND_USD !== '0') fail('nonzero_spend_boundary', 20);
  if (!/^[0-9a-f]{40}$/.test(sourceSha)) fail('invalid_worker_source_sha', 21);

  const rawSpec = readFileSync(specPath, 'utf8');
  if (sha256Text(rawSpec) !== atmJobSpecHash) fail('atm_job_spec_hash_mismatch', 22);
  const spec = JSON.parse(rawSpec);
  if (!spec || typeof spec !== 'object' || Array.isArray(spec)) fail('atm_job_spec_not_object', 23);
  if (spec.scope_hash !== atmScopeHash) fail('atm_scope_hash_mismatch', 24);
  if (String(spec.max_spend_usd) !== '0') fail('atm_nonzero_spend', 25);
  if (String(spec.task_type || '') !== 'across_readonly_unsigned_tx_v1') fail('unsupported_atm_task_type', 26);
  const targetRepository = String(spec.repository_or_input || '').trim();
  const targetBaseSha = String(spec.target_base_sha || '').trim();
  if (!targetRepository.startsWith('https://github.com/')) fail('target_repository_must_be_public_github_https', 27);
  if (!/^[0-9a-f]{40}$/.test(targetBaseSha)) fail('target_base_sha_required_exact', 28);
  if (!Array.isArray(spec.allowed_paths) || spec.allowed_paths.length === 0) fail('allowed_paths_required', 29);
  const staticCheck = targetStaticCheck(spec);

  const ioRoot = dirname(resultPath);
  const nativeRoot = join(ioRoot, 'across-native');
  const stateDir = join(ioRoot, 'across-native-state');
  const outputDir = join(ioRoot, 'across-native-output');
  const preflightTarget = join(ioRoot, 'across-target-preflight');
  mkdirSync(nativeRoot, { recursive: true });
  mkdirSync(stateDir, { recursive: true });
  mkdirSync(outputDir, { recursive: true });

  git(['clone', '--no-checkout', '--filter=blob:none', targetRepository, preflightTarget], ioRoot);
  git(['fetch', '--depth=1', 'origin', targetBaseSha], preflightTarget);
  git(['checkout', '--detach', targetBaseSha], preflightTarget);
  const checkedOutHead = git(['rev-parse', 'HEAD'], preflightTarget);
  if (checkedOutHead !== targetBaseSha) fail('across_target_base_mismatch', 32);
  const checkedOutRemote = normalizeRepo(git(['config', '--get', 'remote.origin.url'], preflightTarget));
  if (checkedOutRemote !== normalizeRepo(targetRepository)) fail('across_target_repository_mismatch', 33);

  const targetIdentity = `${normalizeRepo(targetRepository)}@${targetBaseSha}`;
  const targetDigest = sha256Text(targetIdentity);
  const unsignedTransaction = {
    chain_id: CHAIN_ID,
    to: `0x${targetBaseSha.slice(0, 40)}`,
    data: `0x${targetDigest}`,
    value: 0,
  };

  const nativeTimeoutMs = remainingMs(300000);
  const nativeJob = {
    schema_version: WORKER_PROTOCOL,
    job_id: String(spec.job_id),
    canonical_opportunity_id: String(spec.canonical_opportunity_id),
    worker_id: WORKER_ID,
    work_lease_id: workLeaseId,
    scope_hash: '',
    frozen_acceptance_criteria: {
      criteria: Array.isArray(spec.frozen_acceptance_criteria) ? spec.frozen_acceptance_criteria : [],
      authority: 'ATM_INDEPENDENT_CHECKER_ONLY',
    },
    target_repository: targetRepository,
    target_base_sha: targetBaseSha,
    allowed_paths: [...spec.allowed_paths],
    required_capabilities: ['unsigned_transaction_validation'],
    structured_requirements: {
      external_protocol_mutation: false,
      requested_chain_ids: [CHAIN_ID],
      requested_read_endpoints: [],
      actions: [{ capability: 'unsigned_transaction_validation', transaction: unsignedTransaction }],
    },
    expected_deliverable: {
      kind: 'read_only_unsigned_transaction_validation',
      signing: false,
      broadcast: false,
      write_rpc: false,
    },
    deterministic_checks: [staticCheck],
    allowed_chain_ids: [CHAIN_ID],
    allowed_read_endpoints: [],
    max_spend_usd: 0,
    lease_status: 'ACTIVE',
    lease_expires_at: leaseExpiresAt,
    timeout_seconds: Math.max(1, Math.min(300, Math.floor(nativeTimeoutMs / 1000))),
  };
  const scopeMaterial = { ...nativeJob };
  delete scopeMaterial.scope_hash;
  nativeJob.scope_hash = sha256Json(scopeMaterial);
  const nativeJobPath = join(nativeRoot, 'job.json');
  writeFileSync(nativeJobPath, canonicalJson(nativeJob) + '\n', { encoding: 'utf8', flag: 'wx' });

  const run = boundedSpawn(
    'python',
    ['-m', 'across_edge_worker.cli', 'run', '--job', nativeJobPath, '--state-dir', stateDir, '--output-dir', outputDir],
    {
      cwd: process.cwd(),
      env: { ...process.env, ACROSS_EDGE_WORKER_SOURCE_SHA: sourceSha },
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    },
    nativeTimeoutMs,
  );
  if (run.status !== 0) {
    process.stderr.write(String(run.stderr || run.stdout || 'across_native_worker_failed') + '\n');
    process.exit(run.status || 34);
  }
  const nativeResult = JSON.parse(String(run.stdout || '').trim().split(/\r?\n/).filter(Boolean).at(-1));
  const analysis = JSON.parse(readFileSync(join(outputDir, 'analysis.json'), 'utf8'));
  if (nativeResult.worker_id !== WORKER_ID || nativeResult.source_sha !== sourceSha) fail('across_native_source_binding_mismatch', 35);
  if (nativeResult.job_id !== String(spec.job_id) || nativeResult.work_lease_id !== workLeaseId) fail('across_native_execution_binding_mismatch', 36);
  if (nativeResult.scope_hash !== nativeJob.scope_hash) fail('across_native_scope_binding_mismatch', 37);
  if (nativeResult.status !== 'RESULT_READY' || nativeResult.outgoing_spend_usd !== 0) fail('across_native_result_not_ready_zero_spend', 38);
  if (nativeResult.authoritative_acceptance || nativeResult.paid || nativeResult.withdrawable || nativeResult.executed_onchain || nativeResult.payout_success) fail('across_native_authority_claim_forbidden', 39);
  if (analysis.external_mutation !== false || analysis.outgoing_spend_usd !== 0) fail('across_native_external_mutation_or_spend', 40);
  if (normalizeRepo(analysis.target_repository) !== normalizeRepo(targetRepository) || analysis.target_base_sha !== targetBaseSha) fail('across_native_target_binding_mismatch', 41);

  const observations = Array.isArray(analysis.outputs) ? analysis.outputs : [];
  const unsigned = observations.find((row) => row && row.capability === 'unsigned_transaction_validation');
  if (!unsigned || unsigned.observed?.status !== 'VALID_AS_DATA_ONLY' || unsigned.observed?.chain_id !== CHAIN_ID || unsigned.observed?.signed !== false || unsigned.observed?.executed !== false) fail('across_unsigned_validation_evidence_missing', 42);
  if (unsigned.observed?.to !== unsignedTransaction.to.toLowerCase() || unsigned.observed?.data_bytes !== 32 || unsigned.observed?.value !== 0) fail('across_unsigned_validation_target_derived_mismatch', 43);
  const checks = Array.isArray(analysis.checks) ? analysis.checks : [];
  if (checks.length !== 1 || checks[0]?.kind !== staticCheck.kind || checks[0]?.path !== staticCheck.path || checks[0]?.passed !== true) fail('across_target_static_check_missing', 44);
  if (analysis.project_hash_before !== analysis.project_hash_after) fail('across_worker_checkout_mutated', 45);
  if (Date.now() >= leaseExpiresMs) fail('atm_work_lease_expired_before_result', 18);

  const inputBytes = Buffer.from(targetIdentity, 'utf8');
  const taskResult = {
    schema: 'ATM_TASK_RESULT_V1',
    execution_job_id: executionJobId,
    work_lease_id: workLeaseId,
    scope_hash: atmScopeHash,
    job_spec_hash: atmJobSpecHash,
    task_type: String(spec.task_type),
    producer: {
      worker_id: WORKER_ID,
      worker_source_sha: sourceSha,
      worker_entrypoint: ENTRYPOINT,
      native_entrypoint: 'python -m across_edge_worker.cli',
      native_protocol: WORKER_PROTOCOL,
    },
    bridge_target: {
      repository: normalizeRepo(targetRepository),
      target_base_sha: targetBaseSha,
      checked_out_head: checkedOutHead,
      allowed_paths: [...spec.allowed_paths],
      deterministic_check: staticCheck,
    },
    native_contract_hash: sha256Json(nativeJob),
    native_scope_hash: nativeJob.scope_hash,
    native_transaction_hash: sha256Json(unsignedTransaction),
    native_worker_result_hash: sha256Json(nativeResult),
    native_analysis_hash: sha256Json(analysis),
    native_worker_result: nativeResult,
    native_analysis: analysis,
    task_output: {
      kind: 'SHA256_UTF8_INPUT_V1',
      sha256: sha256Text(inputBytes),
      byte_length: inputBytes.length,
    },
    outgoing_spend_usd: 0,
  };
  writeFileSync(resultPath, canonicalJson(taskResult) + '\n', { encoding: 'utf8', flag: 'wx' });
  process.exit(0);
} catch (error) {
  fail(error instanceof Error ? error.message : String(error), 50);
}
