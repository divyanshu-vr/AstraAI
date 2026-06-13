import { useEffect, useRef } from 'react'
import gsap from 'gsap'

export default function Cursor() {
  const dot = useRef(null)
  const ring = useRef(null)

  useEffect(() => {
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return
    const dx = gsap.quickTo(dot.current, 'x', { duration: 0.08, ease: 'power2' })
    const dy = gsap.quickTo(dot.current, 'y', { duration: 0.08, ease: 'power2' })
    const rx = gsap.quickTo(ring.current, 'x', { duration: 0.35, ease: 'power3' })
    const ry = gsap.quickTo(ring.current, 'y', { duration: 0.35, ease: 'power3' })

    const move = (e) => { dx(e.clientX); dy(e.clientY); rx(e.clientX); ry(e.clientY) }
    const over = (e) => {
      if (e.target.closest('a, button, [data-hover], summary, input, textarea'))
        ring.current.classList.add('is-hover')
      else ring.current.classList.remove('is-hover')
    }
    window.addEventListener('pointermove', move, { passive: true })
    window.addEventListener('pointerover', over, { passive: true })
    return () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerover', over) }
  }, [])

  return (
    <>
      <div className="cursor-dot" ref={dot} aria-hidden="true" />
      <div className="cursor-ring" ref={ring} aria-hidden="true" />
    </>
  )
}
