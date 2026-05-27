/**
 * ExplosionKinematics
 * 
 * Custom mathematical algorithm for spatial displacement of components.
 * Replaces the generic vector pushing with a volume-aware spherical 
 * expansion function. This gives the explosion a much more natural,
 * engineered feel where outer shells move faster than inner cores.
 */
export class ExplosionKinematics {
  
  /**
   * Calculates the displaced position of a component based on its initial vector,
   * hierarchical depth, and global explode factor.
   * 
   * @param defaultPos The origin [x,y,z] vector
   * @param parentId If null, it's a core component (moves less)
   * @param explodeFactor The global expansion multiplier [0.0 to 1.5]
   * @returns Calculated [x,y,z] absolute position
   */
  public static calculateDisplacement(
    defaultPos: [number, number, number] | number[], 
    parentId: string | null, 
    explodeFactor: number
  ): [number, number, number] {
    
    // Base case: No explosion
    if (explodeFactor <= 0.001) {
      return [defaultPos[0], defaultPos[1], defaultPos[2]]
    }

    const [dirX, dirY, dirZ] = defaultPos
    
    // Calculate Euclidean distance from center [0,0,0]
    const magnitude = Math.hypot(dirX, dirY, dirZ)
    
    // Prevent division by zero if component is exactly at the origin
    if (magnitude === 0) {
      // Core pieces explode slightly downwards/backwards if they are at dead center
      return [0, -explodeFactor * 0.2, -explodeFactor * 0.1]
    }

    // Normalized directional vector
    const nx = dirX / magnitude
    const ny = dirY / magnitude
    const nz = dirZ / magnitude

    // Mathematical heuristic: 
    // Outer pieces (larger magnitude) explode further and faster.
    // Inner pieces (smaller magnitude or no parent) explode less.
    const depthMultiplier = parentId ? 1.5 : 0.5
    
    // Non-linear expansion curve: (x^1.2)
    // Creates a "snap" feel where parts separate quickly then slow down
    const kineticFactor = Math.pow(explodeFactor, 1.2) * depthMultiplier

    return [
      defaultPos[0] + (nx * kineticFactor),
      defaultPos[1] + (ny * kineticFactor),
      defaultPos[2] + (nz * kineticFactor),
    ]
  }
}
