/* Interactive topographic contour background (2D canvas — cheap, smooth).
   Nested wobbling contour rings around 3 "peaks"; lines bend away from the
   cursor with a trailing lerp. No text, no overlap — pure cartography. */

import { useEffect, useRef } from 'react'
import { prefersReduced } from '../lib/motion.jsx'

/* Sparse, reference-style cartography: few meandering contours, lots of air. */
const PEAKS = [
  { x: 0.30, y: 0.30, rings: 8, seed: 11 },
  { x: 0.80, y: 0.74, rings: 7, seed: 47 },
  { x: 0.02, y: 1.02, rings: 5, seed: 83 },
]
const PTS = 170          // points per ring (smoothness)
const REPEL_R = 240      // px cursor influence radius
const REPEL_F = 55       // px max displacement

export default function Topo({ className = '' }) {
  const ref = useRef(null)

  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas.getContext('2d')
    const reduced = prefersReduced()
    const dpr = Math.min(window.devicePixelRatio || 1, 1.75)
    let w = 0, h = 0, raf = null, t = 0
    const mouse = { x: -9999, y: -9999, tx: -9999, ty: -9999 }

    const resize = () => {
      const r = canvas.getBoundingClientRect()
      w = r.width; h = r.height
      canvas.width = w * dpr; canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    const onMove = (e) => {
      const r = canvas.getBoundingClientRect()
      mouse.tx = e.clientX - r.left
      mouse.ty = e.clientY - r.top
    }
    const onLeave = () => { mouse.tx = -9999; mouse.ty = -9999 }

    /* periodic-in-angle organic wobble (sums of angle harmonics stay seamless) */
    const wob = (a, ring, seed, time) =>
      0.5 * Math.sin(3 * a + seed + ring * 0.9 + time) +
      0.3 * Math.sin(5 * a - seed * 1.7 + ring * 0.45 - time * 0.7) +
      0.2 * Math.sin(8 * a + seed * 0.6 - ring * 1.3 + time * 0.45)

    const draw = () => {
      ctx.clearRect(0, 0, w, h)
      const base = Math.min(w, h)
      // trailing cursor
      mouse.x += (mouse.tx - mouse.x) * 0.07
      mouse.y += (mouse.ty - mouse.y) * 0.07
      const time = t * 0.00055 // slow idle drift — the map breathes on its own

      for (const p of PEAKS) {
        const cx = p.x * w, cy = p.y * h
        const step = (base * 0.105)
        for (let ring = 1; ring <= p.rings; ring++) {
          const baseR = ring * step
          // line style: faint paper, every 5th amber, ring 4 ember
          if (ring === 3) ctx.strokeStyle = 'rgba(224,86,47,0.36)'
          else if (ring % 4 === 0) ctx.strokeStyle = 'rgba(232,163,61,0.30)'
          else ctx.strokeStyle = 'rgba(236,227,208,0.13)'
          ctx.lineWidth = 1
          ctx.beginPath()
          for (let i = 0; i <= PTS; i++) {
            const a = (i / PTS) * Math.PI * 2
            const r = baseR * (1 + 0.16 * wob(a, ring, p.seed, time))
            let x = cx + Math.cos(a) * r
            let y = cy + Math.sin(a) * r * 0.86
            // cursor repulsion
            const dx = x - mouse.x, dy = y - mouse.y
            const d2 = dx * dx + dy * dy
            if (d2 < REPEL_R * REPEL_R) {
              const d = Math.sqrt(d2) || 1
              const f = (1 - d / REPEL_R)
              const push = f * f * REPEL_F
              x += (dx / d) * push
              y += (dy / d) * push
            }
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
          }
          ctx.stroke()
        }
        // survey marker at peak: dot + crosshair (no text)
        const pulse = reduced ? 1 : 1 + 0.25 * Math.sin(t * 0.0022 + p.seed)
        ctx.fillStyle = p === PEAKS[0] ? 'rgba(224,86,47,0.9)' : 'rgba(232,163,61,0.85)'
        ctx.beginPath(); ctx.arc(cx, cy, 3 * pulse, 0, Math.PI * 2); ctx.fill()
        ctx.strokeStyle = 'rgba(236,227,208,0.25)'
        ctx.beginPath()
        ctx.moveTo(cx - 13, cy); ctx.lineTo(cx - 5, cy)
        ctx.moveTo(cx + 5, cy); ctx.lineTo(cx + 13, cy)
        ctx.moveTo(cx, cy - 13); ctx.lineTo(cx, cy - 5)
        ctx.moveTo(cx, cy + 5); ctx.lineTo(cx, cy + 13)
        ctx.stroke()
      }
    }

    const loop = (now) => { t = now; draw(); raf = requestAnimationFrame(loop) }

    resize()
    window.addEventListener('resize', resize)
    if (!reduced) {
      window.addEventListener('pointermove', onMove, { passive: true })
      window.addEventListener('pointerleave', onLeave)
      const onVis = () => {
        if (document.hidden) { cancelAnimationFrame(raf); raf = null }
        else if (!raf) raf = requestAnimationFrame(loop)
      }
      document.addEventListener('visibilitychange', onVis)
      raf = requestAnimationFrame(loop)
      return () => {
        cancelAnimationFrame(raf)
        window.removeEventListener('resize', resize)
        window.removeEventListener('pointermove', onMove)
        window.removeEventListener('pointerleave', onLeave)
        document.removeEventListener('visibilitychange', onVis)
      }
    }
    t = 1; draw() // static frame for reduced motion
    return () => window.removeEventListener('resize', resize)
  }, [])

  return <canvas ref={ref} className={className} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} aria-hidden="true" />
}
