# Incident rules

Stop immediately if a send flag becomes true, a non-void wallet or secret is requested, any `eth_send*`/non-allow-listed RPC path appears, an endpoint may incur charge, observer replay/reorg corrupts keys, or simulation semantics diverge. Preserve non-secret evidence, mark the run invalid, do not broaden permissions, and escalate to AUD/owner.
