"""R5 — LLM narrates the computed risk report into a 'what breaks if X leaves' briefing.

Usage: python -m astra.skills.risk_brief   (requires `python -m astra.analyze <repo>` first)
"""

from astra import analyze, llm

SYSTEM = (
    "You are Astra, briefing a new engineering lead on a codebase's KNOWLEDGE RISK. "
    "Everything you are given is COMPUTED from git history and the code import graph — real numbers, not opinions. "
    "Write a tight briefing using ONLY these numbers and file paths. Structure:\n"
    "1. Bus-factor risk — who solely owns critical code and what concretely breaks if they leave.\n"
    "2. Top danger zones — name the files and say why each is risky (central? single-owner? stale? untested?).\n"
    "3. Recommendations — 3-4 concrete actions (pair-up, add tests, write a design note), tied to specific files.\n"
    "Cite real file paths and the actual metrics. NEVER invent files, people, or numbers. "
    "Frame 'idle author' honestly as 'based on commit activity'. Be direct and concise."
)


def brief(report: dict | None = None) -> str:
    report = report or analyze.load_report()
    if not report:
        return "No analysis found. Run:  python -m astra.analyze <repo_path>"
    return llm.complete(SYSTEM, analyze.format_for_llm(report))


if __name__ == "__main__":
    print(brief())
