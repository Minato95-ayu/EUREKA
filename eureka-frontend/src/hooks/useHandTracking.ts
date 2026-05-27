import { useCallback, useRef, useState } from 'react'
import type { Hands as MediaPipeHands, Results } from '@mediapipe/hands'
import type { GestureState } from '../types'

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

export function useHandTracking(callbacks: {
  onZoomIn: () => void
  onZoomOut: () => void
  onReset: () => void
  onSwipeLeft: () => void
  onSwipeRight: () => void
  onError: (message: string) => void
}) {
  const [cameraEnabled, setCameraEnabled] = useState(false)
  const [gesture, setGesture] = useState<GestureState>('offline')
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const handsRef = useRef<MediaPipeHands | null>(null)
  const lastPinchRef = useRef<number | null>(null)
  const lastXRef = useRef<number | null>(null)

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
        callbacks.onZoomIn()
      } else if (pinch > lastPinch + 0.035) {
        setGesture('zoom-out')
        callbacks.onZoomOut()
      }
    }

    const extended = [index, middle, ring, pinky].filter((tip) => tip.y < wrist.y - 0.08).length
    if (extended <= 1) {
      setGesture('fist')
      callbacks.onReset()
    } else if (extended === 1) {
      setGesture('point')
    }

    if (lastX !== null) {
      const deltaX = wrist.x - lastX
      if (deltaX > 0.12) {
        setGesture('swipe-right')
        callbacks.onSwipeRight()
      } else if (deltaX < -0.12) {
        setGesture('swipe-left')
        callbacks.onSwipeLeft()
      }
    }

    lastPinchRef.current = pinch
    lastXRef.current = wrist.x
  }, [callbacks])

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
      callbacks.onError('Camera permission failed. Allow webcam access to use hand commands.')
    }
  }, [cameraEnabled, processHands, callbacks])

  const cleanup = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    void handsRef.current?.close()
  }, [])

  return {
    cameraEnabled,
    gesture,
    videoRef,
    toggleCamera,
    cleanup
  }
}
