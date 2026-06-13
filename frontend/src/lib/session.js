// Current chat session id. Module-level → survives page navigation within the SPA,
// resets on a full reload. `newSession()` starts a fresh thread on demand.
let _sid = null

export function sessionId() {
  if (!_sid) {
    _sid = crypto.randomUUID
      ? crypto.randomUUID()
      : 's-' + Date.now() + '-' + Math.random().toString(36).slice(2)
  }
  return _sid
}

export function newSession() {
  _sid = null
  return sessionId()
}
