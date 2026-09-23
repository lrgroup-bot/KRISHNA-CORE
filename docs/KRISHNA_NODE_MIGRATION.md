# KRISHNA Node Migration Stack

The installer may discover KRISHNA peers on a local LAN, but data transfer starts only after owner authorization and trusted-node enrollment. Enrolled nodes have a durable non-secret fingerprint and role.

Migration is incremental: compare manifests, resume large file transfers, verify SHA-256, merge portable JSONL knowledge without duplicate records, select missing components/models according to hardware, regenerate machine-local identity/configuration, install services, run acceptance, then register READY.

Secrets and credentials are not copied by this layer. Secure secret provisioning must use the platform credential store or a separately authenticated encrypted channel. Network transport must be authenticated/encrypted before this stack is exposed beyond a trusted local bootstrap environment.

Knowledge remains explicit and portable: Gyan/Rishi/Project artifacts can be merged; hosted-model hidden weights or private provider state are not treated as transferable learning.
