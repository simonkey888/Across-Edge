#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';

const ENTRYPOINT = 'tools/atm-worker-entrypoint.mjs';
const WORKER_ID = 'across-edge';
const WORKER_PROTOCOL = 'across-edge-worker/v1';

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

try {
  const specPath = required('ATM_JOB_SPEC_PATH');
  const resultPath = required('ATM_TASK_RESULT_PATH');
  const executionJobId = required('ATM_EXECUTION_JOB_ID');
  const workLeaseId = required('ATM_WORK_LEASE_ID');
  const atmScopeHash = required('ATM_SCOPE_HASH');
  const atmJobSpecHash = required('ATM_JOB_SPEC_HASH');
  const sourceSha = required('ATM_WORKER_SOURCE_SHA');
  if (process.env.ATM_MAX_SPEND_USD !== '0') fail('nonzero_spend_boundary', 20);
  if (!/^[0-9a-f]{40}$/.test(sourceSha)) fail('invalid_worker_source_sha', 21);

  const rawSpec = readFileSync(specPath, 'utf8');
  if (sha256Text(rawSpec) !== atmJobSpecHash) fail('atm_job_spec_hash_mismatch', 22);
  const spec = JSON.parse(rawSpec);
  if (!spec || typeof spec !== 'object' || Array.isArray(spec)) fail('atm_job_spec_not_object', 23);
  if (spec.scope_hash !== atmScopeHash) fail('atm_scope_hash_mismatch', 24);
  if (String(spec.max_spend_usd) !== '0') fail('atm_nonzero_spend', 25);
  if (String(spec.task_type || '') !== 'across_readonly_unsigned_tx_v1') fail('unsupported_atm_task_type', 26);
  if (spec.target_base_sha !== sourceSha) fail('target_base_must_equal_pinned_worker_source_for_integration_fixture', 27);
  if (spec.repository_or_input !== 'https://github.com/simonkey888/Across-Edge') fail('integration_fixture_target_mismatch', 28);

  const now = Date.now();
  const nativeJob = {
    schema_version: WORKER_PROTOCOL,
    job_id: String(spec.job_id),
    canonical_opportunity_id: String(spec.canonical_opportunity_id),
    worker_id: WORKER_ID,
    work_lease_id: workLeaseId,
    scope_hash: '',
    frozen_acceptance_criteria: { criteria: Array.isArray(spec.frozen_acceptance_criteria) ? spec.frozen_acceptance_criteria : [] },
    target_repository: String(spec.repository_or_input),
    target_base_sha: sourceSha,
    allowed_paths: ['src/across_edge_worker'],
    required_capabilities: ['unsigned_transaction_validation'],
    structured_requirements: {
      external_protocol_mutation: false,
      requested_chain_ids: [8453],
      requested_read_endpoints: [],
      actions: [{
        capability: 'unsigned_transaction_validation',
        transaction: {
          chain_id: 8453,
          to: '0x0000000000000000000000000000000000000001',
          data: '0x1234',
          value: 0,
        },
      }],
    },
    expected_deliverable: { kind: 'read_only_unsigned_transaction_validation', signing: false, broadcast: false },
    deterministic_checks: [{ kind: 'file_contains', path: 'src/across_edge_worker/capabilities.py', needle: 'VALID_AS_DATA_ONLY' }],
    allowed_chain_ids: [8453],
    allowed_read_endpoints: [],
    max_spend_usd: 0,
    lease_status: 'ACTIVE',
    lease_expires_at: new Date(now + 15 * 60 * 1000).toISOString(),
    timeout_seconds: 300,
  };
  const scopeMaterial = { ...nativeJob };
  delete scopeMaterial.scope_hash;
  nativeJob.scope_hash = sha256Json(scopeMaterial);

  const ioRoot = dirname(resultPath);
  const nativeRoot = join(ioRoot, 'across-native');
  const stateDir = join(ioRoot, 'across-native-state');
  const outputDir = join(ioRoot, 'across-native-output');
  mkdirSync(nativeRoot, { recursive: true });
  mkdirSync(stateDir, { recursive: true });
  mkdirSync(outputDir, { recursive: true });
  const nativeJobPath = join(nativeRoot, 'job.json');
  writeFileSync(nativeJobPath, canonicalJson(nativeJob) + '\n', { encoding: 'utf8', flag: 'wx' });

  const run = spawnSync(
    'python',
    ['-m', 'across_edge_worker.cli', 'run', '--job', nativeJobPath, '--state-dir', stateDir, '--output-dir', outputDir],
    { cwd: process.cwd(), env: process.env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] },
  );
  if (run.status !== 0) {
    process.stderr.write(String(run.stderr || run.stdout || 'across_native_worker_failed') + '\n');
    process.exit(run.status || 31);
  }
  const nativeResult = JSON.parse(String(run.stdout || '').trim().split(/\r?\n/).filter(Boolean).at(-1));
  const analysis = JSON.parse(readFileSync(join(outputDir, 'analysis.json'), 'utf8'));
  if (nativeResult.worker_id !== WORKER_ID || nativeResult.source_sha !== sourceSha) fail('across_native_source_binding_mismatch', 32);
  if (nativeResult.job_id !== String(spec.job_id) || nativeResult.work_lease_id !== workLeaseId) fail('across_native_execution_binding_mismatch', 33);
  if (nativeResult.scope_hash !== nativeJob.scope_hash) fail('across_native_scope_binding_mismatch', 34);
  if (nativeResult.status !== 'RESULT_READY' || nativeResult.outgoing_spend_usd !== 0) fail('across_native_result_not_ready_zero_spend', 35);
  if (nativeResult.authoritative_acceptance || nativeResult.paid || nativeResult.withdrawable || nativeResult.executed_onchain || nativeResult.payout_success) fail('across_native_authority_claim_forbidden', 36);
  if (analysis.external_mutation !== false || analysis.outgoing_spend_usd !== 0) fail('across_native_external_mutation_or_spend', 37);

  const observations = Array.isArray(analysis.outputs) ? analysis.outputs : [];
  const unsigned = observations.find((row) => row && row.capability === 'unsigned_transaction_validation');
  if (!unsigned || unsigned.observed?.status !== 'VALID_AS_DATA_ONLY' || unsigned.observed?.signed !== false || unsigned.observed?.executed !== false) fail('across_unsigned_validation_evidence_missing', 38);

  const inputBytes = Buffer.from(String(spec.repository_or_input), 'utf8');
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
    native_contract_hash: sha256Json(nativeJob),
    native_scope_hash: nativeJob.scope_hash,
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
  fail(error instanceof Error ? error.message : String(error), 40);
}
