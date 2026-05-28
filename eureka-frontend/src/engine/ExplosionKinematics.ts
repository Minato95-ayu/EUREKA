// handles component displacement for explosion animations
export class ExplosionKinematics {
  
  // calculates new pos based on depth and explosion factor
  public static calculateDisplacement(
    defaultPos: [number, number, number] | number[], 
    parentId: string | null, 
    explodeFactor: number
  ): [number, number, number] {
    
    // no explosion
    if (explodeFactor <= 0.001) {
      return [defaultPos[0], defaultPos[1], defaultPos[2]]
    }

    const [dirX, dirY, dirZ] = defaultPos
    
    // dist from center
    const magnitude = Math.hypot(dirX, dirY, dirZ)
    
    // prevent div by zero
    if (magnitude === 0) {
      // core pieces drop slightly if dead center
      return [0, -explodeFactor * 0.2, -explodeFactor * 0.1]
    }

    // normalized dir
    const nx = dirX / magnitude
    const ny = dirY / magnitude
    const nz = dirZ / magnitude

    // outer pieces move more, inner pieces move less
    const depthMultiplier = parentId ? 1.5 : 0.5
    
    // curve for snappy feel
    const kineticFactor = Math.pow(explodeFactor, 1.2) * depthMultiplier

    return [
      defaultPos[0] + (nx * kineticFactor),
      defaultPos[1] + (ny * kineticFactor),
      defaultPos[2] + (nz * kineticFactor),
    ]
  }
}
