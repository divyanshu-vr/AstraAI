"""R6 — LLM produces an ordered learn-first path with who-to-ask, grounded in the risk report.

Usage: python -m astra.skills.onboarding_path "new backend engineer"
"""

import sys

from astra import analyze, llm

SYSTEM = (
    "You are Astra, onboarding a new engineer to a codebase. "
    "You are given the engineer's role/goal and COMPUTED centrality/ownership metrics from git + the import graph. "
    "Produce an ORDERED learning path:\n"
    "- Which files/modules to understand FIRST -> later, ordered by how foundational/central they are (use fan-in).\n"
    "- For each, one line on WHY it matters and WHO to ask (the primary author of that area).\n"
    "- End with 2-3 'watch out' notes for the risky/untested/stale files they'll inevitably touch.\n"
    "Use ONLY the provided data; cite real file paths and real names. Be concrete and concise."
)


def path(role: str, report: dict | None = None) -> str:
    report = report or analyze.load_report()
    if not report:
        return "No analysis found. Run:  python -m astra.analyze <repo_path>"
    user = (
        f"New engineer's role/goal: {role}\n\n"
        f"{analyze.format_for_llm(report)}\n\n"
        "Produce the ordered learning path with who-to-ask."
    )
    return llm.complete(SYSTEM, user)


if __name__ == "__main__":
    role = " ".join(sys.argv[1:]) or "new backend engineer joining the team"
    print(path(role))
