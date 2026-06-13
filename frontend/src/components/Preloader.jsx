/* Boot sequence: giant 0→100 counter (bottom-left), full-width hairline progress,
   cycling status line — then the whole sheet fades up and away. */

import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { prefersReduced } from '../lib/motion.jsx'

const STATUS = ['READING GIT HISTORY…', 'MAPPING THE IMPORT GRAPH…', 'SCORING RISK…', 'OPENING THE DOSSIER…']

export default function Preloader({ onDone }) {
  const root = useRef(null)
  const num = useRef(null)
  const bar = useRef(null)
  const status = useRef(null)

  useEffect(() => {
    if (prefersReduced()) { onDone(); return }
    const obj = { v: 0 }
    let si = 0
    const cycle = setInterval(() => {
      si = (si + 1) % STATUS.length
      if (status.current) status.current.textContent = STATUS[si]
    }, 520)

    const tl = gsap.timeline({ onComplete: () => { clearInterval(cycle); onDone() } })
    tl.fromTo(num.current, { yPercent: 30, opacity: 0 }, { yPercent: 0, opacity: 1, duration: 0.5, ease: 'power3.out' }, 0)
      .to(obj, {
        v: 100, duration: 1.9, ease: 'power3.inOut',
        onUpdate: () => { if (num.current) num.current.textContent = Math.round(obj.v) },
      }, 0.1)
      .to(bar.current, { scaleX: 1, duration: 1.9, ease: 'power3.inOut' }, 0.1)
      .to([num.current, status.current], { opacity: 0, y: -24, duration: 0.35, ease: 'power2.in' }, '+=0.12')
      .to(root.current, { yPercent: -100, duration: 0.95, ease: 'power4.inOut' }, '-=0.1')
    return () => { clearInterval(cycle); tl.kill() }
  }, [onDone])

  return (
    <div className="preloader" ref={root}>
      <div className="pl-status" ref={status}>{STATUS[0]}</div>
      <div className="pl-num-row">
        <span className="pl-num" ref={num}>0</span>
        <span className="pl-pct">%</span>
      </div>
      <div className="pl-bar"><i ref={bar} /></div>
      <div className="pl-brand">✶ ASTRA</div>
    </div>
  )
}
