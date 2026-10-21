"""Optional complete-pass local PDF/EPUB book visual evidence auditor.

Does not download anything or allow remote/cloud OCR. Each page or EPUB
image is attempted IN ORIGINAL ORDER with committed checkpoints, SHA-256,
local OCR (PDF) and installed Ollama vision. Dynamic EPUB CSS backgrounds,
third-party assets and semantic understanding remain unverified.
"""
from __future__ import annotations

import hashlib
from itertools import islice
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path, PurePosixPath
import posixpath
import re
import time
from urllib.parse import unquote, urlsplit
import zipfile

from suryadev_book_reader import BookLedger, file_sha256, _text_units

SUPPORTED = {".pdf", ".epub"}
MAX_VISUAL_ITEMS = 20000
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class MediaRefs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []
    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag.lower() in ("img","image"):
            self.refs.append(("image", props.get("src") or props.get("href") or
                              props.get("xlink:href") or ""))
        elif tag.lower() in ("svg","math"):
            self.refs.append((tag.lower(), ""))


def epub_media(path):
    """Iterate referenced image markers in EPUB linear spine order."""
    chapters = []
    for section, _, _, _ in _text_units(path):
        if section.startswith("chapter ") and section not in chapters:
            chapters.append(section)
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos)>3000 or sum(x.file_size for x in infos)>100*1024*1024:
            raise ValueError("EPUB media exceeds safe archive bounds")
        for chapter in chapters:
            member = chapter.split(": ",1)[1]
            raw = archive.read(member)
            parser = MediaRefs()
            parser.feed(raw.decode("utf-8-sig"))
            folder = PurePosixPath(member).parent
            for number,(kind,href) in enumerate(parser.refs, 1):
                key = chapter+":visual:"+str(number)
                if kind in ("svg","math"):
                    raise ValueError("Inline "+kind+" visual needs additional audited renderer at "+key)
                link = urlsplit(href)
                if link.scheme or link.netloc or href.startswith("/") or not href:
                    raise ValueError("external or missing EPUB image at "+key)
                normalized = posixpath.normpath(str(folder / unquote(link.path)))
                if normalized.startswith("../") or normalized not in archive.namelist():
                    raise ValueError("EPUB image outside archive at "+key)
                data=archive.read(normalized)
                if not data or len(data)>MAX_IMAGE_BYTES:
                    raise ValueError("EPUB image bytes absent or oversized at "+key)
                yield (key, data)


class BookVisualAuditor:
    def __init__(self,root):
        self.ledger=BookLedger(root)
        self.ledger.db.execute("""
        CREATE TABLE IF NOT EXISTS book_visuals(
          book_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
          label TEXT NOT NULL, image_sha256 TEXT NOT NULL,
          observation TEXT NOT NULL, ocr_text TEXT NOT NULL,
          elapsed_seconds REAL NOT NULL, recorded_at REAL NOT NULL,
          PRIMARY KEY(book_id, ordinal))
        """)
        self.ledger.db.execute("""
        CREATE TABLE IF NOT EXISTS book_visual_runs(
          book_id TEXT PRIMARY KEY, completed_at REAL NOT NULL,
          items_total INTEGER NOT NULL)
        """)
        self.ledger.db.commit()

    def close(self):
        self.ledger.close()

    def _sources(self, path, *, pdf_frames=None, epub_images=None, skip=0):
        if path.suffix.lower()==".epub":
            yield from islice(
                (epub_images(path) if epub_images else epub_media(path)),skip,None)
            return
        if pdf_frames is not None:
            yield from islice(pdf_frames(path),skip,None)
            return
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise RuntimeError("Local PDF visuals require pypdfium2") from exc
        document=pdfium.PdfDocument(str(path))
        try:
            for index in range(skip,len(document)):
                image=document[index].render(scale=1.6).to_pil()
                buff=BytesIO();image.save(buff,format="PNG")
                yield ("PDF page "+str(index+1),buff.getvalue())
        finally:
            document.close()

    def run(self,book_id, *, model="gemma3:4b",max_items=0, vision=None,
            ocr=None,pdf_frames=None,epub_images=None):
        if type(max_items) is not int or not 0<=max_items<=MAX_VISUAL_ITEMS:
            raise ValueError("invalid per-run visual budget")
        if not isinstance(model,str) or not 1<=len(model)<=100:
            raise ValueError("explicit installed local vision model required")
        row=self.ledger.db.execute(
            "SELECT filename,format,source_sha256 FROM books WHERE id=?",
            (book_id,)).fetchone()
        if not row:
            raise ValueError("book must be imported before a visual audit")
        filename,fmt,sha=row
        file=Path(filename).resolve(strict=True)
        if not file.is_file() or file.suffix.lower() not in SUPPORTED:
            raise ValueError("visual book audit supports PDF and EPUB only")
        if file_sha256(file)!=sha:
            raise ValueError("book source changed after import")
        if vision is None:
            from PIL import Image
            from suryadev_deep_pdf import ollama_vision
            vision=lambda data,label:ollama_vision(Image.open(BytesIO(data)).convert("RGB"),model)
        if ocr is None and fmt==".pdf":
            try:
                from PIL import Image
                import pytesseract
            except ImportError as exc:
                raise RuntimeError("PDF visual book audit needs Pillow, pytesseract, Tesseract") from exc
            ocr=lambda data,label:pytesseract.image_to_string(
                Image.open(BytesIO(data)).convert("RGB"))
        already=self.ledger.db.execute(
            "SELECT COUNT(*) FROM book_visuals WHERE book_id=?",(book_id,)).fetchone()[0]
        seen=already;added=0;completed_pass=True
        for label,blob in self._sources(file,pdf_frames=pdf_frames,
                                        epub_images=epub_images,skip=already):
            seen+=1
            if seen>MAX_VISUAL_ITEMS:
                raise ValueError("book exceeds 20,000 visual item safety limit")
            digest=hashlib.sha256(blob).hexdigest()
            stored=self.ledger.db.execute(
                "SELECT label,image_sha256 FROM book_visuals WHERE book_id=? AND ordinal=?",
                (book_id,seen)).fetchone()
            if stored:
                if stored!=(label,digest):
                    raise RuntimeError("book visual checkpoint/source mismatch at item "+str(seen))
                continue
            if max_items and added>=max_items:
                completed_pass=False
                break
            if not blob or len(blob)>MAX_IMAGE_BYTES:
                raise ValueError("visual image missing or over 10 MiB at "+label)
            start=time.monotonic()
            words=str(ocr(blob,label) or "").strip() if ocr else ""
            result=str(vision(blob,label) or "").strip()
            if not result:
                raise RuntimeError("local visual model produced no evidence at "+label)
            elapsed=time.monotonic()-start
            with self.ledger.db:
                self.ledger.db.execute(
                    "INSERT INTO book_visuals VALUES(?,?,?,?,?,?,?,?)",
                    (book_id,seen,label,digest,result[:4500],
                     words[:10000],elapsed,time.time()))
            added+=1
        total=self.ledger.db.execute(
            "SELECT COUNT(*) FROM book_visuals WHERE book_id=?",(book_id,)).fetchone()[0]
        if completed_pass:
            with self.ledger.db:
                self.ledger.db.execute(
                    "INSERT OR REPLACE INTO book_visual_runs VALUES(?,?,?)",
                    (book_id,time.time(),total))
        return {"book_id":book_id,"visual_items_processed":total,
                "new_visual_items_this_run":added,
                "inventory_walked_this_run":seen,
                "reached_known_end":completed_pass and seen==total,
                "every_detected_visual_explained_by_model":completed_pass and seen==total,
                "full_semantic_understanding_verified":False,
                "external_assets_and_css_covered":False,
                "brahmagyan_acknowledged":False}
