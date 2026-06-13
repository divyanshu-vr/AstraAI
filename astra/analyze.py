"""R4 — analyze a repo's git/ownership/risk and persist .astra/report.json.

Usage: python -m astra.analyze <repo_path>
The report is consumed by skills/risk_brief.py and skills/onboarding_path.py.
"""

import json
import sys
from pathlib import Path

from astra import risk

_REPORT_DIR = Path(__file__).resolve().parent.parent / ".astra"
_REPORT_PATH = _REPORT_DIR / "report.json"


def analyze_repo(repo: str) -> tuple[dict, Path]:
    rep = risk.analyze(repo)
    _REPORT_DIR.mkdir(exist_ok=True)
    _REPORT_PATH.write_text(json.dumps(rep, indent=2))
    return rep, _REPORT_PATH


def load_report() -> dict | None:
    if not _REPORT_PATH.exists():
        return None
    return json.loads(_REPORT_PATH.read_text())


def format_for_llm(report: dict) -> str:
    """Compact, number-dense rendering the skills hand to Groq (the LLM narrates over THIS)."""
    lines = [f"REPO: {report['repo']}", ""]

    tc = report.get("top_contributors", [])
    lines.append("TOP CONTRIBUTORS (overall commits): " + ", ".join(f"{n} ({c})" for n, c in tc[:8]))
    lines.append("")

    lines.append("KNOWLEDGE SILOS (single-owner source files — 'what breaks if they leave'):")
    for s in report.get("knowledge_silos", []):
        tops = ", ".join(f"{t['file']}(fan-in {t['fan_in']})" for t in s["top_files"])
        lines.append(
            f"  - {s['author']}: {s['owned_files']} solely-owned files, blast-radius fan-in "
            f"{s['blast_radius_fan_in']}. Top: {tops}"
        )
    lines.append("")

    lines.append("DANGER ZONES (risk score 0-100, with computed metrics + reasons):")
    for r in report.get("danger_zones", []):
        lines.append(
            f"  - {r['risk']:.0f}  {r['file']} | fan-in {r['fan_in']}, "
            f"primary {r['primary_author']} ({r['author_concentration']:.0%}), "
            f"{r['contributors']} contributors, last change {r['last_commit_age_days']:.0f}d ago, "
            f"author idle {r['primary_author_idle_days']:.0f}d, tests={r['has_tests']} "
            f"| {', '.join(r['reasons'])}"
        )
    lines.append("")

    lines.append("OWNERSHIP BY DIRECTORY:")
    for o in report.get("ownership_by_dir", []):
        lines.append(f"  - {o['dir']}: {o['files']} files, top owner {o['top_owner']} ({o['owner_share']:.0%})")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m astra.analyze <repo_path>")
    rep, out = analyze_repo(sys.argv[1])
    dz = rep["danger_zones"]
    print(f"Analyzed {rep['summary']['source_files']} source files → {out}")
    if dz:
        print(f"Top danger zone: {dz[0]['file']} (risk {dz[0]['risk']}) — {', '.join(dz[0]['reasons'])}")
