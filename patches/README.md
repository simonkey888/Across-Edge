# Upstream instrumentation policy

Do not vendor or silently modify canonical upstream. Any later exact T0/T1/T2/T3 source hook must be a thin patch against the pinned SHA with file/function anchors in `docs/PIPELINE.md`. No live submission code belongs here under ORDER-001.
