"""Chunk the downloaded 15-122 lecture notes and load them into Chroma.

Run download_notes.py first. Safe to re-run: chunk ids are deterministic,
so upsert() replaces existing chunks instead of duplicating them.
"""
import os
import re
import sys
import time

from pypdf import PdfReader

from store import get_collection

LECTURE_DIR = os.path.join("data", "lectures")
CHUNK_WORDS = 180    # the default embedding model only reads ~256 word pieces
OVERLAP_WORDS = 40   # so an idea split across a boundary still lands whole in one chunk
BATCH_SIZE = 100


def clean(text):
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    return re.sub(r"\s+", " ", text).strip()


def lecture_title(reader, fallback):
    """Pull 'Unbounded Arrays' out of the 'Lecture 11: Unbounded Arrays 2' page header."""
    for page in reader.pages[1:3]:
        first_line = (page.extract_text() or "").strip().split("\n")[0]
        m = re.match(r"Lecture \d+:\s*(.+?)\s*\d*$", first_line)
        if m:
            # PDF kerning splits "Tables" into "T ables"; glue those back together.
            return re.sub(r"\b([A-Z]) ([a-z]{3,})", r"\1\2", m.group(1))
    return fallback


def chunk_pdf(path):
    """Yield (text, page_number) windows of CHUNK_WORDS words, one page at a time."""
    reader = PdfReader(path)
    for page_num, page in enumerate(reader.pages, start=1):
        lines = (page.extract_text() or "").split("\n")
        if lines and lines[0].startswith("Lecture "):
            lines = lines[1:]  # drop the running page header
        words = clean(" ".join(lines)).split()
        step = CHUNK_WORDS - OVERLAP_WORDS
        for start in range(0, max(len(words) - OVERLAP_WORDS, 1), step):
            piece = words[start:start + CHUNK_WORDS]
            if len(piece) >= 25:  # skip near-empty fragments (figure labels, page numbers)
                yield " ".join(piece), page_num


def main(limit=None):
    collection = get_collection()
    files = sorted(f for f in os.listdir(LECTURE_DIR) if f.endswith(".pdf"))
    if not files:
        sys.exit("No PDFs found. Run: python download_notes.py")

    ids, docs, metas = [], [], []
    for fname in files:
        lecture = fname[:-4]
        title = lecture_title(PdfReader(os.path.join(LECTURE_DIR, fname)), lecture)
        for i, (text, page) in enumerate(chunk_pdf(os.path.join(LECTURE_DIR, fname))):
            ids.append(f"{lecture}-p{page}-{i}")
            # Prefix the title so every chunk carries its topic into the embedding.
            docs.append(f"[{title}] {text}")
            metas.append({"source": "lecture", "lecture": lecture, "title": title, "page": page})

    if limit:
        ids, docs, metas = ids[:limit], docs[:limit], metas[:limit]

    print(f"{len(ids)} chunks from {len(files)} lectures; embedding...")
    t0 = time.time()
    for start in range(0, len(ids), BATCH_SIZE):
        end = start + BATCH_SIZE
        collection.upsert(ids=ids[start:end], documents=docs[start:end], metadatas=metas[start:end])
        print(f"  {min(end, len(ids))}/{len(ids)}  ({time.time() - t0:.1f}s)")
    print(f"done. collection now holds {collection.count()} items")


if __name__ == "__main__":
    main(limit=int(sys.argv[1]) if len(sys.argv) > 1 else None)
