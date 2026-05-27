import { useEffect, useState } from 'react'
import { fetchSimulations, createSimulation } from '../neural/DataRelay'

function SimulationBatch() {
  const [simulations, setSimulations] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const loadSims = async () => {
    setLoading(true)
    const data = await fetchSimulations()
    setSimulations(data)
    setLoading(false)
  }

  useEffect(() => {
    void loadSims()
  }, [])

  const handleCreateBatch = async () => {
    const name = prompt("Enter simulation batch name:")
    if (!name) return
    const desc = prompt("Enter simulation description:") || "Molecular dynamics simulation run"
    const simId = await createSimulation(name, desc)
    if (simId) {
      alert(`Successfully created batch: ${simId}`)
      void loadSims()
    } else {
      alert("Failed to create simulation batch. Make sure backend is running.")
    }
  }

  return (
    <main className="stack-screen">
      <section className="hero-copy">
        <h1>Batch Operations</h1>
        <p>Manage active computational pipelines and molecular simulations.</p>
        <button className="primary-button" onClick={handleCreateBatch}>+ New Batch</button>
      </section>

      {loading ? (
        <section className="panel-card">
          <p>Querying simulations queue...</p>
        </section>
      ) : simulations.length > 0 ? (
        simulations.map((sim, idx) => (
          <section key={sim.id || idx} className={`job-card ${idx === 0 ? 'active-job' : 'warning-job'}`} style={{ marginBottom: '16px' }}>
            <div className="job-row">
              <span className="pill">{sim.status || 'Active'}</span>
              <span>ID: {sim.id || `SIM-${idx}`}</span>
              <strong>{sim.progress || '72%'}</strong>
            </div>
            <h2>{sim.name}</h2>
            <div className="progress"><i style={{ width: sim.progress || '72%' }} /></div>
            <div className="job-meta">
              <span><small>Model</small>{sim.simulation_type || 'molecular'}</span>
              <span><small>Particles</small>{sim.particles?.length || 0}</span>
              <span><small>Reactions</small>{sim.reactions?.length || 0}</span>
              <span><small>Description</small>{sim.description}</span>
            </div>
          </section>
        ))
      ) : (
        <>
          <section className="job-card active-job">
            <div className="job-row"><span className="pill">Active</span><span>ID: MD-2049-A</span><strong>72%</strong></div>
            <h2>Molecular Dynamics Simulation</h2>
            <div className="progress"><i style={{ width: '72%' }} /></div>
            <div className="job-meta">
              <span><small>Model</small>GPT-4-Res</span>
              <span><small>Threads</small>16 Core</span>
              <span><small>Source</small>ArXiv Corpus</span>
              <span><small>Compute Node</small>Theta-04</span>
            </div>
          </section>
          <section className="job-card warning-job">
            <div className="job-row"><span className="pill warning">Warning</span><strong>41%</strong></div>
            <h2>Protein Structure Prediction</h2>
            <div className="progress warning"><i style={{ width: '41%' }} /></div>
            <div className="job-meta compact">
              <span><small>Model</small>AlphaFold-v2</span>
              <span><small>Memory</small>98% Utilization</span>
            </div>
          </section>
        </>
      )}

      <section className="panel-card">
        <div className="section-title">Queue <span>3 Pending</span></div>
        {['Quantum Circuit Optimization', 'Material Synthesis Analysis', 'Catalyst Reaction Scan'].map((item, index) => (
          <div className="queue-item" key={item}>
            <b>◷</b>
            <span>{item}<small>ID: Q-{index + 1}01 | Priority: {index === 0 ? 'High' : 'Normal'}</small></span>
          </div>
        ))}
      </section>
    </main>
  )
}

export default SimulationBatch
