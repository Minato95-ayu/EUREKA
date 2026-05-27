/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Html, Edges, RoundedBox } from '@react-three/drei'
import { Geometry, Base, Subtraction } from '@react-three/csg'
import * as THREE from 'three'
import type { ObjectComponent, ObjectGeometry } from '../core/EurekaTypes'
import { ModelLoader } from '../engine/ModelLoader'

interface ComponentMeshProps {
  component: ObjectComponent
  selected: boolean
  onSelect: (component: ObjectComponent) => void
  explodeFactor: number
  shellMode: 'solid' | 'transparent' | 'hidden'
  showLabels: boolean
  isAnimating: boolean
  selectedComponentId?: string
  allComponents?: ObjectComponent[]
}

export function MeshRenderer({
  component,
  selected,
  onSelect,
  explodeFactor,
  shellMode,
  showLabels,
  isAnimating,
  selectedComponentId,
  allComponents
}: ComponentMeshProps) {
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
          {geometry.subtractions?.map((sub: any, idx: number) => (
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
        <ModelLoader 
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
