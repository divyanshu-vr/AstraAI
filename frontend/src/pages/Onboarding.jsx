import { lazy, Suspense, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, fmtDays } from '../lib/api.js'
import { md } from '../lib/md.js'
import { Lines, Rise } from '../lib/motion.jsx'
import Footer from '../components/Footer.jsx'
import '../styles/app.css'

// reagraph pulls in three.js (~500kB) — load it only when this page mounts, not on the landing.
const Atlas = lazy(() => import('../components/Atlas.jsx'))

function Thinking() { return <div className="thinking"><i /><i /><i /></div> }

export default function Onboarding() {
  const [params, setParams] = useSearchParams()
  const [repos, setRepos] = useState([])
  const [graph, setGraph] = useState(null)
  const [people, setPeople] = useState(null)
  const [drift, setDrift] = useState(null)

  const repo = params.get('repo') || repos[0]?.id || null
  const rq = repo ? `repo=${encodeURIComponent(repo)}` : ''

  useEffect(() => {
    api.get('/api/repos').then((d) => setRepos(d.repos.filter((r) => r.status === 'ready'))).catch(() => {})
  }, [])

  useEffect(() => {
    if (!repo) return
    setGraph(null); setPeople(null); setDrift(null)
    api.get(`/api/graph?${rq}`).then(setGraph).catch(() => setGraph({ nodes: [], links: [] }))
    api.get(`/api/people?${rq}`).then((d) => setPeople(d.people)).catch(() => setPeople([]))
  }, [repo])  // eslint-disable-line react-hooks/exhaustive-deps

  const scanDrift = async () => {
    setDrift({ pending: true })
    try {
      const res = await api.get(`/api/drift?${rq}`)
      setDrift({ claims: res.claims })
    } catch (err) { setDrift({ err: err.message }) }
  }

  return (
    <main className="page">
      <div className="page-head">
        <span className="label"><span className="tick">§</span> INDUCTION — THE LAY OF THE LAND</span>
        <Lines play as="h1" className="display" lines={[<>Day one,</>, <><em>without the blindfold.</em></>]} />
        <p className="sub">Not a chat. A map. Astra charts the codebase by what imports what, then names the people who actually hold the knowledge — straight from the git history, nothing written down required.</p>
      </div>

      {repos.length > 0 && (
        <div className="repo-bar">
          <span className="label">REPO</span>
          {repos.map((r) => (
            <button key={r.id} className={'repo-pill' + (r.id === repo ? ' on' : '')} data-hover onClick={() => setParams({ repo: r.id })}>
              {r.name}
            </button>
          ))}
        </div>
      )}

      <Rise>
        <div className="panel">
          <div className="panel-head"><span className="label">✶ THE ATLAS — IMPORT GRAPH</span><span className="label">SIZE = FAN-IN · COLOR = RISK</span></div>
          {!graph ? <Thinking /> : (
            <Suspense fallback={<Thinking />}>
              <Atlas repo={repo} nodes={graph.nodes} links={graph.links} />
            </Suspense>
          )}
        </div>
      </Rise>

      <Rise delay={0.08}>
        <div className="panel" style={{ marginTop: 22 }}>
          <div className="panel-head"><span className="label">⌗ WHO TO ASK — THE ORG NOBODY WROTE DOWN</span><span className="label">FROM GIT HISTORY</span></div>
          {!people ? <Thinking /> : people.length === 0 ? (
            <div className="placeholder">No ownership data for this repo.</div>
          ) : (
            <div className="people-grid">
              {people.map((p) => (
                <div className="person-card" key={p.name}>
                  <div className="pc-top">
                    <span className="pc-name">{p.name}</span>
                    {p.bus_factor_risk && <span className="tag ember">BUS FACTOR</span>}
                  </div>
                  <div className="pc-stats">
                    <span><b>{p.commits.toLocaleString()}</b> commits</span>
                    <span className={p.last_active_days != null && p.last_active_days >= 180 ? 'idle' : ''}>
                      {p.last_active_days != null ? `active ${fmtDays(p.last_active_days)} ago` : 'activity n/a'}
                    </span>
                    {p.solely_owned_files > 0 && <span><b>{p.solely_owned_files}</b> solely-owned</span>}
                    {p.blast_radius > 0 && <span>blast-radius <b>{p.blast_radius}</b></span>}
                  </div>
                  {p.owns_dirs.length > 0 && (
                    <div className="pc-owns">owns {p.owns_dirs.map((d) => d.dir).join(' · ')}</div>
                  )}
                  {p.ask_about.length > 0 && (
                    <div className="pc-ask">ask about {p.ask_about.map((f) => f.split('/').pop()).join(' · ')}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </Rise>

      <Rise delay={0.16}>
        <div className="panel" style={{ marginTop: 22 }}>
          <div className="panel-head"><span className="label">⇄ DOC DRIFT</span><span className="label">DOCS VS CODE</span></div>
          <div className="brief-body">
            {!drift && (
              <div className="brief-gate">
                <div className="display">Do the docs still tell the truth?</div>
                <p>Astra extracts checkable claims from the README, then audits each against retrieved source code.</p>
                <button className="btn" data-hover onClick={scanDrift}>Scan for drift ⇄</button>
              </div>
            )}
            {drift?.pending && <Thinking />}
            {drift?.err && <div style={{ color: 'var(--ember)' }}>{drift.err}</div>}
            {drift?.claims && drift.claims.length === 0 && <div style={{ color: 'var(--paper-faint)' }}>No checkable doc claims found in this repo.</div>}
            {drift?.claims?.map((c, i) => (
              <div className="silo" key={i}>
                <span className={'tag ' + (c.verdict === 'supported' ? 'moss' : c.verdict === 'drifted' ? 'ember' : '')}>{c.verdict}</span>
                <div style={{ fontSize: 12.5, marginTop: 6 }}>{c.claim}</div>
                {c.note && <div className="what">{c.note}{c.files?.length > 0 && <> · {c.files.join(' · ')}</>}</div>}
              </div>
            ))}
          </div>
        </div>
      </Rise>
      <Footer />
    </main>
  )
}
