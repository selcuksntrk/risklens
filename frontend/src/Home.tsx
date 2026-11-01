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
      <h2>Find visible earthquake hazards. Take action. Document the change.</h2>
      <p>Film one room to screen for objects that could fall, tip or obstruct an exit. Get source-linked precautions and re-film to compare visible changes.</p>
      <button className="primary big" onClick={() => go('capture')}>Scan your room</button>
      <p className="fine">Visual screening of sampled views, not a building inspection or installation safety certificate.</p>
      <p className="fine">In a study of New Zealand commercial buildings during 2010–2014 earthquakes, 556 of 947 injuries were attributed to non-structural damage. <a href="https://doi.org/10.1177/8755293019900775" target="_blank" rel="noreferrer">Yeow et al., 2020</a>.</p>
    </section>
    {error && <p className="error" role="alert">{error}</p>}
    {examples.map((e) => <section className="hero" key={e.id}>
      <h3>{e.title}</h3><p>{e.description}</p>
      <div className="actions"><button className="ghost" onClick={() => go(`scan/${e.scan_id}`)}>View a completed example</button>
        <button className="primary" disabled={busy} onClick={() => void tryExample(e.id)}>{busy ? 'Starting…' : 'Try a live sample'}</button></div>
      <p className="fine">Completed example: previously computed. Live sample: a new Meta model run. {e.synthetic && 'Synthetic scene, not a real household or a physical fix.'} <a href={e.source_url} target="_blank" rel="noreferrer">{e.license}</a></p>
    </section>)}
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
