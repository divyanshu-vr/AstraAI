"""R1 — per-file git statistics in ONE log pass (authorship, churn, recency, owner-idle).

Signals no document contains. Feeds risk.py.
"""

import subprocess
import time

_DAY = 86400
_HEADER = "COMMIT\t"


def _run(repo: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        errors="ignore",
        check=True,
    ).stdout


def _current_files(repo: str) -> set[str]:
    return set(_run(repo, "ls-files").splitlines())


def _norm_path(path: str) -> str:
    """Collapse git rename notations to the new path: 'a => b' and 'src/{old => new}.py'."""
    if "=>" not in path:
        return path
    if "{" in path and "}" in path:
        pre, rest = path.split("{", 1)
        inner, post = rest.split("}", 1)
        new = inner.split("=>")[-1].strip()
        return (pre + new + post).replace("//", "/")
    return path.split("=>")[-1].strip()


def _collect(repo: str):
    """Return (files, author_last_active). files[path] = {commits, authors{name:count}, last_ts, first_ts}."""
    out = _run(repo, "log", "--no-merges", "--numstat", f"--format={_HEADER}%H\t%an\t%at")
    files: dict[str, dict] = {}
    author_last: dict[str, int] = {}
    cur_author, cur_ts = None, None

    for line in out.splitlines():
        if line.startswith(_HEADER):
            _, _h, author, ts = line.split("\t", 3)
            cur_author, cur_ts = author, int(ts)
            if author_last.get(author, 0) < cur_ts:
                author_last[author] = cur_ts
        elif line and (line[0].isdigit() or line.startswith("-\t")):
            parts = line.split("\t")
            if len(parts) < 3 or cur_ts is None:
                continue
            path = _norm_path(parts[2])
            f = files.get(path)
            if f is None:
                f = files[path] = {"commits": 0, "authors": {}, "last_ts": 0, "first_ts": cur_ts}
            f["commits"] += 1
            f["authors"][cur_author] = f["authors"].get(cur_author, 0) + 1
            f["last_ts"] = max(f["last_ts"], cur_ts)
            f["first_ts"] = min(f["first_ts"], cur_ts)
    return files, author_last


def compute(repo: str, now: int | None = None) -> dict[str, dict]:
    """Per-file git stats for files that CURRENTLY exist in the repo."""
    now = now or int(time.time())
    files, author_last = _collect(repo)
    current = _current_files(repo)

    stats: dict[str, dict] = {}
    for path, f in files.items():
        if path not in current or not f["authors"]:
            continue
        commits = f["commits"]
        primary, primary_count = max(f["authors"].items(), key=lambda kv: kv[1])
        stats[path] = {
            "commits": commits,
            "contributors": len(f["authors"]),
            "primary_author": primary,
            "author_concentration": round(primary_count / commits, 3),
            "last_commit_age_days": round((now - f["last_ts"]) / _DAY, 1),
            "primary_author_idle_days": round((now - author_last.get(primary, f["last_ts"])) / _DAY, 1),
            "first_commit_age_days": round((now - f["first_ts"]) / _DAY, 1),
        }
    return stats


def author_activity(repo: str, now: int | None = None) -> dict[str, float]:
    """Per-author days since their last commit (one log pass). Feeds the people directory."""
    now = now or int(time.time())
    out = _run(repo, "log", "--no-merges", "--all", "--format=%an\t%at")
    last: dict[str, int] = {}
    for line in out.splitlines():
        name, _, ts = line.partition("\t")
        if not ts:
            continue
        t = int(ts)
        if last.get(name, 0) < t:
            last[name] = t
    return {name: round((now - t) / _DAY, 1) for name, t in last.items()}


def top_contributors(repo: str, n: int = 10) -> list[tuple[str, int]]:
    out = _run(repo, "shortlog", "-sn", "--all", "--no-merges")
    res: list[tuple[str, int]] = []
    for line in out.splitlines():
        count, _, name = line.strip().partition("\t")
        try:
            res.append((name.strip(), int(count.strip())))
        except ValueError:
            continue
    return res[:n]


if __name__ == "__main__":
    import sys

    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    s = compute(repo)
    print(f"{len(s)} current files with history\n")
    print("Top 8 single-owner files by author concentration (potential silos):")
    silos = sorted(s.items(), key=lambda kv: (-kv[1]["author_concentration"], -kv[1]["commits"]))
    for path, st in [x for x in silos if x[1]["commits"] >= 3][:8]:
        print(
            f"  {st['author_concentration']:.0%} {st['primary_author'][:18]:18} "
            f"commits={st['commits']:3} idle={st['primary_author_idle_days']:.0f}d  {path}"
        )
