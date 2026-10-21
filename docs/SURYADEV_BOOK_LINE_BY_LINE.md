# SURYADEV v6.7 — Complete local book reading, in source order

## Purpose and provenance
Use the local-first book approach rather than importing SoBrief's ten-minute
summaries as a substitute for the underlying text. SoBrief is a commercial
summary/reading product, not a verified free whole-book parser. The open-source
projects Morpheis/bookworm (sequential no-lookahead reading/journal, but
Anthropic API dependency) and subev/libratory (OCR and local books) were used
as DESIGN references; this is an independent Python implementation.

**Supported books**: operator-supplied and legally held **DRM-free** TXT, MD,
EPUB and PDF up to 100 MiB. Never scrape copyrighted books, remove DRM,
download unknown files, or transmit text to cloud AI. Existing Ollama is
loopback-only. Reading progress is saved under existing
`D:\Work\SURYADEV-DATA` in a NEW `book-learning.sqlite3` file. Do NOT
delete/change the original `suryadev.sqlite3` job/evidence database.

### Complete start-to-end sequence
1. Operator selects a book file; `book-import` SHA-256 fingerprints it.
2. EPUB parses the book's OPF spine **in defined reading order**. Every
   XHTML spine item is extracted into source-numbered physical/logical lines;
   scripts/styles are omitted as non-reading content. EPUB media not readable
   as text causes a fail, not a skipped chapter.
3. PDF extracts page 1 through final page; every page must contain selectable
   text or, with `--ocr-scanned`, have locally OCR-detected text. The engine
   does not mark a book indexed if any PDF page is unreadable.
   TXT/MD preserve all original text line boundaries, including blanks.
4. An atomic SQLite import creates every numbered line with its SHA-256,
   chapter/page position and overall book fingerprint. Zero partial books
   survive an import error.
5. `book-read` starts at line 1 or the persisted next unread ordinal.
   Default `--lines-per-step 1` gives the local Ollama model one complete,
   numbered source line at a time; never passes any future text. Larger steps
   send every included line in order with explicit ordinal labels. The
   model response, exact evidence digest, time in seconds, and next pointer
   are committed together. Network/model errors leave the cursor unchanged.
6. Resume repeats only the interrupted line/step; never skips a line or
   silently truncates prompt text. `book-verify` rechecks original indexed
   line hashes plus the chronological, contiguous reading journal.
7. `book-status` gives processed/remaining lines, percent, elapsed model
   seconds, average seconds per line, and reached-end state for each model.
   `extractive_record_only` is a separate session and **does not count as
   AI examination**. The `BRAHMAGYAN` ACK flag remains false until a real,
   verified external intake and assessment has occurred.

A model's line-by-line response does not prove deep comprehension. A PDF
text/OCR pass does not guarantee understanding its charts/images/equations;
SURYADEV's separate opt-in deep-PDF vision pathway is required for such
observations, with independent verification still pending. EPUB footnotes,
images, MathML and complex navigation also require an additional multimodal
quality gate before claiming full semantic understanding.

## Laptop commands (after PR tests pass and install updated source)
Stop SURYADEV worker and heavy local video jobs with Ctrl+C (the existing
single-worker lock prevents unsafe competing work). Leave persistent DATA
untouched. Install from the existing feature branch:

```powershell
cd "D:\Work\SURYADEV-SOURCE"
git pull --ff-only origin feat/suryadev-standalone-laptop-20261019
cd "D:\Work\SURYADEV-SOURCE\standalone\suryadev"
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-windows.ps1 -InstallDir "D:\Work\SURYADEV" -DataDir "D:\Work\SURYADEV-DATA"
```

Import any book you already own and are allowed to process:
```powershell
cd "D:\Work\SURYADEV"
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" book-import "D:\Books\my-book.epub"
# PDF with scanned pages, if local Tesseract and Python OCR prerequisites exist:
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" book-import "D:\Books\my-book.pdf" --ocr-scanned
```

Copy the `book_id` exactly from import output. Confirm `ollama list`
contains a local model and start processing each line in order:

```powershell
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" book-read "BOOK_ID_FROM_IMPORT" --model "gemma3:4b" --lines-per-step 1
```

For a long book, one model call per line may require MANY HOURS/DAYS.
To process every line, but group related consecutive lines into one bounded
Ollama call, use `--lines-per-step 20`. There is no hidden first-2000-
characters preview or 220,000-character whole-book cutoff; model prompts
over 12,000 characters are refused without advancing the checkpoint.
`--max-steps 10` processes exactly the next ten steps then exits normally;
omitting it continues to the book's last line. Restart the same command
to resume; model identities have distinct reading cursors.

Read-only status and integrity:
```powershell
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" book-status "BOOK_ID_FROM_IMPORT"
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" book-verify "BOOK_ID_FROM_IMPORT"
```

**No Ollama mode** `--no-ollama` is an evidence recording tool only. It
must not be described as AI reading or learning.

## Further steps not yet implemented
- Automatic scheduling of each book alongside the existing continuous web
  worker; presently the operator selects a local file and invokes the book
  reader with the single-worker lock.
- Model-backed sentence-level factual verification, end-of-chapter exams,
  semantic cross-book search, references and links between books.
- Full page/figure extraction for EPUB and scanned PDFs as a unified book
  multimodal evidence record.
- Authenticated acceptance into Core BRAHMAGYAN and Rishi council with
  explicit digest ACK; do not mark acceptance before that exists.
- Real physical Windows laptop Ollama end-to-end book acceptance; GitHub
  CI simulates the model responses but cannot confirm knowledge quality.
