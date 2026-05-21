import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Sphere, MeshDistortMaterial, Html } from '@react-three/drei'
import type { Hands as MediaPipeHands, Results } from '@mediapipe/hands'
import type { Group } from 'three'
import './App.css'

type Tab = 'status' | 'batch' | 'pipeline' | 'research' | 'results'
type AriaState = 'idle' | 'listening' | 'thinking' | 'speaking'
type GestureState = 'offline' | 'ready' | 'zoom-in' | 'zoom-out' | 'point' | 'fist' | 'swipe-left' | 'swipe-right'

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

function LabScene({ zoomLevel, gesture }: { zoomLevel: number; gesture: GestureState }) {
  const group = useRef<Group>(null)

  useFrame(({ clock, camera }) => {
    const t = clock.getElapsedTime()
    camera.position.z = 6 - zoomLevel * 0.75
    camera.position.y = 1.4 - zoomLevel * 0.12
    if (group.current) {
      group.current.rotation.y = t * 0.22 + (gesture === 'swipe-left' ? -0.35 : gesture === 'swipe-right' ? 0.35 : 0)
      group.current.rotation.x = Math.sin(t * 0.4) * 0.08
    }
  })

  return (
    <>
      <ambientLight intensity={0.65} />
      <directionalLight position={[4, 6, 4]} intensity={1.4} />
      <pointLight position={[-3, 2, 3]} intensity={1.8} color="#00e5f0" />
      <group ref={group}>
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[1.25, 1.25, 1.25]} />
          <meshStandardMaterial color="#d68f8d" emissive="#2b090b" roughness={0.32} metalness={0.25} />
        </mesh>
        <Sphere args={[0.44, 48, 48]} position={[-1.25, -0.28, 0]}>
          <MeshDistortMaterial color="#b9dfe6" emissive="#0b4b51" distort={0.09} speed={1.1} roughness={0.2} />
        </Sphere>
        <Sphere args={[0.44, 48, 48]} position={[1.25, -0.28, 0]}>
          <MeshDistortMaterial color="#b9dfe6" emissive="#0b4b51" distort={0.09} speed={1.1} roughness={0.2} />
        </Sphere>
        <mesh position={[-0.72, -0.15, 0]} rotation={[0, 0, -0.64]}>
          <cylinderGeometry args={[0.035, 0.035, 1.2, 16]} />
          <meshStandardMaterial color="#86d7de" emissive="#0c5960" />
        </mesh>
        <mesh position={[0.72, -0.15, 0]} rotation={[0, 0, 0.64]}>
          <cylinderGeometry args={[0.035, 0.035, 1.2, 16]} />
          <meshStandardMaterial color="#86d7de" emissive="#0c5960" />
        </mesh>
        <Html position={[0, 0.1, 0.66]} center>
          <span className="atom-label">O</span>
        </Html>
        <Html position={[-1.25, -0.28, 0.48]} center>
          <span className="atom-label atom-label-small">H</span>
        </Html>
        <Html position={[1.25, -0.28, 0.48]} center>
          <span className="atom-label atom-label-small">H</span>
        </Html>
      </group>
      <OrbitControls enableDamping dampingFactor={0.08} />
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
  zoomLevel
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
}) {
  return (
    <main className="research-screen">
      <section className="query-card">
        <textarea value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Enter research query or say: ARIA, analyze water molecules" />
        <div className="command-row">
          <button className={`icon-button ${ariaState === 'listening' ? 'active' : ''}`} onClick={onToggleVoice} disabled={!voiceSupported} title="Voice command">⌕</button>
          <button className={`icon-button ${cameraEnabled ? 'active' : ''}`} onClick={onToggleCamera} title="Camera gesture control">◉</button>
          <button className="primary-button execute" onClick={onExecute}>Execute ▷</button>
        </div>
      </section>

      <section className="core-card">
        <div className="core-title"><span>▣</span> EUREKA CORE</div>
        <ul className="core-steps">
          <li>✓ Accessing PubChem database... [OK]</li>
          <li>✓ Retrieving H2O structural data... [OK]</li>
          <li>⌛ Running molecular orbital calculations...</li>
        </ul>
        <div className="scene-shell">
          <Canvas>
            <LabScene zoomLevel={zoomLevel} gesture={gesture} />
          </Canvas>
        </div>
      </section>

      <section className="control-card">
        <div className="section-title">Input Systems <span>{ariaState.toUpperCase()}</span></div>
        <div className="control-grid">
          <div><small>Voice Agent</small><b>{voiceSupported ? ariaState : 'unsupported'}</b></div>
          <div><small>Camera</small><b>{cameraEnabled ? 'tracking' : 'offline'}</b></div>
          <div><small>Gesture</small><b>{gesture}</b></div>
          <div><small>Zoom Level</small><b>{zoomLevel.toFixed(1)}x</b></div>
        </div>
        <video ref={videoRef} className={cameraEnabled ? 'camera-preview active' : 'camera-preview'} muted playsInline />
        <p className="hint">Pinch to zoom, point to select, fist to reset, swipe to switch tabs. Voice supports English and Hindi commands.</p>
      </section>
    </main>
  )
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('research')
  const [query, setQuery] = useState('Analyze water molecules.')
  const [ariaState, setAriaState] = useState<AriaState>('idle')
  const [ariaReply, setAriaReply] = useState('ARIA online. Voice and gesture systems are ready for calibration.')
  const [cameraEnabled, setCameraEnabled] = useState(false)
  const [gesture, setGesture] = useState<GestureState>('offline')
  const [zoomLevel, setZoomLevel] = useState(1)
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

  const executeCommand = useCallback(async (rawCommand?: string) => {
    const command = (rawCommand || query).trim()
    if (!command) return

    const lower = command.toLowerCase()
    if (lower.includes('batch')) setActiveTab('batch')
    if (lower.includes('pipeline')) setActiveTab('pipeline')
    if (lower.includes('result')) setActiveTab('results')
    if (lower.includes('status')) setActiveTab('status')
    if (lower.includes('research') || lower.includes('analyze')) setActiveTab('research')
    if (lower.includes('zoom in')) setZoomLevel((value) => Math.min(4, value + 0.5))
    if (lower.includes('zoom out')) setZoomLevel((value) => Math.max(0, value - 0.5))
    if (lower.includes('reset')) setZoomLevel(1)

    setAriaState('thinking')
    setAriaReply(`Processing command: ${command}`)

    try {
      const params = new URLSearchParams({ message: command })
      const response = await fetch(`http://localhost:8000/api/agents/process?${params.toString()}`, { method: 'POST' })
      const data = await response.json()
      const reply = data?.result?.unified_response || data?.result?.message || `Command accepted: ${command}`
      speak(String(reply).slice(0, 260))
    } catch {
      speak(`ARIA local mode: ${command}. I updated the lab view and kept the command in session memory.`)
    }
  }, [query, speak])

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
        setZoomLevel((value) => Math.min(4, value + 0.08))
      } else if (pinch > lastPinch + 0.035) {
        setGesture('zoom-out')
        setZoomLevel((value) => Math.max(0, value - 0.08))
      }
    }

    const extended = [index, middle, ring, pinky].filter((tip) => tip.y < wrist.y - 0.08).length
    if (extended <= 1) {
      setGesture('fist')
      setZoomLevel(1)
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
            <button onClick={() => void executeCommand('ARIA analyze water molecules')}>Analyze H2O</button>
            <button onClick={() => void executeCommand('zoom in')}>Zoom In</button>
            <button onClick={() => void executeCommand('show results')}>Results</button>
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
