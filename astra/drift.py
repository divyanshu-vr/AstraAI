"""R7 — doc-drift detector: docs say X, does the code still agree?

Two Groq calls per repo (cheap, cached by the server):
  1. extract up to 8 concrete checkable claims from README/docs
  2. judge all claims at once against retrieved CODE evidence (local embeddings)
"""

import json
import re
from pathlib import Path

from astra import llm, retrieve

_CODE_EXTS = [".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".rs", ".c", ".cpp", ".cs"]
_DOC_CANDIDATES = ("README.md", "README.rst", "docs/index.rst", "docs/index.md", "docs/quickstart.rst", "docs/quickstart.md")
_DOC_CHARS = 9000
_MAX_CLAIMS = 6

_EXTRACT_SYSTEM = (
    "You extract CHECKABLE technical claims from software documentation. "
    "A good claim is concrete and verifiable against source code: an API/function that exists, "
    "a default value, a supported version, a described behavior. Skip marketing and opinions. "
    'Return STRICT JSON only: ["claim 1", "claim 2", ...] (max ' + str(_MAX_CLAIMS) + ")."
)

_JUDGE_SYSTEM = (
    "You are auditing documentation against the actual source code. For each numbered claim "
    "you get code excerpts retrieved from the repo. Verdicts: "
    "'supported' (code clearly agrees), 'drifted' (code clearly contradicts or the feature looks "
    "renamed/removed/changed), 'unverifiable' (excerpts insufficient — be honest, prefer this over guessing). "
    "Return STRICT JSON only: [{\"claim\": str, \"verdict\": str, \"note\": str (one short sentence), "
    "\"files\": [str]} ...] in the same order."
)


def _read_docs(repo_path: str) -> str:
    root = Path(repo_path)
    parts = []
    for rel in _DOC_CANDIDATES:
        p = root / rel
        if p.exists():
            parts.append(f"--- {rel} ---\n" + p.read_text(encoding="utf-8", errors="ignore"))
        if sum(len(x) for x in parts) > _DOC_CHARS:
            break
    return "\n\n".join(parts)[:_DOC_CHARS]


def _parse_json(text: str):
    m = re.search(r"[\[{].*[\]}]", text, re.S)
    return json.loads(m.group(0)) if m else None


def scan(repo_id: str, repo_path: str) -> list[dict]:
    docs = _read_docs(repo_path)
    if not docs:
        return []

    raw = llm.complete(_EXTRACT_SYSTEM, f"Documentation:\n{docs}\n\nExtract the claims (JSON array only).")
    claims = _parse_json(raw)
    if not isinstance(claims, list) or not claims:
        return []
    claims = [str(c) for c in claims[:_MAX_CLAIMS]]

    # gather code evidence per claim (local embeddings — free)
    blocks = []
    for i, claim in enumerate(claims, 1):
        hits = retrieve.retrieve(claim, k=3, repos=[repo_id], exts=_CODE_EXTS)
        ev = "\n".join(f"  [{h['source']}] {h['content'][:400]}" for h in hits) or "  (no code retrieved)"
        blocks.append(f"CLAIM {i}: {claim}\nCODE EVIDENCE:\n{ev}")

    raw = llm.complete(_JUDGE_SYSTEM, "\n\n".join(blocks) + "\n\nReturn the JSON verdicts array only.")
    verdicts = _parse_json(raw)
    if not isinstance(verdicts, list):
        return [{"claim": c, "verdict": "unverifiable", "note": "judge output unparseable", "files": []} for c in claims]

    out = []
    for i, c in enumerate(claims):
        v = verdicts[i] if i < len(verdicts) and isinstance(verdicts[i], dict) else {}
        out.append({
            "claim": c,
            "verdict": v.get("verdict", "unverifiable"),
            "note": v.get("note", ""),
            "files": [f for f in v.get("files", []) if isinstance(f, str)][:3],
        })
    return out


if __name__ == "__main__":
    import sys
    rid = sys.argv[1] if len(sys.argv) > 1 else "flask"
    from astra import workspace
    entry = workspace.get_repo(rid)
    if not entry:
        raise SystemExit(f"repo '{rid}' not in workspace")
    for row in scan(rid, entry["path"]):
        print(f"[{row['verdict']:12}] {row['claim'][:80]}\n              {row['note']}")
