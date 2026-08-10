# Economics and evidence classes

Canonical Across `ProfitClient` is the source of truth for fill economics. The ORDER-002 instrumentation propagates, when available, 18-decimal USD fields: input/output amount USD, gross relayer fee USD, native-token fill cost USD, net relayer fee USD, LP fee percentage and selected repayment chain.

Across-Edge normalizes those values without replacing the canonical profitability decision. Rebalance cost is `UNKNOWN` unless it can be observed without financial execution. Capital required is represented by the canonical output-amount USD value for the candidate; future lock duration/rebalance path remain unknown until measurable.

Every economic field must be tagged as one of `OBSERVED_THIS_RUN`, `PRIMARY_SOURCE`, `DERIVED_CALCULATION`, `ASSUMPTION`, `HISTORICAL_PRIOR_RESEARCH`, or `UNKNOWN`. Missing components never become zero. Break-even scenarios are generated for $0/$5/$10/$20 monthly fixed infrastructure only when positive observed/derived net-per-fill exists.
