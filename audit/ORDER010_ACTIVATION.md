# ORDER-010 activation candidate

This commit materializes the AUD-established runtime corrections on the existing Draft PR without changing `main` or the approved upstream pin.

Final static gates executed after the last source/patch representation change:
- Across-Edge pytest: **80 passed**.
- compileall: **PASS**.
- full committed-surface secret scan: **PASS**.
- safety runtime: **PASS**.
- pristine pinned-upstream fast typecheck: **PASS**.
- canonical runtime patch SHA-256: `33f1b17aaf67ab602c62a4e1a3801f61498a0be0453203dd4e5c8db2487ffd1a`.
- upstream regression overlay SHA-256: `fef471a7a967b363114edacc07e76e4088996415f854a2a21ba19f51d4038e40`.
- both Git binary patches apply/check cleanly to the pinned upstream; `git diff --check`: **PASS**.
- patched upstream fast typecheck: **PASS**.
- patched upstream build/emission: **PASS**, 616 emitted files.
- targeted upstream TransactionClient + ProfitClient tests: **34 passing**.

The compact Git binary runtime patch changes only seven required upstream `src/**` files. The separate SHA-bound overlay changes only the two targeted upstream test files. This preserves a small canonical runtime patch while retaining executable regression coverage.

Continuous activation remains strictly zero-write: void wallet, send flags false, no keys, no signing, no transactions, no paid RPC/infra.
