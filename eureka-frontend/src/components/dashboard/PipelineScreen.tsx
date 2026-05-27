import { useEffect, useState } from 'react'

function PipelineScreen() {
  const [cpu, setCpu] = useState(42)
  const [mem, setMem] = useState(14.2)
  const [memoryPercent, setMemoryPercent] = useState(68)
  const [chartBars, setChartBars] = useState([28, 42, 26, 54, 36, 62, 70, 14, 15, 12])

  useEffect(() => {
    const interval = setInterval(() => {
      setCpu(Math.floor(30 + Math.random() * 25))
      const nextMem = 13.5 + Math.random() * 1.5
      setMem(parseFloat(nextMem.toFixed(1)))
      setMemoryPercent(Math.floor((nextMem / 24.0) * 100))
      setChartBars((prev) => [...prev.slice(1), Math.floor(10 + Math.random() * 75)])
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  const steps = [
    ['Parser', 'Completed', 'Successfully parsed 1,204 source documents and standardized schema structures.', '1,204 docs'],
    ['Scraper', 'Active', 'Extracting raw text data from targeted scientific repositories.', '68%'],
    ['AI Agent Analysis', 'Pending', 'Awaiting scraped payload to begin semantic evaluation and pattern recognition.', 'queued'],
    ['Report Generation', 'Locked', 'Final synthesis requires prior steps to complete.', 'locked']
  ]

  return (
    <main className="pipeline-screen">
      <section className="hero-copy compact-hero">
        <p className="eyebrow">Pipeline Status</p>
        <p>Real-time autonomous extraction and analysis flow.</p>
        <div className="button-row">
          <button className="ghost-button">▮▮ Pause</button>
          <button className="primary-button">▷ Run Pipeline</button>
        </div>
      </section>
      <div className="timeline">
        {steps.map(([name, state, detail, stat], index) => (
          <section className={`timeline-card ${state.toLowerCase()}`} key={name}>
            <div className="timeline-dot">{index < 2 ? '✓' : index === 2 ? '⌁' : '▣'}</div>
            <div className="timeline-body">
              <div className="job-row">
                <h2>{name}</h2>
                <span className="mini-status">{state}</span>
              </div>
              <p>{detail}</p>
              <div className="data-tile">{stat}</div>
            </div>
          </section>
        ))}
      </div>
      <section className="panel-card">
        <div className="section-title">System Metrics <span>⌁</span></div>
        <div className="metric-line">
          <span>CPU Usage</span>
          <b>{cpu}%</b>
          <i style={{ width: `${cpu}%` }} />
        </div>
        <div className="metric-line purple">
          <span>Memory</span>
          <b>{mem} GB</b>
          <i style={{ width: `${memoryPercent}%` }} />
        </div>
        <div className="mini-bars">
          {chartBars.map((h, i) => (
            <i key={i} style={{ height: `${h}%` }} />
          ))}
        </div>
      </section>
    </main>
  )
}

export default PipelineScreen
