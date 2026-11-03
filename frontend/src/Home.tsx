import { useEffect, useRef, useState } from 'react'
import { go, startUpload, VIDEO_ACCEPT } from './routing'
import { listScans, listExamples, runExample, newUploadKey, fileUrl, ROOM_LABELS, type ScanRow, type Example } from './api'

export default function Home() {
  const [scans, setScans] = useState<ScanRow[]>([])
  const [examples, setExamples] = useState<Example[]>([])
  const [error, setError] = useState('')
  const [runError, setRunError] = useState('')
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
    setBusy(true); setRunError('')
    keys.current[id] ??= newUploadKey()
    try { go(`scan/${await runExample(id, keys.current[id])}`) }
    catch (e) { setRunError((e as Error).message); setBusy(false) }
  }
  const sample = examples[0]

  return <main className="page wide">
    <header className="topbar">
      <a className="brand" href="#/"><img src="/favicon.svg" alt="" width={28} height={28} /><strong>RiskLens</strong></a>
      {sample && <a href={`#/scan/${sample.scan_id}`}>View sample report</a>}
    </header>

    <section className="task" aria-labelledby="task-title">
      <div>
        <h1 id="task-title">Check a room for earthquake hazards</h1>
        <p className="lead">Film a room for 30–60 seconds. RiskLens points out items that could fall, tip over or block your way out, shows the frame it is based on, and links each next step to FEMA guidance.</p>
      </div>
      <div className="card task-panel">
        <button className="primary" onClick={() => go('capture')}>Record a room</button>
        <label className="secondary file">Upload a video
          <input className="visually-hidden" type="file" accept={VIDEO_ACCEPT} aria-label="Upload a video from this device"
            onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) startUpload(f) }} /></label>
        <p className="task-meta">Results in about 2–3 minutes · video only, microphone optional · a visual screening, not a building inspection.</p>
      </div>
    </section>

    {error && <p className="error" role="alert">{error}</p>}

    {scans.length > 0 && <section className="section" aria-labelledby="scans-title"><h2 id="scans-title">Your scans</h2><ul className="scan-list">
      {scans.map((s) => <li key={s.scan_id}><button className="row" onClick={() => go(`scan/${s.scan_id}`)}>
        <span className="grow"><strong>{ROOM_LABELS[s.room] ?? s.room}</strong>
          <small>{s.hazards} findings · {s.counts.high} high priority · {s.counts.needs_check} need checking</small>
          <small>{s.assessment_status.replaceAll('_', ' ')} · {new Date(s.created_at).toLocaleString()}</small></span><span aria-hidden>›</span>
      </button></li>)}
    </ul></section>}

    <section className="section" aria-labelledby="how-title">
      <h2 id="how-title">How it works</h2>
      <ol className="steps">
        <li><div><h3>Film the room</h3><p>Pan slowly from the door. Include tall furniture, shelves and the wall above beds.</p></div></li>
        <li><div><h3>Meta models find and track objects</h3><p>Muse Spark chooses what to look at; SAM 3.1 follows each object through the video.</p></div></li>
        <li><div><h3>Review the evidence</h3><p>Each finding shows its frame, what is still unknown, and next steps linked to FEMA E-74.</p></div></li>
      </ol>
    </section>

    {sample && <section className="section" aria-labelledby="sample-title">
      <h2 id="sample-title">Try it without filming your home</h2>
      <div className="card sample">
        <img src={fileUrl(sample.scan_id, 'evidence/h1.jpg')} alt="Evidence frame from the sample report: a synthetic bedroom" loading="lazy" />
        <div className="sample-body">
          <h3>{sample.title}</h3>
          <p className="muted">{sample.description}</p>
          <div className="actions">
            <button className="secondary" onClick={() => go(`scan/${sample.scan_id}`)}>Open sample report</button>
            <button className="link-button" disabled={busy} onClick={() => void tryExample(sample.id)}>{busy ? 'Starting…' : 'Run the sample analysis (~2–3 min)'}</button>
          </div>
          {runError && <p className="error" role="alert">{runError} The sample report still opens without any model calls.</p>}
          <p className="fine">The report opens instantly with no new model calls; running the analysis starts a fresh Meta model run, so findings can differ. {sample.synthetic && 'Synthetic scene, not a real household. '}<a href={sample.source_url} target="_blank" rel="noreferrer">{sample.license}</a></p>
        </div>
      </div>
    </section>}

    <footer className="footer">
      <ul className="facts">
        <li>Your scans are private to this browser; a link alone does not give anyone access.</li>
        <li>Videos are kept for 7 days and reports for 30 days. You can delete a scan at any time.</li>
        <li>Findings are model-generated and need checking; hidden attachments are reported as unknown.</li>
      </ul>
      <details><summary>Privacy and data details</summary>
        <p className="fine">Private scans belong to this browser session. Clearing cookies removes access; links alone do not grant access. Source video and extracted frames are retained for 7 days, reports and evidence for 30 days. Expired content becomes inaccessible; physical cleanup runs hourly while the service is active and on startup. Meta AI models process uploaded video remotely.</p>
        <p className="fine">RiskLens is a visual screening prototype, not a building inspection or installation certificate. Real-world physical-change validation is still pending.</p>
      </details>
      <p className="fine">Release {import.meta.env.VITE_RISKLENS_VERSION ?? 'development'}</p>
    </footer>
  </main>
}
