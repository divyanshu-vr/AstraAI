import { useEffect, useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'

import Cursor from './components/Cursor.jsx'
import Preloader from './components/Preloader.jsx'
import Nav from './components/Nav.jsx'
import Landing from './pages/Landing.jsx'
import Repos from './pages/Repos.jsx'
import Explorer from './pages/Explorer.jsx'
import Chat from './pages/Chat.jsx'
import Onboarding from './pages/Onboarding.jsx'
import { WipeProvider } from './lib/wipe.jsx'
import { prefersReduced } from './lib/motion.jsx'

gsap.registerPlugin(ScrollTrigger)

export default function App() {
  const [booted, setBooted] = useState(false)

  /* Lenis smooth scroll, synced with ScrollTrigger (fine-pointer devices only) */
  useEffect(() => {
    if (prefersReduced() || !window.matchMedia('(hover: hover)').matches) return
    const lenis = new Lenis({ duration: 1.1, smoothWheel: true })
    lenis.on('scroll', ScrollTrigger.update)
    const raf = (time) => lenis.raf(time * 1000)
    gsap.ticker.add(raf)
    gsap.ticker.lagSmoothing(0)
    return () => { gsap.ticker.remove(raf); lenis.destroy() }
  }, [])

  return (
    <WipeProvider>
      <Cursor />
      {!booted && <Preloader onDone={() => setBooted(true)} />}
      <Nav />
      <Routes>
        <Route path="/" element={<Landing booted={booted} />} />
        <Route path="/repos" element={<Repos />} />
        <Route path="/explorer" element={<Explorer />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/onboarding" element={<Onboarding />} />
      </Routes>
    </WipeProvider>
  )
}
