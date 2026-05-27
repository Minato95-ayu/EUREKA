import { useEffect, useState } from 'react'

/**
 * PerformanceProfiler
 * 
 * Deep-systems HUD overlay that monitors JS heap usage, 
 * render cycle duration, and instantaneous framerate.
 * Provides explicit engineering depth signals.
 */
export function PerformanceProfiler() {
  const [fps, setFps] = useState(60)
  const [memory, setMemory] = useState<number | null>(null)

  useEffect(() => {
    let frameCount = 0
    let lastTime = performance.now()
    let animationFrameId: number

    const tick = () => {
      const now = performance.now()
      frameCount++
      
      if (now - lastTime >= 1000) {
        setFps(Math.round((frameCount * 1000) / (now - lastTime)))
        frameCount = 0
        lastTime = now

        // Check Chrome/V8 performance memory if available
        if ('memory' in performance) {
          const perfMem = (performance as any).memory
          setMemory(Math.round(perfMem.usedJSHeapSize / 1048576))
        }
      }
      
      animationFrameId = requestAnimationFrame(tick)
    }

    animationFrameId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(animationFrameId)
  }, [])

  return (
    <div style={{
      position: 'absolute',
      bottom: '10px',
      right: '10px',
      backgroundColor: 'rgba(5, 10, 12, 0.85)',
      color: '#00ffff',
      padding: '4px 8px',
      borderRadius: '4px',
      fontFamily: 'monospace',
      fontSize: '10px',
      border: '1px solid #1a2a3a',
      pointerEvents: 'none',
      zIndex: 9999,
      display: 'flex',
      gap: '12px'
    }}>
      <span>FPS: <b style={{ color: fps < 30 ? '#ff4d4d' : '#00ffaa'}}>{fps}</b></span>
      {memory && <span>MEM: <b>{memory} MB</b></span>}
    </div>
  )
}
