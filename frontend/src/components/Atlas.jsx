import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GraphCanvas, darkTheme } from 'reagraph'
import { fmtDays } from '../lib/api.js'

// Risk → palette. Unscored (not a danger zone) reads as neutral, not "safe".
const riskFill = (r) =>
  r == null ? '#6a614f' : r >= 45 ? '#e0562f' : r >= 30 ? '#e8a33d' : '#93a86a'

const theme = {
  ...darkTheme,
  canvas: { ...darkTheme.canvas, background: '#0b0905' },
  node: {
    ...darkTheme.node,
    label: { ...darkTheme.node.label, color: '#ece3d0', activeColor: '#ffb454', stroke: '#0b0905' },
  },
  edge: { ...darkTheme.edge, fill: 'rgba(236,227,208,0.16)', activeFill: '#e8a33d' },
}

export default function Atlas({ repo, nodes, links }) {
  const navigate = useNavigate()
  const [sel, setSel] = useState(null)

  const gnodes = useMemo(
    () =>
      (nodes || []).map((n) => ({
        id: n.id,
        label: n.label,
        fill: riskFill(n.risk),
        size: Math.max(6, Math.min(26, 4 + Math.sqrt(n.fan_in) * 3.5)),
        data: n,
      })),
    [nodes],
  )
  const gedges = links || []

  const node = sel?.data

  return (
    <div className="atlas-shell">
      <div className="atlas-canvas">
        {gnodes.length === 0 ? (
          <div className="placeholder"><div className="display">No code graph yet.</div></div>
        ) : (
          <GraphCanvas
            nodes={gnodes}
            edges={gedges}
            theme={theme}
            layoutType="forceDirected2d"
            labelType="nodes"
            draggable
            onNodeClick={(n) => setSel(n)}
            onCanvasClick={() => setSel(null)}
          />
        )}
        <div className="atlas-legend">
          <span><i style={{ background: '#e0562f' }} /> high risk</span>
          <span><i style={{ background: '#e8a33d' }} /> elevated</span>
          <span><i style={{ background: '#93a86a' }} /> low</span>
          <span><i style={{ background: '#6a614f' }} /> unscored</span>
          <span className="legend-note">node size = fan-in (blast radius)</span>
        </div>
      </div>

      <div className="atlas-detail">
        {!node && (
          <div className="placeholder">
            <div className="display">Pick a node.</div>
            The biggest, reddest nodes are the most-imported, highest-risk files — learn those first.
          </div>
        )}
        {node && (
          <>
            <span className="label">SELECTED FILE</span>
            <div className="ad-name">{node.label}</div>
            <div className="ad-dir">{node.dir}</div>
            <div className="ad-stats">
              <div><b>{node.fan_in}</b><span>fan-in</span></div>
              <div><b className={node.risk >= 45 ? 'ember' : ''}>{node.risk != null ? Math.round(node.risk) : '—'}</b><span>risk</span></div>
              <div><b className={node.has_tests ? 'moss' : 'ember'}>{node.has_tests ? 'yes' : 'no'}</b><span>tests</span></div>
            </div>
            {node.owner && <div className="ad-owner">owner — <em>{node.owner}</em></div>}
            <button className="btn solid" data-hover onClick={() => navigate(`/explorer?repo=${encodeURIComponent(repo)}&path=${encodeURIComponent(node.id)}`)}>
              Open in Explorer →
            </button>
          </>
        )}
      </div>
    </div>
  )
}
