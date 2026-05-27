import React, { Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import * as THREE from 'three'
import type { AriaState, GestureState, ObjectComponent, ExplorableObject } from '../../types'
import { LabScene } from '../canvas/LabScene'

interface ResearchScreenProps {
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
  isAnimating: boolean
  setIsAnimating: (value: boolean) => void
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
  setShowLabels,
  isAnimating,
  setIsAnimating
}: ResearchScreenProps) {
  return (
    <main className="research-screen">
      <section className="query-card">
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Enter research query or say: ARIA, analyze water molecules"
        />
        <div className="command-row">
          <button
            className={`icon-button ${ariaState === 'listening' ? 'active' : ''}`}
            onClick={onToggleVoice}
            disabled={!voiceSupported}
            title="Voice command"
          >
            ⌕
          </button>
          <button
            className={`icon-button ${cameraEnabled ? 'active' : ''}`}
            onClick={onToggleCamera}
            title="Camera gesture control"
          >
            ◉
          </button>
          <button className="ghost-button" onClick={onObjectSearch}>
            Search Object
          </button>
          <button className="primary-button execute" onClick={onExecute}>
            Execute ▷
          </button>
        </div>
      </section>

      <section className="core-card">
        <div className="core-title">
          <span>▣</span> {activeObject ? activeObject.name : 'EUREKA CORE'}
        </div>
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
          <Canvas
            shadows
            dpr={[1, 2]}
            camera={{ position: [4, 3, 6], fov: 45, near: 0.01, far: 100 }}
            gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.1 }}
          >
            <Suspense fallback={<Html center>Loading 3D...</Html>}>
              <LabScene
                zoomLevel={zoomLevel}
                gesture={gesture}
                activeObject={activeObject}
                selectedComponent={selectedComponent}
                onSelectComponent={onSelectComponent}
                explodeFactor={explodeFactor}
                shellMode={shellMode}
                showLabels={showLabels}
                isAnimating={isAnimating}
              />
            </Suspense>
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
              <label>Animation</label>
              <button
                className={`toggle-switch ${isAnimating ? 'active' : ''}`}
                onClick={() => setIsAnimating(!isAnimating)}
              >
                {isAnimating ? 'ON' : 'OFF'}
              </button>
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
          <div className="section-title">
            Component Graph <span>{activeObject.defaultView}</span>
          </div>
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
        <div className="section-title">
          Input Systems <span>{ariaState.toUpperCase()}</span>
        </div>
        <div className="control-grid">
          <div>
            <small>Voice Agent</small>
            <b>{voiceSupported ? ariaState : 'unsupported'}</b>
          </div>
          <div>
            <small>Camera</small>
            <b>{cameraEnabled ? 'tracking' : 'offline'}</b>
          </div>
          <div>
            <small>Gesture</small>
            <b>{gesture}</b>
          </div>
          <div>
            <small>Zoom Level</small>
            <b>{zoomLevel.toFixed(0)}x</b>
          </div>
        </div>
        <video
          ref={videoRef}
          className={cameraEnabled ? 'camera-preview active' : 'camera-preview'}
          muted
          playsInline
        />
        <p className="hint">
          Pinch to zoom, point to select, fist to reset, swipe to switch tabs. Voice supports English and Hindi commands.
        </p>
      </section>
    </main>
  )
}

export default ResearchScreen
