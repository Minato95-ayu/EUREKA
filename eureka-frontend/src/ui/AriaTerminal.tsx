import type { AriaState } from '../core/EurekaTypes'

interface AriaPanelProps {
  ariaState: AriaState
  ariaReply: string
  onLoadEngine: () => void
  onExplainPart: () => void
  onZoomIn: () => void
}

export default function AriaTerminal({ ariaState, ariaReply, onLoadEngine, onExplainPart, onZoomIn }: AriaPanelProps) {
  return (
    <aside className="aria-panel">
      <div className="section-title">ARIA Agent <span>{ariaState}</span></div>
      <p>{ariaReply}</p>
      <div className="aria-chips">
        <button onClick={onLoadEngine}>Load Engine</button>
        <button onClick={onExplainPart}>Explain Part</button>
        <button onClick={onZoomIn}>Zoom In</button>
      </div>
    </aside>
  )
}
