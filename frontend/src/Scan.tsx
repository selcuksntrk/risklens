import { useEffect, useState } from 'react'
import { go } from './App'
import { fileUrl, getScan, makeFixCard, type Verification, RELATION_LABELS, ROOM_LABELS, type Fix, type Hazard, type Report, type TimelineEvent } from './api'

export function riskBand(score: number) {
  if (score >= 70) return { label: 'High risk', cls: 'high' }
  if (score >= 35) return { label: 'Medium risk', cls: 'medium' }
  return { label: 'Low risk', cls: 'low' }
}

function useScan(scanId: string, verifyId?: string) {
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [fixcards, setFixcards] = useState<string[]>([])
  const [verification, setVerification] = useState<Verification | null>(null)
  const [verifying, setVerifying] = useState(!!verifyId)
  const [error, setError] = useState('')

  useEffect(() => {
    let source: EventSource | null = null
    let timer = 0
    let cancelled = false
    const settle = async () => {
      const state = await getScan(scanId)
      if (cancelled) return
      if (state.status === 'done') {
        setReport(state.report); setFixcards(state.fixcards ?? []); setVerification(state.verification ?? null)
      }
      else if (state.status === 'error') setError(state.message)
      return state.status
    }
    // The live stream dropped (network, server restart): ask for the state every 3 s until it settles.
    const poll = async (left: number) => {
      const status = await settle()
      if (!cancelled && status === 'running' && left > 0) timer = window.setTimeout(() => void poll(left - 1), 3000)
    }
    settle().then((status) => {
      if (cancelled || (status !== 'running' && !verifyId)) return
      if (verifyId && status !== 'done') return
      source = new EventSource(`/api/scans/${verifyId ?? scanId}/events`)
      source.onmessage = (e) => {
        const event = JSON.parse(e.data) as TimelineEvent
        setEvents((all) => [...all, event])
        if (event.step === 'error') setError(String(event.message))
      }
      source.addEventListener('end', () => { source?.close(); setVerifying(false); settle() })
      source.onerror = () => { source?.close(); setVerifying(false); void poll(60) }
    })
    return () => { cancelled = true; source?.close(); window.clearTimeout(timer) }
  }, [scanId])
  return { events, report, fixcards, verification, verifying, error }
}

export default function Scan({ scanId, verifyId }: { scanId: string; verifyId?: string }) {
  const { events, report, fixcards, verification, verifying, error } = useScan(scanId, verifyId)
  return (
    <main className="page">
      <header className="bar">
        <button className="ghost" onClick={() => go('')}>‹ Scans</button>
        <span className="muted">Scan {scanId.slice(0, 6)}</span>
      </header>
      {error && <p className="error">{error}</p>}
      {!report && <Timeline events={events} scanId={scanId} />}
      {report && verifying && <VerifyTimeline events={events} />}
      {report && !verifying && <ReportView report={report} fixcards={fixcards} verification={verification} />}
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

function ReportView({ report, fixcards, verification }: { report: Report; fixcards: string[]; verification: Verification | null }) {
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
      {verification && (
        <section className="verified-card">
          <h3>Verified after fixes</h3>
          <p><b>{verification.fixed} of {hazards.length}</b> hazards verified fixed · risk score
            {' '}<b>{verification.risk_score_before}</b> → <b>{verification.risk_score_after}</b></p>
          <small className="muted">Re-filmed {new Date(verification.created_at).toLocaleString()} · checked by SAM 3.1 + Muse Spark</small>
        </section>
      )}
      <h3>{hazards.length} hazard{hazards.length === 1 ? '' : 's'}</h3>
      <ul className="hazards">
        {hazards.map((h) => <HazardCard key={h.id} hazard={h} scanId={report.scan_id} hasCard={fixcards.includes(h.id)}
          check={verification?.results[h.id]} />)}
      </ul>
      {hazards.length > 0 && (
        <button className="primary big" onClick={() => go(`verify/${report.scan_id}`)}>
          {verification ? 'Re-film again to verify' : 'Fixed something? Re-film to verify'}
        </button>
      )}
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

type Check = Verification['results'][string]
const VERDICT = { fixed: 'Verified fixed', not_fixed: 'Not fixed yet', cannot_verify: "Couldn't verify" }

function HazardCard({ hazard, scanId, hasCard, check }: { hazard: Hazard; scanId: string; hasCard: boolean; check?: Check }) {
  const [card, setCard] = useState<{ image: string; before: string } | null>(
    hasCard ? { image: `fixcards/${hazard.id}.jpg`, before: `fixcards/${hazard.id}_before.jpg` } : null)
  const [view, setView] = useState<'evidence' | 'before' | 'after' | 'refilmed'>(check?.verdict === 'fixed' ? 'refilmed' : 'evidence')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function showFixed() {
    setBusy(true); setError('')
    try { setCard(await makeFixCard(scanId, hazard.id)); setView('after') }
    catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }
  const src = view === 'refilmed' && check ? check.after_image
    : view === 'evidence' || !card ? hazard.evidence_image : view === 'before' ? card.before : card.image
  const views = [...(['evidence'] as const), ...(check ? (['refilmed'] as const) : []), ...(card ? (['before', 'after'] as const) : [])]
  const label = { evidence: 'Evidence', refilmed: 'Re-filmed', before: 'Before', after: 'Fixed' }
  return (
    <li className="hazard">
      <div className="media">
        <img src={fileUrl(scanId, src)} alt={view === 'after' ? `${hazard.object}, fixed` : hazard.object} loading="lazy" />
        {view === 'after' && <span className="media-tag">Muse Image · your room, fixed</span>}
        {view === 'refilmed' && <span className="media-tag">After your fix · SAM 3.1</span>}
        {views.length > 1 && (
          <div className="seg" role="tablist">
            {views.map((v) => (
              <button key={v} role="tab" aria-selected={view === v} className={view === v ? 'on' : ''} onClick={() => setView(v)}>
                {label[v]}
              </button>
            ))}
          </div>
        )}
        {!card && hazard.fix && check?.verdict !== 'fixed' && (
          <button className="show-fixed" onClick={showFixed} disabled={busy}>{busy ? 'Imagining the fix…' : 'Show it fixed'}</button>
        )}
      </div>
      <div className="hazard-body">
        <div className="hazard-head">
          <span className={`badge ${hazard.severity}`}>{hazard.severity}</span>
          <span className="relation">{RELATION_LABELS[hazard.relation] ?? hazard.relation}</span>
        </div>
        {check && <p className={`verdict ${check.verdict}`}><b>{VERDICT[check.verdict]}</b> · {check.what_changed}</p>}
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

function VerifyTimeline({ events }: { events: TimelineEvent[] }) {
  const checked = events.filter((e) => e.step === 'verify.hazard')
  const concepts = events.filter((e) => e.step === 'sam.done')
  return (
    <section className="timeline" aria-live="polite">
      <h2>Verifying your fixes…</h2>
      <ol>
        <li className={`step ${concepts.length ? 'done' : 'active'}`}>
          <b>Re-finding each object</b> <span className="tag">{MODEL.sam}</span>
          {concepts.length > 0 && <div className="chips">{concepts.map((e) => (
            <span key={String(e.concept)} className={`chip ${Number(e.objects) ? 'hit' : 'miss'}`}>{String(e.concept)} · {String(e.objects)}</span>
          ))}</div>}
        </li>
        <li className={`step ${checked.length ? 'active' : ''}`}>
          <b>Comparing before and after</b> <span className="tag">{MODEL.spark}</span>
          {checked.map((e) => <small key={String(e.hazard_id)}>{String(e.object)}: {VERDICT[e.verdict as keyof typeof VERDICT]}</small>)}
        </li>
      </ol>
    </section>
  )
}
