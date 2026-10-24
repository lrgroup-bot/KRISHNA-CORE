# SURYADEV automatic hardware-based learning

**Required behavior:** SURYADEV discovers real CPU thread count, RAM headroom,
disk space and supported GPU telemetry on each scheduling cycle. It does not
use a fixed number of parallel jobs. Workload assignment size is independent
of concurrent execution size.

## Workload and concurrency are different

Current configurable source-type ceilings in the development implementation:

| Type | Workload ceiling | Execution admission |
| --- | ---: | --- |
| Websites | 10 | Actual browser tabs limited by hardware and approved host policy |
| YouTube browser videos | 10 | Up to the measured safe count, on exact preapproved videos only |
| PDF documents | 100 | 100 assignments may remain pending; actual parallel parsing is measured |
| Books | 5 | Five distinct approved books can checkpoint; model interpretation shares one local lock |

These are **workload limits**, not guaranteed concurrent activity. For
example: 100 PDF assignments, 5 approved video assignments, and 5 book
assignments may coexist even if the present 16 GB laptop can admit only
one or two costly executions. The scheduler drains all approved assignments
as CPU and memory headroom permits and scales to more work on a future
high-memory, many-core SURYADEV node. The largest source thread pool has
120 potential slots; new threads are launched only when the measured
capacity permits.

## Admission guard

- CPU, RAM and data-drive usage must remain below 85% at admission.
- Supported GPU/VRAM readings also participate; unavailable GPU telemetry
  is displayed as unavailable, never invented.
- Keep at least 2 GiB available to the OS plus a 15% RAM headroom budget;
  reserve at least 2 GiB free storage.
- At CPU ≥70% or RAM ≥75%, admit at most one total new work slot under
  the conservative laptop profile; at ≥85%, no new heavy work starts.
- Windows dashboard **does not set SURYADEV_MAX_PARALLEL=45**. An optional
  explicitly set numeric operator cap can only lower measured concurrency.
- Each new source task is admitted after book/video inflight work is
  included in the measured global capacity. Never launch two simultaneous
  writer supervisors to the same data directory.
- This is a **sampled admission control**, not a hard guarantee CPU
  utilization never momentarily exceeds 85%; active jobs need graceful
  completion and checkpointing when the system gets busy.

## Source-specific truthfulness

- Ten parallel browser-video observations can be attempted only if there
  are ten exact owner-approved URLs, browser prerequisites are installed,
  and hardware capacity truly admits them. The browser evidence must be
  audited; starting Chrome is not verified comprehension.
- YouTube subtitle provider requests remain serialized (maximum one at
  a time) with 429 cooldown. Do not bypass service access controls.
- PDF pages are extracted only from approved files/URLs, scanned pages
  need their own OCR/vision, and a source being queued is not 'read'.
- Separate book journals protect ordered progress and SHA-256 identity.
  Model-intensive source/book summary work remains serialized to one
  local inference at a time unless further benchmarked.
- KRISHNA/BRAHMAGYAN/Rishi acknowledgements and independent assessments
  remain separate from source acquisition completion.

## Live acceptance before installing a new EXE

1. Validate Windows/Linux unit checks and Chromium UI contract.
2. Enqueue 100 approved PDF assignments; verify the dashboard shows the
   number waiting, the smaller number admitted, and no new heavy admissions
   above the 85% threshold.
3. Test five *real* approved YouTube browser jobs (when hardware admits),
   including captions, timestamped frames and evidence integrity. Test
   provider denial paths without retry abuse.
4. Test five distinct approved books advancing their independent journals.
5. Verify graceful stop/restart and authenticated KRISHNA evidence receipts.
6. Only after two-PC hardware acceptance package a release EXE.

**No live device benchmark is claimed by these source-code changes.**
