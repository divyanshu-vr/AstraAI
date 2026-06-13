/* Page-transition wipe: cover (columns rise) → navigate → uncover (columns fall).
   useWipeNav() returns a navigate function that plays the full sequence. */

import { createContext, useCallback, useContext, useLayoutEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { prefersReduced } from './motion.jsx'

const WipeCtx = createContext(() => {})

export function WipeProvider({ children }) {
  const overlay = useRef(null)
  const busy = useRef(false)
  const navigate = useNavigate()
  const location = useLocation()
  const pendingUncover = useRef(false)

  const go = useCallback((to) => {
    if (busy.current) return
    if (to === location.pathname + location.search) return
    if (prefersReduced()) { navigate(to); return }
    busy.current = true
    const cols = overlay.current.querySelectorAll('i')
    gsap.timeline()
      .set(cols, { scaleY: 0, transformOrigin: 'bottom' })
      .to(cols, {
        scaleY: 1, duration: 0.5, stagger: 0.045, ease: 'power3.inOut',
        onComplete: () => {
          pendingUncover.current = true
          navigate(to)
        },
      })
  }, [navigate, location])

  /* after the new route mounts: scroll top, refresh triggers, uncover */
  useLayoutEffect(() => {
    window.scrollTo(0, 0)
    requestAnimationFrame(() => ScrollTrigger.refresh())
    if (!pendingUncover.current) return
    pendingUncover.current = false
    const cols = overlay.current.querySelectorAll('i')
    gsap.timeline({ onComplete: () => { busy.current = false } })
      .to(cols, { scaleY: 0, duration: 0.55, stagger: 0.045, ease: 'power3.inOut', transformOrigin: 'top', delay: 0.08 })
  }, [location.pathname, location.search])

  return (
    <WipeCtx.Provider value={go}>
      <div className="wipe" ref={overlay} aria-hidden="true"><i /><i /><i /><i /><i /></div>
      {children}
    </WipeCtx.Provider>
  )
}

export const useWipeNav = () => useContext(WipeCtx)
