# Astra — Tasks & Build Plan

> **One-liner:** Astra is an onboarding agent that turns a codebase's *tribal knowledge*
> (docs, code, the stuff that lives in a senior engineer's head) into **cited, conversational answers**
> — so a new hire (or the CTO) can ask "how does auth work here?" and get a grounded answer with sources.
>
> **The differentiator (this is the whole game):** RAG-over-docs is commodity and will NOT win — Konveyor only
> placed in a *category* track ("Best Python Agent", $5K), not a grand prize, and the grand-prize winners we
> researched were never RAG bots. Astra's edge is reading **what nobody wrote down** — git history, code
> ownership, churn, bus-factor, and doc-vs-code drift — to produce a live **risk map** ("what breaks if X leaves"),
> a grounded **onboarding path** ("learn this first, ask this person"), and stale-doc detection.
> The RAG Q&A is **table stakes**; the git/ownership analysis is the **win**. All signals are free, local,
> deterministic (git + AST) → the LLM reasons over computed numbers, not just retrieved text.
>
> **Skeleton borrowed from Konveyor** (Doc Navigator + Code Understanding + a 3rd skill + memory), but its weak
> "knowledge-gap taxonomy" 3rd skill is **REPLACED by the Tribal-Knowledge / Risk engine**. All Azure plumbing dropped.

**Status:** ✅ ALL CORE PHASES DONE + **Phase G: MULTI-REPO WORKSPACE** — A/B/C (RAG) · D (router) · D★ (risk engine) · E (Dossier UI) · F (polish) · G (workspace). All verified live.
Run: `cd /data/divyanshu/Astra && ASTRA_HOST=0.0.0.0 .venv/bin/python -m astra.server` → http://localhost:7700 (UI rebuild: `cd frontend && npm run build`).

### Phase G — Multi-repo workspace (user-directed pivot) ✅ DONE & VERIFIED
- `astra/workspace.py`: registry `.astra/repos.json` + per-repo reports `.astra/reports/<id>.json`; `POST /api/repos {path,name}` validates (git history check), then background-threads analyze→ingest with status (queued/analyzing/ingesting/ready/error). DELETE removes chunks+report.
- Chunks namespaced per repo (`<id>::path::n`, metadata `repo:`); retrieve/answer/route accept a repo filter; risk+onboarding combine MULTIPLE reports under `REPO:` headers.
- **UI:** new `/repos` Workspace page (add-repo form, polling status cards w/ stats, EXPLORE/ONBOARD/REMOVE); Explorer+Onboarding repo pills; **Chat searches all repos at once** with toggle pills + repo-badged source chips that deep-link `/explorer?repo=&path=`.
- **Landing fully neutral** — zero repo names; hero CTAs → Workspace; §02 shows aggregate workspace counts only.
- Verified live: flask + requests ingested via the API (2,646 chunks, requests = 917 in ~10s GPU); cross-repo question "How do sessions work?" answered with sources from BOTH repos, disambiguated per repo. 0 console errors. Screenshots `screenshots/w*.png`.
- **G2 — GitHub-URL ingestion** ✅: paste `https://github.com/owner/repo` → server clones into `.astra/clones/<id>` (status `cloning`), then the same analyze→ingest pipeline; REMOVE also deletes the clone. Local paths still accepted. Verified live: pallets/click URL → ready in ~20s.
- **G3 — Scroll containment fix** ✅: Lenis was hijacking wheel events over inner panels (chat log, file tree, code view scrolled the whole page). Fixed with `data-lenis-prevent` + `overscroll-behavior: contain` on all `.scroll` panels. Verified: wheel over code view → panel scrolls 800px, page moves 0px.

### Phase H — Free hosted demo (Hugging Face Spaces, Docker/CPU) ✅ BUILT & VERIFIED LOCALLY
- Why HF: measured Astra RSS = **883 MB**, so 512 MB free tiers OOM; "no cold start" rules out scale-to-zero (Render/Cloud Run). HF free = 16 GB, no card, no mid-demo sleep.
- `Dockerfile` (multi-stage: node builds `frontend/dist` → slim python) + `deploy/bootstrap.py` (build-time: clone flask+requests+embedding-model **pinned to SHAs** → analyze → CPU-ingest = 2,910 chunks) + `requirements-hf.txt` (CPU only) + `.dockerignore` + `README.md` (HF frontmatter) + `deploy/push-to-hf.sh` + `DEPLOY.md`.
- Verified: `docker build` succeeds end-to-end (~3 min); container boots demo-ready (3 repos / 2,910 chunks), SPA+explorer 200, cross-repo RAG + risk routing answer correctly through Groq, browser render confirmed. **Image = 790 MB.**
- Runtime secret: `GROQ_API_KEY` (Space secret). Embeddings local (FastEmbed CPU) — no key. Mathesar excluded from the image (531 MB) — editable via `REPOS` in bootstrap.
- **Deploy iteration (live):** Space `D1vyx/Astra` created. Two real issues found & fixed: (1) HF YAML validation rejected `emoji: ✶` + a 61-char description → emoji 🗺️, desc trimmed; (2) **build OOMKilled (exit 137)** — HF's free build VM can't run onnxruntime embedding. Fix: **moved ingest to RUNTIME** (`ASTRA_SEED=1` → `workspace.seed_demo()` in a startup thread, 16 GB, sequential). Verified locally as UID 1000: port binds instantly, repos ingest in background (flask 100s → requests 145s → embedding-model 160s, 2,910 chunks), cross-repo chat works. Light image, no LFS, OOM-proof build.
- **To go live (only step left, needs the user):** set `GROQ_API_KEY` secret on the Space, then re-run `bash deploy/push-to-hf.sh https://huggingface.co/spaces/D1vyx/Astra`. First boot warms up ~3 min (cards fill live); pre-warm before demo. See `DEPLOY.md`.

**Remaining: NOTHING on the board.** ✅ Every phase (A–H) + both stretch items closed. R7 drift verified live; Slack bot live (mrkdwn-formatted); hosted demo build-verified, one push from live.
**Next:** dry-run the demo script (§4 — open on /repos: paste a GitHub URL LIVE, watch cloning→ready in ~20s, then chat across repos → risk → onboarding → explorer → drift).
**Hackathon constraint:** 48h, must demo live, must run $0.

---

## 0. Reference repo (our correctness anchor)

We are **building lean from scratch**, but every component is ported from the original winner so we don't mess up.
- Original repo: `sdamache/konveyor-onboarding-agent` (Django + Azure, 123 py files — too heavy to fork directly).
- Local clone location: `/data/divyanshu/konveyor-onboarding-agent` (cloned ✅). Backup reference copy: `/tmp/konveyor-inspect`.
- **Rule:** before building each Astra file, open the mapped reference file, port the *logic + prompts*, swap only the provider calls (Azure → Groq/Gemini). The captured prompts/logic are saved in the **Appendix** below in case the clone isn't handy.

### File mapping (Astra ← reference)
| Astra file | Reference file | What to lift |
|---|---|---|
| `ingest.py` | `konveyor/core/documents/`, `apps/documents/services/` | chunking strategy |
| `retrieve.py` | `konveyor/core/rag/`, `apps/search/services/search_service.py` | retrieval + ranking |
| `answer.py` | `konveyor/core/generation/`, `core/formatters/` | **citation formatting** (see Appendix A) |
| `skills/doc_navigator.py` | `skills/documentation_navigator/DocumentationNavigatorSkill.py` | **query preprocessing + citations** (Appendix A,B) |
| `skills/code_understanding.py` | `skills/` (new — their code skill was lighter) | explain-snippet prompt (Appendix C) |
| `gitstats.py` · `codegraph.py` · `risk.py` · `skills/risk_brief.py` · `skills/onboarding_path.py` | **NET-NEW — no reference** ⭐ the differentiator | git + ownership + risk analysis → LLM synthesis |
| `memory.py` | `konveyor/core/conversation/memory.py` (InMemoryConversationManager) | conversation memory pattern + context-enhance (Appendix B) |
| `chat.py` | `konveyor/core/chat/skill.py` | generation system prompt (Appendix A) |
| `slack_bot.py` | `apps/bot/services/` | Slack event handling (do LAST) |

---

## 1. Stack (all free tier)

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| LLM (generation) | **Groq** `llama-3.3-70b-versatile` | free tier, very fast. Key: `GROQ_API_KEY` |
| Embeddings | **Gemini** `gemini-embedding-001` @ **768 dims** | free on Free Tier. Key: `GEMINI_API_KEY`. (`gemini-embedding-2` is newer/auto-normalizes — confirm exact ID against SDK when wiring.) |
| Vector DB | **Chroma** (local, persistent) | `pip install chromadb`, no server |
| Offline fallback embeddings | `sentence-transformers` (all-MiniLM-L6-v2) | if Gemini free-tier RPM bites during bulk ingest |
| Interface (phase 1) | CLI / simple FastAPI web UI | nail the core first |
| Interface (phase 2) | Slack bot (`slack_sdk` + Socket Mode) | do last, only if core is solid |
| Secrets | `.env` (`python-dotenv`) | NO Key Vault |

**`pip install`:** `groq google-genai chromadb python-dotenv tiktoken` (+ `fastapi uvicorn` for web, `slack_sdk` later, `sentence-transformers` if needed).

**Gotcha — Gemini free-tier rate limit:** RPM cap isn't published (check AI Studio dashboard). During **bulk ingestion**, batch embed calls + add a small `time.sleep()` between batches, or fall back to local sentence-transformers for ingest only. Query-time (1 embed per question) is fine.

---

## 2. Architecture

```
  ┌─────── ingestion (per repo) ───────┐   ┌──────── analysis (per repo) ★ ────────┐
 repo → chunk → Gemini embed → Chroma   │   repo/.git → gitstats (authorship, churn, │
        (for RAG retrieval)             │   recency) + codegraph (fan-in, tests)     │
                                        │   → risk scoring → .astra/report.json      │
  └─────────────────────────────────────┘  └─────────────────────────────────────────┘
                   │                                          │
     ┌─────────────┴─────────── query / command ─────────────┴──────────────┐
     │ [router] →                                                            │
     │   Doc Navigator     (RAG cited answer)        ← Chroma                │
     │   Code Understanding(explain + risk context)  ← Chroma + report       │
     │   Risk Brief        ("what breaks if X leaves")← report.json     ★     │
     │   Onboarding Path   (learn-first + who-to-ask) ← report.json + docs ★  │
     │   (stretch) Drift   (docs say X, code does Y)  ← RAG claim vs code     │
     │                    ↑ conversation memory ↑                            │
     └────────────────────────────────────────────────────────────────────────┘
                                    ↓
                    CLI / Web UI (risk-map viz)  →  (stretch) Slack
```

★ = the differentiator. **Two pipelines feed the skills:** RAG (text that exists) + the analysis report
(signals that exist in no doc — git/ownership/risk). The LLM reasons over BOTH. RAG alone = commodity; the
report is what no doc-chatbot can produce.

**RAG design note (already built):** unlike the reference (which concatenates chunks), Astra has Groq
**synthesize** a grounded answer with `[n]` citations + an accurate Sources list.

---

## 3. Task checklist (phased, each with a verify step)

### Phase A — Skeleton + config  ✅ DONE
- [x] A1. Project structure scaffolded.
- [x] A2. `.env.example` written.
- [x] A3. `config.py` loads `.env`, fails loud on missing keys.
- [x] A4. `llm.py` (Groq) + `embeddings.py` (Gemini) — verified live (real completion + 768-d normalized vectors).

### Phase B — Ingestion (the "read the codebase" part)  ✅ DONE
- [x] B1. `ingest.py` walks a repo (ext allowlist; skips node_modules/.git/lockfiles/>1MB).
- [x] B2. `chunk.py` = 1000/200 splitter (ported). Metadata per chunk: `{source, chunk_index, ext}`.
- [x] B3. Gemini batched embed (RETRIEVAL_DOCUMENT, L2-normalized) → Chroma `upsert` (idempotent re-ingest).
- [x] B4. `python -m astra.ingest <repo>` — verified: ingested konveyor/docs → 43 chunks, no rate-limit crash.

### Phase C — Retrieval + cited answer (THE core demo)  ✅ MILESTONE 1 VERIFIED
- [x] C1. `retrieve.py`: embed question (RETRIEVAL_QUERY) → Chroma top-5 → chunks+metadata.
- [x] C2. Query preprocessing — CLOSED: vector search handles synonyms; the valuable half (follow-up context-enhance) was ported in D2 (`answer._enhance_query`). No recall issues observed across three repos.
- [x] C3. `answer.py`: Groq synthesizes a grounded answer with inline `[n]` + accurate Sources list. Verified: cites real files, refuses to invent when sources lack the answer.
- [x] C4. `python -m astra.ask "<q>"` — ⭐ **MILESTONE 1 DONE & VERIFIED** (ingest konveyor/docs → ask → cited answer pointing at architecture.md/INFRASTRUCTURE.md).

### Phase D — Agent layer: memory + RAG/code skills (table stakes)  ✅ DONE (pragmatic forms)
- [x] D1. Conversation memory — implemented as client-side history + `history` param through `/api/ask` (server stays stateless; simpler than a memory.py module and demo-equivalent).
- [x] D2. Follow-up **retrieval enhance** (Appendix B port) in `answer.py::_enhance_query` — key terms from the previous user turn are appended to the retrieval query so "and where is that tested?" retrieves well.
- [x] D3. Code understanding — implemented as `/api/file/ask` (explorer "interrogate this file"): file content + computed risk/ownership metrics → grounded explanation. Verified live on blueprints.py.
- [x] D4. `route.py` heuristic router wired into `/api/ask`: risk-words → **Risk engine** (answers from report.json, danger-zone files as source chips) · onboarding-words → **Onboarding path** · default → **cited RAG**. Chat UI shows which engine answered (·RISK ENGINE / ·ONBOARDING / ·CITED RAG).

### Phase D★ — Tribal-Knowledge / Risk Engine  ⭐ THE DIFFERENTIATOR (net-new; this is what wins)
> Reads what nobody wrote down. All signals free/local/deterministic; the LLM narrates over computed numbers.
> **Prereq:** target repo must be a FULL clone (history). Verify `git -C <repo> rev-list --count HEAD` ≫ 1.
- [x] R1. `gitstats.py` — one git-log pass → per-file authorship/churn/recency/owner-idle. ✅ verified on Flask (matches `git shortlog`).
- [x] R2. `codegraph.py` — fan-in + has_tests heuristic. ✅ verified: core modules (app, globals, wrappers, helpers) rank central.
- [x] R3. `risk.py` — risk_score + danger_zones + knowledge_silos + ownership_by_dir (SOURCE files only). ✅ verified on Flask (blueprints idle 736d, signals 88% single-owner+stale).
- [x] R4. `analyze.py` CLI → `.astra/report.json`. ✅ verified (24 source files → report.json).
- [x] R5. `skills/risk_brief.py` — ⭐ "what breaks if X leaves" brief. ✅ VERIFIED on Flask: real files/owners/metrics, zero hallucination.
- [x] R6. `skills/onboarding_path.py` — ordered learn-first + who-to-ask. ✅ VERIFIED: centrality-ordered, correctly named pgjones (idle owner) vs David Lord.
- [x] R7. `drift.py` — doc-drift detector ✅ DONE & VERIFIED: extracts ≤6 checkable claims from README/docs (1 Groq call), retrieves CODE-only evidence per claim (local embeddings, free), judges all claims in one batched Groq call → supported/drifted/unverifiable + note + files. `GET /api/drift?repo=` (cached) + "⇄ DOC DRIFT" panel on the Onboarding page (scan-gated). Verified on Flask: 5 supported w/ evidence, 1 honestly unverifiable, zero guessing.

### Phase E — Interface  ✅ DONE — v3: Vite + React rebuild ("The Dossier" v2, awwwards-style motion)
> v1 (vanilla HTML) → `frontend-old/` (kept as fallback). v3 = **Vite + React + GSAP ScrollTrigger + Lenis smooth scroll**.
> Aesthetic: warm ink / aged paper / amber phosphor / ember. Instrument Serif + IBM Plex Mono. Zero purple, zero Inter.
- [x] E1. `astra/server.py` (FastAPI :7700): /api/{status,report,brief,onboarding,ask,tree,file,file/ask}, LLM outputs cached. Serves the SPA from `frontend/dist` (catch-all → index.html). Run: `ASTRA_HOST=0.0.0.0 .venv/bin/python -m astra.server`. Rebuild UI: `cd frontend && npm run build`.
- [x] E2. Motion system: preloader (giant 0→100% serif counter + cycling status → sheet fades up), custom cursor (dot + trailing ring), Lenis smooth scroll, venetian-blind route transitions (cover → navigate → uncover via `lib/wipe.jsx`), masked line reveals (`lib/motion.jsx`), magnetic buttons, count-ups.
- [x] E3. Landing (`pages/Landing.jsx`): MAE-ITO-style hero — giant roman serif left ("THE MAP / OF WHAT") + giant amber italic right ("nobody wrote down."), dek + underline CTAs right, mono corner meta + bottom dossier strip (real numbers); **interactive topographic contour canvas** background (`components/Topo.jsx` — 2D, wobbling nested contours around 4 peaks that bend away from the cursor w/ trailing lerp; survey-marker dots; NO text in bg). Then: rotated marquee, §01 stacked editorial statements, §02 LIVE EXHIBIT (count-up stats + danger-zone REDACTION wipe on scroll), §03 pinned horizontal method panels, §04 index-list instrument rows (amber fill hover), fin CTA, giant parallax footer wordmark.
- [x] E4. Explorer/Chat/Onboarding ported to React (same verified API logic; deep-link `/explorer?path=...` works; chat keeps history + source chips).
- [x] E5. PERF: replaced the original Three.js+bloom hero (laggy) with the 2D topo canvas → bundle 1,360KB → 402KB (gzip 134KB). 0 console errors. Verified desktop 1440px + mobile 390px via Playwright (screenshots/v3-*.png).
- [x] E6. Slack bot ✅ CODE-COMPLETE: `astra/slack_bot.py` (Bolt Socket Mode) — @mention or DM → same `route.dispatch` as web chat (risk/onboarding/RAG across all repos) + sources list. Smoke-tested (clean import, graceful no-token exit with setup instructions). **Going live needs YOUR Slack app tokens** (5-min setup documented in the file's docstring): SLACK_BOT_TOKEN + SLACK_APP_TOKEN in .env → `python -m astra.slack_bot`.

### Phase F — Demo polish  ✅ DONE (F1 ingest verified below)
- [x] F1. One coherent story: Chroma reset → **Flask ingested** (1,729 chunks: docs + src), same repo as the risk dossier. **Embeddings switched to FastEmbed** (local ONNX, bge-small-en-v1.5 @384d, CUDA on the A6000 → 15s full-repo ingest; CPU fallback automatic). Why: Gemini free tier has TWO hard caps discovered live — 100 contents/min AND **1,000 contents/day** — so it can't ingest real repos at all. Gemini stays available via `EMBED_PROVIDER=gemini`.
- [x] F2. Chat starters seeded to hit all three engines: "How does routing work?" (RAG) · "What breaks if the top contributor leaves?" (Risk) · "I'm a new backend engineer — what should I learn first?" (Onboarding).
- [x] F3. 90-sec demo script locked (below).
- [x] F4. README rewritten (pitch + instruments table + ascii architecture + honest framing + quickstart).

---

## 4. Demo script — LOCKED (90 sec, all on http://localhost:7700, Flask dossier pre-loaded)
> Pre-flight: server up, `.astra/report.json` + Chroma populated, hard-refresh done, brief/onboarding pre-warmed once (cached) if you want zero latency.
1. **(0:00) Landing.** Let the preloader count 0→100%. Move the mouse — contours bend. One line: *"This is Flask — 5,539 commits, 857 contributors. Astra read all of it."* Scroll fast through §02: the **redaction wipe** declassifies the top danger zone live.
2. **(0:20) Chat → "What breaks if the top contributor leaves?"** → ·RISK ENGINE tag → real names, real files, real %s. Punch: *"No doc contains this. It's computed from git."*
3. **(0:40) Chat → "I'm a new backend engineer — what should I learn first?"** → ·ONBOARDING → ordered path + who-to-ask.
4. **(0:55) Chat → "How does routing work?"** → ·CITED RAG → click a `[n]` source chip → lands in the **Explorer on that exact file**.
5. **(1:10) Explorer.** Click the top danger-zone chip (blueprints.py, risk 57) → stat grid: *single owner pgjones, idle 2 years, zero direct tests, fan-in 4*. Ask it: *"what should I be careful about?"* → grounded answer.
6. **(1:25) Close:** *"RAG over docs is table stakes — every signal you saw was computed from git history and the import graph, free, local, deterministic. Astra reads what nobody wrote down. $0 stack."*

---

## 5. Risks / open decisions
- [x] Gemini embed model + dims — RESOLVED: `gemini-embedding-001` @768, L2-normalized, batched (verified live).
- [x] Groq model id — RESOLVED: `llama-3.3-70b-versatile` live; free tier ~100k tokens/day (~20–40 Qs) — don't burn during dev.
- [x] Demo repo — RESOLVED: **Flask** (5,539 commits / 857 authors, full clone at `/data/divyanshu/flask`). Konveyor clone kept only as the code reference.
- [x] Gemini embed quota — RESOLVED the hard way: free tier = **100 embedded contents/min** (each batched item counts). `embeddings.py` now paces 61s between 100-chunk batches + long retry waits. Big-repo ingest ≈ N_chunks/100 minutes, one-time.
- [x] Router — heuristic regex shipped (`route.py`); upgrade to LLM-classify only if a demo question misroutes.
- [x] fan-in / import resolution is heuristic across languages — ACCEPTED limitation; stated honestly in README. Demo repos are Python (exact-ish).
- [x] "owner may be gone" is inferred from commit recency, NOT HR data — framed as *"based on commit activity"* in prompts + README. ACCEPTED.
- [x] Stretch items shipped: Drift ✅ verified · Slack ✅ code-complete (needs user's tokens to go live).

---

## Appendix A — Captured: citation format + generation prompt (from reference)

**Generation system prompt (from `core/chat/skill.py`):**
> "You are a helpful assistant for the Konveyor project. Provide clear, concise, and accurate responses."
> (Rename "Konveyor" → "Astra". For Astra, extend it to: *"Answer ONLY from the provided sources. Cite each claim with [n] matching the numbered sources. If the sources don't cover it, say so."*)
Context is injected as an extra system message: `{"role":"system","content": f"Previous conversation: {context}"}`.

**Citation format (from `_format_answer_with_citations`):**
- Inline marks `[1]`, `[2]`… after each claim/snippet.
- Truncate long chunks at the last sentence boundary within ~300 chars.
- End with a `---` rule then a `**Sources:**` numbered list. For Astra use `file_path:line` instead of Document IDs:
  ```
  **Sources:**
  1. **auth/middleware.py** (lines 40–72)
  2. **docs/auth.md** (Authentication overview)
  ```

## Appendix B — Captured: query preprocessing + context-enhance (Doc Navigator)
- **Onboarding synonym expansion:** if the query contains a keyword, append synonyms. Map (trim as needed):
  `onboarding → "onboarding process, employee onboarding, new hire, orientation"`,
  `getting started → "onboarding, setup guide, initial steps"`, `setup → "configuration, installation, environment setup"`, `training → "learning, courses, onboarding"`, etc.
- **Preserve technical terms** (don't strip): api, sdk, cli, git, docker, k8s, azure, aws, llm, embedding, vector, auth, etc.
- **Strip** standalone question words (what/how/why/when…) and filler (the/a/in/on/to…), but **only if** >half the words survive — else use the original query.
- **Follow-up context-enhance (`_enhance_query_with_context`):** take key terms from the last ~2 user queries, add up to 5 that aren't already in the current question, append to the search query.

## Appendix C — New prompts to write (skills not in original)
- **Code Understanding:** "You are explaining code to a new engineer. Given this snippet and related files from the same codebase, explain (1) what it does in plain English, (2) its role in the larger system, (3) any non-obvious assumptions. Cite the files you used as [n]."
- **Gap Analyzer:** "Given this person's role/goal and a map of the codebase's docs and modules (provided), produce a prioritized, ordered learning path: what to read/understand first → last, and why. Point to real files/docs as [n]. Be concrete, not generic."

---

## Quick start (once keys are in `.env`)
```
cd /data/divyanshu/Astra
python -m venv .venv && source .venv/bin/activate
pip install groq google-genai chromadb python-dotenv tiktoken
python -m astra.ingest <path-to-a-repo>
python -m astra.ask "how does authentication work?"
```
