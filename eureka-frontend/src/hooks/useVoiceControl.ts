import { useCallback, useMemo, useRef, useState } from 'react'
import type { AriaState, BrowserSpeechRecognition } from '../types'

export function useVoiceControl(onCommand: (transcript: string) => void) {
  const [ariaState, setAriaState] = useState<AriaState>('idle')
  const [ariaReply, setAriaReply] = useState('ARIA online. Voice and gesture systems are ready for calibration.')
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null)

  const SpeechRecognitionCtor = useMemo(() => {
    return window.SpeechRecognition || window.webkitSpeechRecognition
  }, [])

  const voiceSupported = Boolean(SpeechRecognitionCtor)

  const speak = useCallback((text: string) => {
    setAriaReply(text)
    if (!('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = /[\u0900-\u097F]|hindi|हिंदी/i.test(text) ? 'hi-IN' : 'en-US'
    utterance.rate = 0.95
    utterance.pitch = 0.9
    utterance.onstart = () => setAriaState('speaking')
    utterance.onend = () => setAriaState('idle')
    window.speechSynthesis.speak(utterance)
  }, [])

  const toggleVoice = useCallback(() => {
    if (!SpeechRecognitionCtor) return

    if (ariaState === 'listening') {
      recognitionRef.current?.stop()
      setAriaState('idle')
      return
    }

    const recognition = new SpeechRecognitionCtor()
    recognition.lang = 'en-IN'
    recognition.continuous = false
    recognition.interimResults = false
    recognition.onresult = (event) => {
      const transcript = event.results[event.results.length - 1][0].transcript
      onCommand(transcript)
    }
    recognition.onend = () => setAriaState((state) => state === 'listening' ? 'idle' : state)
    recognition.onerror = () => {
      setAriaState('idle')
      setAriaReply('Voice recognition could not hear a clear command. Try again.')
    }
    recognitionRef.current = recognition
    setAriaState('listening')
    recognition.start()
  }, [SpeechRecognitionCtor, ariaState, onCommand])

  const cleanup = useCallback(() => {
    recognitionRef.current?.stop()
  }, [])

  return {
    voiceSupported,
    ariaState,
    setAriaState,
    ariaReply,
    setAriaReply,
    speak,
    toggleVoice,
    cleanup
  }
}
