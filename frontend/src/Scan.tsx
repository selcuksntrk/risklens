import { useEffect, useState } from 'react'
import { go } from './App'
import { fileUrl, getScan, makeFixCard, RELATION_LABELS, ROOM_LABELS, type Fix, type Hazard, type Report, type TimelineEvent } from './api'

export function riskBand(score: number) {
  if (score >= 70) return { label: 'High risk', cls: 'high' }
  if (score >= 35) return { label: 'Medium risk', cls: 'medium' }
  return { label: 'Low risk', cls: 'low' }
}

function useScan(scanId: string) {
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [fixcards, setFixcards] = useState<string[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    let source: EventSource | null = null
    let cancelled = false
    const settle = async () => {
      const state = await getScan(scanId)
      if (cancelled) return
      if (state.status === 'done') { setReport(state.report); setFixcards(state.fixcards ?? []) }
      else if (state.status === 'error') setError(state.message)
      return state.status
    }
    settle().then((status) => {
      if (status !== 'running' || cancelled) return
      source = new EventSource(`/api/scans/${scanId}/events`)
      source.onmessage = (e) => {
        const event = JSON.parse(e.data) as TimelineEvent
        setEvents((all) => [...all, event])
        if (event.step === 'error') setError(String(event.message))
      }
      source.addEventListener('end', () => { source?.close(); settle() })
      source.onerror = () => { source?.close(); settle() }
    })
    return () => { cancelled = true; source?.close() }
  }, [scanId])
  return { events, report, fixcards, error }
}

export default function Scan({ scanId }: { scanId: string }) {
  const { events, report, fixcards, error } = useScan(scanId)
  return (
    <main className="page">
      <header className="bar">
        <button className="ghost" onClick={() => go('')}>‹ Scans</button>
        <span className="muted">Scan {scanId.slice(0, 6)}</span>
      </header>
      {error && <p className="error">{error}</p>}
      {!report && <Timeline events={events} scanId={scanId} />}
      {report && <ReportView report={report} fixcards={fixcards} />}
    </main>
  )
}

const MODEL = { spark: 'Muse Spark 1.3', sam: 'SAM 3.1' }

function Timeline({ events, scanId }: { events: TimelineEvent[]; scanId: string }) {
  const find = (step: string) => events.find((e) => e.step === step)
  const ingest = find('ingest.done')
  const planner = find('planner.done')
  const marks = find('marks.done')
  const surveyor = find('surveyor.done')
  const fixer = find('fixer.done')
  const sam = new Map<string, { done: boolean; objects?: number }>()
  for (const e of events) {
    if (e.step === 'sam.start') sam.set(String(e.concept), { done: false })
    if (e.step === 'sam.done') sam.set(String(e.concept), { done: true, objects: Number(e.objects) })
  }
  const step = (done: boolean, active: boolean) => `step ${done ? 'done' : active ? 'active' : ''}`

  return (
    <section className="timeline" aria-live="polite">
      <h2>Surveying your room…</h2>
      <ol>
        <li className={step(!!ingest, !ingest)}>
          <b>Preparing video</b>
          {ingest && <small>{String(ingest.frames)} frames · {String(ingest.duration_s)} s</small>}
        </li>
        <li className={step(!!planner, !!ingest && !planner)}>
          <b>Planner agent</b> <span className="tag">{MODEL.spark}</span>
          {planner && <>
            <small>Looks like a {ROOM_LABELS[String(planner.room_type)]?.toLowerCase() ?? 'room'}. Deciding what to track:</small>
            <Summary lines={planner.reasoning_summary as string[]} />
          </>}
        </li>
        <li className={step(!!marks, !!planner && !marks)}>
          <b>Tracking objects through the video</b> <span className="tag">{MODEL.sam}</span>
          {sam.size > 0 && <div className="chips">
            {[...sam].map(([concept, s]) => (
              <span key={concept} className={`chip ${s.done ? (s.objects ? 'hit' : 'miss') : 'pending'}`}>
                {concept}{s.done ? ` · ${s.objects}` : ' …'}
              </span>
            ))}
          </div>}
          {marks && <div className="strip">
            {(marks.images as string[]).map((p) => <img key={p} src={fileUrl(scanId, p)} alt="Keyframe with tracked objects" />)}
          </div>}
        </li>
        <li className={step(!!surveyor, !!marks && !surveyor)}>
          <b>Surveyor agent</b> <span className="tag">{MODEL.spark}</span>
          {!!marks && !surveyor && <small>Reasoning about what can fall, tip, shatter or block the exit…</small>}
          {surveyor && <>
            <small>{String(surveyor.hazards)} hazards found</small>
            <Summary lines={surveyor.reasoning_summary as string[]} />
          </>}
        </li>
        <li className={step(!!fixer, !!surveyor && !fixer)}>
          <b>Fix planner</b> <span className="tag">{MODEL.spark}</span> <span className="tag">FEMA E-74</span>
          {!!surveyor && !fixer && <small>Looking up FEMA E-74 guidance for each hazard…</small>}
          {fixer && <small>Read FEMA sections {(fixer.fema_lookups as string[][]).flat().join(', ')}</small>}
        </li>
      </ol>
    </section>
  )
}

function Summary({ lines }: { lines?: string[] }) {
  if (!lines?.length) return null
  return <ul className="summary">{lines.slice(0, 3).map((l, i) => <li key={i}>{l}</li>)}</ul>
}

const SEVERITY_ORDER = { high: 0, medium: 1, low: 2 }

function ReportView({ report, fixcards }: { report: Report; fixcards: string[] }) {
  const band = riskBand(report.room.risk_score)
  const hazards = [...report.hazards].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity])
  return (
    <article className="report">
      <section className={`summary-card ${band.cls}`}>
        <div className="gauge"><span>{report.room.risk_score}</span><small>/100</small></div>
        <div>
          <h2>{ROOM_LABELS[report.room.type] ?? 'Room'} · {band.label}</h2>
          <p>{report.room.summary}</p>
        </div>
      </section>
      <h3>{hazards.length} hazard{hazards.length === 1 ? '' : 's'}</h3>
      <ul className="hazards">
        {hazards.map((h) => <HazardCard key={h.id} hazard={h} scanId={report.scan_id} hasCard={fixcards.includes(h.id)} />)}
      </ul>
      <p className="fine">{report.disclaimer}</p>
      <details className="provenance">
        <summary>Audit trail</summary>
        <dl>
          <dt>Models</dt><dd>{Object.entries(report.provenance.models).map(([k, v]) => `${k}: ${v}`).join(' · ')}</dd>
          <dt>Time</dt><dd>{report.seconds} s {report.timings_s && `(${Object.entries(report.timings_s).map(([k, v]) => `${k} ${v}s`).join(', ')})`}</dd>
          <dt>Cost</dt><dd>${report.cost_usd.total.toFixed(3)}</dd>
          <dt>Video SHA-256</dt><dd className="mono">{report.provenance.source_sha256.slice(0, 16)}…</dd>
          <dt>Prompt hashes</dt><dd className="mono">{Object.entries(report.provenance.prompts_sha256).map(([k, v]) => `${k} ${v.slice(0, 8)}`).join(' · ')}</dd>
        </dl>
      </details>
    </article>
  )
}

function HazardCard({ hazard, scanId, hasCard }: { hazard: Hazard; scanId: string; hasCard: boolean }) {
  const [card, setCard] = useState<{ image: string; before: string } | null>(
    hasCard ? { image: `fixcards/${hazard.id}.jpg`, before: `fixcards/${hazard.id}_before.jpg` } : null)
  const [view, setView] = useState<'evidence' | 'before' | 'after'>('evidence')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function showFixed() {
    setBusy(true); setError('')
    try { setCard(await makeFixCard(scanId, hazard.id)); setView('after') }
    catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }
  const src = view === 'evidence' || !card ? hazard.evidence_image : view === 'before' ? card.before : card.image
  return (
    <li className="hazard">
      <div className="media">
        <img src={fileUrl(scanId, src)} alt={view === 'after' ? `${hazard.object}, fixed` : hazard.object} loading="lazy" />
        {view === 'after' && <span className="media-tag">Muse Image · your room, fixed</span>}
        {card ? (
          <div className="seg" role="tablist">
            {(['evidence', 'before', 'after'] as const).map((v) => (
              <button key={v} role="tab" aria-selected={view === v} className={view === v ? 'on' : ''} onClick={() => setView(v)}>
                {v === 'evidence' ? 'Evidence' : v === 'before' ? 'Before' : 'Fixed'}
              </button>
            ))}
          </div>
        ) : hazard.fix && (
          <button className="show-fixed" onClick={showFixed} disabled={busy}>{busy ? 'Imagining the fix…' : 'Show it fixed'}</button>
        )}
      </div>
      <div className="hazard-body">
        <div className="hazard-head">
          <span className={`badge ${hazard.severity}`}>{hazard.severity}</span>
          <span className="relation">{RELATION_LABELS[hazard.relation] ?? hazard.relation}</span>
        </div>
        <h4>{hazard.object}</h4>
        <p>{hazard.rationale}</p>
        {error && <p className="error">{error}</p>}
        {hazard.fix && <FixBlock fix={hazard.fix} />}
        {hazard.track && <small className="muted">Tracked by SAM 3.1 as {hazard.track} · frame {hazard.evidence_frame}</small>}
      </div>
    </li>
  )
}

function FixBlock({ fix }: { fix: Fix }) {
  return (
    <div className="fix">
      <div className="fix-head">
        <b>How to fix</b>
        <span className={`pill ${fix.diy ? 'diy' : 'pro'}`}>{fix.diy ? 'DIY' : 'Professional'}</span>
        <span className="muted">{fix.cost} · ~{fix.minutes} min</span>
      </div>
      <ol>{fix.actions.map((a, i) => <li key={i}>{a}</li>)}</ol>
      {fix.fema_sections.length > 0 && (
        <small className="muted">
          Source: FEMA E-74 {fix.fema_sections.map((s, i) => (
            <span key={s.id}>{i > 0 && ', '}<a href={s.url} target="_blank" rel="noreferrer">§{s.id} {s.title}</a> (p. {s.pages})</span>
          ))}
        </small>
      )}
    </div>
  )
}
