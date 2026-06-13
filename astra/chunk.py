"""Recursive-ish character splitter — mirrors the reference's RecursiveCharacterTextSplitter(1000/200).

Sliding window of ~1000 chars with ~200 overlap, snapping each cut to the nearest
paragraph/line/space boundary so we don't slice mid-word.
"""

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start, n = 0, len(text)
    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            end = _snap(text, start, end)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _snap(text: str, start: int, end: int) -> int:
    """Move `end` back to the nearest paragraph/line/space boundary in the latter half."""
    window = text[start:end]
    half = (end - start) // 2
    for sep in ("\n\n", "\n", " "):
        idx = window.rfind(sep)
        if idx > half:
            return start + idx + len(sep)
    return end
