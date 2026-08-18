# ORDER-009 baseline

Generated: 2026-08-15T02:06:00Z

- Repository: `simonkey888/Across-Edge`
- Branch: `order-001-shadow-relayer`
- PR: `#2` (`OPEN / DRAFT / UNMERGED`)
- PR/branch HEAD before ORDER-009 edits: `59f5988163449ef5c0866c3a4b9cf52d45032a66`
- Main SHA: `044d195f134178b6127af5dd3f5ad7d660d32e54`
- Approved upstream pin: `741ca9f7d72923f7b13c1c2462ca90eba81e1a87`
- Current upstream `master` observed at baseline: `5b03620f761aefb988c62131ddfd1d6e7146549c`
- Canonical patch manifest SHA-256 before ORDER-009 edits: `1ff30ae3ce2a9a0d98f048e3e3ad019b489eeb46db0caa474c60d7a8be7d7c39`

Authority read before editing:
- Issue #8 / ORDER-009
- Issue #1 / ORDER-001
- Issue #1 comment `5235186743` / Amendment 001-A
- current `audit/EVIDENCE_INDEX.md`
- current PR #2 metadata

Active material defect from independent AUD: the canonical patch applies at the exact upstream pin but introduces TypeScript errors in `TransactionClient.ts` unsigned preparation and in economics field exposure from `ProfitClient.isFillProfitable()`.

Safety envelope remains unchanged: spend $0, no keys, no signing, no transactions, no write RPC, no on-chain value transfer, no merge, no main mutation, no upstream-pin change.
