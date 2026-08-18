# REMOTE_TRUTH — ORDER-WR-004-P1

Observed 2026-08-18T09:27:00Z.

- Control order: https://github.com/simonkey888/ATM-Agent-Teller-Machine/issues/28
- Project order: https://github.com/simonkey888/Across-Edge/issues/11
- `main`: `044d195f134178b6127af5dd3f5ad7d660d32e54`
- Standalone relayer/shadow branch: `order-001-shadow-relayer`
- Standalone relayer PR: https://github.com/simonkey888/Across-Edge/pull/2
- Relayer branch HEAD frozen for worker stack at issuance: `8a70960d838880c9735fcfb405b04bca0b4f4061`
- Relayer qualification remains ORDER-011 / Issue #10 and is not an ATM worker acceptance input.
- Pinned Across relayer upstream: `741ca9f7d72923f7b13c1c2462ca90eba81e1a87`
- Relayer safety at frozen base: `wallet=void`, `send_relays=false`, `send_transactions=false`.
- Dedicated worker branch: `worker/order-wr-004-readiness-r1`.
- Worker PR is stacked on the relayer branch so worker code can reuse validated project logic without adding commits to PR #2.

G0:

```text
ACROSS_EDGE_SHADOW_RESEARCH_CONTINUES=YES
ATM_WORKER_MODE_SEPARATE=YES
CURRENT_RELAYER_AUTHORITY_UNCHANGED=YES
OUTGOING_SPEND_USD=0
```
