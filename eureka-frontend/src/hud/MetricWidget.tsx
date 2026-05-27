function MetricWidget({ label, value, detail, tone = 'cyan' }: { label: string; value: string; detail: string; tone?: 'cyan' | 'pink' | 'green' }) {
  return (
    <section className={`metric-card tone-${tone}`}>
      <div className="metric-label">{label}</div>
      <strong>{value}</strong>
      <span>{detail}</span>
    </section>
  )
}

export default MetricWidget
