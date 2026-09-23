# Hardware-aware provisioning

KRISHNA provisions a trusted new node copy-first. If a verified peer copy is unavailable, interrupted beyond recovery, or fails final hash verification, the artifact may fall back to its approved canonical download source. Downloads must still satisfy KRISHNA's zero-paid-cloud policy and integrity/license rules.

Before provisioning, the node is classified from RAM, GPU VRAM, CPU cores and free disk into power, standard, light or minimal. Artifacts declare compatible profiles. A stronger machine may therefore receive larger local models, heavier vision/diagnostic workers and other approved high-capacity components; a weaker machine receives a smaller compatible set. Hardware capability does not weaken security/privacy/acceptance gates.

Canonical order: inventory -> classify -> select compatible artifact -> trusted peer copy -> verify -> on failure approved download -> verify -> install -> acceptance. Never silently download from an arbitrary URL discovered on the network.
