# ORDER-004 speed-up/version provenance

Approved relayer pin: `across-protocol/relayer@741ca9f7d72923f7b13c1c2462ca90eba81e1a87`.

The pinned relayer imports `isDepositSpedUp`, `resolveDepositMessage`, and related deposit utilities in `src/relayer/Relayer.ts`. At the pinned source, speed-up handling materially uses `updatedRecipient` for the effective recipient and `updatedOutputAmount` for the effective output amount. The pinned relayer also depends on `@across-protocol/sdk@4.4.18`.

The exact SDK v4.4.18 implementation in `src/arch/evm/SpokeUtils.ts` defines the updated-fill path as `fillRelayWithUpdatedDeposit` and passes these update fields: `updatedOutputAmount`, `updatedRecipient`, `updatedMessage`, and `speedUpSignature`. The ordinary relay data also includes `depositor`, `recipient`, `inputToken`, `outputToken`, `inputAmount`, `outputAmount`, `originChainId`, `depositId`, `fillDeadline`, `exclusivityDeadline`, `message`, and `exclusiveRelayer`.

| Field | Source | Canonical role | Identity effect |
|---|---|---|---|
| `updatedOutputAmount` | relayer `Relayer.ts`; SDK v4.4.18 `SpokeUtils.ts` | effective fill output after speed-up | MUST distinguish a materially updated deposit version |
| `updatedRecipient` | relayer `Relayer.ts`; SDK v4.4.18 `SpokeUtils.ts` | effective destination recipient | MUST distinguish a materially updated deposit version |
| `updatedMessage` | SDK v4.4.18 `SpokeUtils.ts` | message used by updated fill | MUST distinguish a materially updated deposit version |
| `speedUpSignature` | SDK v4.4.18 `SpokeUtils.ts` | authorization for updated fill | MUST distinguish update authorization/version |
| original relay data | SDK v4.4.18 `SpokeUtils.ts` | base relay identity and calldata inputs | forms the base deposit/version fingerprint |
| `message` / resolved message | relayer `Relayer.ts` | message support/filtering | material to evaluation where message changes |
| `fillDeadline`, `exclusivityDeadline` | SDK v4.4.18 `SpokeUtils.ts` | relay timing constraints | material to evaluation state |

Across-Edge therefore fingerprints the canonical base/update fields when all update fields are observed. When update provenance is incomplete, it deliberately assigns a conservative unique version identity per evaluation attempt and marks provenance `PARTIAL_UNKNOWN_UPDATE_PROVENANCE`; it does not guess missing upstream semantics.

This document is provenance evidence, not a claim that the pinned upstream runtime was executed in the current sandbox.
