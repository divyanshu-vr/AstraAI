# ✶ Astra — the map of what nobody wrote down

> A new engineer joins on Monday. The one person who understood the auth module left in March.
> The docs cover the easy half of the codebase; the hard half lives in people's heads — and people leave.
>
> **Astra reads the half nobody wrote down.** It mines git history, code ownership and the import
> graph across every repo you own, then briefs your next engineer the way a departing senior would:
> what breaks if the top contributor leaves, which files are silent landmines, what to learn first,
> and *who to ask.*

<p align="center"><em>RAG over docs is table stakes. The win is reading the <strong>tribal knowledge</strong> — the signals that exist in no document. Computed locally and deterministically from git + imports; the LLM narrates over real numbers, never vibes. The whole stack runs <strong>$0</strong> on free tiers.</em></p>

---

## 🌟 The Problem: knowledge that lives in no document

Every codebase holds critical knowledge that was never written down — and it's expensive:

- 🧠 **Tribal knowledge.** Why a module is fragile, who *really* owns auth, which file breaks everything — it's in someone's head. They might resign on Friday.
- 🚌 **Silent bus factor.** Single-owner files accumulate invisibly. Nobody notices the bus factor of one until the bus arrives.
- 🗺️ **Blind onboarding.** New engineers burn months reconstructing context, while seniors repeat themselves instead of building.
- 📉 **Doc drift.** The README confidently describes code that changed two years ago.

Generic AI assistants answer questions *about documentation*. But the most important questions —
*"what happens to this team if she leaves?"*, *"what should I learn first and who do I ask?"* — have
no answer in any document. They're hidden in the git history and the dependency graph.

## 💡 The Solution: Astra

Astra is a **codebase-intelligence and onboarding agent**. You add the repositories your team owns
(by Git URL); Astra clones each one and runs two passes:

1. **A deterministic analysis pass** over git history and imports — *no LLM, no guessing* — producing a
   per-file risk score, knowledge silos, ownership maps and an import graph.
2. **A retrieval pass** that chunks and embeds the source so it can answer cited questions.

Then a single chat box and a set of visual instruments let anyone interrogate the result. Every claim
about the code is **grounded**: risk numbers come from arithmetic on real commits, and chat answers
carry `[n]` citations into real files — or Astra honestly says the corpus doesn't cover it.

## 🛠️ Key Features

| Instrument | What you get | Grounded in |
|---|---|---|
| **Risk Brief** ⭐ | *"David Lord solely owns 8 critical files — if he leaves, `sessions.py`, `signals.py`… have no other owner."* | git log (authorship · churn · idle) × import graph |
| **Danger Zones** ⭐ | Per-file **0–100** risk score with reasons: *central · single-owner · stale 1030d · no tests* | deterministic scoring, no LLM |
| **The Atlas** 🆕 | The import graph as an interactive map — each file a node sized by fan-in, colored by risk, every dependency a line. Click through to the source. | import-edge graph + risk |
| **Who to Ask** 🆕 | The org chart nobody wrote down: per person, what they own, how concentrated it is, who's gone quiet, and what breaks if they leave. | git authorship + ownership + activity |
| **Cited Chat** | Answers with `[n]` citations into real files across every selected repo — or an honest "the corpus doesn't cover it." | Chroma vector RAG |
| **Long-term Memory** 🆕 | Astra remembers *you* across sessions — your name, role, and what you last worked on — and personalizes accordingly. | per-user typed facts in a vector store |
| **Repo Explorer** | Walk the file tree with risk vision (ownership, idle authors, blast radius) and interrogate any file in place. | file content + its computed metrics |
| **Doc Drift** | Extracts checkable claims from the README and audits each against the actual code. | LLM-as-judge over retrieved source |

One chat box routes between Risk, Onboarding and RAG automatically (a lightweight intent router), and
the chat is **multi-repo** — it searches the whole workspace at once, with every selected repo represented.

## 🤖 How Astra Uses AI

Astra is deliberate about *where* AI belongs. Facts are computed; AI explains and retrieves.

1. **Retrieval-Augmented Generation (RAG).** Source is chunked, embedded locally with **FastEmbed**
   (`bge-small`, 384-dim ONNX), and stored in **Chroma**. At query time the question is embedded, the
   nearest chunks are retrieved (with a per-repo coverage guarantee so one repo can't monopolize the
   answer), and **Groq `llama-3.3-70b`** synthesizes a cited answer.
2. **The LLM narrates over computed evidence — it is never the source of truth.** Risk briefs and
   onboarding paths are generated *from* the deterministic git/graph numbers, with prompts that forbid
   inventing files or figures. The arithmetic is auditable; the LLM only translates it into prose.
3. **A heuristic intent router** classifies each question (risk / onboarding / RAG) and dispatches to
   the right skill — fast, transparent, zero-cost classification.
4. **Structured long-term memory.** After each exchange, an LLM extraction step distills *durable facts
   about the user* (typed `profile` / `event` / `knowledge`), which are embedded and stored per user.
   Before answering, the most relevant facts are recalled and injected — a persistent memory layer
   built on top of a stateless model.
5. **LLM-as-judge (Doc Drift).** The model extracts checkable claims from documentation, then audits
   each against retrieved source code and returns a *supported / drifted* verdict.
6. **File interrogation.** Ask about a specific file and the LLM reasons over its line-numbered content
   plus its computed metrics (ownership, fan-in, test coverage).

## 🏗️ Architecture

```
                         ┌─────────── ANALYSIS — the differentiator ★ (no LLM) ───────────┐
  Git URL ──► clone ─────┤ gitstats.py   one git-log pass → authorship, churn, recency,    │
  (workspace.py,         │               owner-idle, per-author activity                    │
   URL-only, multi-repo) │ codegraph.py  imports → fan-in, has_tests, import-edge graph     │──► .astra/reports/<id>.json
                         │ risk.py       score → danger zones · knowledge silos · ownership │
                         │ people.py     git → the "who to ask" directory                   │
                         └─────────────────────────────────────────────────────────────────┘
                         ┌─────────── RAG — table stakes ─────────────────────────────────┐
  repo files ───────────┤ chunk → FastEmbed (bge-small, 384d, local) → Chroma (per-repo)  │
                         └─────────────────────────────────────────────────────────────────┘
                         ┌─────────── CONVERSATION ───────────────────────────────────────┐
                         │ route.py  risk / onboarding / RAG     sessions.py  threads      │
                         │ memory.py per-user typed facts (recall + remember)              │
                         └─────────────────────────────────────────────────────────────────┘
                                          │
        FastAPI  /api/{repos,status,report,brief,onboarding,ask,tree,file,file/ask,drift,people,graph,session}
                                          │   LLM = Groq llama-3.3-70b (outputs cached)
        Vite + React "Dossier" UI — landing · workspace · explorer · chat · onboarding (Atlas + Who-to-Ask)
                              (reagraph for the Atlas, code-split off the landing)
```

### Module structure

```
astra/
├─ workspace.py    # multi-repo registry: clone → analyze → ingest (background), URL-only
├─ gitstats.py     # R1 — per-file git stats in one log pass + per-author activity
├─ codegraph.py    # R2 — import fan-in, has_tests, and the import-edge graph
├─ risk.py         # R3 — danger zones · knowledge silos · ownership-by-dir scoring
├─ people.py       # the "who to ask" directory assembled from the report + activity
├─ chunk.py · ingest.py · embeddings.py · store.py · retrieve.py · answer.py   # RAG
├─ route.py        # heuristic intent router (risk / onboarding / RAG)
├─ memory.py       # long-term per-user memory (typed facts: profile/event/knowledge)
├─ sessions.py     # server-side conversation threads (windowed history)
├─ drift.py        # doc-vs-code drift audit
├─ skills/         # risk_brief · onboarding_path
├─ server.py       # FastAPI: JSON API + serves the SPA
└─ slack_bot.py    # optional Slack interface (Socket Mode)
```

## 🚀 Getting Started

### Prerequisites
- Python 3.11+ and Node 18+
- A free **Groq** API key (`GROQ_API_KEY`). A Gemini key is optional (only if you switch embedding providers).

### Run locally
```bash
# 1. install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add GROQ_API_KEY

# 2. build the frontend
cd frontend && npm install && npm run build && cd ..

# 3. serve  → http://localhost:7700
ASTRA_HOST=0.0.0.0 python -m astra.server
```
Open the **Workspace** page and add any public repo by URL (use a full clone with real history —
not `--depth 1`). Astra clones, analyzes and indexes it in the background; the card fills in live.

CLI equivalents (point at any local full clone):
```bash
python -m astra.analyze /path/to/repo     # risk dossier  → .astra/  (seconds, no LLM)
python -m astra.ingest  /path/to/repo     # RAG corpus    → .chroma
python -m astra.ask "how does routing work?"
```

### Deploy
Astra ships as a single multi-stage Docker image (React build → Python server), so it runs anywhere Docker does.

## 🌐 Why Astra Is Different

1. **It reads what no document contains** — git history and the import graph, not just the docs.
2. **Facts are computed, not generated.** Every risk number is deterministic arithmetic you can audit;
   the LLM only narrates over it.
3. **It maps people, not just code** — the de-facto org chart and bus-factor risk, reconstructed from commits.
4. **It's honest.** Answers cite real files or admit ignorance; "author idle" is framed as *inferred from commit activity*.
5. **It remembers you** across sessions, and the whole stack runs **$0** on free tiers — local embeddings, free LLM tier, local vector store.

## 🔮 Roadmap

- Near-duplicate memory de-duplication and a visible "Astra remembers…" surface in the UI
- Live, data-backed landing visuals (currently an illustrative showcase)
- Rolling-summary compaction for very long sessions
- Trend analysis across time (is a file's bus factor getting worse?)

## ⚖️ Honest framing

- "Author idle" is inferred **from commit activity**, not HR data.
- Import fan-in is a cross-language heuristic (exact for Python-style imports).
---

Made by **Divyanshu Verma**.
