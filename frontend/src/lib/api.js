export const api = {
  async get(path) {
    const r = await fetch(path)
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
    return r.json()
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
    return r.json()
  },
}

// Stable per-browser id so Astra's long-term memory can attribute facts across sessions.
export function userId() {
  let id = localStorage.getItem('astra_uid')
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID() : 'u-' + Date.now() + '-' + Math.random().toString(36).slice(2)
    localStorage.setItem('astra_uid', id)
  }
  return id
}

export const riskClass = (r) =>
  r == null ? 'r-none' : r >= 45 ? 'r-high' : r >= 30 ? 'r-mid' : 'r-low'

export const fmtDays = (d) =>
  d == null ? '—' : d >= 365 ? (d / 365).toFixed(1) + 'y' : Math.round(d) + 'd'
