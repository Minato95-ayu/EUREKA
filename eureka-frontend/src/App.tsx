/* eslint-disable no-useless-assignment, @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useMemo, useRef, useState, Suspense } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Sphere, Html, Edges, Environment, ContactShadows, useGLTF, RoundedBox } from '@react-three/drei'
import { EffectComposer, Bloom, N8AO, Vignette, ToneMapping } from '@react-three/postprocessing'
import { ToneMappingMode } from 'postprocessing'
import { Geometry, Base, Subtraction } from '@react-three/csg'
import type { Hands as MediaPipeHands, Results } from '@mediapipe/hands'
import type { Group } from 'three'
import * as THREE from 'three'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || ''

type Tab = 'status' | 'batch' | 'pipeline' | 'research' | 'results'
type AriaState = 'idle' | 'listening' | 'thinking' | 'speaking'
type GestureState = 'offline' | 'ready' | 'zoom-in' | 'zoom-out' | 'point' | 'fist' | 'swipe-left' | 'swipe-right'
type ScaleLevel = 'object' | 'component' | 'subcomponent' | 'material' | 'molecule' | 'atom'

type ObjectGeometry = {
  type: 'box' | 'cylinder' | 'capsule' | 'fan' | 'gltf' | 'sphere' | 'cone' | 'torus' | 'hemisphere' | 'rounded_box' | 'lathe' | 'csg' | 'empty' | 'none'
  size?: [number, number, number]
  radius?: number
  depth?: number
  blades?: number
  rotation?: [number, number, number]
  url?: string
  tube?: number
  base?: ObjectGeometry & { position?: [number, number, number] }
  subtractions?: (ObjectGeometry & { position?: [number, number, number] })[]
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
  showLabels,
  isAnimating,
  selectedComponentId,
  allComponents
}: {
  component: ObjectComponent
  selected: boolean
  onSelect: (component: ObjectComponent) => void
  explodeFactor: number
  shellMode: 'solid' | 'transparent' | 'hidden'
  showLabels: boolean
  isAnimating: boolean
  selectedComponentId?: string
  allComponents?: ObjectComponent[]
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
    let clearcoat = 0.0
    let clearcoatRoughness = 0.1
    let usePhysical = false
    let ior = 1.5
    let transmission = 0.0
    let thickness = 0.0
    let envMapIntensity = 1.5

    if (shellMode === 'transparent' && isCover) {
      roughness = 0.0
      metalness = 0.0
      transparent = true
      opacity = 0.12
      usePhysical = true
      transmission = 0.95
      ior = 1.52
      thickness = 0.5
      clearcoat = 1.0
      clearcoatRoughness = 0.0
      envMapIntensity = 2.5
    } else {
      if (matName.includes('iron') || matName.includes('cast')) {
        roughness = 0.55
        metalness = 0.85
        clearcoat = 0.15
        envMapIntensity = 1.2
      } else if (matName.includes('steel') || matName.includes('chrome') || matName.includes('metal') || matName.includes('forged')) {
        roughness = 0.08
        metalness = 0.98
        usePhysical = true
        clearcoat = 0.8
        clearcoatRoughness = 0.05
        envMapIntensity = 2.0
      } else if (matName.includes('aluminum') || matName.includes('alloy')) {
        roughness = 0.2
        metalness = 0.92
        usePhysical = true
        clearcoat = 0.4
        clearcoatRoughness = 0.1
        envMapIntensity = 1.8
      } else if (matName.includes('copper') || matName.includes('brass') || matName.includes('bronze')) {
        roughness = 0.15
        metalness = 0.95
        usePhysical = true
        clearcoat = 0.6
        clearcoatRoughness = 0.08
        envMapIntensity = 1.6
      } else if (matName.includes('carbon') || matName.includes('fiber')) {
        roughness = 0.35
        metalness = 0.05
        usePhysical = true
        clearcoat = 1.0
        clearcoatRoughness = 0.03
        envMapIntensity = 1.0
      } else if (matName.includes('glass') || matName.includes('lens') || matName.includes('optical')) {
        roughness = 0.0
        metalness = 0.0
        transparent = true
        opacity = 0.25
        usePhysical = true
        transmission = 0.9
        ior = 1.52
        thickness = 0.3
        clearcoat = 1.0
        clearcoatRoughness = 0.0
        envMapIntensity = 2.5
      } else if (matName.includes('rubber') || matName.includes('belt') || matName.includes('gasket')) {
        roughness = 0.85
        metalness = 0.0
        envMapIntensity = 0.4
      } else if (matName.includes('polymer') || matName.includes('plastic') || matName.includes('composite')) {
        roughness = 0.45
        metalness = 0.05
        clearcoat = 0.3
        envMapIntensity = 0.8
      } else {
        // Default: generic metallic surface
        roughness = 0.35
        metalness = 0.6
        clearcoat = 0.2
        envMapIntensity = 1.3
      }
    }

    return { roughness, metalness, transparent, opacity, clearcoat, clearcoatRoughness, usePhysical, ior, transmission, thickness, envMapIntensity }
  }, [component.material, shellMode, isCover])

  const material = materialProps.usePhysical ? (
    <meshPhysicalMaterial
      color={component.color}
      emissive={selected ? '#00ffff' : '#050a0c'}
      emissiveIntensity={selected ? 0.8 : 0.15}
      roughness={materialProps.roughness}
      metalness={materialProps.metalness}
      transparent={materialProps.transparent}
      opacity={materialProps.opacity}
      clearcoat={materialProps.clearcoat}
      clearcoatRoughness={materialProps.clearcoatRoughness}
      ior={materialProps.ior}
      transmission={materialProps.transmission}
      thickness={materialProps.thickness}
      envMapIntensity={materialProps.envMapIntensity}
    />
  ) : (
    <meshStandardMaterial
      color={component.color}
      emissive={selected ? '#00ffff' : '#050a0c'}
      emissiveIntensity={selected ? 0.7 : 0.1}
      roughness={materialProps.roughness}
      metalness={materialProps.metalness}
      transparent={materialProps.transparent}
      opacity={materialProps.opacity}
      envMapIntensity={materialProps.envMapIntensity}
    />
  )

  const handlePointerDown = (event: any) => {
    event.stopPropagation()
    
    // Check if we clicked a submesh of a compiled GLTF model
    if (geometry.type === 'gltf' && event.intersection?.object?.name && allComponents) {
      const meshName = event.intersection.object.name
      const matchedComp = allComponents.find(comp => 
        meshName === comp.id || 
        meshName.startsWith(`${comp.id}_`) || 
        meshName.startsWith(`${comp.id}.`) ||
        meshName.includes(`_${comp.id}_`)
      )
      if (matchedComp) {
        onSelect(matchedComp)
        return
      }
    }
    
    onSelect(component)
  }

  const edgeColor = selected ? '#00ffff' : '#2b6cb0'

  const groupRef = useRef<THREE.Group>(null)
  const timeRef = useRef(0)

  useFrame((_, delta) => {
    if (!groupRef.current) return
    if (isAnimating) {
      timeRef.current += delta
    }
    const t = timeRef.current
    const name = component.name.toLowerCase()
    const id = component.id.toLowerCase()
    
    // Animation speeds and offsets
    const rpm = 25
    
    if (name.includes('piston') || id.includes('piston')) {
      const numMatch = name.match(/\d+/) || id.match(/\d+/)
      const offset = numMatch ? parseInt(numMatch[0]) * Math.PI / 2 : 0
      groupRef.current.position.y = displacedPos[1] + Math.sin(t * rpm + offset) * 0.12
    }
    
    if (name.includes('crankshaft') || id.includes('crankshaft') || name.includes('camshaft')) {
      groupRef.current.rotation.z = rotation[2] + t * rpm
    }
    
    if (geometry.type === 'fan' || name.includes('fan') || name.includes('pulley') || name.includes('alternator') || name.includes('flywheel')) {
      groupRef.current.rotation.z = rotation[2] + t * rpm
    }
  })

  if (shellMode === 'hidden' && isCover) {
    return null
  }

  if (geometry.type === 'empty' || geometry.type === 'none') {
    return showLabels ? (
      <group position={displacedPos} onPointerDown={handlePointerDown}>
        <Html position={[0, 0, 0]} center>
          <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
        </Html>
      </group>
    ) : null
  }

  // Helper to get pure primitive geometry for CSG
  const getRawGeometry = (geom: ObjectGeometry) => {
    if (geom.type === 'box') return <boxGeometry args={geom.size || [1, 1, 1]} />
    if (geom.type === 'cylinder' || geom.type === 'capsule') return <cylinderGeometry args={[geom.radius || 0.2, geom.radius || 0.2, geom.depth || 0.6, 32]} />
    if (geom.type === 'sphere') return <sphereGeometry args={[geom.radius || 0.3, 64, 64]} />
    if (geom.type === 'cone') return <coneGeometry args={[geom.radius || 0.3, geom.depth || 0.6, 32]} />
    if (geom.type === 'torus') return <torusGeometry args={[geom.radius || 0.4, geom.tube || 0.08, 24, 48]} />
    if (geom.type === 'hemisphere') return <sphereGeometry args={[geom.radius || 0.3, 64, 64, 0, Math.PI * 2, 0, Math.PI / 2]} />
    if (geom.type === 'lathe') {
      const r = geom.radius || 0.4
      const h = geom.depth || 0.3
      const pts = [[0,-h/2], [r*0.7,-h/2], [r,-h/4], [r,h/4], [r*0.7,h/2], [0,h/2]].map(([x,y]) => new THREE.Vector2(x,y))
      return <latheGeometry args={[pts, 48]} />
    }
    return <boxGeometry args={geom.size || [1, 1, 1]} />
  }

  let innerContent = null;

  if (geometry.type === 'csg') {
    innerContent = (
      <mesh castShadow receiveShadow>
        <Geometry>
          <Base position={geometry.base?.position || [0,0,0]} rotation={geometry.base?.rotation || [0,0,0]}>
            {getRawGeometry(geometry.base || { type: 'box' })}
          </Base>
          {geometry.subtractions?.map((sub, idx) => (
            <Subtraction key={idx} position={sub.position || [0,0,0]} rotation={sub.rotation || [0,0,0]}>
              {getRawGeometry(sub)}
            </Subtraction>
          ))}
        </Geometry>
        {material}
        <Edges color={edgeColor} />
        {showLabels && (
          <Html position={[0, (geometry.base?.size?.[1] || geometry.base?.depth || 0.6) / 2 + 0.15, 0]} center>
            <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
          </Html>
        )}
      </mesh>
    )
  } else if (geometry.type === 'fan') {
    const blades = geometry.blades || 6
    const radius = geometry.radius || 0.42
    innerContent = (
      <>
        <mesh castShadow receiveShadow>
          <torusGeometry args={[radius, 0.025, 10, 48]} />
          {material}
          <Edges color={edgeColor} />
        </mesh>
        {Array.from({ length: blades }).map((_, index) => (
          <mesh key={index} rotation={[0, 0, (Math.PI * 2 * index) / blades]} position={[0, 0, 0.02]} castShadow receiveShadow>
            <boxGeometry args={[radius * 0.9, 0.055, 0.035]} />
            {material}
            <Edges color={edgeColor} />
          </mesh>
        ))}
        {showLabels && (
          <Html position={[0, -0.62, 0]} center>
            <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
          </Html>
        )}
      </>
    )
  } else if (geometry.type === 'gltf' && geometry.url) {
    innerContent = (
      <>
        <GltfModelWrapper 
          url={geometry.url} 
          materialProps={materialProps} 
          selected={selected} 
          selectedComponentId={selectedComponentId} 
        />
        {showLabels && (
          <Html position={[0, 0.5, 0]} center>
            <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
          </Html>
        )}
      </>
    )
  } else if (geometry.type === 'sphere') {
    innerContent = (
      <mesh castShadow receiveShadow>
        <sphereGeometry args={[geometry.radius || 0.3, 64, 64]} />
        {material}
        <Edges color={edgeColor} />
        {showLabels && (
          <Html position={[0, (geometry.radius || 0.3) + 0.15, 0]} center>
            <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
          </Html>
        )}
      </mesh>
    )
  } else if (geometry.type === 'cone') {
    innerContent = (
      <mesh castShadow receiveShadow>
        <coneGeometry args={[geometry.radius || 0.3, geometry.depth || 0.6, 32]} />
        {material}
        <Edges color={edgeColor} />
        {showLabels && (
          <Html position={[0, (geometry.depth || 0.6) / 2 + 0.15, 0]} center>
            <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
          </Html>
        )}
      </mesh>
    )
  } else if (geometry.type === 'torus') {
    innerContent = (
      <mesh castShadow receiveShadow>
        <torusGeometry args={[geometry.radius || 0.4, geometry.tube || 0.08, 24, 48]} />
        {material}
        <Edges color={edgeColor} />
        {showLabels && (
          <Html position={[0, (geometry.radius || 0.4) + 0.2, 0]} center>
            <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
          </Html>
        )}
      </mesh>
    )
  } else if (geometry.type === 'hemisphere') {
    innerContent = (
      <mesh castShadow receiveShadow>
        <sphereGeometry args={[geometry.radius || 0.3, 64, 64, 0, Math.PI * 2, 0, Math.PI / 2]} />
        {material}
        {showLabels && (
          <Html position={[0, (geometry.radius || 0.3) + 0.1, 0]} center>
            <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
          </Html>
        )}
      </mesh>
    )
  } else if (geometry.type === 'rounded_box') {
    const rbSize = geometry.size || [1, 1, 1]
    innerContent = (
      <mesh castShadow receiveShadow>
        <RoundedBox args={rbSize as [number, number, number]} radius={geometry.radius || 0.05} smoothness={4}>
          {material}
        </RoundedBox>
        {showLabels && (
          <Html position={[0, (rbSize[1] || 1) / 2 + 0.2, 0]} center>
            <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
          </Html>
        )}
      </mesh>
    )
  } else if (geometry.type === 'lathe') {
    const segments = 48
    const r = geometry.radius || 0.4
    const h = geometry.depth || 0.3
    const points: [number, number][] = [
      [0, -h/2], [r * 0.7, -h/2], [r, -h/4], [r, h/4], [r * 0.7, h/2], [0, h/2]
    ]
    innerContent = (
      <mesh castShadow receiveShadow>
        <latheGeometry args={[points.map(([x,y]) => new THREE.Vector2(x,y)), segments]} />
        {material}
        {showLabels && (
          <Html position={[0, h / 2 + 0.15, 0]} center>
            <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
          </Html>
        )}
      </mesh>
    )
  } else {
    innerContent = (
      <mesh castShadow receiveShadow>
        {geometry.type === 'box' && <boxGeometry args={geometry.size || [1, 1, 1]} />}
        {(geometry.type === 'cylinder' || geometry.type === 'capsule') && (
          <cylinderGeometry args={[geometry.radius || 0.2, geometry.radius || 0.2, geometry.depth || 0.6, 32]} />
        )}
        {material}
        <Edges color={edgeColor} />
        {showLabels && (
          <Html position={[0, geometry.type === 'box' ? (geometry.size?.[1] ? geometry.size[1]/2 + 0.32 : 0.82) : (geometry.depth ? geometry.depth/2 + 0.18 : 0.48), 0]} center>
            <span className={selected ? 'component-label selected' : 'component-label'}>{component.name}</span>
          </Html>
        )}
      </mesh>
    )
  }

  return (
    <group ref={groupRef} position={displacedPos} rotation={rotation} onPointerDown={handlePointerDown}>
      {innerContent}
    </group>
  )
}

function GltfModelWrapper({ 
  url, 
  materialProps, 
  selected, 
  selectedComponentId 
}: { 
  url: string, 
  materialProps: any, 
  selected: boolean,
  selectedComponentId?: string 
}) {
  const { scene } = useGLTF(url)
  const clonedScene = useMemo(() => {
    const clone = scene.clone()
    clone.traverse((child: any) => {
      if (child.isMesh) {
        child.castShadow = true
        child.receiveShadow = true
        if (child.material) {
          child.material = child.material.clone()
          child.material.transparent = materialProps.transparent
          child.material.opacity = materialProps.opacity
          
          if (materialProps.transparent) {
            child.material.roughness = materialProps.roughness
            child.material.metalness = materialProps.metalness
          }
          
          const meshName = child.name || ''
          const isThisMeshSelected = selected || (selectedComponentId && (
            meshName === selectedComponentId || 
            meshName.startsWith(`${selectedComponentId}_`) || 
            meshName.startsWith(`${selectedComponentId}.`) ||
            meshName.includes(`_${selectedComponentId}_`)
          ))
          
          if (isThisMeshSelected) {
            child.material.emissive.set('#00ffff')
            child.material.emissiveIntensity = 0.8
          } else {
            child.material.emissive.setHex(0x000000)
            child.material.emissiveIntensity = 0.0
          }
        }
      }
    })
    return clone
  }, [scene, materialProps, selected, selectedComponentId])
  return <primitive object={clonedScene} />
}

function LabScene({
  zoomLevel,
  gesture,
  activeObject,
  selectedComponent,
  onSelectComponent,
  explodeFactor,
  shellMode,
  showLabels,
  isAnimating
}: {
  zoomLevel: number
  gesture: GestureState
  activeObject: ExplorableObject | null
  selectedComponent: ObjectComponent | null
  onSelectComponent: (component: ObjectComponent) => void
  explodeFactor: number
  shellMode: 'solid' | 'transparent' | 'hidden'
  showLabels: boolean
  isAnimating: boolean
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
      {/* === PHOTOREALISTIC LIGHTING SETUP === */}
      {/* Subtle ambient fill so nothing is pure black */}
      <ambientLight intensity={0.08} />

      {/* Key light: warm directional from upper-right */}
      <directionalLight
        position={[6, 10, 5]}
        intensity={2.2}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-bias={-0.0001}
        color="#fff5e6"
      />

      {/* Fill light: cool blue from the left to create depth */}
      <directionalLight position={[-5, 4, -3]} intensity={0.6} color="#a0c4ff" />

      {/* Rim/accent light: cyan edge highlight from behind */}
      <pointLight position={[-3, 2, -5]} intensity={1.0} color="#00e5f0" distance={20} decay={2} />

      {/* Top spotlight for specular highlights on metal */}
      <spotLight
        position={[0, 12, 0]}
        intensity={1.5}
        angle={0.5}
        penumbra={1}
        castShadow
        shadow-bias={-0.0002}
        color="#ffffff"
      />

      {/* Bottom subtle bounce */}
      <pointLight position={[0, -3, 0]} intensity={0.3} color="#2d4a5e" distance={10} decay={2} />

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
              isAnimating={isAnimating}
              selectedComponentId={selectedComponent?.id}
              allComponents={activeObject.components}
            />
          ))
        ) : (
          <>
            <mesh position={[0, 0, 0]}>
              <boxGeometry args={[1.25, 1.25, 1.25]} />
              <meshPhysicalMaterial
                color="#556270"
                roughness={0.12}
                metalness={0.92}
                clearcoat={0.6}
                clearcoatRoughness={0.05}
                envMapIntensity={2.0}
              />
            </mesh>
            <Sphere args={[0.44, 64, 64]} position={[-1.25, -0.28, 0]}>
              <meshPhysicalMaterial
                color="#dfe6e9"
                roughness={0.05}
                metalness={0.95}
                clearcoat={1.0}
                clearcoatRoughness={0.02}
                envMapIntensity={2.5}
              />
            </Sphere>
            <Sphere args={[0.44, 64, 64]} position={[1.25, -0.28, 0]}>
              <meshPhysicalMaterial
                color="#2f3640"
                roughness={0.2}
                metalness={0.88}
                clearcoat={0.5}
                clearcoatRoughness={0.08}
                envMapIntensity={1.8}
              />
            </Sphere>
          </>
        )}
      </group>

      {/* === HDRI ENVIRONMENT for realistic reflections === */}
      <Environment preset="city" background backgroundBlurriness={0.8} />

      {/* === GROUND SHADOWS === */}
      <ContactShadows
        position={[0, -1.2, 0]}
        opacity={0.6}
        scale={12}
        blur={3}
        far={3}
        resolution={512}
        color="#0a1520"
      />

      {/* Subtle grid */}
      <gridHelper args={[20, 20, '#00e5f0', '#1a2a3a']} position={[0, -1.2, 0]} />

      {/* === POST-PROCESSING === */}
      <EffectComposer multisampling={4}>
        {/* Ambient Occlusion: dark crevices & corners like real life */}
        <N8AO
          aoRadius={0.8}
          intensity={2.5}
          distanceFalloff={0.5}
        />
        {/* Bloom: natural glow on bright metallic highlights */}
        <Bloom
          luminanceThreshold={0.7}
          luminanceSmoothing={0.3}
          intensity={0.4}
          mipmapBlur
        />
        {/* Vignette: subtle darkened edges like a real camera lens */}
        <Vignette offset={0.3} darkness={0.6} />
        {/* Tone Mapping: cinematic color grading */}
        <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
      </EffectComposer>

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
  setShowLabels,
  isAnimating,
  setIsAnimating
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
  isAnimating: boolean
  setIsAnimating: (value: boolean) => void
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
  const [isAnimating, setIsAnimating] = useState(true)
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
      const generateResponse = await fetch(`${API_BASE}/api/objects/generate?${params.toString()}`, {
        method: 'POST'
      })
      if (!generateResponse.ok) throw new Error('Generation failed')
      const objectData = await generateResponse.json()
      setActiveObject(objectData)
      setSelectedComponent(objectData.components?.[0] || null)
      setActiveTab('research')
      speak(`Loaded ${objectData.name}. Select a component or ask ARIA what it does.`)
    } catch {
      // Smart dynamic fallback: fetch Wikipedia info and build a unique procedural model
      let wikiTitle = searchText
      let wikiDesc = `A procedurally generated 3D model of ${searchText}.`

      try {
        const encoded = encodeURIComponent(searchText.replace(/ /g, '_'))
        const wikiRes = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${encoded}`)
        if (wikiRes.ok) {
          const wikiData = await wikiRes.json()
          wikiTitle = wikiData.title || searchText
          wikiDesc = wikiData.description || wikiData.extract?.slice(0, 160) || wikiDesc
        } else {
          const searchRes = await fetch(`https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(searchText)}&format=json&origin=*&utf8=`)
          if (searchRes.ok) {
            const searchData = await searchRes.json()
            const top = searchData?.query?.search?.[0]
            if (top?.title) { wikiTitle = top.title; wikiDesc = top.snippet?.replace(/<[^>]+>/g, '') || wikiDesc }
          }
        }
      } catch { /* Wikipedia fetch failed - use generic */ }

      const q = searchText.toLowerCase()
      const isJetEngine = (q.includes('airplane') || q.includes('aircraft') || q.includes('jet') || q.includes('turbine')) && q.includes('engine')
      const isCarEngine = q.includes('car') && q.includes('engine') && !isJetEngine
      const isMicroscope = q.includes('microscope')
      const isRocket = q.includes('rocket') || q.includes('missile')
      const isDrone = q.includes('drone') || q.includes('quadcopter')

      let rootColor = '#4a4e69', rootSize: [number,number,number] = [1.8, 0.8, 1.2]
      let p1N = 'Primary Module', p1C = '#c0c5ce', p1G: Record<string,unknown> = { type: 'cylinder', radius: 0.3, depth: 0.6 }, p1P: [number,number,number] = [0, 0.6, 0]
      let p2N = 'Secondary Module', p2C = '#b87333', p2G: Record<string,unknown> = { type: 'sphere', radius: 0.22 }, p2P: [number,number,number] = [0.8, 0, 0]
      let p3N = 'Support Base', p3G: Record<string,unknown> = { type: 'box', size: [1.4, 0.15, 1.0] }, p3P: [number,number,number] = [0, -0.5, 0]

      if (isJetEngine) {
        rootColor = '#3d3d3d'; rootSize = [0.85, 0.85, 2.2]
        p1N = 'Turbofan Blades'; p1G = { type: 'fan', radius: 0.78, blades: 18, rotation: [1.57,0,0] }; p1P = [0,0,1.2]; p1C = '#c0c5ce'
        p2N = 'Combustion Chamber'; p2G = { type: 'cylinder', radius: 0.38, depth: 1.0, rotation: [1.57,0,0] }; p2P = [0,0,0]; p2C = '#b87333'
        p3N = 'Exhaust Nozzle'; p3G = { type: 'cone', radius: 0.42, depth: 0.7 }; p3P = [0,0,-1.3]
      } else if (isCarEngine) {
        rootColor = '#3d3d3d'; rootSize = [1.5, 0.7, 0.9]
        p1N = 'Cylinder Head'; p1G = { type: 'box', size: [1.5, 0.18, 0.85] }; p1P = [0,0.44,0]; p1C = '#c0c5ce'
        p2N = 'Crankshaft'; p2G = { type: 'cylinder', radius: 0.06, depth: 1.4 }; p2P = [0,-0.15,0]; p2C = '#71797e'
        p3N = 'Oil Pan'; p3G = { type: 'box', size: [1.4, 0.18, 0.85] }; p3P = [0,-0.44,0]
      } else if (isMicroscope) {
        rootColor = '#2c3e50'; rootSize = [0.4, 0.8, 0.5]
        p1N = 'Eyepiece Lens'; p1G = { type: 'cylinder', radius: 0.14, depth: 0.35 }; p1P = [0,1.1,0.1]; p1C = '#d4f1f9'
        p2N = 'Objective Lens'; p2G = { type: 'cylinder', radius: 0.1, depth: 0.3 }; p2P = [0,0.1,0.3]; p2C = '#b87333'
        p3N = 'Stage'; p3G = { type: 'box', size: [0.6, 0.05, 0.6] }; p3P = [0,0,0]
      } else if (isRocket) {
        rootColor = '#c0c5ce'; rootSize = [0.5, 2.5, 0.5]
        p1N = 'Nose Cone'; p1G = { type: 'cone', radius: 0.25, depth: 0.7 }; p1P = [0,1.6,0]; p1C = '#e8e8e8'
        p2N = 'Rocket Nozzle'; p2G = { type: 'cone', radius: 0.3, depth: 0.5 }; p2P = [0,-1.5,0]; p2C = '#b87333'
        p3N = 'Fin Assembly'; p3G = { type: 'box', size: [0.8, 0.5, 0.05] }; p3P = [0,-1.2,0.3]
      } else if (isDrone) {
        rootColor = '#2c2f33'; rootSize = [1.4, 0.12, 1.4]
        p1N = 'Front Motor'; p1G = { type: 'cylinder', radius: 0.08, depth: 0.22 }; p1P = [-0.7,0.15,0.7]; p1C = '#1a1a1a'
        p2N = 'Propeller'; p2G = { type: 'fan', radius: 0.35, blades: 2 }; p2P = [-0.7,0.28,0.7]; p2C = '#c0c5ce'
        p3N = 'Flight Controller'; p3G = { type: 'box', size: [0.3, 0.04, 0.3] }; p3P = [0,0.06,0]
      }

      const oid = searchText.toLowerCase().replace(/[^a-z0-9]+/g, '_')
      let fallbackComponents: ExplorableObject['components'] = []

      if (isJetEngine) {
        fallbackComponents = [
          {
            id: `${oid}_central_shaft`,
            name: "Central Shaft",
            parentId: null,
            scaleLevel: "component",
            function: "Central main shaft transmitting rotational torque from the turbines at the back to the fan and compressors at the front.",
            material: "Titanium Alloy",
            riskIfRemoved: "Total mechanical lock; compressor/fan cannot spin, leading to zero thrust and engine seizure.",
            position: [0, 0, 0],
            color: "#7f8c8d",
            geometry: { type: "cylinder", radius: 0.15, depth: 3.6, rotation: [0, 0, 1.5708] } as any,
            children: [`${oid}_intake_fan`, `${oid}_lp_compressor`, `${oid}_hp_compressor`, `${oid}_combustion_chamber`, `${oid}_hp_turbine`, `${oid}_lp_turbine`, `${oid}_exhaust_cone`, `${oid}_fan_casing`, `${oid}_engine_stand`],
            microLevels: []
          },
          {
            id: `${oid}_intake_fan`,
            name: "Titanium Intake Fan",
            parentId: `${oid}_central_shaft`,
            scaleLevel: "subcomponent",
            function: "Large front fan drawing in massive volumes of air, providing the bulk of thrust through the bypass duct.",
            material: "Titanium Alloy",
            riskIfRemoved: "Total loss of bypass thrust (80%+ of engine power) and no airflow to core.",
            position: [-1.7, 0, 0],
            color: "#00b0ff",
            geometry: { type: "fan", radius: 1.4, blades: 24, rotation: [0, 0, 1.5708] } as any,
            children: [`${oid}_nose_cone`],
            microLevels: []
          },
          {
            id: `${oid}_nose_cone`,
            name: "Nose Cone Spinner",
            parentId: `${oid}_intake_fan`,
            scaleLevel: "subcomponent",
            function: "Aerodynamic nose cone that diverts incoming air smoothly into the fan and compressor, and sheds ice.",
            material: "Composite Materials",
            riskIfRemoved: "Extreme aerodynamic drag, ice accumulation, and air turbulence leading to engine surge.",
            position: [-1.85, 0, 0],
            color: "#1a1a1a",
            geometry: { type: "cone", radius: 0.35, depth: 0.6, rotation: [0, 0, -1.5708] } as any,
            children: [],
            microLevels: []
          },
          {
            id: `${oid}_lp_compressor`,
            name: "Low-Pressure Compressor",
            parentId: `${oid}_central_shaft`,
            scaleLevel: "subcomponent",
            function: "First compression stage raising air pressure and temperature before it enters the high-pressure section.",
            material: "Titanium",
            riskIfRemoved: "Loss of initial compression, leading to immediate stall and engine failure.",
            position: [-1.0, 0, 0],
            color: "#2ecc71",
            geometry: { type: "cylinder", radius: 0.8, depth: 0.6, rotation: [0, 0, 1.5708] } as any,
            children: [],
            microLevels: []
          },
          {
            id: `${oid}_hp_compressor`,
            name: "High-Pressure Compressor",
            parentId: `${oid}_central_shaft`,
            scaleLevel: "subcomponent",
            function: "Final compressor stage compressing air to extremely high pressure before combustion.",
            material: "Nickel Alloy",
            riskIfRemoved: "Engine cannot maintain self-sustaining combustion due to lack of compression.",
            position: [-0.4, 0, 0],
            color: "#8eff1e",
            geometry: { type: "cylinder", radius: 0.65, depth: 0.6, rotation: [0, 0, 1.5708] } as any,
            children: [],
            microLevels: []
          },
          {
            id: `${oid}_combustion_chamber`,
            name: "Combustion Chamber",
            parentId: `${oid}_central_shaft`,
            scaleLevel: "subcomponent",
            function: "Area where fuel is injected, mixed with compressed air, and ignited to create hot, high-velocity gas.",
            material: "Ceramic Matrix Composite",
            riskIfRemoved: "No combustion possible; engine produces zero energy and stops.",
            position: [0.2, 0, 0],
            color: "#e67e22",
            geometry: { type: "cylinder", radius: 0.7, depth: 0.6, rotation: [0, 0, 1.5708] } as any,
            children: [],
            microLevels: []
          },
          {
            id: `${oid}_hp_turbine`,
            name: "High-Pressure Turbine",
            parentId: `${oid}_central_shaft`,
            scaleLevel: "subcomponent",
            function: "Extracts energy from hot gas flow to drive the high-pressure compressor stage via outer shaft.",
            material: "Single-Crystal Nickel Superalloy",
            riskIfRemoved: "High-pressure compressor stops rotating; engine ceases operation immediately.",
            position: [0.8, 0, 0],
            color: "#f1c40f",
            geometry: { type: "cylinder", radius: 0.75, depth: 0.4, rotation: [0, 0, 1.5708] } as any,
            children: [],
            microLevels: []
          },
          {
            id: `${oid}_lp_turbine`,
            name: "Low-Pressure Turbine",
            parentId: `${oid}_central_shaft`,
            scaleLevel: "subcomponent",
            function: "Extracts remaining gas energy to drive the main intake fan and low-pressure compressor.",
            material: "Nickel Alloy",
            riskIfRemoved: "Intake fan stops spinning; engine loses virtually all thrust.",
            position: [1.3, 0, 0],
            color: "#e74c3c",
            geometry: { type: "cylinder", radius: 0.85, depth: 0.5, rotation: [0, 0, 1.5708] } as any,
            children: [],
            microLevels: []
          },
          {
            id: `${oid}_exhaust_cone`,
            name: "Exhaust Nozzle Cone",
            parentId: `${oid}_central_shaft`,
            scaleLevel: "subcomponent",
            function: "Channels exhaust gas flow to maximize velocity and direct the thrust vector.",
            material: "Inconel Alloy",
            riskIfRemoved: "Thrust efficiency drops dramatically; exhaust gases disperse unevenly.",
            position: [1.75, 0, 0],
            color: "#d35400",
            geometry: { type: "cone", radius: 0.4, depth: 0.6, rotation: [0, 0, 1.5708] } as any,
            children: [],
            microLevels: []
          },
          {
            id: `${oid}_fan_casing`,
            name: "Outer Fan Casing",
            parentId: `${oid}_central_shaft`,
            scaleLevel: "subcomponent",
            function: "Surrounds fan blades to contain blade fragments in case of failure and duct incoming air.",
            material: "Kevlar & Aluminum",
            riskIfRemoved: "Critical safety risk: fan blade out event would destroy the aircraft wing/fuselage.",
            position: [-1.2, 0, 0],
            color: "#3f51b5",
            geometry: { type: "torus", radius: 1.45, tube: 0.08, rotation: [0, 0, 1.5708] } as any,
            children: [],
            microLevels: []
          },
          {
            id: `${oid}_engine_stand`,
            name: "Structural Display Stand",
            parentId: `${oid}_central_shaft`,
            scaleLevel: "subcomponent",
            function: "Heavy display stand supporting the engine assembly for research and presentation.",
            material: "Structural Steel",
            riskIfRemoved: "Engine falls to the ground; cannot be operated or inspected.",
            position: [0, -1.2, 0],
            color: "#7f8c8d",
            geometry: { type: "box", size: [2.4, 0.2, 1.2] } as any,
            children: [],
            microLevels: []
          }
        ]
      } else {
        fallbackComponents = [
          { id: `${oid}_body`, name: `${wikiTitle} Body`, parentId: null, scaleLevel: 'component',
            function: `Main structural body of the ${wikiTitle}.`, material: 'Alloy',
            riskIfRemoved: 'Complete structural failure.', position: [0,0,0], color: rootColor,
            geometry: { type: 'box', size: rootSize } as ExplorableObject['components'][0]['geometry'],
            children: [`${oid}_p1`,`${oid}_p2`,`${oid}_p3`], microLevels: [] },
          { id: `${oid}_p1`, name: p1N, parentId: `${oid}_body`, scaleLevel: 'subcomponent',
            function: `Primary component of the ${wikiTitle}.`, material: 'Aluminum',
            riskIfRemoved: 'Primary function fails.', position: p1P, color: p1C,
            geometry: p1G as ExplorableObject['components'][0]['geometry'], children: [], microLevels: [] },
          { id: `${oid}_p2`, name: p2N, parentId: `${oid}_body`, scaleLevel: 'subcomponent',
            function: `Secondary component of the ${wikiTitle}.`, material: 'Steel',
            riskIfRemoved: 'Secondary function lost.', position: p2P, color: p2C,
            geometry: p2G as ExplorableObject['components'][0]['geometry'], children: [], microLevels: [] },
          { id: `${oid}_p3`, name: p3N, parentId: `${oid}_body`, scaleLevel: 'subcomponent',
            function: `Support structure for the ${wikiTitle}.`, material: 'Cast Iron',
            riskIfRemoved: 'Loses structural support.', position: p3P, color: '#4a4a4f',
            geometry: p3G as ExplorableObject['components'][0]['geometry'], children: [], microLevels: [] }
        ]
      }

      const fallback: ExplorableObject = {
        id: oid, name: wikiTitle, type: 'mechanical_system', summary: wikiDesc,
        defaultView: 'assembled', model: { kind: 'procedural', assetUrl: null },
        components: fallbackComponents
      }
      setActiveObject(fallback)
      setSelectedComponent(fallback.components[0])
      setActiveTab('research')
      speak(`Loaded offline model for ${wikiTitle}. Reconnect backend for full AI-generated details.`)
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
      const response = await fetch(`${API_BASE}/api/agents/process?${params.toString()}`, { method: 'POST' })
      const data = await response.json()
      const reply = data?.result?.unified_response || data?.result?.message || `Command accepted: ${command}`
      speak(String(reply).slice(0, 260))
    } catch {
      speak(`ARIA local mode: ${command}. I updated the lab view and kept the command in session memory.`)
    }
  }, [activeObject, query, searchObject, selectedComponent, speak])

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
        isAnimating={isAnimating}
        setIsAnimating={setIsAnimating}
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
