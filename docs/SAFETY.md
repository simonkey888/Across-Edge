# Safety envelope

ORDER-001 is zero-spend and zero-capital-at-risk. Code rejects real secret variables, requires `--wallet void`, rejects true send flags, allow-lists read-only RPC methods, and exposes only a broadcaster stub that raises `LIVE_EXECUTION_PROHIBITED_BY_ORDER_001`.

No registration/nomination write, exchange credential, swap/rebalance, paid RPC/compute, transaction broadcast, gas spend, token purchase, funded wallet, or value transfer is authorized. `tests/test_safety.py` proves key/send/wallet/RPC-write failures. `scripts/secret_scan.py` performs a dependency-free repository scan.
