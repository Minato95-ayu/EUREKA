import { useEffect, useState } from 'react'
import MetricWidget from './MetricWidget'
import { logs as initialLogs } from '../core/Constants'
import { fetchDetailedHealth } from '../neural/DataRelay'

function TelemetryScreen() {
  const [checks, setChecks] = useState<Record<string, string>>({
    database: 'loading',
    redis: 'loading',
    ollama: 'loading'
  })
  const [logList, setLogList] = useState<string[]>(initialLogs)

  useEffect(() => {
    let active = true
    const check = async () => {
      const data = await fetchDetailedHealth()
      if (active && data?.checks) {
        setChecks(data.checks)
      }
    }
    void check()
    const interval = setInterval(check, 8000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      const systemMessages = [
        `[${new Date().toLocaleTimeString()}] TELEMETRY: Stream synchronized`,
        `[${new Date().toLocaleTimeString()}] HEARTBEAT: Connection alpha-node-01 active`,
        `[${new Date().toLocaleTimeString()}] COMPUTE: Node GPU capacity at ${Math.floor(15 + Math.random() * 45)}%`,
        `[${new Date().toLocaleTimeString()}] AGENT: Telemetry sweep verified`,
        `[${new Date().toLocaleTimeString()}] MEMORY: Buffer collection completed`
      ]
      const nextMsg = systemMessages[Math.floor(Math.random() * systemMessages.length)]
      setLogList((prev) => [...prev.slice(-15), nextMsg])
    }, 4500)
    return () => clearInterval(interval)
  }, [])

  return (
    <main className="screen-grid">
      <section className="hero-copy">
        <p className="eyebrow">SYS.ONLINE</p>
        <h1>System Overview</h1>
        <p>Global telemetry and autonomous research operations.</p>
      </section>
      <div className="metric-grid">
        <MetricWidget
          label="DATABASE"
          value={checks.database === 'healthy' ? 'OK' : checks.database === 'loading' ? '...' : 'OFF'}
          detail="PostgreSQL backend engine"
          tone={checks.database === 'healthy' ? 'green' : 'pink'}
        />
        <MetricWidget
          label="OLLAMA LLM"
          value={checks.ollama === 'healthy' ? 'OK' : checks.ollama === 'loading' ? '...' : 'OFF'}
          detail="Local model host status"
          tone={checks.ollama === 'healthy' ? 'green' : 'pink'}
        />
        <MetricWidget
          label="REDIS QUEUE"
          value={checks.redis === 'healthy' ? 'OK' : checks.redis === 'loading' ? '...' : 'OFF'}
          detail="Task queue status feed"
          tone={checks.redis === 'healthy' ? 'green' : 'pink'}
        />
      </div>
      <section className="terminal-card">
        <div className="terminal-head">▣ STD_OUT // Live Feed <span>●●●</span></div>
        <div className="terminal-lines">
          {logList.map((line, idx) => (
            <p key={idx}>{line}</p>
          ))}
        </div>
      </section>
      <section className="chart-card">
        <div className="section-title">Ingestion Rate <span>⌁</span></div>
        <div className="bar-chart">
          {[34, 58, 42, 82, 66, 96, 48].map((height, index) => (
            <i key={index} style={{ height: `${height}%` }} />
          ))}
        </div>
        <div className="chart-axis"><span>T-6h</span><span>Now</span></div>
      </section>
    </main>
  )
}

export default TelemetryScreen
