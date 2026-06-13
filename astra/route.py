"""D4 — heuristic router: one chat entry point, three skills, workspace-aware.

  'risk'       → narrate from the computed report(s) ("what breaks if X leaves?")
  'onboarding' → ordered learn-first path for the stated role
  'rag'        → cited retrieval answer across the selected repos (default)
"""

import re

from astra import analyze, llm, memory, workspace
from astra import answer as answer_mod

_MEM_CLAUSE = (
    " An 'ABOUT THIS USER' block may precede the evidence — facts remembered about this user across "
    "sessions. Use it to personalize ordering/tone and to answer questions about the user themselves; "
    "claims about the CODE must still come from the evidence below."
)

_RISK = re.compile(
    r"\b(bus factor|danger|risk|risky|silo|leaves?|left|quits?|gets hit|"
    r"who owns|ownership|single owner|breaks if|idle author)\b", re.I)
_ONBOARD = re.compile(
    r"\b(onboard\w*|new (\w+ )?(engineer|dev|developer|hire|joiner)|joining|"
    r"learn first|start( learning)?|where (do|should) i (start|begin)|learning path|"
    r"what (should|do) i (do|learn|read|tackle|study|focus on) (first|next))\b", re.I)

_RISK_SYSTEM = (
    "You are Astra. Answer the user's question using ONLY the computed git/ownership "
    "evidence below (real numbers from git history + the import graph; possibly several "
    "repos, each under a 'REPO:' header). Cite real file paths and real names — prefix "
    "files with their repo when more than one repo is present. Never invent. Frame "
    "author-idleness honestly as 'based on commit activity'. Be direct and concise."
)

_ONBOARD_SYSTEM = (
    "You are Astra, onboarding a new engineer to a workspace of repositories. "
    "Given their role/goal and COMPUTED centrality/ownership metrics (one 'REPO:' block "
    "per repo), produce an ORDERED learning path: which repo + files to understand first "
    "and later (use fan-in), one line on WHY each matters and WHO to ask (the primary "
    "author). End with 2-3 'watch out' notes on the riskiest files they'll touch. "
    "Use ONLY the provided data; cite real paths and names. Be concrete and concise."
)


def classify(question: str) -> str:
    if _ONBOARD.search(question):
        return "onboarding"
    if _RISK.search(question):
        return "risk"
    return "rag"


def _selected_reports(repos: list[str] | None) -> list[tuple[str, dict]]:
    ready = workspace.ready_repos()
    if repos:
        ready = [r for r in ready if r["id"] in repos]
    out = []
    for r in ready:
        rep = workspace.get_report(r["id"])
        if rep:
            out.append((r["id"], rep))
    return out


def _evidence(reports: list[tuple[str, dict]]) -> str:
    return "\n\n".join(
        f"REPO: {rid}\n{analyze.format_for_llm(rep)}" for rid, rep in reports
    )


def _report_sources(reports: list[tuple[str, dict]], n: int = 3) -> list[dict]:
    out = []
    for rid, rep in reports:
        for z in rep.get("danger_zones", [])[:n]:
            out.append({"repo": rid, "source": z["file"], "chunk_index": "git analysis", "risk": z["risk"]})
    return out[:6]


def dispatch(
    question: str, history: str | None = None,
    repos: list[str] | None = None, user_id: str | None = None,
) -> dict:
    kind = classify(question)
    mem = memory.recall(user_id, question)

    if kind in ("risk", "onboarding"):
        reports = _selected_reports(repos)
        if reports:
            system = (_RISK_SYSTEM if kind == "risk" else _ONBOARD_SYSTEM) + (_MEM_CLAUSE if mem else "")
            prefix = "" if kind == "risk" else "New engineer's role/goal: " + question + "\n\n"
            user = f"{prefix}{memory.format_block(mem)}{_evidence(reports)}\n\nQUESTION: {question}"
            text = llm.complete(system, user)
            return {"answer": text, "sources": _report_sources(reports), "skill": kind}

    text, hits = answer_mod.answer(question, history=history, repos=repos, mem=mem)
    return {"answer": text, "sources": hits, "skill": "rag"}
