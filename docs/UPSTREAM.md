# Upstream pin and license

- repository: `https://github.com/across-protocol/relayer`
- exact pin: `741ca9f7d72923f7b13c1c2462ca90eba81e1a87`
- package license at the pin: `AGPL-3.0-only`
- Node engine at the pin: `>=22.18.0`
- safe CLI: `yarn relay --wallet void`
- patch: `patches/across-relayer-order002-instrumentation.patch`
- patch SHA-256: `2f6633b67582fbe30d0a6d74573e2278657bdf27e9f57e9633eafbb861f30f45`

`verify_upstream_checkout()` fails closed unless both the origin identity and exact HEAD match. `apply_upstream_patch.py` validates the patch hash and uses `git apply --check`; a silently repinned checkout is rejected.

Across-Edge does not vendor the upstream source. The instrumentation patch is intended solely for the AGPL-3.0-only upstream and must be handled consistently with that upstream license. Any deployed modified upstream must provide corresponding source as required by AGPL.
