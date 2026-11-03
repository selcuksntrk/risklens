import { useEffect, useRef, useState } from 'react'
import { go, startUpload, VIDEO_ACCEPT } from './routing'
import { listScans, listExamples, runExample, newUploadKey, exampleMedia, ROOM_LABELS, RELATION_LABELS, type ScanRow, type Example } from './api'
import { Logo } from './components'
import { MODELS, fmtSeconds } from './ui'

const REPO = 'https://github.com/selcuksntrk/risklens'

export default function Home() {
  const [scans, setScans] = useState<ScanRow[]>([])
  const [examples, setExamples] = useState<Example[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    Promise.all([listScans(), listExamples()]).then(([s, e]) => { if (active) { setScans(s); setExamples(e) } })
      .catch((e) => { if (active) setError((e as Error).message) })
    return () => { active = false }
  }, [])
  const real = examples.find((e) => e.kind === 'real') ?? examples[0]

  return <main className="page wide">
    <header className="topbar">
      <Logo />
      <nav className="nav" aria-label="Main">
        <a href="#/" onClick={(e) => { e.preventDefault(); document.getElementById('samples')?.scrollIntoView({ behavior: 'smooth' }) }}>Samples</a>
        <a className="hide-sm" href="#/" onClick={(e) => { e.preventDefault(); document.getElementById('how')?.scrollIntoView({ behavior: 'smooth' }) }}>How it works</a>
        <a className="hide-sm" href={REPO} target="_blank" rel="noreferrer">GitHub</a>
      </nav>
    </header>

    <section className="hero" aria-labelledby="hero-title">
      <div>
        <span className="eyebrow">Earthquake preparedness · one room at a time</span>
        <h1 id="hero-title">See what could fall before the ground shakes.</h1>
        <p className="lead">Film a room for 30–60 seconds. <strong>Muse Spark</strong> decides what to look at, <strong>SAM 3.1</strong> tracks each object through your video, and every finding shows the exact frame it is based on, what is still unknown, and next steps linked to FEMA guidance.</p>
        <div className="hero-cta">
          <button className="primary" onClick={() => go('capture')}>Record a room</button>
          <label className="secondary file">Upload a video
            <input className="visually-hidden" type="file" accept={VIDEO_ACCEPT} aria-label="Upload a video from this device"
              onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) startUpload(f) }} /></label>
        </div>
        <ul className="hero-meta"><li>Results in 2–3 minutes</li><li>Private to this browser</li><li>No account</li></ul>
      </div>
      {real && <HeroLens example={real} />}
    </section>

    {error && <p className="error" role="alert">{error}</p>}

    {scans.length > 0 && <section className="section" aria-labelledby="scans-title"><div className="section-head"><h2 id="scans-title">Your scans</h2></div><ul className="scan-list">
      {scans.map((s) => <li key={s.scan_id}><button className="row" onClick={() => go(`scan/${s.scan_id}`)}>
        <span className="grow"><strong>{ROOM_LABELS[s.room] ?? s.room}</strong>
          <small>{s.hazards} findings · {s.counts.high} high priority · {s.counts.needs_check} need checking</small>
          <small>{s.assessment_status.replaceAll('_', ' ')} · {new Date(s.created_at).toLocaleString()}</small></span><span aria-hidden>›</span>
      </button></li>)}
    </ul></section>}

    {examples.length > 0 && <section className="section" id="samples" aria-labelledby="samples-title">
      <div className="section-head"><div><h2 id="samples-title">Try it without filming your home</h2>
        <p>One real home and three designed scenes. Reports open instantly with no new model calls; each replay shows the recorded run of the Meta models.</p></div></div>
      <div className="samples">{examples.map((e, i) => <SampleCard key={e.id} example={e} featured={i === 0 && e.kind === 'real'} />)}</div>
    </section>}

    <section className="section" id="how" aria-labelledby="how-title">
      <div className="section-head"><div><h2 id="how-title">How it works</h2><p>Three Meta models, each doing the part it is best at, with every claim tied back to evidence.</p></div></div>
      <ol className="pipeline">
        <li><h3>Film one room</h3><span className="pill model">Your phone</span><p>Pan slowly from the door. Include tall furniture, shelves and the wall above beds.</p></li>
        <li><h3>Plan what matters</h3><span className="pill model">{MODELS.spark}</span><p>The planner agent looks at sampled frames and picks the objects worth examining in this room.</p></li>
        <li><h3>Track every object</h3><span className="pill model">{MODELS.sam}</span><p>SAM 3.1 follows each object through the whole video, so findings point to an exact frame and box.</p></li>
        <li><h3>Survey and next steps</h3><span className="pill model">{MODELS.spark} + FEMA E-74</span><p>Separates what is visible from what needs checking, then links next steps to the FEMA sections it read.</p></li>
      </ol>
    </section>

    <section className="section" aria-labelledby="scope-title">
      <h2 id="scope-title" className="visually-hidden">What RiskLens is and is not</h2>
      <div className="scope">
        <div><h3>What RiskLens does</h3><ul>
          <li>Screens visible contents: furniture, shelves, glass, hanging items and exit paths</li>
          <li>Shows the frame and box behind every finding</li>
          <li>Says what it cannot see, like hidden wall anchors</li>
          <li>Lets you re-film one item to compare a visible change</li></ul></div>
        <div><h3>What it is not</h3><ul>
          <li>Not a building or structural inspection</li>
          <li>Not proof that anything is safely installed</li>
          <li>Not expert-reviewed: findings are model-generated</li>
          <li>Not a full-room guarantee: unseen areas remain unknown</li></ul></div>
      </div>
    </section>

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
      <p className="fine">Built for the Meta AI Developer Hackathon · <a href={REPO} target="_blank" rel="noreferrer">Source code</a> · Release {import.meta.env.VITE_RISKLENS_VERSION ?? 'development'}</p>
    </footer>
  </main>
}

function HeroLens({ example }: { example: Example }) {
  const top = example.top_finding
  return <figure className="lens-figure">
    {example.has_poster && <img src={exampleMedia(example.id, 'poster.jpg')} alt={`Evidence frame from ${example.title.toLowerCase()}${top ? `: ${top.object}` : ''}, marked by SAM 3.1`} />}
    <div className="scanline" aria-hidden />
    <span className="corner tl" aria-hidden /><span className="corner tr" aria-hidden />
    <span className="rec" aria-hidden>LENS</span>
    <figcaption className="lens-caption">
      {top && <span className="finding-chip"><span className="dot" aria-hidden />{top.object} <span className="muted" style={{ color: 'rgb(255 255 255 / .8)' }}>· {top.severity} priority</span></span>}
      <small>{example.kind === 'real' ? 'Real scan of the author’s home, Istanbul · photos blurred' : example.title}</small>
    </figcaption>
  </figure>
}

function SampleCard({ example, featured }: { example: Example; featured: boolean }) {
  const [busy, setBusy] = useState(false)
  const [runError, setRunError] = useState('')
  const key = useRef<string | null>(null)
  async function runLive() {
    if (busy) return
    setBusy(true); setRunError('')
    key.current ??= newUploadKey()
    try { go(`scan/${await runExample(example.id, key.current)}`) }
    catch (e) { setRunError((e as Error).message); setBusy(false) }
  }
  const counts = example.counts
  const answer = example.answer_key
  return <article className={`sample-card sample${featured ? ' featured' : ''}`} aria-labelledby={`s-${example.id}`}>
    <div className="sample-media">
      {example.has_poster && <img src={exampleMedia(example.id, 'poster.jpg')} alt="" loading={featured ? 'eager' : 'lazy'} />}
      <span className={`pill ${example.synthetic ? 'synthetic' : 'real'}`}>{example.synthetic ? 'AI-generated scene' : 'Real home · Istanbul'}</span>
      {example.duration_s ? <span className="duration">{fmtSeconds(example.duration_s)} video</span> : null}
    </div>
    <div className="sample-body">
      <span className="eyebrow">{ROOM_LABELS[example.room ?? ''] ?? 'Room'}</span>
      <h3 id={`s-${example.id}`}>{example.title}</h3>
      <p>{example.description}</p>
      {counts && <div className="counts">
        {counts.high > 0 && <span className="badge high">{counts.high} high</span>}
        {counts.medium > 0 && <span className="badge medium">{counts.medium} medium</span>}
        {counts.low > 0 && <span className="badge low">{counts.low} low</span>}
        {counts.needs_check > 0 && <span className="status needs_check">{counts.needs_check} to check</span>}
      </div>}
      {answer && <span className="answer-line">Answer key: {answer.matched} of {answer.designed} designed hazards matched</span>}
      {featured && example.top_finding && <p>Top finding: <b>{example.top_finding.object}</b> · {RELATION_LABELS[example.top_finding.relation]?.toLowerCase()}</p>}
      <div className="sample-actions">
        <button className="primary" onClick={() => go(`scan/${example.scan_id}`)}>Open report</button>
        {example.has_replay && <button className="secondary" onClick={() => go(`replay/${example.id}`)}>Watch analysis replay</button>}
      </div>
      <button className="link-button" disabled={busy} onClick={() => void runLive()}>{busy ? 'Starting…' : 'Run it live (~2–3 min, new model run)'}</button>
      {runError && <p className="error" role="alert">{runError} The sample report still opens without any model calls.</p>}
      <p className="fine">{example.license}{example.source_url && <> · <a href={example.source_url} target="_blank" rel="noreferrer">Source</a></>}</p>
    </div>
  </article>
}
