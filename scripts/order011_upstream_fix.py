#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

PINNED_UPSTREAM_SHA = "741ca9f7d72923f7b13c1c2462ca90eba81e1a87"
TARGET = Path("src/relayer/index.ts")
MARKER = "ACROSS_EDGE_MEMORY"

_START_BEFORE = '''      const tLoopStart = profiler.start("Relayer execution loop");
      const ready = await relayer.update();
'''
_START_AFTER = '''      const tLoopStart = profiler.start("Relayer execution loop");
      const acrossEdgeMemoryStart = process.memoryUsage();
      logger.info({
        at: "AcrossEdge::memory",
        message: "ACROSS_EDGE_MEMORY",
        phase: "start",
        loopCount: run,
        heapUsed: acrossEdgeMemoryStart.heapUsed,
        heapTotal: acrossEdgeMemoryStart.heapTotal,
        rss: acrossEdgeMemoryStart.rss,
      });
      const ready = await relayer.update();
'''

_END_BEFORE = '''        const runTimeMilliseconds = tLoopStart.stop({
          message: "Completed relayer execution loop.",
          loopCount: run,
        });
        if (!abortController.signal.aborted) {
'''
_END_AFTER = '''        const runTimeMilliseconds = tLoopStart.stop({
          message: "Completed relayer execution loop.",
          loopCount: run,
        });
        const acrossEdgeMemoryEnd = process.memoryUsage();
        logger.info({
          at: "AcrossEdge::memory",
          message: "ACROSS_EDGE_MEMORY",
          phase: "end",
          loopCount: run,
          heapUsed: acrossEdgeMemoryEnd.heapUsed,
          heapTotal: acrossEdgeMemoryEnd.heapTotal,
          rss: acrossEdgeMemoryEnd.rss,
        });
        if (!abortController.signal.aborted) {
'''


def _git_head(repo: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def apply_fix(repo: Path) -> Path:
    repo = repo.resolve()
    actual = _git_head(repo)
    if actual != PINNED_UPSTREAM_SHA:
        raise RuntimeError(f"upstream SHA mismatch: expected {PINNED_UPSTREAM_SHA}, got {actual}")
    target = repo / TARGET
    source = target.read_text()
    if source.count(MARKER) == 2:
        return target
    if MARKER in source:
        raise RuntimeError("partial ORDER-011 memory instrumentation detected")
    if source.count(_START_BEFORE) != 1 or source.count(_END_BEFORE) != 1:
        raise RuntimeError("pinned upstream loop anchors changed; refusing fuzzy instrumentation")
    source = source.replace(_START_BEFORE, _START_AFTER, 1).replace(_END_BEFORE, _END_AFTER, 1)
    if source.count(MARKER) != 2:
        raise RuntimeError("ORDER-011 memory instrumentation invariant failed")
    target.write_text(source)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_dir")
    args = parser.parse_args(argv)
    target = apply_fix(Path(args.upstream_dir))
    print(f"ORDER011_UPSTREAM_MEMORY_FIX=PASS target={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
