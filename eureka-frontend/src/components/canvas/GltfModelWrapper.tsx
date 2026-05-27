/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo } from 'react'
import { useGLTF } from '@react-three/drei'

export function GltfModelWrapper({ 
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
