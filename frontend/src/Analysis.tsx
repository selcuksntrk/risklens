import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { fileUrl, ROOM_LABELS, type Hazard, type PartialReport, type TimelineEvent } from './api'
import { Fold, Severity } from './components'
import { MODELS, STAGES, cap } from './ui'

interface StageProps {
  events: TimelineEvent[]
  scanId: string
  elapsed: number
  title?: string
  subtitle?: string
  banner?: ReactNode
  partial?: PartialReport | null
}

/** Progress of a scan in plain words: one picture, one sentence about what is happening now, details on request. */
export default function Stage({ events, scanId, elapsed, banner, partial, title = 'Looking at your room',
  subtitle = 'This usually takes 2–3 minutes. You can close this page; the report will be here when you come back.' }: StageProps) {
  const find = (step: string) => events.find((e) => e.step === step)
  const ingest = find('ingest.done'), planner = find('planner.done'), marks = find('marks.done')
  const surveyor = find('surveyor.done'), ready = find('findings.ready'), fixer = find('fixer.done')
  const concepts = (planner?.concepts as string[] | undefined) ?? []
  const tracking = events.filter((e) => e.step === 'sam.done')
  const tracked = Object.keys((marks?.objects as Record<string, string> | undefined) ?? {}).length
  const done = { ingest: !!ingest, planner: !!planner, sam: !!marks, surveyor: !!surveyor, fixer: !!fixer }
  const active = STAGES.find((s) => !done[s.key])?.key
  const found: Hazard[] = ((ready?.findings as PartialReport | undefined) ?? partial)?.hazards ?? []
  const lastT = events.reduce((m, e) => Math.max(m, Number(e.t) || 0), 0)
  const shown = Math.max(elapsed, lastT)
  const room = ROOM_LABELS[String(planner?.room_type)]?.toLowerCase()

  const result: Record<string, string> = {
    ingest: ingest ? `${String(ingest.duration_s)} s of video, ${(ingest.keyframes as number[] | undefined)?.length ?? 'a few'} still frames` : '',
    planner: planner ? `Looks like a ${room ?? 'room'}. Watching: ${concepts.slice(0, 6).join(', ')}` : '',
    sam: marks ? `${tracked} objects followed` : tracking.length ? `${tracking.length} of ${concepts.length || '?'} kinds of object done` : '',
    surveyor: surveyor ? `${String(surveyor.hazards)} things to check` : '',
    fixer: fixer ? 'Done' : '',
  }
  const now = !ingest ? 'Getting your video ready…'
    : !planner ? `${MODELS.spark} is studying the still frames to decide what matters in this room…`
    : !marks ? `${MODELS.sam} is following ${concepts.length ? concepts.slice(0, 3).join(', ') : 'each object'} through your video…`
    : !surveyor ? `${MODELS.spark} is checking what could fall, tip over or block the way out…`
    : !fixer ? 'Looking up FEMA guidance for each item…'
    : 'Done. Opening your report…'

  return <section aria-live="polite" aria-busy={!fixer}>
    <h1>{title}</h1>
    <p className="muted">{subtitle}</p>
    {banner}
    <Frame images={(marks?.images as string[] | undefined) ?? []} scanId={scanId} />
    <p className="now">{now} <span className="timer">{Math.floor(shown / 60)}:{String(Math.floor(shown % 60)).padStart(2, '0')}</span></p>
    {found.length > 0 && <><b>Found so far</b><ul className="found">{found.map((h) => <li key={h.id}><Severity severity={h.severity} /> {cap(h.object)}</li>)}</ul></>}
    <ol className="progress" aria-label="Steps">
      {STAGES.map((s) => <li key={s.key} className={done[s.key] ? 'done' : active === s.key ? 'active' : ''} aria-current={active === s.key ? 'step' : undefined}>
        <span>{s.label}<small>{result[s.key] || s.model}</small></span></li>)}
    </ol>
    {(planner || surveyor || fixer) && <Fold title="What the models said">
      {planner && <><p><b>{MODELS.spark}, planning</b></p><Summary lines={planner.reasoning_summary as string[]} /></>}
      {tracking.length > 0 && <p><b>{MODELS.sam}</b>: {tracking.map((e) => `${String(e.concept)} (${String(e.objects)})`).join(', ')}</p>}
      {surveyor && <><p><b>{MODELS.spark}, checking</b></p><Summary lines={surveyor.reasoning_summary as string[]} /></>}
      {fixer && <p><b>FEMA E-74 sections read</b>: {(fixer.fema_lookups as string[][] | undefined ?? []).flat().join(', ')}</p>}
    </Fold>}
  </section>
}

function Summary({ lines }: { lines?: string[] }) {
  if (!lines?.length) return null
  return <ul className="fine">{lines.slice(0, 4).map((l, i) => <li key={i}>{l}</li>)}</ul>
}

function Frame({ images, scanId }: { images: string[]; scanId: string }) {
  const [index, setIndex] = useState(0)
  useEffect(() => {
    if (images.length < 2) return
    const timer = window.setInterval(() => setIndex((i) => (i + 1) % images.length), 1800)
    return () => window.clearInterval(timer)
  }, [images.length])
  const urls = useMemo(() => images.map((p) => fileUrl(scanId, p)), [images, scanId])
  const on = urls.length ? index % urls.length : 0
  return <div className="frame">
    {urls.map((u, i) => <img key={u} src={u} className={i === on ? 'on' : ''} alt={i === on ? `Frame ${i + 1} of ${urls.length}, with the objects SAM 3.1 is following boxed` : ''} />)}
    {!urls.length && <div className="empty">The boxed frames will appear here once {MODELS.sam} has followed the objects.</div>}
    {urls.length > 0 && <span className="caption">Frame {on + 1} of {urls.length} · boxes by {MODELS.sam}</span>}
  </div>
}
