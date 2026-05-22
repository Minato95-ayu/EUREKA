import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Sphere, MeshDistortMaterial, Html, Edges, Environment, ContactShadows } from '@react-three/drei'
import type { Hands as MediaPipeHands, Results } from '@mediapipe/hands'
import type { Group } from 'three'
import './App.css'

type Tab = 'status' | 'batch' | 'pipeline' | 'research' | 'results'
type AriaState = 'idle' | 'listening' | 'thinking' | 'speaking'
type GestureState = 'offline' | 'ready' | 'zoom-in' | 'zoom-out' | 'point' | 'fist' | 'swipe-left' | 'swipe-right'
type ScaleLevel = 'object' | 'component' | 'subcomponent' | 'material' | 'molecule' | 'atom'

type ObjectGeometry = {
  type: 'box' | 'cylinder' | 'capsule' | 'fan'
  size?: [number, number, number]
  radius?: number
  depth?: number
  blades?: number
  rotation?: [number, number, number]
}

type ObjectComponent = {
  id: string
  name: string
  parentId: string | null
  scaleLevel: ScaleLevel
  function: string
  material?: string | null
  riskIfRemoved?: string | null
  position: [number, number, number]
  color: string
  geometry: ObjectGeometry
  children: string[]
  microLevels: Array<{ level: ScaleLevel; name: string; description: string; next?: string | null }>
}

type ExplorableObject = {
  id: string
  name: string
  type: string
  summary: string
  defaultView: string
  model: { kind: 'procedural' | 'gltf'; assetUrl: string | null }
  components: ObjectComponent[]
}

type SpeechRecognitionResultItem = {
  transcript: string
}

type SpeechRecognitionResult = {
  0: SpeechRecognitionResultItem
}

type SpeechRecognitionEventLike = {
  results: {
    length: number
    [index: number]: SpeechRecognitionResult
  }
}

type BrowserSpeechRecognition = {
  lang: string
  continuous: boolean
  interimResults: boolean
  start: () => void
  stop: () => void
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onend: (() => void) | null
  onerror: (() => void) | null
}

declare global {
  interface Window {
    SpeechRecognition?: new () => BrowserSpeechRecognition
    webkitSpeechRecognition?: new () => BrowserSpeechRecognition
    Hands?: new (config?: { locateFile?: (file: string) => string }) => MediaPipeHands
  }
}

function loadMediaPipeHands(): Promise<new (config?: { locateFile?: (file: string) => string }) => MediaPipeHands> {
  if (window.Hands) return Promise.resolve(window.Hands)

  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-eureka-mediapipe-hands]')
    if (existing) {
      existing.addEventListener('load', () => window.Hands ? resolve(window.Hands) : reject(new Error('MediaPipe Hands unavailable')))
      existing.addEventListener('error', () => reject(new Error('MediaPipe Hands failed to load')))
      return
    }

    const script = document.createElement('script')
    script.dataset.eurekaMediapipeHands = 'true'
    script.src = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js'
    script.async = true
    script.onload = () => window.Hands ? resolve(window.Hands) : reject(new Error('MediaPipe Hands unavailable'))
    script.onerror = () => reject(new Error('MediaPipe Hands failed to load'))
    document.head.appendChild(script)
  })
}

const tabs: Array<{ id: Tab; label: string; icon: string }> = [
  { id: 'status', label: 'Status', icon: '▦' },
  { id: 'batch', label: 'Batch', icon: '▷' },
  { id: 'pipeline', label: 'Pipeline', icon: '⌬' },
  { id: 'research', label: 'Research', icon: '▣' },
  { id: 'results', label: 'Results', icon: '▤' }
]

const logs = [
  '[SYSTEM INIT] telemetry stream stable',
  '> Connecting to instance alpha-node-01... [OK]',
  '[10:42:01] FETCHING: ArXiv/Quantum_Computing',
  '[10:42:04] PARSING: metadata and abstracts',
  '[10:42:08] WARN: rate limit approaching',
  '[10:42:15] PROCESSING: Neural_Network_Model',
  '[10:42:18] SUCCESS: vectors indexed',
  '> Awaiting input'
]

const papers = [
  {
    title: 'Emergent Behaviors in Large-Scale Multi-Agent Reinforcement Learning Environments',
    authors: 'D. Evans, S. Chen, M. Botava',
    relevance: 98
  },
  {
    title: 'Optimizing Latent Space Representations for Zero-Shot Anomaly Detection',
    authors: 'A. Kim, L. Thorne',
    relevance: 86
  },
  {
    title: 'Neuromorphic Hardware Substrates for Energy-Efficient Edge Inference',
    authors: 'A. Patel, J. Zhang, W. Brooks',
    relevance: 72
  }
]

function ComponentMesh({
  component,
  selected,
  onSelect,
  explodeFactor,
  shellMode,
  showLabels
}: {
  component: ObjectComponent
  selected: boolean
  onSelect: (component: ObjectComponent) => void
  explodeFactor: number
  shellMode: 'solid' | 'transparent' | 'hidden'
  showLabels: boolean
}) {
  const geometry = component.geometry
  const rotation = geometry.rotation || [0, 0, 0]

  const isCover = useMemo(() => {
    return /block|head|pan|chassis|base|cover|housing|shell/i.test(component.name) || component.id === 'engine_block';
  }, [component.name, component.id])

  const defaultPos = component.position
  const displacedPos = useMemo(() => {
    let pos = [...defaultPos] as [number, number, number]
    if (component.parentId !== null) {
      const dirX = defaultPos[0]
      const dirY = defaultPos[1]
      const dirZ = defaultPos[2]
      const length = Math.hypot(dirX, dirY, dirZ) || 1.0
      pos = [
        defaultPos[0] + (dirX / length) * explodeFactor * 1.2,
        defaultPos[1] + (dirY / length) * explodeFactor * 1.2,
        defaultPos[2] + (dirZ / length) * explodeFactor * 1.2,
      ]
    }
    return pos
  }, [defaultPos, component.parentId, explodeFactor])

  const materialProps = useMemo(() => {
    const matName = (component.material || '').toLowerCase()
    let roughness = 0.4
    let metalness = 0.3
    let transparent = false
    let opacity = 1.0

    if (shellMode === 'transparent' && isCover) {
      roughness = 0.05
      metalness = 0.95
      transparent = true
      opacity = 0.15
    } else {
      if (matName.includes('iron')) {
        roughness = 0.6
        metalness = 0.8
      } else if (matName.includes('steel') || matName.includes('chrome') || matName.includes('metal')) {
        roughness = 0.15
        metalness = 0.95
      } else if (matName.includes('aluminum') || matName.includes('alloy')) {
        roughness = 0.3
        metalness = 0.85
      } else if (matName.includes('copper') || matName.includes('brass') || matName.includes('bronze')) {
        roughness = 0.2
        metalness = 0.9
      } else if (matName.includes('carbon') || matName.includes('fiber')) {
        roughness = 0.45
        metalness = 0.1
      } else if (matName.includes('glass') || matName.includes('lens') || matName.includes('optical')) {
        roughness = 0.05
        metalness = 0.9
        transparent = true
        opacity = 0.35
      } else if (matName.includes('polymer') || matName.includes('plastic') || matName.includes('composite')) {
        roughness = 0.5
        metalness = 0.1
      }
    }

    return { roughness, metalness, transparent, opacity }
  }, [component.material, shellMode, isCover])

  if (shellMode === 'hidden' && isCover) {
    return null
  }

  const material = (
    <meshStandardMaterial
      color={component.color}
      emissive={selected ? '#145b63' : '#071114'}
      roughness={materialProps.roughness}
      metalness={materialProps.metalness}
      transparent={materialProps.transparent}
      opacity={materialProps.opacity}
    />
  )

  const handlePointerDown = (event: { stopPropagation: () => void }) => {
    event.stopPropagation()
    onSelect(component)
  }

  const edgeColor = selected ? '#00ffff' : '#2b6cb0'
  const edgeThickness = selected ? 2 : 1

  if (geometry.type === 'fan') {
    const blades = geometry.blades || 6
    const radius = geometry.radius || 0.42
    return (
      <group position={displacedPos} rotation={rotation} onPointerDown={handlePointerDown}>
        <mesh castShadow receiveShadow>
          <torusGeometry args={[radius, 0.025, 10, 48]} />
          {material}
          <Edges color={edgeColor} thickness={edgeThickness} />
        </mesh>
        {Array.from({ length: blades }).map((_, index) => (
          <mesh key={index} rotation={[0, 0, (Math.PI * 2 * index) / blades]} position={[0, 0, 0.02]} castShadow receiveShadow>
            <boxGeometry args={[radius * 0.9, 0.055, 0.035]} />
            {material}
            <Edges color={edgeColor} thickness={edgeThickness} />
          </mesh>
        ))}
        {showLabels && (
          <Html position={[0, -0.62, 0]} center>
            <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
          </Html>
        )}
      </group>
    )
  }

  return (
    <mesh position={displacedPos} rotation={rotation} onPointerDown={handlePointerDown} castShadow receiveShadow>
      {geometry.type === 'box' && <boxGeometry args={geometry.size || [1, 1, 1]} />}
      {(geometry.type === 'cylinder' || geometry.type === 'capsule') && (
        <cylinderGeometry args={[geometry.radius || 0.2, geometry.radius || 0.2, geometry.depth || 0.6, 32]} />
      )}
      {material}
      <Edges color={edgeColor} thickness={edgeThickness} />
      {showLabels && (
        <Html position={[0, geometry.type === 'box' ? (geometry.size?.[1] ? geometry.size[1]/2 + 0.32 : 0.82) : (geometry.depth ? geometry.depth/2 + 0.18 : 0.48), 0]} center>
          <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
        </Html>
      )}
    </mesh>
  )
}

function LabScene({
  zoomLevel,
  gesture,
  activeObject,
  selectedComponent,
  onSelectComponent,
  explodeFactor,
  shellMode,
  showLabels
}: {
  zoomLevel: number
  gesture: GestureState
  activeObject: ExplorableObject | null
  selectedComponent: ObjectComponent | null
  onSelectComponent: (component: ObjectComponent) => void
  explodeFactor: number
  shellMode: 'solid' | 'transparent' | 'hidden'
  showLabels: boolean
}) {
  const group = useRef<Group>(null)

  useFrame(({ clock, camera }) => {
    const t = clock.getElapsedTime()
    // Logarithmic camera distance to support 100x zoom cleanly without sudden clipping
    const zoomLog = Math.log10(zoomLevel) // ranges from 0 (at 1x) to 2 (at 100x)
    camera.position.z = Math.max(0.08, 6 - zoomLog * 2.75)
    camera.position.y = Math.max(0.02, 1.4 - zoomLog * 0.65)
    
    if (group.current) {
      group.current.rotation.y = t * 0.22 + (gesture === 'swipe-left' ? -0.35 : gesture === 'swipe-right' ? 0.35 : 0)
      group.current.rotation.x = Math.sin(t * 0.4) * 0.08
    }
  })

  return (
    <>
      <ambientLight intensity={0.25} />
      <directionalLight position={[5, 8, 5]} intensity={1.5} castShadow />
      <pointLight position={[-4, 3, 4]} intensity={1.5} color="#00e5f0" />
      <spotLight position={[0, 10, 0]} intensity={1.2} angle={0.6} penumbra={0.8} />
      <group ref={group}>
        {activeObject ? (
          activeObject.components.map((component) => (
            <ComponentMesh
              component={component}
              key={component.id}
              selected={selectedComponent?.id === component.id}
              onSelect={onSelectComponent}
              explodeFactor={explodeFactor}
              shellMode={shellMode}
              showLabels={showLabels}
            />
          ))
        ) : (
          <>
            <mesh position={[0, 0, 0]}>
              <boxGeometry args={[1.25, 1.25, 1.25]} />
              <meshStandardMaterial color="#556270" roughness={0.2} metalness={0.8} />
            </mesh>
            <Sphere args={[0.44, 48, 48]} position={[-1.25, -0.28, 0]}>
              <MeshDistortMaterial color="#dfe6e9" distort={0.09} speed={1.1} roughness={0.1} metalness={0.9} />
            </Sphere>
            <Sphere args={[0.44, 48, 48]} position={[1.25, -0.28, 0]}>
              <MeshDistortMaterial color="#2f3640" distort={0.09} speed={1.1} roughness={0.3} metalness={0.8} />
            </Sphere>
          </>
        )}
      </group>
      <Environment preset="studio" />
      <ContactShadows position={[0, -1.2, 0]} opacity={0.75} scale={10} blur={2.5} far={2} />
      <gridHelper args={[20, 20, '#00e5f0', '#2d3748']} position={[0, -1.2, 0]} />
      <OrbitControls enableDamping dampingFactor={0.08} minDistance={0.05} maxDistance={30.0} />
    </>
  )
}

function MetricCard({ label, value, detail, tone = 'cyan' }: { label: string; value: string; detail: string; tone?: 'cyan' | 'pink' | 'green' }) {
  return (
    <section className={`metric-card tone-${tone}`}>
      <div className="metric-label">{label}</div>
      <strong>{value}</strong>
      <span>{detail}</span>
    </section>
  )
}

function StatusScreen() {
  return (
    <main className="screen-grid">
      <section className="hero-copy">
        <p className="eyebrow">SYS.ONLINE</p>
        <h1>System Overview</h1>
        <p>Global telemetry and autonomous research operations.</p>
      </section>
      <div className="metric-grid">
        <MetricCard label="ACTIVE SWARM" value="03" detail="Puppeteer instances running" />
        <MetricCard label="PIPELINE YIELD" value="85%" detail="Optimal range" tone="green" />
        <MetricCard label="CORPUS INTAKE" value="12" detail="Research papers processed today" />
      </div>
      <section className="terminal-card">
        <div className="terminal-head">▣ STD_OUT // Live Feed <span>●●●</span></div>
        <div className="terminal-lines">
          {logs.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      </section>
      <section className="chart-card">
        <div className="section-title">Ingestion Rate <span>⌁</span></div>
        <div className="bar-chart">
          {[34, 58, 42, 82, 66, 96, 48].map((height, index) => (
            <i key={index} style={{ height: `${height}%` }} />
          ))}
        </div>
        <div className="chart-axis"><span>T-6h</span><span>Now</span></div>
      </section>
    </main>
  )
}

function BatchScreen() {
  return (
    <main className="stack-screen">
      <section className="hero-copy">
        <h1>Batch Operations</h1>
        <p>Manage active computational pipelines.</p>
        <button className="primary-button">+ New Batch</button>
      </section>
      <section className="job-card active-job">
        <div className="job-row"><span className="pill">Active</span><span>ID: MD-2049-A</span><strong>72%</strong></div>
        <h2>Molecular Dynamics Simulation</h2>
        <div className="progress"><i style={{ width: '72%' }} /></div>
        <div className="job-meta">
          <span><small>Model</small>GPT-4-Res</span>
          <span><small>Threads</small>16 Core</span>
          <span><small>Source</small>ArXiv Corpus</span>
          <span><small>Compute Node</small>Theta-04</span>
        </div>
      </section>
      <section className="job-card warning-job">
        <div className="job-row"><span className="pill warning">Warning</span><strong>41%</strong></div>
        <h2>Protein Structure Prediction</h2>
        <div className="progress warning"><i style={{ width: '41%' }} /></div>
        <div className="job-meta compact">
          <span><small>Model</small>AlphaFold-v2</span>
          <span><small>Memory</small>98% Utilization</span>
        </div>
      </section>
      <section className="panel-card">
        <div className="section-title">Queue <span>3 Pending</span></div>
        {['Quantum Circuit Optimization', 'Material Synthesis Analysis', 'Catalyst Reaction Scan'].map((item, index) => (
          <div className="queue-item" key={item}>
            <b>◷</b>
            <span>{item}<small>ID: Q-{index + 1}01 | Priority: {index === 0 ? 'High' : 'Normal'}</small></span>
          </div>
        ))}
      </section>
    </main>
  )
}

function PipelineScreen() {
  const steps = [
    ['Parser', 'Completed', 'Successfully parsed 1,204 source documents and standardized schema structures.', '1,204 docs'],
    ['Scraper', 'Active', 'Extracting raw text data from targeted scientific repositories.', '68%'],
    ['AI Agent Analysis', 'Pending', 'Awaiting scraped payload to begin semantic evaluation and pattern recognition.', 'queued'],
    ['Report Generation', 'Locked', 'Final synthesis requires prior steps to complete.', 'locked']
  ]

  return (
    <main className="pipeline-screen">
      <section className="hero-copy compact-hero">
        <p className="eyebrow">Pipeline Status</p>
        <p>Real-time autonomous extraction and analysis flow.</p>
        <div className="button-row"><button className="ghost-button">▮▮ Pause</button><button className="primary-button">▷ Run Pipeline</button></div>
      </section>
      <div className="timeline">
        {steps.map(([name, state, detail, stat], index) => (
          <section className={`timeline-card ${state.toLowerCase()}`} key={name}>
            <div className="timeline-dot">{index < 2 ? '✓' : index === 2 ? '⌁' : '▣'}</div>
            <div className="timeline-body">
              <div className="job-row"><h2>{name}</h2><span className="mini-status">{state}</span></div>
              <p>{detail}</p>
              <div className="data-tile">{stat}</div>
            </div>
          </section>
        ))}
      </div>
      <section className="panel-card">
        <div className="section-title">System Metrics <span>⌁</span></div>
        <div className="metric-line"><span>CPU Usage</span><b>42%</b><i style={{ width: '42%' }} /></div>
        <div className="metric-line purple"><span>Memory</span><b>14.2 GB</b><i style={{ width: '68%' }} /></div>
        <div className="mini-bars">{[28, 42, 26, 54, 36, 62, 70, 14, 15, 12].map((h, i) => <i key={i} style={{ height: `${h}%` }} />)}</div>
      </section>
    </main>
  )
}

function ResultsScreen() {
  return (
    <main className="results-screen">
      <section className="hero-copy compact-hero">
        <h1>Research Results</h1>
        <p>Fetch source: puppeteer cluster 04 // status complete</p>
      </section>
      <section className="paper-list">
        {papers.map((paper, index) => (
          <article className={index === 0 ? 'paper-card selected' : 'paper-card'} key={paper.title}>
            <div><span>ID: P-{index + 43}</span><span>Relevance: {paper.relevance}%</span></div>
            <h2>{paper.title}</h2>
            <p>Authors: {paper.authors}</p>
          </article>
        ))}
      </section>
      <section className="analysis-card">
        <p className="eyebrow">Document Analysis ● Live Sync</p>
        <h2>{papers[0].title}</h2>
        <p className="summary">ARIA summary generated: experiments show unpredictable compact behaviors that arise when scaling multi-agent systems beyond 10,000 agents. The authors demonstrate a novel consensus algorithm that mitigates reward-hacking while supporting cooperative resource allocation.</p>
        <div className="insight-list">
          <span><b>◇ Spontaneous Protocol Formation</b> Agents develop compressed communication routines.</span>
          <span><b>△ Reward Hacking Migration</b> Standard mitigation failed at larger scales.</span>
          <span><b>⌁ Scalability Threshold</b> Performance degrades past 10K agents.</span>
        </div>
        <div className="button-row"><button className="ghost-button">Save to Pipeline</button><button className="primary-button">Visualize in 3D</button></div>
      </section>
    </main>
  )
}

function ResearchScreen({
  query,
  setQuery,
  onExecute,
  ariaState,
  voiceSupported,
  onToggleVoice,
  cameraEnabled,
  onToggleCamera,
  videoRef,
  gesture,
  zoomLevel,
  setZoomLevel,
  activeObject,
  selectedComponent,
  onObjectSearch,
  onSelectComponent,
  explodeFactor,
  setExplodeFactor,
  shellMode,
  setShellMode,
  showLabels,
  setShowLabels
}: {
  query: string
  setQuery: (value: string) => void
  onExecute: () => void
  ariaState: AriaState
  voiceSupported: boolean
  onToggleVoice: () => void
  cameraEnabled: boolean
  onToggleCamera: () => void
  videoRef: React.RefObject<HTMLVideoElement | null>
  gesture: GestureState
  zoomLevel: number
  setZoomLevel: (value: number | ((prev: number) => number)) => void
  activeObject: ExplorableObject | null
  selectedComponent: ObjectComponent | null
  onObjectSearch: () => void
  onSelectComponent: (component: ObjectComponent) => void
  explodeFactor: number
  setExplodeFactor: (value: number) => void
  shellMode: 'solid' | 'transparent' | 'hidden'
  setShellMode: (value: 'solid' | 'transparent' | 'hidden') => void
  showLabels: boolean
  setShowLabels: (value: boolean) => void
}) {
  return (
    <main className="research-screen">
      <section className="query-card">
        <textarea value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Enter research query or say: ARIA, analyze water molecules" />
        <div className="command-row">
          <button className={`icon-button ${ariaState === 'listening' ? 'active' : ''}`} onClick={onToggleVoice} disabled={!voiceSupported} title="Voice command">⌕</button>
          <button className={`icon-button ${cameraEnabled ? 'active' : ''}`} onClick={onToggleCamera} title="Camera gesture control">◉</button>
          <button className="ghost-button" onClick={onObjectSearch}>Search Object</button>
          <button className="primary-button execute" onClick={onExecute}>Execute ▷</button>
        </div>
      </section>

      <section className="core-card">
        <div className="core-title"><span>▣</span> {activeObject ? activeObject.name : 'EUREKA CORE'}</div>
        <ul className="core-steps">
          {activeObject ? (
            <>
              <li>Loaded {activeObject.components.length} explorable components.</li>
              <li>Selected: {selectedComponent ? selectedComponent.name : 'none'}</li>
              <li>{selectedComponent ? selectedComponent.function : activeObject.summary}</li>
            </>
          ) : (
            <>
              <li>Accessing demo molecular structure... [OK]</li>
              <li>Search car engine to load the first invention object.</li>
              <li>Awaiting object command...</li>
            </>
          )}
        </ul>
        <div className="scene-shell" style={{ position: 'relative' }}>
          <Canvas>
            <LabScene
              zoomLevel={zoomLevel}
              gesture={gesture}
              activeObject={activeObject}
              selectedComponent={selectedComponent}
              onSelectComponent={onSelectComponent}
              explodeFactor={explodeFactor}
              shellMode={shellMode}
              showLabels={showLabels}
            />
          </Canvas>
          <div className="viewport-controls-overlay">
            <div className="control-group">
              <label>Dismantle (Exploded View)</label>
              <div className="slider-wrapper">
                <input
                  type="range"
                  min="0"
                  max="1.5"
                  step="0.05"
                  value={explodeFactor}
                  onChange={(e) => setExplodeFactor(parseFloat(e.target.value))}
                />
                <span className="control-val">{(explodeFactor * 66.6).toFixed(0)}%</span>
              </div>
            </div>
            
            <div className="control-group">
              <label>Outer Covers Mode</label>
              <div className="btn-toggle-group">
                <button
                  className={shellMode === 'solid' ? 'active' : ''}
                  onClick={() => setShellMode('solid')}
                >
                  Solid
                </button>
                <button
                  className={shellMode === 'transparent' ? 'active' : ''}
                  onClick={() => setShellMode('transparent')}
                >
                  Glass
                </button>
                <button
                  className={shellMode === 'hidden' ? 'active' : ''}
                  onClick={() => setShellMode('hidden')}
                >
                  Hidden
                </button>
              </div>
            </div>

            <div className="control-group">
              <label>Deep Zoom (up to 100x)</label>
              <div className="slider-wrapper">
                <input
                  type="range"
                  min="1"
                  max="100"
                  step="1"
                  value={zoomLevel}
                  onChange={(e) => setZoomLevel(parseInt(e.target.value))}
                />
                <span className="control-val">{zoomLevel}x</span>
              </div>
            </div>

            <div className="control-group inline">
              <label>Component Labels</label>
              <button
                className={`toggle-switch ${showLabels ? 'active' : ''}`}
                onClick={() => setShowLabels(!showLabels)}
              >
                {showLabels ? 'ON' : 'OFF'}
              </button>
            </div>
          </div>
        </div>
      </section>

      {activeObject && (
        <section className="component-card">
          <div className="section-title">Component Graph <span>{activeObject.defaultView}</span></div>
          <div className="component-list">
            {activeObject.components.map((component) => (
              <button
                className={selectedComponent?.id === component.id ? 'selected' : ''}
                key={component.id}
                onClick={() => onSelectComponent(component)}
              >
                <b>{component.name}</b>
                <span>{component.scaleLevel}</span>
              </button>
            ))}
          </div>
          {selectedComponent && (
            <div className="component-detail">
              <h2>{selectedComponent.name}</h2>
              <p>{selectedComponent.function}</p>
              <span>Material: {selectedComponent.material || 'unknown'}</span>
              <span>Risk: {selectedComponent.riskIfRemoved || 'not defined'}</span>
            </div>
          )}
        </section>
      )}

      <section className="control-card">
        <div className="section-title">Input Systems <span>{ariaState.toUpperCase()}</span></div>
        <div className="control-grid">
          <div><small>Voice Agent</small><b>{voiceSupported ? ariaState : 'unsupported'}</b></div>
          <div><small>Camera</small><b>{cameraEnabled ? 'tracking' : 'offline'}</b></div>
          <div><small>Gesture</small><b>{gesture}</b></div>
          <div><small>Zoom Level</small><b>{zoomLevel.toFixed(0)}x</b></div>
        </div>
        <video ref={videoRef} className={cameraEnabled ? 'camera-preview active' : 'camera-preview'} muted playsInline />
        <p className="hint">Pinch to zoom, point to select, fist to reset, swipe to switch tabs. Voice supports English and Hindi commands.</p>
      </section>
    </main>
  )
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('research')
  const [query, setQuery] = useState('car engine')
  const [ariaState, setAriaState] = useState<AriaState>('idle')
  const [ariaReply, setAriaReply] = useState('ARIA online. Voice and gesture systems are ready for calibration.')
  const [activeObject, setActiveObject] = useState<ExplorableObject | null>(null)
  const [selectedComponent, setSelectedComponent] = useState<ObjectComponent | null>(null)
  const [cameraEnabled, setCameraEnabled] = useState(false)
  const [gesture, setGesture] = useState<GestureState>('offline')
  const [zoomLevel, setZoomLevel] = useState(1)
  const [explodeFactor, setExplodeFactor] = useState(0.0)
  const [shellMode, setShellMode] = useState<'solid' | 'transparent' | 'hidden'>('solid')
  const [showLabels, setShowLabels] = useState(true)
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const handsRef = useRef<MediaPipeHands | null>(null)
  const lastPinchRef = useRef<number | null>(null)
  const lastXRef = useRef<number | null>(null)

  const SpeechRecognitionCtor = useMemo(() => {
    return window.SpeechRecognition || window.webkitSpeechRecognition
  }, [])

  const voiceSupported = Boolean(SpeechRecognitionCtor)

  const selectComponent = useCallback((component: ObjectComponent) => {
    setSelectedComponent(component)
    setAriaReply(`${component.name} selected. ${component.function}`)
  }, [])

  const speak = useCallback((text: string) => {
    setAriaReply(text)
    if (!('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = /[\u0900-\u097F]|hindi|हिंदी/i.test(text) ? 'hi-IN' : 'en-US'
    utterance.rate = 0.95
    utterance.pitch = 0.9
    utterance.onstart = () => setAriaState('speaking')
    utterance.onend = () => setAriaState('idle')
    window.speechSynthesis.speak(utterance)
  }, [])

  const searchObject = useCallback(async (rawQuery?: string) => {
    const searchText = (rawQuery || query).trim() || 'car engine'
    setAriaState('thinking')
    setAriaReply(`Searching object library for ${searchText}...`)

    try {
      const params = new URLSearchParams({ q: searchText })
      const generateResponse = await fetch(`http://localhost:8000/api/objects/generate?${params.toString()}`, {
        method: 'POST'
      })
      if (!generateResponse.ok) throw new Error('Generation failed')
      const objectData = await generateResponse.json()
      setActiveObject(objectData)
      setSelectedComponent(objectData.components?.[0] || null)
      setActiveTab('research')
      speak(`Loaded ${objectData.name}. Select a component or ask ARIA what it does.`)
    } catch {
      const fallback: ExplorableObject = {
        id: 'car_engine',
        name: 'Inline-4 Car Engine',
        type: 'mechanical_system',
        summary: 'Offline high-fidelity inline-4 engine representation with realistic PBR styling.',
        defaultView: 'assembled',
        model: { kind: 'procedural', assetUrl: null },
        components: [
          {
            id: 'engine_block',
            name: 'Engine Block',
            parentId: null,
            scaleLevel: 'component',
            function: 'Central structural block housing cylinders, cooling channels, and crankshaft support.',
            material: 'Cast Iron',
            riskIfRemoved: 'Engine structure collapses; no housing for cylinders or oil flow.',
            position: [0, 0, 0],
            color: '#556270',
            geometry: { type: 'box', size: [2.2, 0.8, 1.0] },
            children: ['cylinder_head', 'oil_pan', 'crankshaft', 'piston_1', 'piston_2', 'piston_3', 'piston_4', 'cooling_fan'],
            microLevels: []
          },
          {
            id: 'cylinder_head',
            name: 'Cylinder Head',
            parentId: 'engine_block',
            scaleLevel: 'subcomponent',
            function: 'Closes the top of the cylinders to form combustion chambers and houses valves.',
            material: 'Aluminum Alloy',
            riskIfRemoved: 'Loss of compression; combustion cannot occur.',
            position: [0, 0.5, 0],
            color: '#778899',
            geometry: { type: 'box', size: [2.2, 0.2, 0.9] },
            children: [],
            microLevels: []
          },
          {
            id: 'oil_pan',
            name: 'Oil Pan',
            parentId: 'engine_block',
            scaleLevel: 'subcomponent',
            function: 'Reservoir for engine oil and collects lubricating fluid under the block.',
            material: 'Pressed Steel',
            riskIfRemoved: 'Oil leaks immediately, causing severe engine seizure due to lack of lubrication.',
            position: [0, -0.5, 0],
            color: '#2c3e50',
            geometry: { type: 'box', size: [2.0, 0.2, 0.8] },
            children: [],
            microLevels: []
          },
          {
            id: 'crankshaft',
            name: 'Crankshaft',
            parentId: 'engine_block',
            scaleLevel: 'subcomponent',
            function: 'Converts linear piston motion into rotational force for the drivetrain.',
            material: 'Forged Steel',
            riskIfRemoved: 'Linear piston energy cannot be converted to mechanical drive.',
            position: [0, -0.3, 0],
            color: '#a8b2c1',
            geometry: { type: 'cylinder', radius: 0.1, depth: 2.2, rotation: [0, 0, 1.57] },
            children: ['flywheel'],
            microLevels: []
          },
          {
            id: 'flywheel',
            name: 'Flywheel',
            parentId: 'crankshaft',
            scaleLevel: 'subcomponent',
            function: 'Heavy disk storing rotational inertia to smooth out engine cycles.',
            material: 'Cast Iron',
            riskIfRemoved: 'Severe engine vibration and stalling between power strokes.',
            position: [1.15, -0.3, 0],
            color: '#34495e',
            geometry: { type: 'cylinder', radius: 0.45, depth: 0.1, rotation: [0, 0, 1.57] },
            children: [],
            microLevels: []
          },
          {
            id: 'piston_1',
            name: 'Piston 1',
            parentId: 'engine_block',
            scaleLevel: 'subcomponent',
            function: 'Reciprocating piston that compresses air-fuel mixture and transmits combustion pressure.',
            material: 'Aluminum Alloy',
            riskIfRemoved: 'Cylinder 1 loses power and creates severe balance issues.',
            position: [-0.75, 0.1, 0.0],
            color: '#dfe6e9',
            geometry: { type: 'cylinder', radius: 0.22, depth: 0.35 },
            children: ['connecting_rod_1'],
            microLevels: []
          },
          {
            id: 'connecting_rod_1',
            name: 'Connecting Rod 1',
            parentId: 'piston_1',
            scaleLevel: 'subcomponent',
            function: 'Connects piston 1 to the crankshaft, translating linear motion.',
            material: 'Forged Steel',
            riskIfRemoved: 'Piston 1 motion is disconnected from the crankshaft.',
            position: [-0.75, -0.15, 0.0],
            color: '#7f8c8d',
            geometry: { type: 'cylinder', radius: 0.05, depth: 0.3 },
            children: [],
            microLevels: []
          },
          {
            id: 'piston_2',
            name: 'Piston 2',
            parentId: 'engine_block',
            scaleLevel: 'subcomponent',
            function: 'Reciprocating piston that compresses air-fuel mixture and transmits combustion pressure.',
            material: 'Aluminum Alloy',
            riskIfRemoved: 'Cylinder 2 loses power.',
            position: [-0.25, 0.1, 0.0],
            color: '#dfe6e9',
            geometry: { type: 'cylinder', radius: 0.22, depth: 0.35 },
            children: ['connecting_rod_2'],
            microLevels: []
          },
          {
            id: 'connecting_rod_2',
            name: 'Connecting Rod 2',
            parentId: 'piston_2',
            scaleLevel: 'subcomponent',
            function: 'Connects piston 2 to the crankshaft, translating linear motion.',
            material: 'Forged Steel',
            riskIfRemoved: 'Piston 2 motion is disconnected.',
            position: [-0.25, -0.15, 0.0],
            color: '#7f8c8d',
            geometry: { type: 'cylinder', radius: 0.05, depth: 0.3 },
            children: [],
            microLevels: []
          },
          {
            id: 'piston_3',
            name: 'Piston 3',
            parentId: 'engine_block',
            scaleLevel: 'subcomponent',
            function: 'Reciprocating piston that compresses air-fuel mixture and transmits combustion pressure.',
            material: 'Aluminum Alloy',
            riskIfRemoved: 'Cylinder 3 loses power.',
            position: [0.25, 0.1, 0.0],
            color: '#dfe6e9',
            geometry: { type: 'cylinder', radius: 0.22, depth: 0.35 },
            children: ['connecting_rod_3'],
            microLevels: []
          },
          {
            id: 'connecting_rod_3',
            name: 'Connecting Rod 3',
            parentId: 'piston_3',
            scaleLevel: 'subcomponent',
            function: 'Connects piston 3 to the crankshaft, translating linear motion.',
            material: 'Forged Steel',
            riskIfRemoved: 'Piston 3 motion is disconnected.',
            position: [0.25, -0.15, 0.0],
            color: '#7f8c8d',
            geometry: { type: 'cylinder', radius: 0.05, depth: 0.3 },
            children: [],
            microLevels: []
          },
          {
            id: 'piston_4',
            name: 'Piston 4',
            parentId: 'engine_block',
            scaleLevel: 'subcomponent',
            function: 'Reciprocating piston that compresses air-fuel mixture and transmits combustion pressure.',
            material: 'Aluminum Alloy',
            riskIfRemoved: 'Cylinder 4 loses power.',
            position: [0.75, 0.1, 0.0],
            color: '#dfe6e9',
            geometry: { type: 'cylinder', radius: 0.22, depth: 0.35 },
            children: ['connecting_rod_4'],
            microLevels: []
          },
          {
            id: 'connecting_rod_4',
            name: 'Connecting Rod 4',
            parentId: 'piston_4',
            scaleLevel: 'subcomponent',
            function: 'Connects piston 4 to the crankshaft, translating linear motion.',
            material: 'Forged Steel',
            riskIfRemoved: 'Piston 4 motion is disconnected.',
            position: [0.75, -0.15, 0.0],
            color: '#7f8c8d',
            geometry: { type: 'cylinder', radius: 0.05, depth: 0.3 },
            children: [],
            microLevels: []
          },
          {
            id: 'cooling_fan',
            name: 'Cooling Fan',
            parentId: 'engine_block',
            scaleLevel: 'subcomponent',
            function: 'Pulls cooling air through radiator to prevent overheating.',
            material: 'Composite Polymer',
            riskIfRemoved: 'Engine runs hot under load, high thermal seizure risk.',
            position: [-1.25, 0.0, 0.0],
            color: '#2f3640',
            geometry: { type: 'fan', radius: 0.5, blades: 6, rotation: [0, 0, 1.57] },
            children: [],
            microLevels: []
          }
        ]
      }
      setActiveObject(fallback)
      setSelectedComponent(fallback.components[0])
      setActiveTab('research')
      speak('Backend offline. Loaded local car engine demo.')
    }
  }, [query, speak])

  const executeCommand = useCallback(async (rawCommand?: string) => {
    const command = (rawCommand || query).trim()
    if (!command) return

    const lower = command.toLowerCase()
    if (lower.includes('batch')) setActiveTab('batch')
    if (lower.includes('pipeline')) setActiveTab('pipeline')
    if (lower.includes('result')) setActiveTab('results')
    if (lower.includes('status')) setActiveTab('status')
    if (lower.includes('research') || lower.includes('analyze')) setActiveTab('research')
    if (lower.includes('car') || lower.includes('engine') || lower.includes('search')) void searchObject(command)
    if (lower.includes('zoom in') || lower.includes('zoom-in') || lower.includes('pass aao')) {
      setZoomLevel((value) => Math.min(100, value * 1.5))
    }
    if (lower.includes('zoom out') || lower.includes('zoom-out') || lower.includes('dur jao')) {
      setZoomLevel((value) => Math.max(1, value / 1.5))
    }
    if (lower.includes('dismantle') || lower.includes('explode') || lower.includes('alag karna') || lower.includes('dismant')) {
      setExplodeFactor(1.2)
      speak("Dismantling components to exploded view.")
    }
    if (lower.includes('assemble') || lower.includes('jodna') || lower.includes('jode')) {
      setExplodeFactor(0.0)
      speak("Assembling components back to default view.")
    }
    if (lower.includes('remove cover') || lower.includes('hide cover') || lower.includes('cover hata') || lower.includes('hide block')) {
      setShellMode('hidden')
      speak("Outer covers removed. Internal components are now visible.")
    }
    if (lower.includes('glass cover') || lower.includes('transparent cover') || lower.includes('glass mode') || lower.includes('glass block')) {
      setShellMode('transparent')
      speak("Outer covers set to transparent glass.")
    }
    if (lower.includes('show cover') || lower.includes('solid cover') || lower.includes('cover dikha')) {
      setShellMode('solid')
      speak("Outer covers restored to solid.")
    }
    if (lower.includes('hide label') || lower.includes('remove label') || lower.includes('label hata')) {
      setShowLabels(false)
      speak("Viewport labels hidden.")
    }
    if (lower.includes('show label') || lower.includes('label dikha')) {
      setShowLabels(true)
      speak("Viewport labels restored.")
    }
    if (lower.includes('reset')) {
      setZoomLevel(1)
      setExplodeFactor(0)
      setShellMode('solid')
      setShowLabels(true)
    }

    setAriaState('thinking')
    setAriaReply(`Processing command: ${command}`)

    try {
      const context = selectedComponent
        ? `\n\nSelected object: ${activeObject?.name || 'unknown'}\nSelected component: ${selectedComponent.name}\nFunction: ${selectedComponent.function}\nMaterial: ${selectedComponent.material || 'unknown'}\nRisk if removed: ${selectedComponent.riskIfRemoved || 'unknown'}`
        : ''
      const params = new URLSearchParams({ message: `${command}${context}` })
      const response = await fetch(`http://localhost:8000/api/agents/process?${params.toString()}`, { method: 'POST' })
      const data = await response.json()
      const reply = data?.result?.unified_response || data?.result?.message || `Command accepted: ${command}`
      speak(String(reply).slice(0, 260))
    } catch {
      speak(`ARIA local mode: ${command}. I updated the lab view and kept the command in session memory.`)
    }
  }, [activeObject?.name, query, searchObject, selectedComponent, speak])

  const toggleVoice = useCallback(() => {
    if (!SpeechRecognitionCtor) return

    if (ariaState === 'listening') {
      recognitionRef.current?.stop()
      setAriaState('idle')
      return
    }

    const recognition = new SpeechRecognitionCtor()
    recognition.lang = 'en-IN'
    recognition.continuous = false
    recognition.interimResults = false
    recognition.onresult = (event) => {
      const transcript = event.results[event.results.length - 1][0].transcript
      setQuery(transcript)
      void executeCommand(transcript)
    }
    recognition.onend = () => setAriaState((state) => state === 'listening' ? 'idle' : state)
    recognition.onerror = () => {
      setAriaState('idle')
      setAriaReply('Voice recognition could not hear a clear command. Try again.')
    }
    recognitionRef.current = recognition
    setAriaState('listening')
    recognition.start()
  }, [SpeechRecognitionCtor, ariaState, executeCommand])

  const processHands = useCallback((results: Results) => {
    const hand = results.multiHandLandmarks?.[0]
    if (!hand) {
      setGesture('ready')
      return
    }

    const thumb = hand[4]
    const index = hand[8]
    const wrist = hand[0]
    const middle = hand[12]
    const ring = hand[16]
    const pinky = hand[20]
    const pinch = Math.hypot(thumb.x - index.x, thumb.y - index.y)
    const lastPinch = lastPinchRef.current
    const lastX = lastXRef.current

    if (lastPinch !== null) {
      if (pinch < lastPinch - 0.035) {
        setGesture('zoom-in')
        setZoomLevel((value) => Math.min(100, value * 1.05))
      } else if (pinch > lastPinch + 0.035) {
        setGesture('zoom-out')
        setZoomLevel((value) => Math.max(1, value / 1.05))
      }
    }

    const extended = [index, middle, ring, pinky].filter((tip) => tip.y < wrist.y - 0.08).length
    if (extended <= 1) {
      setGesture('fist')
      setZoomLevel(1)
      setExplodeFactor(0)
      setShellMode('solid')
      setShowLabels(true)
    } else if (extended === 1) {
      setGesture('point')
    }

    if (lastX !== null) {
      const deltaX = wrist.x - lastX
      if (deltaX > 0.12) {
        setGesture('swipe-right')
        setActiveTab('results')
      } else if (deltaX < -0.12) {
        setGesture('swipe-left')
        setActiveTab('pipeline')
      }
    }

    lastPinchRef.current = pinch
    lastXRef.current = wrist.x
  }, [])

  const toggleCamera = useCallback(async () => {
    if (cameraEnabled) {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      handsRef.current?.close()
      handsRef.current = null
      setCameraEnabled(false)
      setGesture('offline')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }

      const HandsCtor = await loadMediaPipeHands()
      const hands = new HandsCtor({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
      })
      hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.65,
        minTrackingConfidence: 0.65
      })
      hands.onResults(processHands)
      handsRef.current = hands
      setCameraEnabled(true)
      setGesture('ready')

      const loop = async () => {
        if (!handsRef.current || !videoRef.current || videoRef.current.readyState < 2) return
        await handsRef.current.send({ image: videoRef.current })
        if (handsRef.current) requestAnimationFrame(loop)
      }
      requestAnimationFrame(loop)
    } catch {
      setGesture('offline')
      setAriaReply('Camera permission failed. Allow webcam access to use hand commands.')
    }
  }, [cameraEnabled, processHands])

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      void handsRef.current?.close()
      recognitionRef.current?.stop()
    }
  }, [])

  const screen = {
    status: <StatusScreen />,
    batch: <BatchScreen />,
    pipeline: <PipelineScreen />,
    research: (
      <ResearchScreen
        query={query}
        setQuery={setQuery}
        onExecute={() => void executeCommand()}
        ariaState={ariaState}
        voiceSupported={voiceSupported}
        onToggleVoice={toggleVoice}
        cameraEnabled={cameraEnabled}
        onToggleCamera={() => void toggleCamera()}
        videoRef={videoRef}
        gesture={gesture}
        zoomLevel={zoomLevel}
        setZoomLevel={setZoomLevel}
        activeObject={activeObject}
        selectedComponent={selectedComponent}
        onObjectSearch={() => void searchObject()}
        onSelectComponent={selectComponent}
        explodeFactor={explodeFactor}
        setExplodeFactor={setExplodeFactor}
        shellMode={shellMode}
        setShellMode={setShellMode}
        showLabels={showLabels}
        setShowLabels={setShowLabels}
      />
    ),
    results: <ResultsScreen />
  }[activeTab]

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span>⚚</span><b>EUREKA</b></div>
        <button className="settings-button" title="Settings">⚙</button>
      </header>
      <div className="content-shell">
        {screen}
        <aside className="aria-panel">
          <div className="section-title">ARIA Agent <span>{ariaState}</span></div>
          <p>{ariaReply}</p>
          <div className="aria-chips">
            <button onClick={() => void searchObject('car engine')}>Load Engine</button>
            <button onClick={() => void executeCommand('ARIA explain selected component')}>Explain Part</button>
            <button onClick={() => void executeCommand('zoom in')}>Zoom In</button>
          </div>
        </aside>
      </div>
      <nav className="bottom-nav">
        {tabs.map((tab) => (
          <button className={activeTab === tab.id ? 'active' : ''} key={tab.id} onClick={() => setActiveTab(tab.id)}>
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  )
}

export default App
