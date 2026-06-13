"""R3 — combine git + code-graph signals into a risk report (source files only).

Produces danger_zones, knowledge_silos (what breaks if X leaves), and ownership_by_dir.
Pure computation; the LLM narrates over this in skills/risk_brief.py.
"""

import time

from astra import codegraph, gitstats

# Dirs that aren't product source — excluded from danger/ownership scoring.
_EXCLUDE_DIRS = {
    "tests", "test", "__tests__", "examples", "example", "docs", "doc",
    "benchmarks", "benchmark", "bench", "fixtures", "scripts",
}


def _is_source(path: str) -> bool:
    return not any(part in _EXCLUDE_DIRS for part in path.split("/")[:-1])


def _reasons(fan, max_fan, conc, contributors, idle, age, has_tests, primary) -> list[str]:
    r = []
    if fan >= max(4, max_fan * 0.4):
        r.append(f"central (fan-in {fan})")
    if conc >= 0.8:
        r.append(f"single-owner ({conc:.0%} {primary})")
    elif conc >= 0.6 and contributors <= 3:
        r.append(f"concentrated ({conc:.0%} {primary})")
    if idle >= 180:
        r.append(f"primary author idle {idle:.0f}d")
    if not has_tests:
        r.append("no direct tests")
    if age >= 365:
        r.append(f"stale ({age:.0f}d since last change)")
    return r


def analyze(repo: str, now: int | None = None, top_n: int = 12) -> dict:
    now = now or int(time.time())
    gstats = gitstats.compute(repo, now=now)
    graph = codegraph.compute(repo)

    src = [f for f in graph if _is_source(f) and f in gstats]
    max_fan = max((graph[f]["fan_in"] for f in src), default=1) or 1

    rows = []
    for f in src:
        g, cg = gstats[f], graph[f]
        fan, conc = cg["fan_in"], g["author_concentration"]
        contributors, idle = g["contributors"], g["primary_author_idle_days"]
        age, has_tests = g["last_commit_age_days"], cg["has_tests"]

        score = 100 * (
            0.35 * (fan / max_fan)
            + 0.25 * conc
            + 0.20 * min(idle / 365, 1)
            + 0.10 * min(age / 365, 1)
            + 0.10 * (0 if has_tests else 1)
        )
        rows.append(
            {
                "file": f,
                "risk": round(score, 1),
                "fan_in": fan,
                "primary_author": g["primary_author"],
                "author_concentration": conc,
                "contributors": contributors,
                "commits": g["commits"],
                "last_commit_age_days": age,
                "primary_author_idle_days": idle,
                "has_tests": has_tests,
                "reasons": _reasons(fan, max_fan, conc, contributors, idle, age, has_tests, g["primary_author"]),
            }
        )
    rows.sort(key=lambda r: -r["risk"])

    return {
        "repo": repo,
        "generated_at": now,
        "summary": {
            "source_files": len(src),
            "total_commits": sum(c for _, c in gitstats.top_contributors(repo, n=10_000)),
            "contributors": len(gitstats.top_contributors(repo, n=10_000)),
        },
        "top_contributors": gitstats.top_contributors(repo, n=10),
        "danger_zones": rows[:top_n],
        "knowledge_silos": _silos(rows),
        "ownership_by_dir": _ownership_by_dir(rows),
    }


def _silos(rows: list[dict], min_conc: float = 0.8) -> list[dict]:
    """Group single-owner source files by author → 'what breaks if they leave'."""
    by_author: dict[str, list[dict]] = {}
    for r in rows:
        if r["author_concentration"] >= min_conc:
            by_author.setdefault(r["primary_author"], []).append(r)
    silos = []
    for author, files in by_author.items():
        files.sort(key=lambda r: -r["fan_in"])
        silos.append(
            {
                "author": author,
                "owned_files": len(files),
                "blast_radius_fan_in": sum(r["fan_in"] for r in files),
                "top_files": [{"file": r["file"], "fan_in": r["fan_in"]} for r in files[:6]],
            }
        )
    silos.sort(key=lambda s: (-s["owned_files"], -s["blast_radius_fan_in"]))
    return silos[:6]


def _ownership_by_dir(rows: list[dict]) -> list[dict]:
    by_dir: dict[str, dict[str, int]] = {}
    for r in rows:
        d = "/".join(r["file"].split("/")[:-1]) or "."
        by_dir.setdefault(d, {})
        by_dir[d][r["primary_author"]] = by_dir[d].get(r["primary_author"], 0) + 1
    out = []
    for d, owners in by_dir.items():
        total = sum(owners.values())
        top_owner, top_count = max(owners.items(), key=lambda kv: kv[1])
        out.append({"dir": d, "files": total, "top_owner": top_owner, "owner_share": round(top_count / total, 2)})
    out.sort(key=lambda o: -o["files"])
    return out[:10]


if __name__ == "__main__":
    import sys

    rep = analyze(sys.argv[1] if len(sys.argv) > 1 else ".")
    print(f"Source files scored: {rep['summary']['source_files']}\n")
    print("=== TOP DANGER ZONES ===")
    for r in rep["danger_zones"]:
        print(f"  risk={r['risk']:5.1f}  {r['file']}\n            {', '.join(r['reasons'])}")
    print("\n=== KNOWLEDGE SILOS (what breaks if they leave) ===")
    for s in rep["knowledge_silos"]:
        print(f"  {s['author']}: {s['owned_files']} solely-owned files, blast-radius fan-in {s['blast_radius_fan_in']}")
