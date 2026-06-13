import { useLayoutEffect, useRef } from 'react'
import gsap from 'gsap'
import { prefersReduced } from '../lib/motion.jsx'

export default function Footer() {
  const big = useRef(null)
  useLayoutEffect(() => {
    if (prefersReduced()) return
    const tw = gsap.fromTo(big.current, { yPercent: 35 }, {
      yPercent: 0, ease: 'none',
      scrollTrigger: { trigger: big.current, start: 'top bottom', end: 'bottom bottom', scrub: true },
    })
    return () => { tw.scrollTrigger?.kill(); tw.kill() }
  }, [])

  return (
    <footer className="footer">
      <div className="big" ref={big}>ASTRA✶</div>
      <div className="row">
        <span><span className="star">✶</span> reads what nobody wrote down</span>
        <span>git history · import graph · groq · gemini · chroma</span>
        <span>Made by <span className="maker">Divyanshu Verma</span></span>
      </div>
    </footer>
  )
}
