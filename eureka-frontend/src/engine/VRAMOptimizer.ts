import * as THREE from 'three'

// util to clean up threejs memory leaks on unmount
export class VRAMOptimizer {
  
  // recursively dumps geometries/materials. 
  // only call this when component unmounts or else webgl crashes.
  public static purge(object: THREE.Object3D | null | undefined): void {
    if (!object) return

    object.traverse((node: THREE.Object3D) => {
      const mesh = node as THREE.Mesh

      // 1. drop geometry
      if (mesh.geometry) {
        mesh.geometry.dispose()
      }

      // 2. drop materials & textures
      if (mesh.material) {
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
        
        for (const material of materials) {
          // iterate props to find textures
          for (const key in material) {
            const value = (material as any)[key]
            if (value && value instanceof THREE.Texture) {
              value.dispose()
            }
          }
          material.dispose()
        }
      }
    })

    // 3. remove from parent
    if (object.parent) {
      object.parent.remove(object)
    }
    
    // don't nullify object here, let js gc handle it
  }
}
