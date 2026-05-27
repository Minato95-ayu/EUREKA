import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children?: ReactNode
}

interface State {
  hasError: boolean
  errorMsg: string
}

export class RenderErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    errorMsg: ''
  }

  public static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, errorMsg: error.message }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // usually happens when WebGL context is lost on mobile or GPU runs out of memory
    console.error('Uncaught rendering error:', error, errorInfo)
  }

  private handleReset = () => {
    // try to recover context
    this.setState({ hasError: false, errorMsg: '' })
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          width: '100%',
          backgroundColor: '#050a0c',
          color: '#ff4d4d',
          padding: '2rem',
          textAlign: 'center',
          fontFamily: 'monospace'
        }}>
          <h2>GPU / WebGL Crash Detected</h2>
          <p>The rendering engine encountered a fatal error. This usually happens when the device runs out of memory or loses WebGL context.</p>
          <div style={{ backgroundColor: '#1a0505', padding: '1rem', margin: '1rem 0', borderRadius: '4px', maxWidth: '80%', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            <code>{this.state.errorMsg}</code>
          </div>
          <button 
            onClick={this.handleReset}
            style={{
              padding: '10px 20px',
              backgroundColor: '#ff4d4d',
              color: '#000',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold',
              marginTop: '1rem'
            }}
          >
            Attempt Recovery
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
