import { useEffect, useState } from 'react'
import { go } from './routing'
import { useScan } from './useScan'
import { deleteScan, getAttempts, hasRequest, findingCounts, fileUrl, makeFixCard, type Attempt, type Verification, RELATION_LABELS, ROOM_LABELS, type Fix, type Hazard, type Report, type TimelineEvent } from './api'

export default function Scan({ scanId, verifyId }: { scanId: string; verifyId?: string }) {
  const { events, report, partial, fixcards, verification, verifying, readOnly, error, retryStatus } = useScan(scanId, verifyId)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  async function remove() {
    if (!window.confirm('Delete this scan, its videos, report and all derived images? This cannot be undone.')) return
    setDeleting(true)
    try { await deleteScan(scanId); go('') } catch (e) { setDeleteError((e as Error).message); setDeleting(false) }
  }
  return <main className="page">
    <header className="bar"><button className="ghost" onClick={() => go('')}>‹ Home</button><span className="muted">{readOnly ? 'Sample report' : `Scan ${scanId.slice(0, 6)}`}</span></header>
    {readOnly && <p className="sample-label">Precomputed synthetic example · no new model calls · Hypersim © Apple Inc., <a href="https://creativecommons.org/licenses/by-sa/3.0/">CC BY-SA 3.0</a>. Not a physical-fix demonstration.</p>}
    {error && <p className="error" role="alert">{error} <button onClick={retryStatus}>Retry status</button></p>}
    {!report && !error && <Timeline events={events} scanId={scanId} />}
    {!report && partial && <section className="notice"><h2>Partial findings · analysis is not complete</h2><p>{partial.room.summary}</p>
      <ul>{partial.hazards.map((h) => <li key={h.id}>{h.object}: {h.evidence_observation || h.rationale}</li>)}</ul></section>}
    {report && verifying && <VerifyTimeline events={events} />}
    {report && <ReportView report={report} fixcards={fixcards} verification={verification} readOnly={readOnly || verifying} />}
    {report && <History scanId={scanId} verifyId={verification?.verify_id} />}
    {report && !readOnly && <button className="ghost danger" disabled={deleting} onClick={() => void remove()}>{deleting ? 'Deleting…' : 'Delete scan and all media'}</button>}
    {deleteError && <p className="error">{deleteError}</p>}
  </main>
}

const MODEL = { spark: 'Muse Spark 1.3', sam: 'SAM 3.1' }

function Timeline({ events, scanId }: { events: TimelineEvent[]; scanId: string }) {
  const find = (step: string) => events.find((e) => e.step === step)
  const ingest = find('ingest.done')
  const planner = find('planner.done')
  const marks = find('marks.done')
  const surveyor = find('surveyor.done')
  const fixer = find('fixer.done')
  const sam = new Map<string, { done: boolean; objects?: number; error?: boolean }>()
  for (const e of events) {
    if (e.step === 'sam.start') sam.set(String(e.concept), { done: false })
    if (e.step === 'sam.done') sam.set(String(e.concept), { done: true, objects: Number(e.objects), error: e.status !== 'completed' })
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
        <li className={marks && [...sam.values()].some((s) => s.error) ? 'step failed' : step(!!marks, !!planner && !marks)}>
          <b>Tracking objects through the video</b> <span className="tag">{MODEL.sam}</span>
          {sam.size > 0 && <div className="chips">
            {[...sam].map(([concept, s]) => (
              <span key={concept} className={`chip ${s.done ? (s.error ? 'pending' : s.objects ? 'hit' : 'miss') : 'pending'}`}>
                {concept}{s.done ? s.error ? ' · tracking error' : ` · ${s.objects}` : ' …'}
              </span>
            ))}
          </div>}
          {marks && [...sam.values()].some((s) => s.error) && <small>Tracking errors occurred. Assessment may be incomplete.</small>}
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

export function ReportView({ report, fixcards, verification, readOnly = false }: { report: Report; fixcards: string[]; verification: Verification | null; readOnly?: boolean }) {
  const hazards = [...report.hazards].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity])
  const counts = findingCounts(hazards)
  const legacyVerification = !!verification && verification.schema_version !== 2
  const assessment = report.assessment ?? { status: 'legacy_unknown', warnings: ['Historical report: assessment completeness is unknown.'] }
  return <article className="report">
    <section className="summary-card"><h1>{ROOM_LABELS[report.room.type] ?? 'Room'} · visible findings</h1><p>{report.room.summary}</p>
      <dl className="stats" aria-label="Findings by priority">
        <div><dt>High</dt><dd>{counts.high}</dd></div><div><dt>Medium</dt><dd>{counts.medium}</dd></div>
        <div><dt>Low</dt><dd>{counts.low}</dd></div><div><dt>To check</dt><dd>{counts.needs_check}</dd></div>
      </dl></section>
    <p className="fine">Model-generated findings, not expert-reviewed. Check each statement against the image; hidden attachments remain unknown.</p>
    <section className={`notice assessment-${assessment.status}`}><b>Assessment: {assessment.status.replace('_', ' ')}</b>
      <p className="fine">Stage completion is not room safety or full-room coverage.</p>
      {assessment.warnings.map((w, i) => <p key={i}>{w}</p>)}</section>
    {report.context?.occupant_narration && <details><summary>Room context supplied by the user</summary><p>{report.context.occupant_narration}</p><small>This is user context, not a visual observation.</small></details>}
    {verification && <section className={verification.fixed > 0 && verification.schema_version === 2 ? 'verified-card' : 'notice'}>
      <h3>{verification.schema_version === 2 ? 'Re-filming results' : 'Historical verification · current safeguards were not recorded'}</h3>
      <p><b>{verification.fixed}</b> {legacyVerification ? 'historical fix claims (current evidence checks unknown)' : 'visible changes confirmed'} · <b>{Object.values(verification.results).filter((r) => r.verdict === 'not_fixed').length}</b> still visible · <b>{Object.values(verification.results).filter((r) => r.verdict === 'cannot_verify').length}</b> not assessable</p>
      <p>{verification.unchecked_hazard_ids?.length ?? Math.max(0, hazards.length - Object.keys(verification.results).length)} findings not examined in this attempt. This is not whole-room verification.</p>
      <small>Re-filmed {new Date(verification.created_at).toLocaleString()}. Visible changes do not certify installation adequacy.</small>
    </section>}
    <h3>{hazards.length ? `${hazards.length} findings` : 'No visible hazards identified in the sampled views.'}</h3>
    <ul className="hazards">{hazards.map((h) => <HazardCard key={`${h.id}/${verification?.verify_id ?? ''}`} hazard={h} scanId={report.scan_id} hasCard={fixcards.includes(h.id)} check={verification?.results[h.id]} legacy={legacyVerification} readOnly={readOnly} />)}</ul>
    {!!hazards.length && !readOnly && <><button className="primary big" onClick={() => go(`verify/${report.scan_id}`)}>Re-film to compare visible changes</button><p className="fine">Experimental comparison: real-world physical-change validation is still pending.</p></>}
    <p className="fine">{report.disclaimer}</p>
    <details className="provenance"><summary>Audit trail</summary><dl>
      <dt>Schema / release</dt><dd>{report.schema_version ?? 1} / {report.provenance?.app_version ?? 'legacy/unknown'}</dd>
      <dt>Models</dt><dd>{Object.entries(report.provenance?.models ?? {}).map(([k, v]) => `${k}: ${v ?? 'unknown'}`).join(' · ')}</dd>
      <dt>Time</dt><dd>{report.seconds ?? 'unknown'} s</dd>
      <dt>Recorded cost</dt><dd>{report.cost_usd?.total !== undefined ? `$${report.cost_usd.total.toFixed(3)}` : 'unknown'}</dd>
      <dt>Video SHA-256</dt><dd className="mono">{report.provenance?.source_sha256 ?? 'legacy/unknown'}</dd>
      <dt>Prompt hashes</dt><dd className="mono">{Object.entries(report.provenance?.prompts_sha256 ?? {}).map(([k, v]) => `${k}: ${v}`).join(' · ') || 'legacy/unknown'}</dd>
    </dl></details>
  </article>
}

type Check = Verification['results'][string]
const VERDICT = { fixed: 'Visible change confirmed', not_fixed: 'Still visible', cannot_verify: 'Need another view / Manual review needed' }
function sourceSupported(fix: Fix | null) {
  return !!fix && fix.source_status === 'verified' && fix.actions.length > 0 && fix.action_sources.length === fix.actions.length
    && fix.action_sources.every((ids) => ids.length > 0 && ids.every((id) => fix.fema_sections.some((s) => s.id === id)))
}
function HazardCard({ hazard, scanId, hasCard, check, readOnly, legacy = false }: { hazard: Hazard; scanId: string; hasCard: boolean; check?: Check; readOnly: boolean; legacy?: boolean }) {
  const supported = sourceSupported(hazard.fix)
  const [card, setCard] = useState<{ image: string; before: string } | null>(hasCard && supported ? { image: `fixcards/${hazard.id}.jpg`, before: `fixcards/${hazard.id}_before.jpg` } : null)
  const [view, setView] = useState<'evidence' | 'illustration' | 'refilmed'>('evidence')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function illustrate() {
    setBusy(true); setError('')
    try { setCard(await makeFixCard(scanId, hazard.id)); setView('illustration') } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const src = view === 'refilmed' && check ? check.after_image : view === 'illustration' && card ? card.image : hazard.evidence_image
  const views = [...(['evidence'] as const), ...(card && supported ? (['illustration'] as const) : []), ...(check?.after_image ? (['refilmed'] as const) : [])]
  const label = { evidence: 'Original evidence', illustration: 'AI fix illustration', refilmed: 'Re-filmed evidence' }
  return <li className="hazard"><div className="media">
    {src && <img src={fileUrl(scanId, src)} alt={`${label[view]}: ${hazard.object}`} loading="lazy" />}
    {view === 'illustration' && <span className="media-tag">AI-generated illustration · not installation guidance or verification</span>}
    {views.length > 1 && <div className="seg" role="tablist" aria-label="Evidence type">{views.map((v) => <button key={v} role="tab" aria-selected={view === v} className={view === v ? 'on' : ''} onClick={() => setView(v)}>{label[v]}</button>)}</div>}
    {!card && supported && !readOnly && <button className="show-fixed" disabled={busy} onClick={() => void illustrate()}>{busy ? 'Creating illustration…' : 'Illustrate recommendation'}</button>}
  </div><div className="hazard-body"><div className="hazard-head"><span className={`badge ${hazard.severity}`}>{hazard.severity} priority</span><span className="status">{hazard.evidence_status === 'observed' ? 'Reported visible' : hazard.evidence_status === 'needs_check' ? 'Needs checking' : 'Legacy / unknown'}</span></div>
    <h4>{hazard.object}</h4><span className="relation">{RELATION_LABELS[hazard.relation] ?? hazard.relation}</span>
    <p>{hazard.evidence_observation}</p><p>{hazard.rationale}</p>
    <small className="tracking">{hazard.tracking_supported ? `Exact-frame tracking support · frame ${hazard.evidence_frame}` : hazard.tracking_note || 'No exact-frame tracking support recorded.'}</small>
    {check && <p className={`verdict ${legacy ? 'cannot_verify' : check.verdict}`}><b>{legacy ? 'Historical result · current safeguards unknown' : VERDICT[check.verdict]}</b> · {check.what_changed}{check.rationale && check.rationale !== check.what_changed && <><br />{check.rationale}</>}{hasRequest(check.next_view_request) && <><br />{check.next_view_request}</>}</p>}
    {hasRequest(hazard.next_view_request) && <p className="request"><b>Requested view:</b> {hazard.next_view_request}</p>}
    {supported && hazard.fix ? <FixBlock fix={hazard.fix} /> : <p className="notice">Source-linked recommendations are unavailable for this finding. No actionable instructions or AI illustration are offered.</p>}
    {!readOnly && <button className="ghost" onClick={() => go(`verify/${scanId}/${hazard.id}`)}>Show this detail</button>}
    {error && <p className="error">{error}</p>}
  </div></li>
}
function FixBlock({ fix }: { fix: Fix }) {
  return <div className="fix"><div className="fix-head"><b>Source-linked suggestions</b><span className={`pill ${fix.diy ? 'diy' : 'pro'}`}>{fix.diy ? 'DIY' : 'Professional'}</span><span className="muted">Estimates: {fix.cost} · {fix.minutes} min</span></div>
    <ol>{fix.actions.map((action, i) => <li key={i}>{action}<small> Source: {fix.action_sources[i].map((id) => { const section = fix.fema_sections.find((s) => s.id === id)!; return <a key={id} href={section.url} target="_blank" rel="noreferrer">FEMA E-74 §{id} (p. {section.pages}) </a> })}</small></li>)}</ol>
    <small>Linked to sections read by the model; not expert validation. Installation conditions and adequacy require appropriate assessment.</small>
  </div>
}
function History({ scanId, verifyId }: { scanId: string; verifyId?: string }) {
  const [attempts, setAttempts] = useState<Attempt[]>([])
  const [error, setError] = useState('')
  useEffect(() => { let active = true; getAttempts(scanId).then((a) => { if (active) setAttempts(a) }).catch((e) => { if (active) setError((e as Error).message) }); return () => { active = false } }, [scanId, verifyId])
  return <details className="provenance"><summary>Re-filming history ({attempts.length})</summary>{error && <p className="error">{error}</p>}<ul>{attempts.map((a) => <li key={a.verify_id}><button className="ghost" onClick={() => go(`scan/${scanId}/v/${a.verify_id}`)}>{a.created_at ? new Date(a.created_at).toLocaleString() : a.verify_id} · {a.status} · {a.hazard_id ? `Finding ${a.hazard_id}` : 'All findings'}</button></li>)}</ul></details>
}
function VerifyTimeline({ events }: { events: TimelineEvent[] }) {
  return <section className="timeline" aria-live="polite"><h2>Comparing re-filmed evidence…</h2><p>Checking object identity and the relevant visible change.</p>{events.filter((e) => e.step === 'verify.hazard').map((e) => <p key={String(e.hazard_id)}>{String(e.object)}: {VERDICT[e.verdict as keyof typeof VERDICT]}</p>)}</section>
}
