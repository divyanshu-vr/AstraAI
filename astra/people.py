"""The org chart nobody wrote down — per-person profiles assembled from the risk report
(top contributors, knowledge silos, ownership-by-dir) + per-author last-active.

Answers "who do I ask about X?" and "what breaks if they leave?" as data, not prose.
Pure assembly over already-computed signals; no LLM, no extra git work beyond activity.
"""


def directory(report: dict, activity: dict[str, float], limit: int = 12) -> list[dict]:
    commits = dict(report.get("top_contributors", []))         # name -> commit count
    silos = {s["author"]: s for s in report.get("knowledge_silos", [])}

    dirs_by_owner: dict[str, list[dict]] = {}
    for d in report.get("ownership_by_dir", []):
        dirs_by_owner.setdefault(d["top_owner"], []).append(
            {"dir": d["dir"], "files": d["files"], "share": d["owner_share"]}
        )

    names = set(commits) | set(silos) | set(dirs_by_owner)
    people = []
    for name in names:
        silo = silos.get(name)
        idle = activity.get(name)
        solely = silo["owned_files"] if silo else 0
        blast = silo["blast_radius_fan_in"] if silo else 0
        owns_dirs = sorted(dirs_by_owner.get(name, []), key=lambda x: -x["files"])[:4]
        people.append({
            "name": name,
            "commits": commits.get(name, 0),
            "last_active_days": idle,
            "owns_dirs": owns_dirs,
            "solely_owned_files": solely,
            "blast_radius": blast,
            "ask_about": [t["file"] for t in (silo["top_files"][:3] if silo else [])],
            # a person is a bus-factor risk if they solely own central code AND have gone quiet
            "bus_factor_risk": bool(solely >= 1 and idle is not None and idle >= 180),
        })

    people.sort(key=lambda p: (-p["blast_radius"], -p["solely_owned_files"], -p["commits"]))
    return people[:limit]
