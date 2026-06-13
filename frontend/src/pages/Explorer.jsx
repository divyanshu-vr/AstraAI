import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, riskClass, fmtDays } from '../lib/api.js'
import { md } from '../lib/md.js'
import { Lines, Rise } from '../lib/motion.jsx'
import Footer from '../components/Footer.jsx'
import '../styles/app.css'

function Thinking() { return <div className="thinking"><i /><i /><i /></div> }

function buildTree(files) {
  const root = {}
  for (const f of files) {
    let node = root
    const parts = f.path.split('/')
    parts.forEach((p, i) => {
      if (i === parts.length - 1) (node.__files ??= []).push({ ...f, name: p })
      else node = (node[p] ??= {})
    })
  }
  return root
}

function Dir({ node, base, onOpen, selected, openSet }) {
  const dirs = Object.keys(node).filter((k) => k !== '__files').sort()
  const files = (node.__files || []).slice().sort((a, b) => a.name.localeCompare(b.name))
  return (
    <>
      {dirs.map((d) => {
        const full = base + d + '/'
        const defaultOpen = base === '' && (d === 'src' || d === 'astra')
        return (
          <details key={d} open={defaultOpen || openSet.has(full)}>
            <summary data-hover>{d}/</summary>
            <Dir node={node[d]} base={full} onOpen={onOpen} selected={selected} openSet={openSet} />
          </details>
        )
      })}
      {files.map((f) => (
        <button
          key={f.path}
          className={'file' + (selected === f.path ? ' sel' : '')}
          title={f.path}
          data-hover
          onClick={() => onOpen(f.path)}
        >
          <span className={'risk-dot ' + riskClass(f.risk)} />
          <span className="nm">{f.name}</span>
        </button>
      ))}
    </>
  )
}

export default function Explorer() {
  const [params, setParams] = useSearchParams()
  const [repos, setRepos] = useState([])
  const [report, setReport] = useState(null)
  const [tree, setTree] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loadingFile, setLoadingFile] = useState(false)
  const [qa, setQa] = useState([])
  const [asking, setAsking] = useState(false)
  const detailRef = useRef(null)
  const inputRef = useRef(null)

  const selected = params.get('path')
  const repo = params.get('repo') || repos[0]?.id || null
  const rq = repo ? `repo=${encodeURIComponent(repo)}` : ''

  useEffect(() => {
    api.get('/api/repos').then((d) => setRepos(d.repos.filter((r) => r.status === 'ready'))).catch(() => {})
  }, [])

  useEffect(() => {
    if (!repo) return
    setReport(null); setTree(null)
    api.get(`/api/report?${rq}`).then(setReport).catch(() => {})
    api.get(`/api/tree?${rq}`).then(setTree).catch(() => setTree({ files: [], error: true }))
  }, [repo])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selected || !repo) return
    setLoadingFile(true)
    setQa([])
    api.get(`/api/file?${rq}&path=${encodeURIComponent(selected)}`)
      .then(setDetail)
      .catch((e) => setDetail({ error: e.message }))
      .finally(() => setLoadingFile(false))
  }, [selected, repo])  // eslint-disable-line react-hooks/exhaustive-deps

  const rootNode = useMemo(() => (tree ? buildTree(tree.files) : null), [tree])
  const openSet = useMemo(() => {
    const s = new Set()
    if (selected) {
      const parts = selected.split('/')
      let acc = ''
      for (let i = 0; i < parts.length - 1; i++) { acc += parts[i] + '/'; s.add(acc) }
    }
    return s
  }, [selected])

  const openFile = (path) => {
    setParams(repo ? { repo, path } : { path })
    requestAnimationFrame(() => detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  const switchRepo = (id) => setParams({ repo: id })

  const ask = async (e) => {
    e.preventDefault()
    const q = inputRef.current.value.trim()
    if (!q || asking) return
    inputRef.current.value = ''
    setAsking(true)
    setQa((prev) => [{ q, a: null }, ...prev])
    try {
      const res = await api.post('/api/file/ask', { repo, path: selected, question: q })
      setQa((prev) => prev.map((x, i) => (i === 0 ? { ...x, a: res.answer } : x)))
    } catch (err) {
      setQa((prev) => prev.map((x, i) => (i === 0 ? { ...x, err: err.message } : x)))
    } finally { setAsking(false) }
  }

  const g = detail?.git, cg = detail?.graph, r = detail?.risk

  return (
    <main className="page">
      <div className="page-head">
        <span className="label"><span className="tick">§</span> FIELD KIT — REPO EXPLORER</span>
        <Lines play as="h1" className="display" lines={[<>Walk the tree with</>, <><em>risk vision.</em></>]} />
        <p className="sub">
          {report
            ? <>{report.summary.source_files} source files scored · {report.summary.contributors} contributors · {report.summary.total_commits.toLocaleString()} commits read</>
            : repos.length === 0 ? <>workspace is empty — add a repo on the Workspace page</> : 'loading dossier…'}
        </p>
      </div>

      {repos.length > 0 && (
        <div className="repo-bar">
          <span className="label">REPO</span>
          {repos.map((r) => (
            <button key={r.id} className={'repo-pill' + (r.id === repo ? ' on' : '')} data-hover onClick={() => switchRepo(r.id)}>
              {r.name}
            </button>
          ))}
        </div>
      )}

      {report && (
        <Rise>
          <div className="label" style={{ marginBottom: 10 }}>DANGER ZONES — CLICK TO INSPECT</div>
          <div className="danger-strip scroll" data-lenis-prevent>
            {report.danger_zones.map((z) => (
              <button className="dz-chip" key={z.file} data-hover onClick={() => openFile(z.file)}>
                <span className="score">{Math.round(z.risk)}</span>
                <span className="path">{z.file}</span>
                <span className={'risk-dot ' + riskClass(z.risk)} />
              </button>
            ))}
          </div>
        </Rise>
      )}

      <div className="split">
        <aside className="panel tree-panel scroll" data-lenis-prevent>
          <div className="panel-head"><span className="label">FILES</span><span className="label">{tree?.files?.length ?? '…'}</span></div>
          <div className="tree">
            {rootNode
              ? <Dir node={rootNode} base="" onOpen={openFile} selected={selected} openSet={openSet} />
              : <Thinking />}
          </div>
        </aside>

        <section className="panel" ref={detailRef}>
          {!selected && (
            <div className="detail-empty">
              <div className="display">No file under the lens.</div>
              Select a file from the tree — or hit a danger zone above.
            </div>
          )}
          {selected && loadingFile && <div style={{ padding: 24 }}><Thinking /></div>}
          {selected && !loadingFile && detail?.error && <div className="detail-empty">{detail.error}</div>}
          {selected && !loadingFile && detail && !detail.error && (
            <>
              <div className="file-head">
                <div className="label">FILE UNDER THE LENS</div>
                <div className="path">{detail.path}</div>
                <div className="tags">
                  {r
                    ? r.reasons.map((x, i) => <span className="tag ember" key={i}>{x}</span>)
                    : <span className="tag moss">no elevated risk signals</span>}
                </div>
              </div>
              <div className="statgrid">
                <div className="s"><div className={'v ' + (r ? (r.risk >= 45 ? 'ember' : r.risk >= 30 ? 'amber' : 'moss') : '')}>{r ? Math.round(r.risk) : '—'}</div><div className="k">risk / 100</div></div>
                <div className="s"><div className="v">{cg ? cg.fan_in : '—'}</div><div className="k">fan-in (importers)</div></div>
                <div className="s"><div className="v small">{g ? g.primary_author : '—'}</div><div className="k">primary author {g ? `(${Math.round(g.author_concentration * 100)}%)` : ''}</div></div>
                <div className="s"><div className="v">{g ? fmtDays(g.primary_author_idle_days) : '—'}</div><div className="k">author idle</div></div>
                <div className="s"><div className="v">{g ? g.commits : '—'}</div><div className="k">commits</div></div>
                <div className="s"><div className="v">{g ? g.contributors : '—'}</div><div className="k">contributors</div></div>
                <div className="s"><div className="v">{g ? fmtDays(g.last_commit_age_days) : '—'}</div><div className="k">last change</div></div>
                <div className="s"><div className={'v ' + (cg?.has_tests ? 'moss' : 'ember')}>{cg ? (cg.has_tests ? 'yes' : 'no') : '—'}</div><div className="k">direct tests</div></div>
              </div>
              <div className="panel-head"><span className="label">CONTENTS {detail.truncated ? '— TRUNCATED' : ''}</span></div>
              <div className="code-wrap scroll" data-lenis-prevent>
                <div className="code">
                  {(detail.content || '').split('\n').slice(0, 400).map((l, i) => (
                    <div className="ln" key={i}>{l || ' '}</div>
                  ))}
                </div>
              </div>
              <div className="ask-box">
                <div className="label" style={{ marginBottom: 10 }}>INTERROGATE THIS FILE</div>
                <form onSubmit={ask}>
                  <input ref={inputRef} className="input" placeholder="why does this file exist? what's risky here? who reviews my change?" autoComplete="off" />
                  <button className="btn solid" type="submit" disabled={asking} data-hover>Ask</button>
                </form>
                <div className="qa">
                  {qa.map((x, i) => (
                    <div key={i}>
                      <div className="q">{x.q}</div>
                      {x.a == null && !x.err && <Thinking />}
                      {x.a && <div className="a md" dangerouslySetInnerHTML={{ __html: md(x.a) }} />}
                      {x.err && <div className="err">{x.err}</div>}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </section>
      </div>
      <Footer />
    </main>
  )
}
