"""R2 — code graph: fan-in (how many files import a module) + has_tests heuristic.

Import resolution is intentionally heuristic (matches imported segments to file stems);
it's approximate across languages but gives a faithful *relative* centrality ranking.
"""

import re
import subprocess
from pathlib import Path

CODE_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rb", ".php", ".rs", ".cs"}
_SKIP_STEMS = {"__init__", "index", "__main__", "setup", "conftest"}
_JS_IMPORT = re.compile(r"""(?:from\s+|require\(\s*|import\s+)['"]([^'"]+)['"]""")


def _ls_files(repo: str) -> list[str]:
    out = subprocess.run(
        ["git", "-C", repo, "ls-files"], capture_output=True, text=True, errors="ignore", check=True
    ).stdout
    return out.splitlines()


def _is_test(path: str) -> bool:
    parts = path.lower().split("/")
    name = parts[-1]
    return (
        any(p in ("test", "tests", "__tests__") for p in parts)
        or name.startswith("test_")
        or "_test." in name
        or ".test." in name
    )


def _py_candidates(text: str) -> set[str]:
    """Last segment of each imported module + each imported name (filtered to file stems later)."""
    cands: set[str] = set()
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("from "):
            m = re.match(r"from\s+([.\w]+)\s+import\s+(.+)", s)
            if not m:
                continue
            x, names = m.group(1), m.group(2).replace("(", "").replace(")", "")
            if x.strip("."):
                cands.add(x.split(".")[-1])
            for nm in names.split(","):
                nm = nm.strip().split(" as ")[0].strip()
                if nm and nm != "*":
                    cands.add(nm.split(".")[-1])
        elif s.startswith("import "):
            for mod in s[len("import "):].split(","):
                mod = mod.strip().split(" as ")[0].strip()
                if mod:
                    cands.add(mod.split(".")[-1])
    return cands


def _js_candidates(text: str) -> set[str]:
    cands: set[str] = set()
    for m in _JS_IMPORT.finditer(text):
        seg = m.group(1).rstrip("/").split("/")[-1]
        if "." in seg:
            seg = seg.rsplit(".", 1)[0]
        if seg:
            cands.add(seg)
    return cands


def _scan(repo: str):
    """One pass over code files → (files, importers{tgt:{src…}}, has_test{tgt:bool})."""
    files = [f for f in _ls_files(repo) if Path(f).suffix.lower() in CODE_EXTS]

    stem_map: dict[str, set[str]] = {}
    for f in files:
        st = Path(f).stem
        if st not in _SKIP_STEMS:
            stem_map.setdefault(st, set()).add(f)

    importers: dict[str, set[str]] = {}
    has_test: dict[str, bool] = {}
    for f in files:
        try:
            text = (Path(repo) / f).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        cands = _py_candidates(text) if f.endswith(".py") else _js_candidates(text)
        is_test = _is_test(f)
        for c in cands:
            for tgt in stem_map.get(c, ()):
                if tgt == f:
                    continue
                importers.setdefault(tgt, set()).add(f)
                if is_test:
                    has_test[tgt] = True
    return files, importers, has_test


def compute(repo: str) -> dict[str, dict]:
    files, importers, has_test = _scan(repo)
    return {
        f: {"fan_in": len(importers.get(f, ())), "has_tests": bool(has_test.get(f, False))}
        for f in files
    }


def graph_data(repo: str, limit: int = 40) -> tuple[list[str], list[tuple[str, str]], dict, dict]:
    """Top-`limit` files by fan-in + the import edges among them (legible subgraph).
    Returns (top_files, edges[(src,tgt)], fan_in{file:int}, has_test{file:bool})."""
    files, importers, has_test = _scan(repo)
    fan_in = {f: len(importers.get(f, ())) for f in files}
    top = sorted(files, key=lambda f: -fan_in[f])[:limit]
    topset = set(top)
    edges = [
        (src, tgt)
        for tgt in top
        for src in importers.get(tgt, ())
        if src in topset
    ]
    return top, edges, fan_in, has_test


if __name__ == "__main__":
    import sys

    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    g = compute(repo)
    print(f"{len(g)} code files\n\nTop 10 by fan-in (most central / biggest blast radius):")
    for f, st in sorted(g.items(), key=lambda kv: -kv[1]["fan_in"])[:10]:
        flag = "" if st["has_tests"] else "  ⚠ no tests"
        print(f"  fan_in={st['fan_in']:3}  tests={st['has_tests']!s:5}  {f}{flag}")
