import type { Hands as MediaPipeHands } from '@mediapipe/hands'

export type Tab = 'status' | 'batch' | 'pipeline' | 'research' | 'results'
export type AriaState = 'idle' | 'listening' | 'thinking' | 'speaking'
export type GestureState = 'offline' | 'ready' | 'zoom-in' | 'zoom-out' | 'point' | 'fist' | 'swipe-left' | 'swipe-right'
export type ScaleLevel = 'object' | 'component' | 'subcomponent' | 'material' | 'molecule' | 'atom'

export type ObjectGeometry = {
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

export type ObjectComponent = {
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

export type ExplorableObject = {
  id: string
  name: string
  type: string
  summary: string
  defaultView: string
  model: { kind: 'procedural' | 'gltf'; assetUrl: string | null }
  components: ObjectComponent[]
}

export type SpeechRecognitionResultItem = {
  transcript: string
}

export type SpeechRecognitionResult = {
  0: SpeechRecognitionResultItem
}

export type SpeechRecognitionEventLike = {
  results: {
    length: number
    [index: number]: SpeechRecognitionResult
  }
}

export type BrowserSpeechRecognition = {
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
