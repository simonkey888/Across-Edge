from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter_ns
from typing import Dict


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

@dataclass
class StageClock:
    wall_t0_utc: str = field(default_factory=utc_now)
    marks: Dict[str, int] = field(default_factory=dict)

    def mark(self, stage: str) -> int:
        if stage not in {"T0", "T1", "T2", "T3"}:
            raise ValueError(f"unknown timing stage: {stage}")
        now = perf_counter_ns()
        previous = [self.marks[s] for s in ("T0", "T1", "T2", "T3") if s in self.marks]
        if previous and now < previous[-1]:
            raise RuntimeError("monotonic clock moved backwards")
        self.marks[stage] = now
        return now

    def duration_ms(self, start: str, end: str) -> float | None:
        if start not in self.marks or end not in self.marks:
            return None
        return (self.marks[end] - self.marks[start]) / 1_000_000
