/* tiny safe markdown: escape first, then transform (ported from v1, verified) */

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

function inline(s) {
  return s
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[(\d+)\]/g, '<code class="cite">[$1]</code>')
}

export function md(src) {
  if (!src) return ''
  const lines = esc(src.trim()).split('\n')
  const out = []
  let list = null
  let para = []

  const closeList = () => { if (list) { out.push(`</${list}>`); list = null } }
  const flushPara = () => { if (para.length) { out.push(`<p>${inline(para.join(' '))}</p>`); para = [] } }

  for (const raw of lines) {
    const line = raw.trimEnd()
    const h = line.match(/^(#{1,3})\s+(.*)/)
    const ol = line.match(/^\s*\d+[.)]\s+(.*)/)
    const ul = line.match(/^\s*[-*•]\s+(.*)/)

    if (!line.trim()) { flushPara(); closeList(); continue }
    if (h) { flushPara(); closeList(); out.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`); continue }
    if (/^---+$/.test(line.trim())) { flushPara(); closeList(); out.push('<hr>'); continue }
    if (ol) { flushPara(); if (list !== 'ol') { closeList(); out.push('<ol>'); list = 'ol' } out.push(`<li>${inline(ol[1])}</li>`); continue }
    if (ul) { flushPara(); if (list !== 'ul') { closeList(); out.push('<ul>'); list = 'ul' } out.push(`<li>${inline(ul[1])}</li>`); continue }
    para.push(line.trim())
  }
  flushPara(); closeList()
  return out.join('\n')
}
