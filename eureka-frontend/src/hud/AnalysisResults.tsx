import { useEffect, useState } from 'react'
import { fetchPapersFromAPI } from '../neural/DataRelay'

interface ResultsScreenProps {
  query?: string
  activeObject?: any
}

function AnalysisResults({ query, activeObject }: ResultsScreenProps) {
  const [paperList, setPaperList] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedIdx, setSelectedIdx] = useState(0)

  const searchTerm = activeObject?.name || query || 'Quantum computing'

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      const data = await fetchPapersFromAPI(searchTerm)
      if (active) {
        setPaperList(data)
        setSelectedIdx(0)
        setLoading(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [searchTerm])

  const selectedPaper = paperList[selectedIdx]

  return (
    <main className="results-screen">
      <section className="hero-copy compact-hero">
        <h1>Research Results</h1>
        <p>Fetch source: Wikipedia / ArXiv database // query: "{searchTerm}"</p>
      </section>
      {loading ? (
        <section className="paper-list" style={{ gridColumn: 'span 2' }}>
          <p>Querying scientific databases for "{searchTerm}"...</p>
        </section>
      ) : (
        <>
          <section className="paper-list">
            {paperList.map((paper, index) => (
              <article
                className={selectedIdx === index ? 'paper-card selected' : 'paper-card'}
                key={index}
                onClick={() => setSelectedIdx(index)}
                style={{ cursor: 'pointer' }}
              >
                <div><span>ID: P-{index + 43}</span><span>Relevance: {paper.relevance}%</span></div>
                <h2>{paper.title}</h2>
                <p>Authors: {paper.authors}</p>
              </article>
            ))}
          </section>
          {selectedPaper && (
            <section className="analysis-card">
              <p className="eyebrow">Document Analysis ● Live Sync</p>
              <h2>{selectedPaper.title}</h2>
              <p className="summary">
                Summary for {searchTerm}: Paper discusses various structural and behavioral properties. Key metrics show high correlation with expected baseline values.
              </p>
              <div className="insight-list">
                <span><b>◇ Main Topic:</b> Found matches for {searchTerm}.</span>
                <span><b>△ Methods:</b> Standard empirical validation.</span>
                <span><b>⌁ Relevance:</b> Rated at {selectedPaper.relevance}% score.</span>
              </div>
              <div className="button-row">
                <button className="ghost-button">Save to Pipeline</button>
                <button className="primary-button">Visualize in 3D</button>
              </div>
            </section>
          )}
        </>
      )}
    </main>
  )
}

export default AnalysisResults
