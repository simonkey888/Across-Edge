# Upstream integration

Canonical pin: `across-protocol/relayer@741ca9f7d72923f7b13c1c2462ca90eba81e1a87`, default branch `master`, license `AGPL-3.0-only`, Node `>=22.18.0`.

Verified at that SHA: CLI accepts `--wallet void`; `SignerUtils` creates an ethers `VoidSigner`; `sendingRelaysEnabled` is true only for literal `SEND_RELAYS=true`; `runRelayer()` enters simulation if transaction or relay sending is disabled; canonical simulation is `TransactionClient.simulate/_simulate/willSucceed`; native `SpeedProvider`/`spray` exists; external/event-listener configuration exists.

Across-Edge pins upstream externally rather than copying its source tree. See `config/upstream-pin.json`.
