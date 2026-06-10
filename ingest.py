"""
Ingestion and chunking pipeline for The Unofficial Guide (Austin restaurants).

Chunk sizes per planning.md:
  - reviews/  : 200–300 chars, one review = one chunk
  - reddit/   : 500–800 chars for post title+body; 300–500 chars per comment thread unit
  - blogs/    : 150–200 chars, prefixed with metadata (restaurant, neighborhood, cuisine)

Overlap: 0 — content is opinion-discrete.
"""

import re
import html
from pathlib import Path
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    text: str
    source_type: str   # "review" | "reddit" | "blog"
    source_file: str
    metadata: dict = field(default_factory=dict)

    def __str__(self):
        meta = " | ".join(f"{k}: {v}" for k, v in self.metadata.items())
        label = f"[{self.source_type.upper()}] {self.source_file}"
        if meta:
            label += f" | {meta}"
        return f"{label}\n{self.text}"


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def clean(text: str) -> str:
    """Remove HTML tags, decode entities, collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)        # strip HTML tags
    text = html.unescape(text)                   # &amp; &nbsp; &#39; etc.
    text = re.sub(r"\s+", " ", text)             # collapse whitespace
    return text.strip()


# ---------------------------------------------------------------------------
# Chunkers — one per source type
# ---------------------------------------------------------------------------

def _split_to_fit(text: str, min_chars: int, max_chars: int) -> list[str]:
    """
    Split text into segments that fit within [min_chars, max_chars].
    Splits on sentence boundaries first, then word boundaries.
    If the text is already within range, returns it as-is.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    current = ""
    for sentence in sentences:
        candidate = (current + " " + sentence).strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current and len(current) >= min_chars:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks if chunks else [text[:max_chars]]


def chunk_reviews(raw: str, source_file: str) -> list[Chunk]:
    """
    One review = one chunk. Reviews are separated by '---'.
    Each review block has header lines (SOURCE:, RESTAURANT:) and body text.
    Target: 200–300 chars per chunk.
    """
    chunks = []
    blocks = [b.strip() for b in raw.split("---") if b.strip()]

    for block in blocks:
        lines = block.splitlines()
        meta = {}
        body_lines = []
        for line in lines:
            if line.startswith("SOURCE:"):
                meta["source"] = line.split(":", 1)[1].strip()
            elif line.startswith("RESTAURANT:"):
                meta["restaurant"] = line.split(":", 1)[1].strip()
            else:
                body_lines.append(line)

        body = clean(" ".join(body_lines))
        if not body:
            continue

        # Each review is already one discrete opinion; keep as one chunk.
        # If it's unusually long, split into sentence-level sub-chunks.
        sub_chunks = _split_to_fit(body, min_chars=100, max_chars=300)
        for sc in sub_chunks:
            chunks.append(Chunk(text=sc, source_type="review",
                                source_file=source_file, metadata=meta.copy()))
    return chunks


def chunk_reddit(raw: str, source_file: str) -> list[Chunk]:
    """
    Post title + body → one chunk (500–800 chars).
    Comment thread → one chunk per comment block (300–500 chars).
    Blocks separated by '---'.
    """
    chunks = []
    blocks = [b.strip() for b in raw.split("---") if b.strip()]

    for block in blocks:
        lines = block.splitlines()
        meta = {}
        title = body = comments_raw = ""

        for line in lines:
            if line.startswith("SOURCE:"):
                meta["source"] = line.split(":", 1)[1].strip()
            elif line.startswith("SUBREDDIT:"):
                meta["subreddit"] = line.split(":", 1)[1].strip()
            elif line.startswith("TYPE:"):
                meta["type"] = line.split(":", 1)[1].strip()
            elif line.startswith("TITLE:"):
                title = line.split(":", 1)[1].strip()
            elif line.startswith("BODY:"):
                body = line.split(":", 1)[1].strip()
            elif line.startswith("COMMENT_THREAD:"):
                comments_raw = line.split(":", 1)[1].strip()

        # Post chunk: title + body, target 500–800 chars
        post_text = clean(f"{title}. {body}" if title else body)
        if post_text:
            sub_chunks = _split_to_fit(post_text, min_chars=200, max_chars=800)
            for sc in sub_chunks:
                chunks.append(Chunk(text=sc, source_type="reddit",
                                    source_file=source_file,
                                    metadata={**meta, "part": "post"}))

        # Comment chunk: top-level comment + replies, target 300–500 chars
        if comments_raw:
            comments = [c.strip() for c in comments_raw.split("||") if c.strip()]
            comment_block = clean(" | ".join(comments))
            sub_chunks = _split_to_fit(comment_block, min_chars=100, max_chars=500)
            for sc in sub_chunks:
                chunks.append(Chunk(text=sc, source_type="reddit",
                                    source_file=source_file,
                                    metadata={**meta, "part": "comments"}))
    return chunks


def chunk_blogs(raw: str, source_file: str) -> list[Chunk]:
    """
    150–200 chars per chunk, prefixed with metadata.
    Blocks separated by '---'. Each block has header tags and a TEXT: field.
    """
    chunks = []
    blocks = [b.strip() for b in raw.split("---") if b.strip()]

    for block in blocks:
        lines = block.splitlines()
        meta = {}
        text_lines = []

        for line in lines:
            if line.startswith("SOURCE:"):
                meta["source"] = line.split(":", 1)[1].strip()
            elif line.startswith("SITE:"):
                meta["site"] = line.split(":", 1)[1].strip()
            elif line.startswith("RESTAURANT:"):
                meta["restaurant"] = line.split(":", 1)[1].strip()
            elif line.startswith("NEIGHBORHOOD:"):
                meta["neighborhood"] = line.split(":", 1)[1].strip()
            elif line.startswith("CUISINE:"):
                meta["cuisine"] = line.split(":", 1)[1].strip()
            elif line.startswith("TEXT:"):
                text_lines.append(line.split(":", 1)[1].strip())
            else:
                text_lines.append(line)

        body = clean(" ".join(text_lines))
        if not body:
            continue

        # Metadata prefix compensates for sparse text on picture-heavy pages
        prefix = ""
        if meta.get("restaurant"):
            prefix = f"{meta['restaurant']}"
            if meta.get("neighborhood"):
                prefix += f", {meta['neighborhood']}"
            if meta.get("cuisine"):
                prefix += f" ({meta['cuisine']})"
            prefix += ": "

        # Account for prefix length when splitting so the total stays within range
        effective_max = max(80, 200 - len(prefix))
        sub_chunks = _split_to_fit(body, min_chars=60, max_chars=effective_max)
        for sc in sub_chunks:
            prefixed = prefix + sc
            chunks.append(Chunk(text=prefixed, source_type="blog",
                                source_file=source_file, metadata=meta.copy()))
    return chunks


# ---------------------------------------------------------------------------
# Loader — dispatch by subfolder name
# ---------------------------------------------------------------------------

CHUNKERS = {
    "reviews": chunk_reviews,
    "reddit":  chunk_reddit,
    "blogs":   chunk_blogs,
}


def load_documents(docs_dir: str = "documents") -> list[Chunk]:
    all_chunks: list[Chunk] = []
    root = Path(docs_dir)

    for source_type, chunker in CHUNKERS.items():
        folder = root / source_type
        if not folder.exists():
            print(f"  [skip] {folder} not found")
            continue
        txt_files = list(folder.glob("*.txt"))
        if not txt_files:
            print(f"  [skip] no .txt files in {folder}")
            continue
        for path in txt_files:
            raw = path.read_text(encoding="utf-8")
            chunks = chunker(raw, source_file=str(path.relative_to(root)))
            print(f"  loaded {path.name} → {len(chunks)} chunks")
            all_chunks.extend(chunks)

    return all_chunks


# ---------------------------------------------------------------------------
# Inspection helpers
# ---------------------------------------------------------------------------

def inspect_chunks(chunks: list[Chunk], n: int = 5) -> None:
    """Print n representative chunks spread across the full list."""
    print("\n" + "=" * 70)
    print(f"CHUNK INSPECTION  (showing {n} of {len(chunks)} total)")
    print("=" * 70)

    if not chunks:
        print("No chunks to inspect.")
        return

    # Pick spread: first, last, and evenly spaced in between
    if len(chunks) <= n:
        sample_indices = list(range(len(chunks)))
    else:
        step = (len(chunks) - 1) / (n - 1)
        sample_indices = [round(i * step) for i in range(n)]

    for idx in sample_indices:
        chunk = chunks[idx]
        print(f"\n--- Chunk #{idx + 1} | type={chunk.source_type} | {len(chunk.text)} chars ---")
        print(chunk.text)

    print("\n" + "=" * 70)
    print(f"TOTAL CHUNKS: {len(chunks)}")

    by_type: dict[str, int] = {}
    for c in chunks:
        by_type[c.source_type] = by_type.get(c.source_type, 0) + 1
    for t, count in sorted(by_type.items()):
        print(f"  {t:10s}: {count}")

    lengths = [len(c.text) for c in chunks]
    avg = sum(lengths) / len(lengths)
    print(f"\n  avg char length : {avg:.0f}")
    print(f"  min char length : {min(lengths)}")
    print(f"  max char length : {max(lengths)}")

    if len(chunks) < 50:
        print("\n  WARNING: fewer than 50 chunks — chunks may be too large or you need more documents.")
    elif len(chunks) > 2000:
        print("\n  WARNING: more than 2000 chunks — chunks may be too small.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Loading documents...")
    chunks = load_documents("documents")

    if not chunks:
        print("\nNo chunks produced. Add .txt files to documents/reviews/, "
              "documents/reddit/, or documents/blogs/ and re-run.")
    else:
        inspect_chunks(chunks, n=5)
