import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { api } from '../lib/api.js'
import { Lines, Rise, Magnetic, Count, prefersReduced } from '../lib/motion.jsx'
import { useWipeNav } from '../lib/wipe.jsx'
import Topo from '../components/Topo.jsx'
import Footer from '../components/Footer.jsx'
import '../styles/landing.css'

gsap.registerPlugin(ScrollTrigger)

const MARQUEE = ['BUS FACTOR', 'IMPORT ATLAS', 'KNOWLEDGE SILOS', 'WHO TO ASK', 'DANGER ZONES', 'IDLE AUTHORS', 'FAN-IN', 'PERSISTENT MEMORY', 'TRIBAL KNOWLEDGE', 'DOC DRIFT']

const STEPS = [
  { title: <>Read every <em>commit.</em></>, body: 'One pass over the full git log. Per file: who wrote it, how concentrated that ownership is, when it last changed — and how long its primary author has been silent.', frag: <>every commit → every file mapped<br />authorship · churn · recency · idle</> },
  { title: <>Map the <em>import graph.</em></>, body: 'Imports become fan-in: the files the whole system leans on. Then cross-check which of those load-bearing walls no test ever touches.', frag: <>fan-in(core module) = <b>high</b><br />direct tests: <b>none</b></> },
  { title: <>Score the <em>risk.</em></>, body: 'Centrality × single-ownership × staleness × missing tests — folded into a deterministic 0–100 score per file. No vibes. Just arithmetic on evidence.', frag: <>risk = .35·fan + .25·own + .2·idle + …<br />deterministic, <b>0–100</b> per file</> },
  { title: <>Brief the <em>human.</em></>, body: 'An LLM narrates the computed evidence — what breaks if she leaves, what to learn first, who to ask. Every claim traces back to a number.', frag: <>“one engineer solely owns <b>8</b> critical files…”<br />grounded · cited · $0 stack</> },
]

export default function Landing({ booted }) {
  const [ws, setWs] = useState(null) // /api/status workspace summary
  const go = useWipeNav()
  const heroRef = useRef(null)
  const heroInner = useRef(null)
  const hwrap = useRef(null)
  const htrack = useRef(null)
  const verdictRef = useRef(null)

  useEffect(() => { api.get('/api/status').then(setWs).catch(() => {}) }, [])

  /* hero gently fades + drifts up as you leave it */
  useLayoutEffect(() => {
    if (prefersReduced()) return
    const tw = gsap.to(heroInner.current, {
      opacity: 0.14, yPercent: -6, ease: 'none',
      scrollTrigger: { trigger: heroRef.current, start: 'top top', end: 'bottom top', scrub: true },
    })
    return () => { tw.scrollTrigger?.kill(); tw.kill() }
  }, [])

  /* §03 pinned horizontal scroll (desktop only) */
  useLayoutEffect(() => {
    const mm = gsap.matchMedia()
    mm.add('(min-width: 900px) and (prefers-reduced-motion: no-preference)', () => {
      const track = htrack.current
      gsap.to(track, {
        x: () => -(track.scrollWidth - window.innerWidth),
        ease: 'none',
        scrollTrigger: {
          trigger: hwrap.current, start: 'top top',
          end: () => '+=' + (track.scrollWidth - window.innerWidth),
          scrub: 1, pin: true, invalidateOnRefresh: true, anticipatePin: 1,
        },
      })
    })
    return () => mm.revert()
  }, [])

  /* verdict redaction wipe */
  useLayoutEffect(() => {
    if (prefersReduced()) return
    const bars = verdictRef.current?.querySelectorAll('.bar')
    if (!bars?.length) return
    const tw = gsap.to(bars, {
      scaleX: 0, ease: 'power2.inOut',
      scrollTrigger: { trigger: verdictRef.current, start: 'top 78%', end: 'top 42%', scrub: true },
    })
    return () => { tw.scrollTrigger?.kill(); tw.kill() }
  }, [ws])

  const ready = ws?.ready ?? 0
  const agg = (ws?.workspace || []).filter((r) => r.status === 'ready').reduce(
    (a, r) => ({ commits: a.commits + (r.stats.total_commits || 0), contributors: a.contributors + (r.stats.contributors || 0) }),
    { commits: 0, contributors: 0 },
  )
  const wipeTo = (to) => (e) => { e.preventDefault(); go(to) }

  return (
    <main>
      {/* HERO — interactive contour map, MAE-ITO composition (product-neutral) */}
      <header className="hero-map" ref={heroRef}>
        <Topo />
        <div className="hm-inner" ref={heroInner}>
          <div className="hm-meta hm-tl">
            <Lines play={booted} stagger={0} lines={[<>✶ TRIBAL-KNOWLEDGE CARTOGRAPHY</>]} />
          </div>
          <div className="hm-meta hm-tr">
            <Lines play={booted} stagger={0} lines={[<>FOR EVERY CODEBASE YOU OWN</>]} />
          </div>

          <h1 className="hm-title display">
            <Lines play={booted} delay={0.12} stagger={0.11} lines={[<>THE MAP</>, <>OF WHAT</>]} />
          </h1>

          <div className="hm-right">
            <Lines
              play={booted} delay={0.45} as="div"
              lines={[<p className="hm-dek">Astra reads git history, ownership and the import graph across your repos — then briefs your next engineer like a departing senior would.</p>]}
            />
            <Lines
              play={booted} delay={0.58} as="div"
              lines={[
                <span className="hm-links">
                  <a href="/repos" data-hover onClick={wipeTo('/repos')}><i>→</i> OPEN THE WORKSPACE</a>
                  <a href="/chat" data-hover onClick={wipeTo('/chat')}><i>→</i> ASK THE DOSSIER</a>
                </span>,
              ]}
            />
          </div>

          <div className="hm-accent display">
            <Lines play={booted} delay={0.3} stagger={0.11} lines={[<em>nobody</em>, <em>wrote down.</em>]} />
          </div>

          <div className="hm-strip">
            <span><i className="dot" /> {ready > 0 ? `WORKSPACE — ${ready} REPO${ready > 1 ? 'S' : ''} UNDER THE LENS` : 'BRING YOUR REPOS'}</span>
            <span className="hm-strip-mid">RISK · OWNERSHIP · ONBOARDING — COMPUTED, NOT GUESSED</span>
            <span>SCROLL ↓</span>
          </div>
        </div>
      </header>

      {/* MARQUEE */}
      <div className="marquee" aria-hidden="true">
        <span className="track">
          {[...MARQUEE, ...MARQUEE].map((w, i) => (
            <span key={i}>{w}<span className="sep">✶</span></span>
          ))}
        </span>
      </div>

      {/* §01 PROBLEM */}
      <section className="sec">
        <div className="ghost-no">01</div>
        <div className="secno"><span className="label"><span className="tick">§</span> 01 — THE PROBLEM</span><span className="rule" /></div>
        <Lines
          as="h2" className="display problem-st" stagger={0.12}
          lines={[
            <>Every codebase holds knowledge</>,
            <>that lives in <em>no document.</em></>,
            <>It lives in <em>people.</em></>,
            <>And people <em>leave.</em></>,
          ]}
        />
        <div className="problem-notes">
          <Rise className="note" delay={0}>
            <div className="no">i.</div>
            <p>Why that module is scary, who really owns auth, which file breaks everything — it's in someone's head. They might resign on Friday.</p>
          </Rise>
          <Rise className="note" delay={0.1}>
            <div className="no">ii.</div>
            <p>Single-owner files accumulate silently. Nobody notices the bus factor of one — until the bus arrives.</p>
          </Rise>
          <Rise className="note" delay={0.2}>
            <div className="no">iii.</div>
            <p>New engineers burn months reconstructing context nobody wrote down, while seniors repeat themselves instead of building.</p>
          </Rise>
        </div>
      </section>

      {/* §02 THE WORKSPACE — neutral, aggregate-only */}
      <section className="sec">
        <div className="ghost-no">02</div>
        <div className="secno"><span className="label"><span className="tick">§</span> 02 — THE WORKSPACE</span><span className="rule" /></div>
        <Rise>
          <div className="exhibit-frame">
            <span className="exhibit-stamp">YOUR REPOS, ONE DOSSIER</span>
            <div className="exhibit-stats">
              <div>
                <div className="big">{ready > 0 ? <Count to={ready} /> : '∅'}</div>
                <div className="cap">{ready > 0 ? 'repos under the lens — chat searches them all at once' : 'repos ingested so far — bring yours, it takes seconds'}</div>
              </div>
              <div>
                <div className="big amber">{agg.commits > 0 ? <Count to={agg.commits} /> : '0–100'}</div>
                <div className="cap">{agg.commits > 0 ? 'commits read, one pass, no LLM involved' : 'deterministic risk score per file — arithmetic, not vibes'}</div>
              </div>
              <div>
                <div className="big">{agg.contributors > 0 ? <Count to={agg.contributors} /> : '$0'}</div>
                <div className="cap">{agg.contributors > 0 ? 'contributors mapped to the code they actually own' : 'free local embeddings + free LLM tier — the whole stack'}</div>
              </div>
            </div>
            <div className="verdict" ref={verdictRef}>
              <div className="label vlabel"><span className="tick">⚠</span> EVERY WORKSPACE HAS ONE — DECLASSIFIED ON SCROLL</div>
              <span className="vfile">your riskiest file already exists.<span className="bar" /></span>
              <div className="vtags">
                <span className="tag ember">single owner</span>
                <span className="tag ember">author idle for months</span>
                <span className="tag ember">no direct tests</span>
                <span className="tag ember">everything imports it</span>
              </div>
              <div style={{ marginTop: 18 }}>
                <a className="hm-links-inline" href="/repos" data-hover onClick={wipeTo('/repos')} style={{ color: 'var(--amber)', fontSize: 11, letterSpacing: '.2em', textDecoration: 'none' }}>→ FIND YOURS IN THE WORKSPACE</a>
              </div>
            </div>
          </div>
        </Rise>
      </section>

      {/* §03 METHOD — pinned horizontal */}
      <section style={{ marginTop: 'clamp(110px, 16vh, 190px)' }}>
        <div className="sec" style={{ paddingTop: 0 }}>
          <div className="secno"><span className="label"><span className="tick">§</span> 03 — METHOD</span><span className="rule" /><span className="label">SCROLL TO PAN →</span></div>
        </div>
        <div className="hwrap" ref={hwrap}>
          <div className="htrack" ref={htrack}>
            {STEPS.map((s, i) => (
              <div className="hpanel" key={i}>
                <div className="pno">{`0${i + 1}`}</div>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
                <div className="frag">{s.frag}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* §04 NEWLY DECLASSIFIED — the new instruments */}
      <section className="sec">
        <div className="ghost-no">04</div>
        <div className="secno"><span className="label"><span className="tick">§</span> 04 — NEWLY DECLASSIFIED</span><span className="rule" /><span className="label">THE MAP, THE PEOPLE, THE MEMORY</span></div>
        <div className="newgrid">
          <Rise className="newcard" delay={0}>
            <span className="label">⌖ THE ATLAS</span>
            <svg className="constellation" viewBox="0 0 200 120" aria-hidden="true" preserveAspectRatio="xMidYMid meet">
              <line x1="40" y1="72" x2="92" y2="36" /><line x1="40" y1="72" x2="138" y2="62" />
              <line x1="92" y1="36" x2="138" y2="62" /><line x1="138" y1="62" x2="172" y2="30" />
              <line x1="40" y1="72" x2="108" y2="98" /><line x1="92" y1="36" x2="60" y2="26" />
              <line x1="138" y1="62" x2="108" y2="98" />
              <circle cx="40" cy="72" r="11" fill="#e0562f" /><circle cx="92" cy="36" r="6.5" fill="#e8a33d" />
              <circle cx="138" cy="62" r="8" fill="#e8a33d" /><circle cx="172" cy="30" r="4" fill="#93a86a" />
              <circle cx="108" cy="98" r="5" fill="#6a614f" /><circle cx="60" cy="26" r="4" fill="#6a614f" />
            </svg>
            <h3 className="display">Every import,<br /><em>a line on the map.</em></h3>
            <p>Your codebase as a star chart — each file a node sized by fan-in, lit by risk, every dependency a thread. The load-bearing walls, finally visible.</p>
          </Rise>
          <Rise className="newcard" delay={0.1}>
            <span className="label">⌗ WHO TO ASK</span>
            <div className="owners">
              <div className="owner"><span>David Lord</span><span>owns 80%</span><i className="obar"><b style={{ width: '80%' }} /></i></div>
              <div className="owner"><span>idle author</span><span className="warn">quiet 6y</span><i className="obar"><b style={{ width: '52%', background: 'var(--ember)' }} /></i></div>
              <div className="owner"><span>Nate Prewitt</span><span>owns 64%</span><i className="obar"><b style={{ width: '64%' }} /></i></div>
            </div>
            <h3 className="display">The org chart<br /><em>nobody wrote down.</em></h3>
            <p>Reconstructed from commits, not HR. Who owns each corner, how concentrated it is, who's gone quiet — and what breaks the day they leave.</p>
          </Rise>
          <Rise className="newcard" delay={0.2}>
            <span className="label">✶ IT REMEMBERS YOU</span>
            <div className="memchips">
              <span className="memchip"><span className="mstar">✶</span> name · Divyanshu</span>
              <span className="memchip"><span className="mstar">✶</span> role · backend</span>
              <span className="memchip"><span className="mstar">✶</span> last touched · embeddings</span>
            </div>
            <h3 className="display">Tell it once.<br /><em>It carries it.</em></h3>
            <p>Astra keeps a long-term memory of who you are and what you last touched — across every session and page. Close the tab; the dossier still knows you back.</p>
          </Rise>
        </div>
      </section>

      {/* §05 INSTRUMENTS */}
      <section className="sec">
        <div className="ghost-no">05</div>
        <div className="secno"><span className="label"><span className="tick">§</span> 05 — THE INSTRUMENTS</span><span className="rule" /></div>
        <Rise>
          <div className="index-list">
            <a className="irow" href="/repos" data-hover onClick={wipeTo('/repos')}>
              <span className="idx">00</span>
              <span className="iname display">Workspace</span>
              <span className="desc">Bring every repo your team owns. Git analysis in seconds, embedding in ~15s — then the whole workspace is one dossier.</span>
              <span className="arr">→</span>
            </a>
            <a className="irow" href="/explorer" data-hover onClick={wipeTo('/explorer')}>
              <span className="idx">01</span>
              <span className="iname display">Repo Explorer</span>
              <span className="desc">Walk the tree with risk vision — ownership, idle authors, blast radius — and interrogate any file where it stands.</span>
              <span className="arr">→</span>
            </a>
            <a className="irow" href="/chat" data-hover onClick={wipeTo('/chat')}>
              <span className="idx">02</span>
              <span className="iname display">Cited Chat</span>
              <span className="desc">Every claim carries a [n] citation into a real file — and it remembers you across sessions: your name, your role, what you last touched.</span>
              <span className="arr">→</span>
            </a>
            <a className="irow" href="/onboarding" data-hover onClick={wipeTo('/onboarding')}>
              <span className="idx">03</span>
              <span className="iname display">The Atlas & Who to Ask</span>
              <span className="desc">The import graph as a living map, beside the org chart nobody wrote down — who owns what, who's gone quiet, what breaks if they leave.</span>
              <span className="arr">→</span>
            </a>
          </div>
        </Rise>
      </section>

      {/* FIN */}
      <section className="fin">
        <Lines
          as="h2" className="display" stagger={0.12}
          lines={[<>Stop onboarding</>, <><em>blindfolded.</em></>]}
        />
        <Rise delay={0.2}>
          <Magnetic strength={0.5}><a className="btn solid" href="/repos" data-hover onClick={wipeTo('/repos')}>Open the workspace ✶</a></Magnetic>
        </Rise>
      </section>

      <Footer />
    </main>
  )
}
