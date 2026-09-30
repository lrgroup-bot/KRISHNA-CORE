# BRAHMAGYAN — Alex Xu / ByteByteGo System Design Learning Program

Status: implemented curriculum + resource-gated scheduler  
Start date: 1 October 2026  
Timezone: Asia/Kolkata  
Learning windows: 02:30 IST and 14:30 IST  
Maximum progress: one verified new module per day

## Source rule

The syllabus uses Alex Xu / ByteByteGo's official public GitHub material:

- `alex-xu-system/bytebytego/system_design_links.md`
- `alex-xu-system/bytebytego/system_design_links_vol2.md`
- `ByteByteGoHq/system-design-101`

A third-party repository containing a full PDF copy of the book is deliberately excluded from ingestion. The Rishis use the official public reference indexes to discover each topic, then verify reusable claims against primary/current technical sources such as original papers, standards, protocol specifications, official project documentation and engineering publications.

Reading is not treated as verified learning. Every mission remains subject to BRAHMAGYAN's normal provenance, source-independence, contradiction, Gautama review, Veda Vyasa synthesis and L0-L8 maturity gates.

## Rishi ownership

- Bharadvaja — system-design method, requirements, capacity planning, architecture tests, load tests and implementation-gap audits.
- Aryabhata — back-of-the-envelope estimates, QPS, bandwidth, storage, latency and throughput models.
- Pingala — consistent hashing, partitioning, distributed KV stores, IDs, queues, tries and indexes.
- Jamadagni — reliability, rate limits, retries, backpressure, idempotency, message delivery, observability, storage durability and failure recovery.
- Vishwamitra — web crawling, media platforms, large-scale service architecture and frontier implementations.
- Madhava — metrics, time series, event aggregation and stream processing.
- Baudhayana — proximity systems, spatial indexes, map tiles and routing graphs.
- Panini — multilingual autocomplete, Unicode-aware indexing and query normalization.
- Chanakya — distributed operations, reservations, capacity/resource allocation, payment/wallet architecture and exchange-system operations.
- Narada — payment/wallet/exchange regulatory and compliance review where applicable.
- Gautama — mandatory evidence/trade-off/assumption review.
- Veda Vyasa — mandatory synthesis, deduplication, provenance and reusable architecture knowledge maps.

## 30-day curriculum

| Day | Date | Topic | Lead |
|---:|---|---|---|
| 1 | 2026-10-01 | Scale from zero to millions | Bharadvaja |
| 2 | 2026-10-02 | Back-of-the-envelope estimation | Aryabhata |
| 3 | 2026-10-03 | System-design framework | Bharadvaja |
| 4 | 2026-10-04 | Rate limiter | Jamadagni |
| 5 | 2026-10-05 | Consistent hashing | Pingala |
| 6 | 2026-10-06 | Distributed key-value store | Pingala |
| 7 | 2026-10-07 | Distributed unique ID generator | Pingala |
| 8 | 2026-10-08 | URL shortener | Vishvakarma |
| 9 | 2026-10-09 | Web crawler | Vishwamitra |
| 10 | 2026-10-10 | Notification system | Jamadagni |
| 11 | 2026-10-11 | News feed | Chanakya |
| 12 | 2026-10-12 | Chat system | Jamadagni |
| 13 | 2026-10-13 | Search autocomplete | Panini |
| 14 | 2026-10-14 | Video platform | Vishwamitra |
| 15 | 2026-10-15 | Cloud drive / file sync | Jamadagni |
| 16 | 2026-10-16 | Proximity service | Baudhayana |
| 17 | 2026-10-17 | Nearby friends | Baudhayana |
| 18 | 2026-10-18 | Maps | Baudhayana |
| 19 | 2026-10-19 | Distributed message queue | Pingala |
| 20 | 2026-10-20 | Metrics monitoring | Madhava |
| 21 | 2026-10-21 | Event aggregation / stream processing | Madhava |
| 22 | 2026-10-22 | Reservation system | Chanakya |
| 23 | 2026-10-23 | Distributed email | Jamadagni |
| 24 | 2026-10-24 | S3-like object storage | Jamadagni |
| 25 | 2026-10-25 | Real-time leaderboard | Pingala |
| 26 | 2026-10-26 | Payment system | Chanakya |
| 27 | 2026-10-27 | Digital wallet | Chanakya |
| 28 | 2026-10-28 | Stock exchange | Chanakya |
| 29 | 2026-10-29 | Cross-cutting distributed-systems synthesis | Veda Vyasa |
| 30 | 2026-10-30 | KRISHNA implementation-gap audit | Bharadvaja |

If a module misses its evidence gate, it is retried instead of skipped. The 14:30 window serves as a second opportunity when the 02:30 window could not run or verify because production was busy, CPU/RAM were above the BRAHMAGYAN limits, or evidence was insufficient. Once a module is verified for the day, no second new module runs that day.

## Runtime flow

```text
SystemDesignLearningScheduler
  -> BRAHMAGYAN resource gate
     production idle
     CPU < 50%
     RAM < 70%
  -> Rishi Live Research
  -> GARUDA web/source discovery
  -> atomic claims + provenance
  -> counter-evidence search
  -> Gautama evidence review
  -> Bharadvaja application/test plan
  -> Veda Vyasa synthesis
  -> RishiLearningLedger
  -> BRAHMAGYAN persisted mission/claim state
  -> Gyan-Bhandar only through the existing trusted-promotion gate
```

The scheduled task uses `auto_propose=False`. Background learning therefore cannot silently promote material to trusted Gyan.

## What KRISHNA already has

Alex Xu patterns must strengthen these components rather than duplicate them:

1. **Durable action idempotency** — SharedActionBus has a SQLite idempotency journal, fingerprints, execution reservation and safe replay.
2. **Durable queue** — persistent queue states, claim/lease, ACK, retry counters and interrupted-worker recovery already exist.
3. **Durable event journal** — lifecycle events are persisted and replayable by sequence.
4. **Resource governor** — production workload and resource pressure already gate optional research.
5. **Content-addressed Gyan archive** — SHA-256 deduplication and integrity verification already exist.
6. **BRAHMAGYAN evidence maturation** — source provenance, independent-source checks, contradictions and L0-L8 maturity already exist.

## Implementation backlog from the curriculum

### Strengthen now

**1. Distributed rate-limit layer**

Add one reusable limiter at Shared Action Bus / HTTP / connector boundaries rather than custom limits in each subsystem. Learn token bucket, leaky bucket, fixed/sliding window and distributed-counter trade-offs. Required properties: caller/action scopes, burst allowance, retry-after information, bounded storage and auditable rejects.

**2. Queue retry policy + dead-letter handling**

DurableQueue already retries, but should gain standardized exponential backoff with jitter, a next-attempt timestamp, explicit dead-letter state/reason and operator replay controls. Never silently retry consequential external actions.

**3. Observability v2**

Current tracing is lightweight. Add consistent operation IDs, latency histograms, error counters, queue depth/age, saturation, SLO/error-budget views and trace correlation across Action Bus -> Job Runtime -> provider/worker -> verification.

**4. Capacity estimator**

Implement Aryabhata/Bharadvaja capacity estimates inside Project Genesis / Engineering Scheduler: expected users/jobs, read/write QPS, payload size, bandwidth, storage/day, retention, RAM/cache, concurrency and latency target. Assumptions must stay visible and editable.

**5. Standard event/message envelope**

Standardize event ID, occurred-at, producer, schema version, ordering key, idempotency key, correlation/causation IDs, attempt count and integrity/provenance fields across queues and event buses.

**6. GARUDA crawler frontier**

Add bounded URL-frontier concepts learned from crawler design: normalized URL fingerprint, host politeness budget, robots policy, domain concurrency, retry/backoff, duplicate-content hash, crawl depth and source provenance. This is research acquisition, not unrestricted scraping.

**7. Gyan search/autocomplete**

Add Unicode-aware normalization, prefix/trie or appropriate search index, ranking by verified maturity/relevance/recency and result provenance. Avoid introducing a distributed search cluster until actual corpus size demands it.

**8. Device/file synchronization protocol**

For HAWKEYE/SURYDEV/LocalSend-style artifact handoffs, add chunk hashes, resumable manifests, version vectors or an explicit conflict rule, atomic finalization and integrity receipts. Differential sync should be evaluated before implementation rather than assumed useful for every file.

**9. HAWKEYE geospatial index**

For nearby objects/boundaries, evaluate geohash/H3/S2/quadtree-style indexing, spatial partitioning, stale-location rules and offline tile caches. Keep precise-location privacy boundaries explicit.

### Implement when scale proves the need

- Consistent/rendezvous hashing for multi-node worker/cache placement.
- Partitioned append-only log and consumer groups if the existing DurableQueue becomes a measured throughput bottleneck.
- Replicated/erasure-coded object storage if local Gyan/media durability requirements outgrow current backup/storage.
- Dedicated stream-processing infrastructure only when event rate/windowing requirements justify it.
- Dedicated distributed KV store only if SQLite/local stores cannot meet measured availability/throughput requirements.

### Knowledge only / no autonomous execution

Payment, wallet and stock-exchange chapters are useful for idempotency, ledgers, reconciliation, event ordering, sagas and resilience. They must not grant KRISHNA autonomous spending, wallet movement, trading or financial authority. Any future financial implementation remains under the existing owner approval, legal/compliance and zero-spend boundaries.

## Success criteria

The curriculum is successful when the final implementation-gap audit can identify, for each candidate pattern:

- the measured problem it solves;
- current KRISHNA component being improved;
- primary evidence and alternatives;
- reliability/security trade-offs;
- expected resource cost;
- test/load/failure-injection plan;
- measurable acceptance criteria;
- whether to implement now, defer, or reject.

The goal is not to make KRISHNA look like a hyperscale company. The goal is to use proven system-design principles only where KRISHNA's measured workload and reliability requirements justify them.
