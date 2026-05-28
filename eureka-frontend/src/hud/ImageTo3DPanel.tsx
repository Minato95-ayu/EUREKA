import { useState, useRef } from 'react'

interface ImageTo3DPanelProps {
  onModelGenerated: (url: string) => void
}

export function ImageTo3DPanel({ onModelGenerated }: ImageTo3DPanelProps) {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError("Please select an image first.")
      return
    }

    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      // Connecting to the FastAPI backend that acts as orchestrator
      const response = await fetch('http://localhost:8000/api/3d/generate', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}: ${await response.text()}`)
      }

      const data = await response.json()
      if (data.model_url) {
        onModelGenerated(data.model_url)
      } else {
        throw new Error("Invalid response from server: No model URL found.")
      }
    } catch (err: any) {
      setError(err.message || "Failed to generate 3D model.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="query-card" style={{ marginTop: '1rem' }}>
      <div className="section-title">
        TripoSR AI <span>Image to 3D</span>
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
        <input 
          type="file" 
          accept="image/*" 
          onChange={handleFileChange} 
          ref={fileInputRef}
          style={{ display: 'none' }}
        />
        
        <div 
          onClick={() => fileInputRef.current?.click()}
          style={{ 
            border: '2px dashed #00e5f0', 
            padding: '2rem', 
            textAlign: 'center', 
            cursor: 'pointer',
            borderRadius: '8px',
            background: 'rgba(0, 229, 240, 0.05)'
          }}
        >
          {file ? file.name : "Click to select or drag & drop an image here"}
        </div>

        {error && <div style={{ color: '#ff4444', fontSize: '0.9rem' }}>{error}</div>}

        <button 
          className="primary-button execute" 
          onClick={handleUpload}
          disabled={loading || !file}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          {loading ? 'Generating... (Takes ~10-15s)' : 'Generate 3D Model ▷'}
        </button>
      </div>
    </section>
  )
}
