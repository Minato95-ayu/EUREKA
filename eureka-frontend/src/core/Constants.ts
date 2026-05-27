import type { Tab } from '../core/EurekaTypes'

export const tabs: Array<{ id: Tab; label: string; icon: string }> = [
  { id: 'status', label: 'Status', icon: '▦' },
  { id: 'batch', label: 'Batch', icon: '▷' },
  { id: 'pipeline', label: 'Pipeline', icon: '⌬' },
  { id: 'research', label: 'Research', icon: '▣' },
  { id: 'results', label: 'Results', icon: '▤' }
]

export const logs = [
  '[SYSTEM INIT] telemetry stream stable',
  '> Connecting to instance alpha-node-01... [OK]',
  '[10:42:01] FETCHING: ArXiv/Quantum_Computing',
  '[10:42:04] PARSING: metadata and abstracts',
  '[10:42:08] WARN: rate limit approaching',
  '[10:42:15] PROCESSING: Neural_Network_Model',
  '[10:42:18] SUCCESS: vectors indexed',
  '> Awaiting input'
]

export const papers = [
  {
    title: 'Emergent Behaviors in Large-Scale Multi-Agent Reinforcement Learning Environments',
    authors: 'D. Evans, S. Chen, M. Botava',
    relevance: 98
  },
  {
    title: 'Optimizing Latent Space Representations for Zero-Shot Anomaly Detection',
    authors: 'A. Kim, L. Thorne',
    relevance: 86
  },
  {
    title: 'Neuromorphic Hardware Substrates for Energy-Efficient Edge Inference',
    authors: 'A. Patel, J. Zhang, W. Brooks',
    relevance: 72
  }
]
