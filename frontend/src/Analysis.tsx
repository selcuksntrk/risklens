import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { fileUrl, ROOM_LABELS, RELATION_LABELS, type Hazard, type PartialReport, type TimelineEvent } from './api'
import { MODELS, STAGES } from './ui'

interface StageProps {
  events: TimelineEvent[]
  scanId: string
  elapsed: number
  title?: string
  banner?: ReactNode
  partial?: PartialReport | null
  subtitle?: string
}

/** Dark "lens" stage: the Meta pipeline made visible, live or replayed from a recorded run. */
export default function Stage({ events, scanId, elapsed, title = 'Analysing your room', banner, partial,
  subtitle = 'Typically 2–3 minutes. You can leave this page; the analysis keeps running.' }: StageProps) {
  const find = (step: string) => events.find((e) => e.step === step)
  const ingest = find('ingest.done'), planner = find('planner.done'), marks = find('marks.done')
  const surveyor = find('surveyor.done'), ready = find('findings.ready'), fixer = find('fixer.done')
  const sam = new Map<string, { done: boolean; objects?: number; error?: boolean }>()
  for (const e of events) {
    if (e.step === 'sam.start') sam.set(String(e.concept), { done: false })
    if (e.step === 'sam.done') sam.set(String(e.concept), { done: true, objects: Number(e.objects), error: e.status !== 'completed' })
  }
  const done = { ingest: !!ingest, planner: !!planner, sam: !!marks, surveyor: !!surveyor, fixer: !!fixer }
  const active = STAGES.find((s) => !done[s.key])?.key
  const images = (marks?.images as string[] | undefined) ?? []
  const provisional = ((ready?.findings as PartialReport | undefined) ?? partial)?.hazards ?? []
  const objects = sam.size ? [...sam.values()].reduce((n, s) => n + (s.objects ?? 0), 0) : 0
  const lastT = events.reduce((m, e) => Math.max(m, Number(e.t) || 0), 0)
  const shown = Math.max(elapsed, lastT)

  return <section className="stage" aria-live="polite" aria-busy={!fixer}>
    <div className="stage-head">
      <div><h1>{title}</h1><p>{subtitle}</p></div>
      <span className="timer" aria-label={`Elapsed ${Math.round(shown)} seconds`}>{Math.floor(shown / 60)}:{String(Math.floor(shown % 60)).padStart(2, '0')}</span>
    </div>
    {banner}
    <ol className="stepper" aria-label="Analysis stages">
      {STAGES.map((s) => <li key={s.key} className={done[s.key] ? 'done' : active === s.key ? 'active' : ''} aria-current={active === s.key ? 'step' : undefined}>
        <b>{s.label}</b><span className="model">{s.model}</span>
      </li>)}
    </ol>
    <div className="stage-grid">
      <Viewer images={images} scanId={scanId} sampling={!!ingest && !marks} keyframes={(ingest?.keyframes as number[] | undefined)?.length} />
      <div className="log">
        {ingest && <div className="log-item"><h3>Video prepared</h3>
          <p>{String(ingest.duration_s)} s · {(ingest.keyframes as number[] | undefined)?.length ?? '?'} keyframes sampled for the models</p></div>}
        {planner && <div className="log-item"><h3>Planner agent <span className="tag">{MODELS.spark}</span></h3>
          <p>Looks like a {ROOM_LABELS[String(planner.room_type)]?.toLowerCase() ?? 'room'}. Chose what to track:</p>
          <div className="chips" style={{ marginTop: 8 }}>{(planner.concepts as string[] | undefined ?? []).map((c) => <span key={c} className="chip">{c}</span>)}</div>
          <Reasoning lines={planner.reasoning_summary as string[]} /></div>}
        {sam.size > 0 && <div className="log-item"><h3>Tracking through the video <span className="tag">{MODELS.sam}</span></h3>
          <div className="chips">{[...sam].map(([concept, s]) => <span key={concept} className={`chip ${s.done ? (s.error ? 'pending' : s.objects ? 'hit' : '') : 'pending'}`}>
            {concept}{s.done ? s.error ? ' · error' : ` · ${s.objects}` : ' …'}</span>)}</div>
          {marks && <p style={{ marginTop: 8 }}>{objects} objects tracked · each finding will point to an exact frame and box</p>}</div>}
        {marks && !surveyor && <div className="log-item wait"><h3>Surveyor agent <span className="tag">{MODELS.spark}</span></h3><p>Reasoning about what could fall, tip over, break or block the way out…</p></div>}
        {surveyor && <div className="log-item"><h3>Surveyor agent <span className="tag">{MODELS.spark}</span></h3>
          <p>{String(surveyor.hazards)} findings, each tied to a marked frame</p>
          {provisional.length > 0 && <ul className="provisional" style={{ marginTop: 8 }}>{provisional.map((h: Hazard) =>
            <li key={h.id}><span className={`sev ${h.severity}`} aria-hidden /><span><b>{h.object}</b> · {RELATION_LABELS[h.relation] ?? h.relation}</span></li>)}</ul>}
          <Reasoning lines={surveyor.reasoning_summary as string[]} /></div>}
        {surveyor && !fixer && <div className="log-item wait"><h3>Fix planner <span className="tag">{MODELS.spark}</span> <span className="tag">FEMA E-74</span></h3><p>Looking up FEMA E-74 guidance for each finding…</p></div>}
        {fixer && <div className="log-item"><h3>Fix planner <span className="tag">{MODELS.spark}</span> <span className="tag">FEMA E-74</span></h3>
          <p>Read FEMA E-74 sections {(fixer.fema_lookups as string[][] | undefined ?? []).flat().join(', ')}</p></div>}
        {!ingest && <div className="log-item wait"><h3>Preparing video</h3><p>Checking the file and sampling keyframes…</p></div>}
      </div>
    </div>
  </section>
}

function Reasoning({ lines }: { lines?: string[] }) {
  if (!lines?.length) return null
  return <details style={{ marginTop: 8 }}><summary className="fine" style={{ minHeight: 36 }}>Reasoning summary</summary>
    <ul>{lines.slice(0, 4).map((l, i) => <li key={i}>{l}</li>)}</ul></details>
}

function Viewer({ images, scanId, sampling, keyframes }: { images: string[]; scanId: string; sampling: boolean; keyframes?: number }) {
  const [index, setIndex] = useState(0)
  const [pinned, setPinned] = useState(false)
  useEffect(() => {
    if (images.length < 2 || pinned) return
    const timer = window.setInterval(() => setIndex((i) => (i + 1) % images.length), 1800)
    return () => window.clearInterval(timer)
  }, [images.length, pinned])
  const urls = useMemo(() => images.map((p) => fileUrl(scanId, p)), [images, scanId])
  return <div>
    <div className="viewer">
      <div className="grid-overlay" />
      {urls.map((u, i) => <img key={u} src={u} className={i === index % urls.length ? 'on' : ''} alt={i === index % urls.length ? `Keyframe ${i + 1} of ${urls.length} with tracked objects marked by SAM 3.1` : ''} />)}
      {!urls.length && <div className="placeholder"><div><div className="ring" />{sampling ? `Muse Spark is reviewing ${keyframes ?? 'the'} keyframes; SAM 3.1 will mark tracked objects here.` : 'Preparing the video…'}</div></div>}
      {urls.length > 0 && <span className="viewer-label">Keyframe {index % urls.length + 1}/{urls.length} · tracked by {MODELS.sam}</span>}
    </div>
    {urls.length > 1 && <div className="thumbs" role="tablist" aria-label="Keyframes">{urls.map((u, i) =>
      <button key={u} role="tab" aria-selected={i === index % urls.length} aria-label={`Keyframe ${i + 1}`} className={i === index % urls.length ? 'on' : ''} onClick={() => { setIndex(i); setPinned(true) }}><img src={u} alt="" /></button>)}</div>}
  </div>
}
