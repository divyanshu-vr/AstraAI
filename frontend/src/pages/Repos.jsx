import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api.js'
import { Lines, Rise } from '../lib/motion.jsx'
import Footer from '../components/Footer.jsx'
import '../styles/app.css'

const STATUS_LABEL = {
  queued: 'QUEUED', cloning: 'CLONING FROM GIT…', analyzing: 'READING GIT HISTORY…',
  ingesting: 'EMBEDDING CHUNKS…', ready: 'READY', error: 'FAILED',
}

export default function Repos() {
  const [repos, setRepos] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const pathRef = useRef(null)
  const nameRef = useRef(null)

  const load = () => api.get('/api/repos').then((d) => setRepos(d.repos)).catch(() => setRepos([]))

  useEffect(() => {
    load()
    const t = setInterval(() => {
      // keep polling while anything is processing
      setRepos((cur) => {
        if (cur?.some((r) => ['queued', 'cloning', 'analyzing', 'ingesting'].includes(r.status))) load()
        return cur
      })
    }, 2500)
    return () => clearInterval(t)
  }, [])

  const add = async (e) => {
    e.preventDefault()
    const path = pathRef.current.value.trim()
    if (!path || busy) return
    setBusy(true); setErr(null)
    try {
      await api.post('/api/repos', { path, name: nameRef.current.value.trim() || null })
      pathRef.current.value = ''; nameRef.current.value = ''
      await load()
    } catch (e2) { setErr(e2.message) } finally { setBusy(false) }
  }

  const remove = async (id) => {
    if (!confirm(`Remove '${id}' from the workspace? (chunks + report are deleted)`)) return
    await fetch(`/api/repos/${id}`, { method: 'DELETE' })
    load()
  }

  return (
    <main className="page">
      <div className="page-head">
        <span className="label"><span className="tick">§</span> THE WORKSPACE — YOUR REPOS</span>
        <Lines play as="h1" className="display" lines={[<>Every repo,</>, <><em>one dossier.</em></>]} />
        <p className="sub">Paste a GitHub link. Astra clones it, reads every commit, maps the import graph, scores the risk, and indexes the text — then the chat knows them all at once.</p>
      </div>

      <Rise>
        <div className="panel role-form">
          <span className="label">ADD A REPOSITORY — PUBLIC GIT URL</span>
          <form onSubmit={add}>
            <input ref={pathRef} className="input" placeholder="https://github.com/owner/repo" autoComplete="off" style={{ flex: 2 }} />
            <input ref={nameRef} className="input" placeholder="name (optional)" autoComplete="off" style={{ flex: 1 }} />
            <button className="btn solid" type="submit" disabled={busy} data-hover>Ingest ✶</button>
          </form>
          {err && <div style={{ color: 'var(--ember)', marginTop: 12, fontSize: 12 }}>{err}</div>}
        </div>
      </Rise>

      <div className="repo-grid">
        {repos == null && <div className="thinking"><i /><i /><i /></div>}
        {repos?.length === 0 && (
          <div className="detail-empty" style={{ gridColumn: '1/-1' }}>
            <div className="display">The workspace is empty.</div>
            Add your first repo above — analysis takes seconds, embedding ~15s on GPU.
          </div>
        )}
        {repos?.map((r) => (
          <div className="repo-card panel" key={r.id}>
            <div className="rc-head">
              <span className="rc-name display">{r.name}</span>
              <span className={'rc-status ' + r.status}>{STATUS_LABEL[r.status] || r.status}</span>
            </div>
            <div className="rc-path">{r.path}</div>
            {r.status === 'ready' && (
              <div className="rc-stats">
                <div><b>{(r.stats.total_commits ?? 0).toLocaleString()}</b><span>commits</span></div>
                <div><b>{r.stats.contributors ?? '—'}</b><span>contributors</span></div>
                <div><b>{r.stats.chunks ?? '—'}</b><span>chunks</span></div>
                <div><b className={r.stats.top_risk >= 45 ? 'ember' : ''}>{r.stats.top_risk ? Math.round(r.stats.top_risk) : '—'}</b><span>top risk</span></div>
              </div>
            )}
            {r.status === 'error' && <div className="rc-err">{r.error}</div>}
            {['queued', 'analyzing', 'ingesting'].includes(r.status) && <div className="thinking"><i /><i /><i /></div>}
            <div className="rc-actions">
              {r.status === 'ready' && (
                <>
                  <Link to={`/explorer?repo=${r.id}`} data-hover>EXPLORE →</Link>
                  <Link to={`/onboarding?repo=${r.id}`} data-hover>ONBOARD →</Link>
                </>
              )}
              <button onClick={() => remove(r.id)} data-hover className="rc-remove">REMOVE</button>
            </div>
          </div>
        ))}
      </div>
      <Footer />
    </main>
  )
}
