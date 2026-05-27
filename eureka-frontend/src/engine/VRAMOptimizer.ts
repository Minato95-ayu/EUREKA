import * as THREE from 'three'

/**
 * VRAMOptimizer
 * 
 * Deep systems-engineered utility for strict WebGL memory lifecycle management.
 * AI-generated prototypes often leak WebGL buffers because React's component 
 * lifecycle doesn't automatically drop GPU-bound Three.js primitives.
 * This class ensures 0-leak execution during massive layout shifts.
 */
export class VRAMOptimizer {
  
  /**
   * Recursively traverses a Three.js scene graph and forcibly disposes
   * of all bound Geometries, Materials, and Textures.
   * 
   * WARNING: Call this ONLY when the object is fully unmounted from the graph.
   * Calling this on active objects will cause a fatal WebGL crash.
   */
  public static purge(object: THREE.Object3D | null | undefined): void {
    if (!object) return

    object.traverse((node: THREE.Object3D) => {
      const mesh = node as THREE.Mesh

      // 1. Purge Geometry Buffers
      if (mesh.geometry) {
        mesh.geometry.dispose()
      }

      // 2. Purge Material & Texture Buffers
      if (mesh.material) {
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
        
        for (const material of materials) {
          // Iterate over material properties to find and dispose textures
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

    // 3. Clear node hierarchy
    if (object.parent) {
      object.parent.remove(object)
    }
    
    // hint: we don't nullify the object itself to avoid V8 deoptimization
    // let the JS garbage collector handle the CPU heap side.
  }
}
