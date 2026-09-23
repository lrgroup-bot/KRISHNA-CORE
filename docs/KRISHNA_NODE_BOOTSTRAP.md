# KRISHNA Trusted Node Bootstrap

At install/startup KRISHNA may discover candidate KRISHNA nodes on the local Wi-Fi/LAN. Discovery never grants trust. The owner must authorize a node before transfer.

After authorization, KRISHNA compares content hashes and transfers only missing/changed portable artifacts. Knowledge stores, Project Brain artifacts, capability metadata and approved model assets can therefore be reused rather than relearned/redownloaded. Secrets, credentials, PID/runtime state, caches, temporary files and camera evidence are excluded by default.

Canonical flow: discover -> owner authorization -> inventory -> manifest comparison -> delta transfer -> SHA-256 verification -> machine-local regeneration -> acceptance -> node registration.

The bootstrap deliberately does not blindly clone an installation. Machine identity, certificates, ports, hardware configuration and secrets remain machine-specific. Remote/WAN enrollment requires a separately authenticated private transport.
