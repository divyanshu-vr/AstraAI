"""Multi-repo workspace: registry + per-repo reports + background analyze/ingest.

Layout:
  .astra/repos.json          — registry: [{id, name, path, status, stats…}]
  .astra/reports/<id>.json   — risk report per repo
  Chroma chunks              — ids prefixed "<repo_id>::", metadata {"repo": id, …}
"""

import json
import re
import subprocess
import threading
import time
from pathlib import Path

from astra import risk

_ROOT = Path(__file__).resolve().parent.parent / ".astra"
_REGISTRY = _ROOT / "repos.json"
_REPORTS = _ROOT / "reports"
_CLONES = _ROOT / "clones"
_lock = threading.Lock()

_URL_RE = re.compile(r"^(https?://|git@)")


# ---------- registry io ----------

def _load() -> list[dict]:
    if not _REGISTRY.exists():
        return []
    return json.loads(_REGISTRY.read_text())


def _save(repos: list[dict]) -> None:
    _ROOT.mkdir(exist_ok=True)
    _REGISTRY.write_text(json.dumps(repos, indent=2))


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "repo"


def list_repos() -> list[dict]:
    with _lock:
        return _load()


def get_repo(repo_id: str) -> dict | None:
    return next((r for r in list_repos() if r["id"] == repo_id), None)


def ready_repos() -> list[dict]:
    return [r for r in list_repos() if r["status"] == "ready"]


def get_report(repo_id: str) -> dict | None:
    p = _REPORTS / f"{repo_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def _update(repo_id: str, **fields) -> None:
    with _lock:
        repos = _load()
        for r in repos:
            if r["id"] == repo_id:
                r.update(fields)
        _save(repos)


# ---------- add / remove ----------

def _validate(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise ValueError(f"Path not found: {p}")
    n = subprocess.run(
        ["git", "-C", str(p), "rev-list", "--count", "HEAD"],
        capture_output=True, text=True, errors="ignore",
    )
    if n.returncode != 0:
        raise ValueError(f"Not a git repository: {p}")
    if int(n.stdout.strip() or 0) < 10:
        raise ValueError(
            f"Repo has only {n.stdout.strip()} commits — Astra needs real history "
            "(use a full clone, not --depth 1)"
        )
    return p


def _register(source: str, name: str | None) -> tuple[dict, str, str | None]:
    """Validate + add a 'queued' entry. Returns (entry, work_path, clone_url|None)."""
    source = source.strip()
    is_url = bool(_URL_RE.match(source))

    if is_url:
        base = source.rstrip("/").removesuffix(".git").split("/")[-1]
        name = (name or base).strip()
        repo_id = _slug(name)
        path, clone_url = str(_CLONES / repo_id), source
    else:
        p = _validate(source)
        name = (name or p.name).strip()
        repo_id = _slug(name)
        path, clone_url = str(p), None

    with _lock:
        repos = _load()
        if any(r["id"] == repo_id for r in repos):
            raise ValueError(f"Repo '{repo_id}' already exists in the workspace")
        entry = {
            "id": repo_id, "name": name, "path": path, "source": source,
            "status": "queued", "error": None, "added_at": int(time.time()),
            "stats": {},
        }
        repos.append(entry)
        _save(repos)
    return entry, path, clone_url


def add_repo(source: str, name: str | None = None) -> dict:
    """Public entry: accepts a Git URL ONLY. Local paths are rejected so an exposed
    instance can't be pointed at other git repos on the host to read their source."""
    if not _URL_RE.match(source.strip()):
        raise ValueError("Only Git URLs are accepted (e.g. https://github.com/owner/repo).")
    entry, path, clone_url = _register(source, name)
    threading.Thread(target=_process, args=(entry["id"], path, clone_url), daemon=True).start()
    return entry


# Demo workspace seeded on first boot of the hosted Space (ASTRA_SEED=1). Cloned at
# HEAD and analyzed fresh, so it's always self-consistent. Sequential to keep peak RAM low.
_DEMO_REPOS = [
    ("flask", "https://github.com/pallets/flask.git"),
    ("requests", "https://github.com/psf/requests.git"),
    ("lightweight-embeddings", "https://github.com/lh0x00/lightweight-embeddings"),
]


def seed_demo() -> None:
    for name, url in _DEMO_REPOS:
        try:
            entry, path, clone_url = _register(url, name)
        except ValueError:
            continue  # already present
        _process(entry["id"], path, clone_url)  # synchronous → one repo at a time


def _clone(repo_id: str, url: str, dest: str) -> None:
    _CLONES.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rm", "-rf", dest], check=True)
    r = subprocess.run(
        ["git", "clone", url, dest],
        capture_output=True, text=True, errors="ignore", timeout=600,
    )
    if r.returncode != 0:
        raise ValueError(f"git clone failed: {(r.stderr or '').strip()[:200]}")
    _validate(dest)  # full history check applies to clones too


def _process(repo_id: str, path: str, clone_url: str | None = None) -> None:
    try:
        if clone_url:
            _update(repo_id, status="cloning")
            _clone(repo_id, clone_url, path)
        _update(repo_id, status="analyzing")
        report = risk.analyze(path)
        _REPORTS.mkdir(parents=True, exist_ok=True)
        (_REPORTS / f"{repo_id}.json").write_text(json.dumps(report, indent=2))

        _update(repo_id, status="ingesting")
        from astra.ingest import ingest_repo
        n_chunks = ingest_repo(path, repo_id)

        _update(repo_id, status="ready", stats={
            "chunks": n_chunks,
            "source_files": report["summary"]["source_files"],
            "contributors": report["summary"]["contributors"],
            "total_commits": report["summary"]["total_commits"],
            "top_risk_file": report["danger_zones"][0]["file"] if report["danger_zones"] else None,
            "top_risk": report["danger_zones"][0]["risk"] if report["danger_zones"] else None,
        })
    except Exception as e:  # noqa: BLE001 — surface in the UI instead of dying silently
        _update(repo_id, status="error", error=str(e)[:300])


def remove_repo(repo_id: str) -> None:
    from astra import store
    try:
        store.get_collection().delete(where={"repo": repo_id})
    except Exception:  # noqa: BLE001 — registry cleanup must proceed regardless
        pass
    (_REPORTS / f"{repo_id}.json").unlink(missing_ok=True)
    clone_dir = (_CLONES / repo_id).resolve()
    if clone_dir.exists() and str(clone_dir).startswith(str(_CLONES.resolve())):
        subprocess.run(["rm", "-rf", str(clone_dir)], check=False)
    with _lock:
        _save([r for r in _load() if r["id"] != repo_id])
