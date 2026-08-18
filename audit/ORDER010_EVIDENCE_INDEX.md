# ORDER-010 evidence index

Static source-bound verification committed under `evidence/ORDER010_FINAL/`:
- `pytest.log`
- `compileall.txt`
- `secret_scan.txt`
- `safety.txt`
- `patch_integrity.txt`
- `upstream_clean_typecheck.log`
- `upstream_typecheck.txt`
- `upstream_build.txt`
- `upstream_tests.txt`
- `runtime_profile.json`
- `static_verification.json`

Dynamic liveness/qualification files are intentionally written by the persistent runtime after the final commit so they bind to the actual final source HEAD without requiring another source mutation: `identity.txt`, `heartbeat.json`, `watchdog.json`, `qualification.json`, `final_status.json`.
