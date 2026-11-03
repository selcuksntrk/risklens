import { useEffect, useRef, useState } from 'react'
import { go } from './routing'
import { listScans, listExamples, runExample, newUploadKey, ROOM_LABELS, type ScanRow, type Example } from './api'

export default function Home() {
  const [scans, setScans] = useState<ScanRow[]>([])
  const [examples, setExamples] = useState<Example[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const keys = useRef<Record<string, string>>({})
  useEffect(() => {
    let active = true
    Promise.all([listScans(), listExamples()]).then(([s, e]) => { if (active) { setScans(s); setExamples(e) } })
      .catch((e) => { if (active) setError((e as Error).message) })
    return () => { active = false }
  }, [])
  async function tryExample(id: string) {
    if (busy) return
    setBusy(true); setError('')
    keys.current[id] ??= newUploadKey()
    try { go(`scan/${await runExample(id, keys.current[id])}`) }
    catch (e) { setError((e as Error).message); setBusy(false) }
  }
  return <main className="page">
    <header className="brand"><img src="/favicon.svg" alt="" width={36} height={36} /><h1>RiskLens</h1></header>
    <section className="hero">
      <span className="eyebrow">Earthquake preparedness · Build for Your World</span>
      <h2>A visible finding. The evidence. A practical next step.</h2>
      <p>RiskLens connects sampled room views to tracked objects and source-linked precautions. When a detail is unclear, it asks for better evidence.</p>
      <p className="fine">Visual screening prototype, not a building inspection or installation certificate. Real-world physical-change validation is still pending.</p>
    </section>
    {error && <p className="error" role="alert">{error}</p>}
    {examples.map((e) => <section className="hero" key={e.id}>
      <span className="eyebrow">Explore without recording your home</span>
      <h3>{e.title}</h3><p>{e.description}</p>
      <div className="actions"><button className="primary" onClick={() => go(`scan/${e.scan_id}`)}>Open completed report</button>
        <button className="ghost" disabled={busy} onClick={() => void tryExample(e.id)}>{busy ? 'Starting…' : 'Run sample with Meta AI'}</button></div>
      <p className="fine">Completed report: opens immediately, no model calls. Run sample: starts a new analysis; findings and waiting time can vary.</p>
      <p className="fine">{e.synthetic && 'Synthetic scene, not a real household or a physical fix. '}<a href={e.source_url} target="_blank" rel="noreferrer">{e.license}</a></p>
    </section>)}
    <section className="notice"><h3>How the evidence is built</h3><p>Muse Spark selects objects and reviews their visible relationships. SAM 3.1 tracks them through the clip. Recommendations link to FEMA E-74 sections actually read by the model.</p>
      <button className="ghost" onClick={() => go('capture')}>Use your own video</button>
      <p className="fine privacy-note">Your own recording is optional. The public demo uses licensed synthetic footage.</p></section>
    {scans.length > 0 && <section><h3>Your scans in this browser</h3><ul className="scan-list">
      {scans.map((s) => <li key={s.scan_id}><button className="row" onClick={() => go(`scan/${s.scan_id}`)}>
        <span className="grow"><strong>{ROOM_LABELS[s.room] ?? s.room}</strong>
          <small>{s.hazards} findings · {s.counts.high} high priority · {s.counts.needs_check} need checking</small>
          <small>{s.assessment_status.replaceAll('_', ' ')} · {new Date(s.created_at).toLocaleString()}</small></span><span aria-hidden>›</span>
      </button></li>)}
    </ul></section>}
    <p className="fine">Release {import.meta.env.VITE_RISKLENS_VERSION ?? 'development'}</p>
    <p className="fine privacy-note">Private scans belong to this browser session. Clearing cookies removes access; links alone do not grant access. You can delete your scans. Source video and extracted frames are retained for 7 days, reports and evidence for 30 days. Expired content becomes inaccessible; physical cleanup runs hourly while the service is active and on startup.</p>
  </main>
}
