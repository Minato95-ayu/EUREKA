import { useState, useRef, useCallback } from 'react'

interface ImageTo3DPanelProps {
  onModelGenerated: (url: string) => void
}

const API_BASE = import.meta.env.VITE_API_URL || ''

const STATUS_STEPS = [
  'Uploading image...',
  'Analyzing geometry...',
  'Processing on GPU...',
  'Constructing mesh...',
  'Rendering 3D model...',
]

export function ImageTo3DPanel({ onModelGenerated }: ImageTo3DPanelProps) {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [progress, setProgress] = useState(0)
  const [statusText, setStatusText] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const handleFile = useCallback((f: File) => {
    if (!f.type.startsWith('image/')) {
      setError('Please select a valid image file (PNG, JPG, WebP).')
      return
    }
    if (f.size > 20 * 1024 * 1024) {
      setError('File too large. Maximum size is 20 MB.')
      return
    }
    setFile(f)
    setError(null)
    setPreviewUrl(URL.createObjectURL(f))
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
    const droppedFile = e.dataTransfer.files?.[0]
    if (droppedFile) handleFile(droppedFile)
  }

  const startProgressSimulation = () => {
    let step = 0
    setProgress(5)
    setStatusText(STATUS_STEPS[0])
    progressRef.current = setInterval(() => {
      step++
      if (step < STATUS_STEPS.length) {
        setStatusText(STATUS_STEPS[step])
        setProgress(Math.min(90, (step / STATUS_STEPS.length) * 90 + 5))
      }
    }, 2500)
  }

  const stopProgressSimulation = (success: boolean) => {
    if (progressRef.current) clearInterval(progressRef.current)
    if (success) {
      setProgress(100)
      setStatusText('Complete!')
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError("Please select an image first.")
      return
    }

    setLoading(true)
    setError(null)
    startProgressSimulation()

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${API_BASE}/api/3d/generate`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}: ${await response.text()}`)
      }

      const data = await response.json()
      if (data.model_url) {
        stopProgressSimulation(true)
        onModelGenerated(data.model_url)
      } else {
        throw new Error("Invalid response from server: No model URL found.")
      }
    } catch (err: any) {
      stopProgressSimulation(false)
      setError(err.message || "Failed to generate 3D model. Make sure the backend is running.")
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setFile(null)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(null)
    setError(null)
    setProgress(0)
    setStatusText('')
  }

  return (
    <section className="query-card image-to-3d-card">
      <div className="section-title">
        Image to 3D <span>experimental</span>
      </div>
      {!expanded && (
        <button
          className="ghost-button"
          onClick={() => setExpanded(true)}
          style={{ width: '100%', justifyContent: 'center', marginTop: '1rem' }}
        >
          Open Image Upload ▷
        </button>
      )}
      
      {expanded && <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
        <input 
          type="file" 
          accept="image/*" 
          onChange={handleFileChange} 
          ref={fileInputRef}
          style={{ display: 'none' }}
        />
        
        <div 
          className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {file ? (
            <>📎 {file.name} ({(file.size / 1024).toFixed(0)} KB)</>
          ) : (
            <>🖼️ Click or drag & drop an image here</>
          )}
        </div>

        {previewUrl && (
          <div className="upload-preview">
            <img src={previewUrl} alt="Preview of uploaded file" />
          </div>
        )}

        {loading && (
          <>
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
            </div>
            <div className="upload-status">{statusText}</div>
          </>
        )}

        {error && <div style={{ color: '#ff4444', fontSize: '0.85rem', fontFamily: 'ui-monospace, monospace' }}>⚠ {error}</div>}

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="ghost-button"
            onClick={() => { handleClear(); setExpanded(false); }}
            disabled={loading}
            style={{ flex: 1, justifyContent: 'center' }}
          >
            Close
          </button>
          {file && !loading && (
            <button
              className="ghost-button"
              onClick={handleClear}
              style={{ justifyContent: 'center' }}
            >
              Clear
            </button>
          )}
          <button 
            className="primary-button execute" 
            onClick={handleUpload}
            disabled={loading || !file}
            style={{ flex: 1, justifyContent: 'center' }}
          >
            {loading ? 'Generating...' : 'Generate 3D ▷'}
          </button>
        </div>
      </div>}
    </section>
  )
}
