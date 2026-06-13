import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, userId } from '../lib/api.js'
import { sessionId, newSession } from '../lib/session.js'
import { md } from '../lib/md.js'
import { Lines } from '../lib/motion.jsx'
import Footer from '../components/Footer.jsx'
import '../styles/app.css'

const STARTERS = [
  'How do sessions work?',
  'What breaks if the top contributor leaves?',
  "I'm a new backend engineer — what should I learn first?",
]

const stamp = () => new Date().toTimeString().slice(0, 8)

export default function Chat() {
  const [entries, setEntries] = useState([])
  const [busy, setBusy] = useState(false)
  const [chunks, setChunks] = useState(null)
  const [repos, setRepos] = useState([])           // ready repos
  const [active, setActive] = useState(new Set())  // toggled-on repo ids
  const inputRef = useRef(null)
  const logRef = useRef(null)

  useEffect(() => {
    api.get('/api/status').then((s) => {
      setChunks(s.chroma_chunks)
      const ready = (s.workspace || []).filter((r) => r.status === 'ready')
      setRepos(ready)
      setActive(new Set(ready.map((r) => r.id)))   // all on by default
    }).catch(() => {})
    // Restore the current session's transcript so navigating away & back isn't blank.
    api.get(`/api/session/${sessionId()}`).then((d) => {
      const restored = (d.turns || []).flatMap((t) => [
        { who: 'you', t: t.t, text: t.q },
        { who: 'astra', t: t.t, text: t.a, sources: t.sources, skill: t.skill },
      ])
      if (restored.length) setEntries(restored)
    }).catch(() => {})
  }, [])

  const startNew = () => { newSession(); setEntries([]) }

  const toggle = (id) => setActive((cur) => {
    const next = new Set(cur)
    if (next.has(id)) { if (next.size > 1) next.delete(id) } else next.add(id)
    return next
  })

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [entries])

  const send = async (text) => {
    const q = (text ?? inputRef.current.value).trim()
    if (!q || busy) return
    if (inputRef.current) inputRef.current.value = ''
    setBusy(true)
    setEntries((prev) => [...prev, { who: 'you', t: stamp(), text: q }, { who: 'astra', t: stamp(), pending: true }])
    try {
      const repoFilter = active.size === repos.length ? null : [...active]
      // Server owns the conversation thread — we send only the session id, not the transcript.
      const res = await api.post('/api/ask', { question: q, repos: repoFilter, user_id: userId(), session_id: sessionId() })
      setEntries((prev) => prev.map((e) => (e.pending ? { who: 'astra', t: e.t, text: res.answer, sources: res.sources, skill: res.skill } : e)))
    } catch (err) {
      setEntries((prev) => prev.map((e) => (e.pending ? { who: 'astra', t: e.t, err: err.message } : e)))
    } finally { setBusy(false) }
  }

  return (
    <main className="page">
      <div className="page-head">
        <span className="label" style={{ display: 'inline-flex', alignItems: 'center', gap: 16 }}>
          <span><span className="tick">§</span> INTERROGATION — CITED CHAT</span>
          {entries.length > 0 && (
            <button type="button" className="src-chip" data-hover onClick={startNew}>↻ NEW SESSION</button>
          )}
        </span>
        <Lines play as="h1" className="display" lines={[<>Ask. Get answers that</>, <><em>show their work.</em></>]} />
        <p className="sub">
          {chunks != null
            ? <>Corpus: <b style={{ color: 'var(--paper)' }}>{chunks} chunks</b> in the vector index. Every claim carries a [n] citation — or Astra admits it doesn't know.</>
            : 'Every claim carries a [n] citation into a real file — or Astra admits the corpus doesn\'t cover it.'}
        </p>
      </div>

      <div className="panel chat-shell">
        <div className="log scroll" ref={logRef} data-lenis-prevent>
          {entries.length === 0 && (
            <div className="empty-log">
              <div className="display">The log is empty.</div>
              Open with a question — or pick a starter below.
            </div>
          )}
          {entries.map((e, i) => (
            <div className={'entry ' + (e.who === 'you' ? 'you' : 'astra')} key={i}>
              <div className="meta">
                {e.who === 'you'
                  ? `YOU — ${e.t}`
                  : <><b>✶ ASTRA</b> — {e.t}{e.skill && <span style={{ color: e.skill === 'rag' ? 'var(--paper-faint)' : 'var(--ember)' }}> · {e.skill === 'rag' ? 'CITED RAG' : e.skill === 'risk' ? 'RISK ENGINE' : 'ONBOARDING'}</span>}</>}
              </div>
              {e.pending && <div className="thinking"><i /><i /><i /></div>}
              {e.text && e.who === 'you' && <div className="body">{e.text}</div>}
              {e.text && e.who === 'astra' && <div className="body md" dangerouslySetInnerHTML={{ __html: md(e.text) }} />}
              {e.err && <div className="body" style={{ color: 'var(--ember)' }}>{e.err}</div>}
              {e.sources?.length > 0 && (
                <div className="src-row">
                  {e.sources.map((s, j) => (
                    <Link className="src-chip" key={j} to={`/explorer?repo=${encodeURIComponent(s.repo || '')}&path=${encodeURIComponent(s.source)}`} data-hover>
                      <span className="n">[{j + 1}]</span>
                      {s.repo && <span className="repo-badge">{s.repo}</span>}
                      {s.source}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="composer">
          {repos.length > 0 && (
            <div className="repo-bar" style={{ marginBottom: 12 }}>
              <span className="label">SEARCHING</span>
              {repos.map((r) => (
                <button key={r.id} type="button" className={'repo-pill' + (active.has(r.id) ? ' on' : '')} data-hover onClick={() => toggle(r.id)}>
                  {r.name}
                </button>
              ))}
            </div>
          )}
          <div className="suggest">
            {STARTERS.map((s) => (
              <button key={s} type="button" data-hover onClick={() => send(s)}>{s}</button>
            ))}
          </div>
          <form onSubmit={(e) => { e.preventDefault(); send() }}>
            <input ref={inputRef} className="input" placeholder="ask about the code, the risk, or where to start…" autoComplete="off" />
            <button className="btn solid" type="submit" disabled={busy} data-hover>Send</button>
          </form>
        </div>
      </div>
      <Footer />
    </main>
  )
}
