# SURYADEV connection-first bootstrap

The paired laptop connects before it has a learning plan. Do not create an empty
learning-plan.json to unlock connection. Pairing, source approval, evidence
collection and BRAHMAGYAN acceptance are separate states.

## Protocol

1. The dashboard launches its single locked worker with the existing paired Core
   configuration even when the plan is absent. No learning scheduler or model
   inference is started during connection bootstrap.
2. The worker uses the existing pinned-leaf TLS transport and device token for
   POST /api/suryadev/device/heartbeat. The credential is sent only after the pin
   matches. It advertises worker_running=false and awaiting_approved_plan with
   zero queued/running work and no hardware capacity. Only a matching accepted
   device response produces the authenticated heartbeat receipt.
3. After that acknowledgement, POST /api/suryadev/learning-plan/request requests
   the plan. This newly implemented route is restricted by the native TLS route
   allowlist, private remote policy and existing paired-device authentication.
   Core additionally requires a fresh authenticated heartbeat (150 seconds).
4. Core reads its existing operator-curated mission-authority/approved-curriculum.json
   under the SURYADEV runtime state. A missing catalogue returns
   awaiting_owner_approved_plan. Invalid or oversized catalogues fail closed.
   The route never creates approvals or discovers sources. The response contains
   exact catalogue URLs, validated mission approval evidence and a canonical
   SHA-256 delivery identifier, bound to the requesting device.
5. The laptop checks identity, schema, digest, nonempty exact source approvals,
   HTTPS source syntax, no literal private IPs, 1..300 URLs, no delegated hosts,
   no feeds/transcript permissions, and conservative quotas (5 intake / 75 queued).
   It validates staged bytes with the existing plan reader, flushes them and
   records exclusive, content-addressed delivery evidence including the TLS pin.
   Atomic publication refuses to replace an existing owner plan. The receiver
   deletes only its own newly created staging file. Pairing files, historical
   evidence and existing learning files are retained.
6. Only a valid plan permits entry into the existing learning scheduler. Existing
   acquisition IP/DNS validation, deduplication, immutable source evidence, fleet
   leases, local model restrictions and 85 percent admission guards still apply.
   Delivery and heartbeat never claim knowledge or Rishi/BRAHMAGYAN acceptance.

Connection failure, unsupported routes, bad approval evidence or invalid plans
leave learning disabled and retry every 20 seconds. Heartbeats continue while
waiting. An existing local owner plan is preserved and validated after the first
accepted heartbeat. Automatic remote replacement/revocation is outside this
initial-delivery protocol; an existing owner plan remains a durable local grant.
Hash-addressed evidence detects changes; it is not hardware-enforced WORM storage.

## Rollout and validation

Deploy both the Core source changes and the rebuilt full laptop package. Restart
Core using its existing state, pairing store, TLS certificate/key and binding.
Do not reprovision credentials or change the certificate pin. The laptop retries
without a new pairing or placeholder plan. The Core operator must supply the
actual approved curriculum if none is installed; do not fabricate one.

Validated on 30 October 2026:
- 448 laptop source tests passed.
- 63 SURYADEV Core tests passed, including eight bootstrap tests.
- Isolated real TLS test: a wrong pin sends no credential-bearing HTTP request;
  wrong token returns 401; a plan request before heartbeat returns 403; successful
  heartbeat then receives the approved plan with evidence.
- The actual laptop identity suryadev-1 was accepted over its configured pinned
  TLS connection. The rebuilt worker maintains heartbeat without a local plan.
- The running physical Core returned HTTP 403 for the new plan route. Real plan
  reception and learning remain unverified pending server update and owner plan.

No live owner-approved plan was invented, installed or reported as received.
