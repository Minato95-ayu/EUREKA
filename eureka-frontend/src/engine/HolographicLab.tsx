import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { OrbitControls, Sphere, Environment, ContactShadows } from '@react-three/drei'
import { EffectComposer, Bloom, N8AO, Vignette, ToneMapping } from '@react-three/postprocessing'
import { ToneMappingMode } from 'postprocessing'
import type { Group } from 'three'
import type { ObjectComponent, ExplorableObject, GestureState } from '../core/EurekaTypes'
import { MeshRenderer } from '../engine/MeshRenderer'

interface LabSceneProps {
  zoomLevel: number
  gesture: GestureState
  activeObject: ExplorableObject | null
  selectedComponent: ObjectComponent | null
  onSelectComponent: (component: ObjectComponent) => void
  explodeFactor: number
  shellMode: 'solid' | 'transparent' | 'hidden'
  showLabels: boolean
  isAnimating: boolean
}

export function HolographicLab({
  zoomLevel,
  gesture,
  activeObject,
  selectedComponent,
  onSelectComponent,
  explodeFactor,
  shellMode,
  showLabels,
  isAnimating
}: LabSceneProps) {
  const group = useRef<Group>(null)

  useFrame(({ clock, camera }) => {
    const t = clock.getElapsedTime()
    // TODO: logarithmic zoom is still slightly janky on mobile when zooming past 100x. Temporary fix for now.
    // the sudden clipping was causing WebGL context loss on some Android devices.
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
      {/* temporary optimization for low-end GPU devices: reducing ambient intensity */}
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
          activeObject.components.map((component: any) => (
            <MeshRenderer
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
      {/* warning: EffectComposer tanks fps on Safari if multisampling > 4 */}
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
