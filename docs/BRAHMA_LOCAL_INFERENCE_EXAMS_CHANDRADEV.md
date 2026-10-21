# BRAHMA, Rishis, local Ollama and CHANDRADEV — integration gates

Changes are committed to draft PR #229. None of these commits deploys a binary or changes the user's existing Windows data.

## Responsibilities

- KRISHNA sets and authorizes scope; it does not own browser tabs or run inference for all nodes.
- BRAHMA maintains existing approved work and an inexpensive, resource-guarded Rishi exam schedule. This schedule creates assignments, not grades or claimed understanding.
- BRAHMAGYAN holds the authoritative L0–L8 evidence/claim/exam records. Received fleet collection receipts are unverified candidates; a SHA-256 alone is not factual proof.
- The registered Rishi/Acharya Council selects subject experts, authors difficult theory/practical tests and separately reviews results. Profiles are logical model roles, not 35 simultaneously running model processes.
- SURYADEV nodes are owner-paired collectors of approved URLs, captions and local book indexes; node counts do not divide the Rishi Council into static ownership partitions.
- CHANDRADEV adds independent, read-only fleet health assessment to its existing camera/QC duties. Missing GPU utilization or thermal sensors remain explicitly unknown.

## Dedicated private Ollama host

Install Ollama and a model manually on a separate owner-controlled inference PC before activation. The new script does not pull/download models or depend on cloud APIs.
Run standalone/brahma/local_ollama_gateway.py with --bind, --port, --cert, --key, --token-file and --model. Example conceptual invocation:

    python standalone/brahma/local_ollama_gateway.py --bind 192.168.0.33 --port 18787 --cert C:/secure/brahma.crt --key C:/secure/brahma.key --token-file C:/secure/brahma-token.txt --model qwen3.5:4b

Use the actual PC IP and operator-created files instead of the example. Gateway binds only RFC1918 LAN/loopback, requires long token + HTTPS and only calls 127.0.0.1:11434/api/generate with authorized installed model IDs. No public service or arbitrary shell/network action exists.

Configure KRISHNA_BRAHMA_LOCAL_INFERENCE_CONFIG to point to an operator-owned JSON file using schema krishna.brahma.local-inference.v1 with endpoint (private HTTPS origin), cert_sha256 (DER leaf certificate SHA-256), token_file, model. The secret and certificate private key must NEVER be added to GitHub.

## Exam workflow

1. Existing BRAHMA idle consolidation tick schedules due Rishi assignments when source/claim evidence exists. It does not make model calls on the KRISHNA PC.
2. Local-only GET /api/brahma/exams/schedule shows due assignments. The issuer and reviewer are distinct Council members.
3. Local-only POST /api/brahma/exams/draft with assignment_id asks the dedicated gateway for structured difficult questions based only on actual BRAHMAGYAN claim source references. Malformed output and invented source links are rejected.
4. Local-only POST /api/brahma/exams/issue requires explicit issuer_approved:true and the draft proposal; original references are verified again before BRAHMAGYAN records the exam.
5. A different Council specialist evaluates actual submitted responses and practical artifacts. An AI persona is NOT cryptographic proof of examiner independence. A passing recorded grade is NOT proof of physical tests unless its artifacts are independently reproduced.
6. Recorded passes schedule 1-, 7- and 30-day recall tasks from the actual exam date, not arbitrary fake completion times.

## 85 percent and evidence

The 85% threshold is an admission/throttle limit, not an OS-level hard CPU/RAM/GPU cap. The fleet client reports measured CPU/RAM/disk and cached real Windows CPU/GPU identities where available. Unsupported GPU load and temperatures are unknown. No unapproved source URLs or full-video downloads are initiated by the new modules.

## Still required before merge/pull

- CI green on the same head: Core Windows/Linux, standalone Windows/Linux, browser and security smoke.
- Real two-PC paired TLS setup, source approval comparisons, power-loss/lease-expiration recovery, long-running 85%-guard observation, and a dedicated GPU/CPU inference-host benchmark.
- Authenticated reviewer attestations and deterministic physical/simulated lab evaluations; never count an LLM assertion as an actual experiment.
- Finite approved source catalogue can be exhausted. Expanding research coverage requires owner authorization; no infinite unique collection is promised.
- No automatic production installation or EXE build until the original browser-first acceptance policy and owner approval gates pass.