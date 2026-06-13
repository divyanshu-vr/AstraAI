import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { api } from '../lib/api.js'
import { useWipeNav } from '../lib/wipe.jsx'

const LINKS = [
  ['/', 'Index'],
  ['/repos', 'Workspace'],
  ['/explorer', 'Explorer'],
  ['/chat', 'Chat'],
  ['/onboarding', 'Onboarding'],
]

export default function Nav() {
  const [ready, setReady] = useState(null)
  const go = useWipeNav()
  const { pathname } = useLocation()

  useEffect(() => {
    api.get('/api/status').then((s) => setReady(s.ready)).catch(() => {})
  }, [pathname])

  const wipeTo = (to) => (e) => { e.preventDefault(); if (to !== pathname) go(to) }

  return (
    <nav className="nav">
      <NavLink to="/" className="brand" data-hover onClick={wipeTo('/')}>
        <span className="star">✶</span>ASTRA
        {ready > 0 && <span className="repo-suffix" style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.2em', color: 'var(--paper-faint)', marginLeft: 10 }}>/ {ready} REPO{ready > 1 ? 'S' : ''}</span>}
      </NavLink>
      <div className="links">
        {LINKS.map(([to, name]) => (
          <NavLink key={to} to={to} end={to === '/'} onClick={wipeTo(to)} className={({ isActive }) => (isActive ? 'active' : '')}>
            {name}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
