"""Astra web server: workspace-aware JSON API over the verified skills + the SPA.

Run:  ASTRA_HOST=0.0.0.0 python -m astra.server   →  http://localhost:7700
"""

import os
import subprocess
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from astra import codegraph, gitstats, llm, workspace
from astra.skills import onboarding_path as onboarding_skill
from astra.skills import risk_brief

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Astra")

# In-memory caches: git/graph stats per repo path + LLM outputs (Groq ≈ 100k tok/day).
_cache: dict = {"stats": {}, "brief": {}, "onboarding": {}, "drift": {}}
_FILE_PREVIEW_BYTES = 60_000
_FILE_ASK_CHARS = 48_000  # ~12k tokens; fits llama-3.3-70b's 128k context with room to spare


# ---------- helpers ----------

def _repo_entry(repo: str | None) -> dict:
    ready = workspace.ready_repos()
    if not ready:
        raise HTTPException(404, "No repos in the workspace yet — add one on the Workspace page.")
    if repo is None:
        return ready[0]
    entry = next((r for r in ready if r["id"] == repo), None)
    if not entry:
        raise HTTPException(404, f"Repo '{repo}' not found or not ready")
    return entry


def _report_for(entry: dict) -> dict:
    rep = workspace.get_report(entry["id"])
    if not rep:
        raise HTTPException(404, f"No report for repo '{entry['id']}'")
    return rep


def _repo_stats(entry: dict) -> dict:
    """gitstats + codegraph for a repo, computed once per path and cached."""
    key = entry["path"]
    if key not in _cache["stats"]:
        _cache["stats"][key] = {
            "git": gitstats.compute(key),
            "graph": codegraph.compute(key),
            "ls": subprocess.run(
                ["git", "-C", key, "ls-files"],
                capture_output=True, text=True, errors="ignore", check=True,
            ).stdout.splitlines(),
        }
    return _cache["stats"][key]


def _risk_index(rep: dict) -> dict[str, dict]:
    return {r["file"]: r for r in rep.get("danger_zones", [])}


# ---------- request models ----------

class AskBody(BaseModel):
    question: str
    history: str | None = None
    repos: list[str] | None = None
    user_id: str | None = None
    session_id: str | None = None


class FileAskBody(BaseModel):
    repo: str | None = None
    path: str
    question: str


class RoleBody(BaseModel):
    role: str
    repo: str | None = None


class RepoBody(BaseModel):
    path: str
    name: str | None = None


# ---------- startup: seed the demo workspace at runtime (hosted Space) ----------

@app.on_event("startup")
def _seed_on_startup():
    # Embedding can't run in HF's low-RAM build step, so seed here (16GB runtime).
    # Server binds the port immediately; ingestion runs in the background and the
    # repo cards fill in live as each one becomes ready.
    if os.getenv("ASTRA_SEED") and not workspace.list_repos():
        threading.Thread(target=workspace.seed_demo, daemon=True).start()


# ---------- workspace ----------

@app.get("/api/repos")
def repos_list():
    return {"repos": workspace.list_repos()}


@app.post("/api/repos")
def repos_add(body: RepoBody):
    try:
        return workspace.add_repo(body.path, body.name)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.delete("/api/repos/{repo_id}")
def repos_remove(repo_id: str):
    workspace.remove_repo(repo_id)
    return {"ok": True}


@app.get("/api/status")
def status():
    repos = workspace.list_repos()
    ready = [r for r in repos if r["status"] == "ready"]
    chroma_count = None
    try:
        from astra import store
        chroma_count = store.get_collection().count()
    except Exception:  # noqa: BLE001 — status must never 500 on a cold chroma
        pass
    return {
        "repos": len(repos),
        "ready": len(ready),
        "chroma_chunks": chroma_count,
        "workspace": [
            {"id": r["id"], "name": r["name"], "status": r["status"], "stats": r.get("stats", {})}
            for r in repos
        ],
    }


# ---------- per-repo analysis ----------

@app.get("/api/report")
def report(repo: str | None = None):
    entry = _repo_entry(repo)
    rep = _report_for(entry)
    rep["repo_id"] = entry["id"]
    return rep


@app.get("/api/brief")
def brief(repo: str | None = None):
    entry = _repo_entry(repo)
    rep = _report_for(entry)
    key = (entry["id"], rep["generated_at"])
    if key not in _cache["brief"]:
        _cache["brief"][key] = risk_brief.brief(rep)
    return {"text": _cache["brief"][key], "repo": entry["id"]}


@app.post("/api/onboarding")
def onboarding(body: RoleBody):
    entry = _repo_entry(body.repo)
    rep = _report_for(entry)
    key = (entry["id"], rep["generated_at"], body.role.strip().lower())
    if key not in _cache["onboarding"]:
        _cache["onboarding"][key] = onboarding_skill.path(body.role, rep)
    return {"text": _cache["onboarding"][key], "repo": entry["id"]}


@app.get("/api/people")
def people_directory(repo: str | None = None):
    """Who-to-ask: per-person profiles (areas owned, blast radius, idle, bus-factor)."""
    from astra import people
    entry = _repo_entry(repo)
    rep = _report_for(entry)
    activity = gitstats.author_activity(entry["path"])
    return {"repo": entry["id"], "people": people.directory(rep, activity)}


@app.get("/api/graph")
def code_graph(repo: str | None = None, limit: int = 40):
    """Import-graph atlas: top-`limit` central files as nodes + edges among them,
    joined with risk + owner so the frontend can size by fan-in and color by risk."""
    entry = _repo_entry(repo)
    nodes_f, edges, fan_in, has_test = codegraph.graph_data(entry["path"], limit=limit)
    risk_idx = _risk_index(_report_for(entry))
    git = _repo_stats(entry)["git"]
    nodes = []
    for f in nodes_f:
        r = risk_idx.get(f)
        g = git.get(f)
        nodes.append({
            "id": f,
            "label": f.split("/")[-1],
            "fan_in": fan_in[f],
            "risk": r["risk"] if r else None,
            "has_tests": has_test.get(f, False),
            "dir": "/".join(f.split("/")[:-1]) or ".",
            "owner": g["primary_author"] if g else None,
        })
    links = [{"id": f"{s}->{t}", "source": s, "target": t} for s, t in edges]
    return {"repo": entry["id"], "nodes": nodes, "links": links}


@app.get("/api/drift")
def drift_scan(repo: str | None = None):
    from astra import drift
    entry = _repo_entry(repo)
    key = (entry["id"],)
    if key not in _cache["drift"]:
        _cache["drift"][key] = drift.scan(entry["id"], entry["path"])
    return {"repo": entry["id"], "claims": _cache["drift"][key]}


# ---------- chat (multi-repo) ----------

@app.post("/api/ask")
def ask(body: AskBody):
    from astra import memory, route, sessions
    # Server-side session is the source of truth: the client sends only session_id,
    # we reconstruct a windowed history here (falls back to client-sent history for Slack).
    history = sessions.history_str(body.session_id) if body.session_id else body.history
    result = route.dispatch(body.question, history=history, repos=body.repos, user_id=body.user_id)
    if body.session_id:
        sessions.append(body.session_id, body.question, result["answer"], result.get("sources"), result.get("skill"))
    if body.user_id:  # distil + persist durable facts off the hot path
        threading.Thread(
            target=memory.remember, args=(body.user_id, body.question, result["answer"]), daemon=True
        ).start()
    return result


@app.get("/api/session/{session_id}")
def session_get(session_id: str):
    from astra import sessions
    return {"turns": sessions.get(session_id)}


@app.delete("/api/session/{session_id}")
def session_reset(session_id: str):
    from astra import sessions
    sessions.reset(session_id)
    return {"ok": True}


# ---------- explorer ----------

@app.get("/api/tree")
def tree(repo: str | None = None):
    entry = _repo_entry(repo)
    stats = _repo_stats(entry)
    risk_idx = _risk_index(_report_for(entry))
    files = []
    for path in stats["ls"]:
        g = stats["git"].get(path)
        cg = stats["graph"].get(path)
        r = risk_idx.get(path)
        files.append({
            "path": path,
            "risk": r["risk"] if r else None,
            "fan_in": cg["fan_in"] if cg else None,
            "has_tests": cg["has_tests"] if cg else None,
            "primary_author": g["primary_author"] if g else None,
            "author_concentration": g["author_concentration"] if g else None,
            "commits": g["commits"] if g else None,
            "last_commit_age_days": g["last_commit_age_days"] if g else None,
        })
    return {"repo": entry["id"], "repo_path": entry["path"], "files": files}


@app.get("/api/file")
def file_detail(path: str, repo: str | None = None):
    entry = _repo_entry(repo)
    root = Path(entry["path"]).resolve()
    stats = _repo_stats(entry)
    if path not in set(stats["ls"]):
        raise HTTPException(404, "File not tracked in this repo")
    full = (root / path).resolve()
    if not str(full).startswith(str(root)):
        raise HTTPException(400, "Invalid path")
    try:
        raw = full.read_bytes()[:_FILE_PREVIEW_BYTES]
        content = raw.decode("utf-8", errors="ignore")
    except OSError:
        content = ""
    return {
        "repo": entry["id"],
        "path": path,
        "git": stats["git"].get(path),
        "graph": stats["graph"].get(path),
        "risk": _risk_index(_report_for(entry)).get(path),
        "content": content,
        "truncated": full.stat().st_size > _FILE_PREVIEW_BYTES,
    }


_FILE_ASK_SYSTEM = (
    "You are Astra, explaining one specific file from a codebase to an engineer. "
    "You are given the file's content with a line number prefixing every line (format `<n>: <code>`), "
    "plus COMPUTED metrics from git history and the import graph. Answer using ONLY this material. "
    "When asked about a line number, use the `<n>:` prefixes to find it exactly. "
    "If the content is marked truncated and the line isn't shown, say so plainly. "
    "If the metrics show risk (single owner, idle author, no tests, high fan-in), weave that in. "
    "Never invent code or numbers. Be concise."
)


def _number_lines(text: str, budget: int) -> tuple[str, bool]:
    """Prefix each line with its 1-based number; cut to `budget` chars on a line boundary."""
    out, used = [], 0
    for i, line in enumerate(text.split("\n"), 1):
        row = f"{i}: {line}"
        if used + len(row) + 1 > budget:
            return "\n".join(out), True
        out.append(row)
        used += len(row) + 1
    return "\n".join(out), False


@app.post("/api/file/ask")
def file_ask(body: FileAskBody):
    detail = file_detail(body.path, repo=body.repo)
    g, cg, r = detail["git"], detail["graph"], detail["risk"]
    metrics = []
    if g:
        metrics.append(
            f"commits={g['commits']}, contributors={g['contributors']}, "
            f"primary_author={g['primary_author']} ({g['author_concentration']:.0%}), "
            f"last change {g['last_commit_age_days']:.0f}d ago, "
            f"primary author idle {g['primary_author_idle_days']:.0f}d"
        )
    if cg:
        metrics.append(f"fan_in={cg['fan_in']}, has_tests={cg['has_tests']}")
    if r:
        metrics.append(f"risk_score={r['risk']} ({', '.join(r['reasons'])})")

    numbered, cut = _number_lines(detail["content"], _FILE_ASK_CHARS)
    trunc = " (TRUNCATED — later lines not shown)" if (cut or detail["truncated"]) else ""
    user = (
        f"FILE: {body.path} (repo: {detail['repo']})\n"
        f"METRICS: {' | '.join(metrics) or 'n/a'}\n\n"
        f"CONTENT{trunc}:\n{numbered}\n\n"
        f"QUESTION: {body.question}"
    )
    return {"answer": llm.complete(_FILE_ASK_SYSTEM, user), "path": body.path, "repo": detail["repo"]}


# ---------- static frontend (SPA) ----------

_DIST = ROOT / "frontend" / "dist"

if _DIST.exists():
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str = ""):
        candidate = (_DIST / full_path).resolve()
        if full_path and candidate.is_file() and str(candidate).startswith(str(_DIST)):
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("ASTRA_HOST", "localhost"),
        port=int(os.getenv("ASTRA_PORT", "7700")),
    )
