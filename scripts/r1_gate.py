from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


def _dt(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def sample(heartbeat: Path, history: Path, state: Path) -> int:
    if not heartbeat.is_file() or heartbeat.stat().st_size == 0:
        return 0
    try:
        payload = json.loads(heartbeat.read_text())
    except (OSError, json.JSONDecodeError):
        return 0
    timestamp = str(payload.get("last_heartbeat_utc") or "")
    if not timestamp:
        return 0
    previous = state.read_text().strip() if state.exists() else ""
    if timestamp == previous:
        return 0
    payload["_sampled_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    state.write_text(timestamp + "\n")
    return 0


def _healthy(sample: dict, head: str, pin: str) -> bool:
    return (
        sample.get("source_head") == head
        and sample.get("upstream_sha") == pin
        and sample.get("relayer_alive") is True
        and sample.get("observer_arbitrum_alive") is True
        and sample.get("observer_base_alive") is True
        and sample.get("send_relays") is False
        and sample.get("send_transactions") is False
        and sample.get("wallet") == "void"
        and sample.get("spend_usd") == 0
        and sample.get("private_keys") == 0
        and sample.get("signing") == 0
        and sample.get("transactions") == 0
        and sample.get("write_rpc") == 0
        and sample.get("onchain_value_transfer") == 0
    )


def verify(root: Path, out: Path, head: str, pin: str) -> int:
    out.mkdir(parents=True, exist_ok=True)
    histories = list(root.rglob("history.jsonl"))
    logs = list(root.rglob("activation.log"))
    metas = list(root.rglob("run-metadata.json"))
    records = list(root.rglob("shadow-records.jsonl"))
    errors: list[str] = []
    if len(histories) < 2:
        errors.append("missing_lane_history")
    if len(logs) < 2:
        errors.append("missing_activation_log")

    oom_count = 0
    memory_end: list[tuple[int, int, int, int]] = []
    memory_pattern = re.compile(
        r'"phase": "end".*?"loopCount": (\d+).*?"heapUsed": (\d+).*?"heapTotal": (\d+).*?"rss": (\d+)',
        re.S,
    )
    for path in logs:
        text = path.read_text(errors="replace")
        oom_count += len(re.findall(r"Reached heap limit|JavaScript heap out of memory", text))
        for match in memory_pattern.finditer(text):
            memory_end.append(tuple(map(int, match.groups())))
    if oom_count:
        errors.append("oom_persisted")
    if len(memory_end) < 10:
        errors.append("insufficient_memory_end_samples")
    heap_ceiling = int(2048 * 1024 * 1024 * 0.90)
    if memory_end and max(row[1] for row in memory_end) >= heap_ceiling:
        errors.append("heap_not_bounded_below_90pct_stopgap")

    intervals: list[tuple[float, float]] = []
    healthy_samples = 0
    for path in histories:
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        rows.sort(key=lambda row: _dt(row["_sampled_utc"]))
        healthy_samples += sum(_healthy(row, head, pin) for row in rows)
        for left, right in zip(rows, rows[1:]):
            start, end = _dt(left["_sampled_utc"]), _dt(right["_sampled_utc"])
            if _healthy(left, head, pin) and _healthy(right, head, pin) and 0 < end - start <= 90:
                intervals.append((start, end))
    intervals.sort()
    merged: list[list[float]] = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    continuous = max((end - start for start, end in merged), default=0.0)
    if continuous < 21600:
        errors.append("continuous_healthy_coverage_lt_21600")

    fingerprints: list[str] = []
    for path in metas:
        try:
            value = json.loads(path.read_text()).get("config_fingerprint_sha256")
        except (OSError, json.JSONDecodeError):
            value = None
        if value:
            fingerprints.append(str(value))
    if len(fingerprints) < 2 or len(set(fingerprints)) != 1:
        errors.append("config_fingerprint_mismatch")

    best: dict[tuple[str, str], tuple[int, dict]] = {}
    for path in records:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            economics = row.get("economics") or {}
            decision = str(row.get("profitability_decision") or "UNKNOWN")
            net = economics.get("net_relayer_fee_usd_wei")
            if decision in {"", "UNKNOWN", "None"} or net in {None, "UNKNOWN"}:
                continue
            identity = (
                str(row.get("deposit_key") or ""),
                str(
                    row.get("deposit_version_fingerprint")
                    or row.get("upstream_trace_id")
                    or row.get("evaluation_attempt_id")
                    or ""
                ),
            )
            if not all(identity):
                errors.append("economic_row_missing_dedup_identity")
                continue
            score = sum(value not in {None, "UNKNOWN", ""} for value in economics.values())
            score += sum(row.get(field) is not None for field in ("t1_monotonic_ns", "t2_monotonic_ns", "t3_monotonic_ns"))
            if identity not in best or score > best[identity][0]:
                best[identity] = (score, row)

    economic_rows = [entry[1] for entry in best.values()]
    evaluations = len(economic_rows)
    profitable = sum(str(row.get("profitability_decision")) == "profitable" for row in economic_rows)
    net_ev = Decimal(0)
    for row in economic_rows:
        try:
            net_ev += Decimal(str((row.get("economics") or {})["net_relayer_fee_usd_wei"])) / Decimal(10**18)
        except (KeyError, InvalidOperation, ValueError):
            errors.append("invalid_net_ev_value")

    if "oom_persisted" in errors or "heap_not_bounded_below_90pct_stopgap" in errors:
        status = "STOP_ROUTE"
    elif any(
        error in errors
        for error in (
            "continuous_healthy_coverage_lt_21600",
            "missing_lane_history",
            "missing_activation_log",
            "config_fingerprint_mismatch",
        )
    ):
        status = "BLOCKED_REAL"
    elif evaluations < 10:
        status = "STOP_ROUTE"
    elif profitable >= 2 and net_ev > 0:
        status = "GO_FOR_BOUNDED_LIVE_DESIGN"
    elif evaluations >= 20 and profitable == 0:
        status = "STOP_ROUTE"
    else:
        status = "BLOCKED_REAL"

    payload = {
        "order": "ORDER-011-R1",
        "status": status,
        "source_head": head,
        "upstream_pin": pin,
        "continuous_healthy_coverage_seconds": continuous,
        "oom_count": oom_count,
        "memory_end_samples": len(memory_end),
        "max_heap_used_bytes": max((row[1] for row in memory_end), default=None),
        "healthy_samples": healthy_samples,
        "economic_evaluations_deduped": evaluations,
        "profitable_count": profitable,
        "aggregate_net_ev_usd": str(net_ev),
        "config_fingerprints": fingerprints,
        "errors": sorted(set(errors)),
        "safety": {
            "authorized_spend_usd": 0,
            "authorized_capital_at_risk_usd": 0,
            "private_keys": 0,
            "signing": 0,
            "transaction_broadcast": 0,
            "onchain_value_transfer": 0,
            "write_rpc": 0,
            "wallet": "void",
            "send_relays": False,
            "send_transactions": False,
        },
    }
    (out / "ORDER011_R1_FINAL.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (out / "terminal.txt").write_text(f"ORDER_011_R1_STATUS={status}\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 2 if status == "BLOCKED_REAL" else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sampler = sub.add_parser("sample")
    sampler.add_argument("--heartbeat", type=Path, required=True)
    sampler.add_argument("--history", type=Path, required=True)
    sampler.add_argument("--state", type=Path, required=True)
    verifier = sub.add_parser("verify")
    verifier.add_argument("--root", type=Path, required=True)
    verifier.add_argument("--out", type=Path, required=True)
    verifier.add_argument("--head", required=True)
    verifier.add_argument("--pin", required=True)
    args = parser.parse_args()
    if args.command == "sample":
        return sample(args.heartbeat, args.history, args.state)
    return verify(args.root, args.out, args.head, args.pin)


if __name__ == "__main__":
    raise SystemExit(main())
