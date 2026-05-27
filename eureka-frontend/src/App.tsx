import { useCallback, useState, useRef } from 'react'
import type { Tab, ObjectComponent, ExplorableObject } from './types'
import { searchObjectFromAPI, fetchWikipediaSummary, processAgentCommand } from './services/api'
import { useVoiceControl } from './hooks/useVoiceControl'
import { useHandTracking } from './hooks/useHandTracking'
import { generateFallbackObject } from './data/fallbackObjects'
import { TopBar, BottomNav, AriaPanel } from './components/layout'
import { StatusScreen, BatchScreen, PipelineScreen, ResearchScreen, ResultsScreen } from './components/dashboard'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('research')
  const [query, setQuery] = useState('car engine')
  const [activeObject, setActiveObject] = useState<ExplorableObject | null>(null)
  const [selectedComponent, setSelectedComponent] = useState<ObjectComponent | null>(null)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [explodeFactor, setExplodeFactor] = useState(0.0)
  const [shellMode, setShellMode] = useState<'solid' | 'transparent' | 'hidden'>('solid')
  const [showLabels, setShowLabels] = useState(true)
  const [isAnimating, setIsAnimating] = useState(true)

  // Ref to hold the command executor to break circular dependencies
  const executeCommandRef = useRef<((rawCommand?: string) => Promise<void>) | null>(null)

  // Voice control hook
  const { voiceSupported, ariaState, ariaReply, speak, toggleVoice, setAriaState, setAriaReply } = useVoiceControl(
    useCallback((transcript) => {
      setQuery(transcript)
      void executeCommandRef.current?.(transcript)
    }, [])
  )

  // Hand tracking hook
  const { cameraEnabled, gesture, videoRef, toggleCamera } = useHandTracking({
    onZoomIn: useCallback(() => setZoomLevel((value) => Math.min(100, value * 1.05)), []),
    onZoomOut: useCallback(() => setZoomLevel((value) => Math.max(1, value / 1.05)), []),
    onReset: useCallback(() => {
      setZoomLevel(1)
      setExplodeFactor(0)
      setShellMode('solid')
      setShowLabels(true)
    }, []),
    onSwipeLeft: useCallback(() => setActiveTab('pipeline'), []),
    onSwipeRight: useCallback(() => setActiveTab('results'), []),
    onError: useCallback((msg) => setAriaReply(msg), [setAriaReply])
  })

  // Object search logic
  const searchObject = useCallback(async (rawQuery?: string) => {
    const searchText = (rawQuery || query).trim() || 'car engine'
    setAriaState('thinking')
    setAriaReply(`Searching object library for ${searchText}...`)

    try {
      const objectData = await searchObjectFromAPI(searchText)
      setActiveObject(objectData)
      setSelectedComponent(objectData.components?.[0] || null)
      setActiveTab('research')
      speak(`Loaded ${objectData.name}. Select a component or ask ARIA what it does.`)
    } catch {
      try {
        const wiki = await fetchWikipediaSummary(searchText)
        const fallback = generateFallbackObject(searchText, wiki.title, wiki.description)
        setActiveObject(fallback)
        setSelectedComponent(fallback.components[0])
        setActiveTab('research')
        speak(`Loaded offline model for ${wiki.title}. Reconnect backend for full AI-generated details.`)
      } catch {
        speak("Failed to load object model.")
        setAriaState('idle')
      }
    }
  }, [query, speak, setAriaState, setAriaReply])

  // Command execution logic
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
      const reply = await processAgentCommand(`${command}${context}`)
      speak(reply)
    } catch {
      speak(`ARIA local mode: ${command}. I updated the lab view and kept the command in session memory.`)
    }
  }, [activeObject, query, searchObject, selectedComponent, speak, setAriaState, setAriaReply])

  // Sync ref with the latest callback
  executeCommandRef.current = executeCommand

  return (
    <div className="app-shell">
      <TopBar />
      <div className="content-shell">
        {{
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
              onSelectComponent={useCallback((component) => {
                setSelectedComponent(component)
                speak(`${component.name} selected. ${component.function}`)
              }, [speak])}
              explodeFactor={explodeFactor}
              setExplodeFactor={setExplodeFactor}
              shellMode={shellMode}
              setShellMode={setShellMode}
              showLabels={showLabels}
              setShowLabels={setShowLabels}
              isAnimating={isAnimating}
              setIsAnimating={setIsAnimating}
            />
          ),
          results: <ResultsScreen query={query} activeObject={activeObject} />
        }[activeTab]}
        <AriaPanel
          ariaState={ariaState}
          ariaReply={ariaReply}
          onLoadEngine={() => void searchObject('car engine')}
          onExplainPart={() => void executeCommand('ARIA explain selected component')}
          onZoomIn={() => void executeCommand('zoom in')}
        />
      </div>
      <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  )
}

export default App
