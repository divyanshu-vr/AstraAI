/* Motion primitives: masked line reveals, scroll fades, magnetic hover. */

import { useEffect, useLayoutEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

/* Demo site — motion IS the product. Many Windows machines report
   prefers-reduced-motion (OS "animation effects" off), which silently killed
   the preloader/topo/reveals for real users. Forced on. */
export const prefersReduced = () => false

/* Masked line reveal. `lines` = array of strings/JSX. play: true → animate now (hero);
   play: 'scroll' → reveal when scrolled into view. */
export function Lines({ lines, play = 'scroll', delay = 0, stagger = 0.09, className = '', as: Tag = 'div' }) {
  const ref = useRef(null)

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const inners = el.querySelectorAll('.split-line > .inner')
    if (prefersReduced()) { gsap.set(inners, { y: 0 }); return }
    if (play === true) {
      const tw = gsap.to(inners, {
        y: 0, duration: 1.15, delay, stagger, ease: 'power4.out',
      })
      return () => tw.kill()
    }
    if (play === 'scroll') {
      const tw = gsap.to(inners, {
        y: 0, duration: 1.05, stagger, ease: 'power4.out',
        scrollTrigger: { trigger: el, start: 'top 85%', once: true },
      })
      return () => { tw.scrollTrigger?.kill(); tw.kill() }
    }
    return undefined
  }, [play, delay, stagger])

  return (
    <Tag ref={ref} className={className}>
      {lines.map((l, i) => (
        <span className="split-line" key={i}>
          <span className="inner">{l}</span>
        </span>
      ))}
    </Tag>
  )
}

/* Generic scroll-in fade/rise for blocks. */
export function Rise({ children, y = 36, delay = 0, className = '', once = true }) {
  const ref = useRef(null)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    if (prefersReduced()) return
    gsap.set(el, { opacity: 0, y })
    const tw = gsap.to(el, {
      opacity: 1, y: 0, duration: 1, delay, ease: 'power3.out',
      scrollTrigger: { trigger: el, start: 'top 87%', once },
    })
    return () => { tw.scrollTrigger?.kill(); tw.kill() }
  }, [y, delay, once])
  return <div ref={ref} className={className}>{children}</div>
}

/* Magnetic hover (desktop only). */
export function Magnetic({ children, strength = 0.35 }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el || !window.matchMedia('(hover: hover)').matches) return
    const xTo = gsap.quickTo(el, 'x', { duration: 0.4, ease: 'power3' })
    const yTo = gsap.quickTo(el, 'y', { duration: 0.4, ease: 'power3' })
    const move = (e) => {
      const r = el.getBoundingClientRect()
      xTo((e.clientX - (r.left + r.width / 2)) * strength)
      yTo((e.clientY - (r.top + r.height / 2)) * strength)
    }
    const leave = () => { xTo(0); yTo(0) }
    el.addEventListener('mousemove', move)
    el.addEventListener('mouseleave', leave)
    return () => { el.removeEventListener('mousemove', move); el.removeEventListener('mouseleave', leave) }
  }, [strength])
  return <span ref={ref} style={{ display: 'inline-block' }}>{children}</span>
}

/* Count-up number on scroll. */
export function Count({ to, className = '' }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (prefersReduced()) { el.textContent = (+to).toLocaleString(); return }
    el.textContent = '0'
    const obj = { v: 0 }
    const tw = gsap.to(obj, {
      v: +to, duration: 1.8, ease: 'power2.out',
      scrollTrigger: { trigger: el, start: 'top 88%', once: true },
      onUpdate: () => { el.textContent = Math.round(obj.v).toLocaleString() },
    })
    return () => { tw.scrollTrigger?.kill(); tw.kill() }
  }, [to])
  return <span ref={ref} className={className} />
}
