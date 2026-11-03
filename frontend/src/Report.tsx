import { useEffect, useState } from 'react'
import { go } from './routing'
import { exampleMedia, fileUrl, findingCounts, getAttempts, hasRequest, makeFixCard, RELATION_LABELS, ROOM_LABELS,
  type Attempt, type Example, type Fix, type Hazard, type Report, type Verification } from './api'
import { EvidenceStatus, Lightbox, SeverityBadge } from './components'
import { MODELS, STAGES, fmtSeconds } from './ui'

const SEVERITY_ORDER = { high: 0, medium: 1, low: 2 }
const scrollToFinding = (id: string) => document.getElementById(`finding-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

export function ReportView({ report, fixcards, verification, readOnly = false, example = null }:
  { report: Report; fixcards: string[]; verification: Verification | null; readOnly?: boolean; example?: Example | null }) {
  const hazards = [...report.hazards].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity])
  const counts = findingCounts(hazards)
  const legacyVerification = !!verification && verification.schema_version !== 2
  const assessment = report.assessment ?? { status: 'legacy_unknown', warnings: ['Historical report: assessment completeness is unknown.'] }
  const objectOf = (id: string) => report.hazards.find((h) => h.id === id)?.object ?? id
  return <article className="report">
    {example && <SamplePlayer example={example} />}
    <section className="card report-hero">
      <div className="headline-row">
        <span className={`assess ${assessment.status}`}>Assessment {assessment.status.replace('_', ' ')}</span>
        {example && <span className={`pill ${example.synthetic ? 'synthetic' : 'real'}`}>{example.synthetic ? 'AI-generated scene' : 'Real home · Istanbul'}</span>}
      </div>
      <h1>{ROOM_LABELS[report.room.type] ?? 'Room'}: {hazards.length ? `${hazards.length} visible findings` : 'no visible findings'}</h1>
      <p className="summary">{report.room.summary}</p>
      <dl className="stats" aria-label="Findings by priority">
        <div className="high"><dt>High</dt><dd>{counts.high}</dd></div><div className="medium"><dt>Medium</dt><dd>{counts.medium}</dd></div>
        <div className="low"><dt>Low</dt><dd>{counts.low}</dd></div><div><dt>To check</dt><dd>{counts.needs_check}</dd></div>
      </dl>
      {hazards.length > 0 && <div><span className="eyebrow">Look at these first</span>
        <ol className="do-first">{hazards.slice(0, 3).map((h) => <li key={h.id}>
          <a href={`#/scan/${report.scan_id}`} onClick={(e) => { e.preventDefault(); scrollToFinding(h.id) }}>
            <img src={fileUrl(report.scan_id, h.evidence_image)} alt="" />
            <span><b>{h.object}</b><small>{h.severity} priority · {RELATION_LABELS[h.relation] ?? h.relation}</small></span>
          </a></li>)}</ol></div>}
      <p className="fine">Model-generated findings, not expert-reviewed. Check each statement against its image; hidden attachments remain unknown.</p>
    </section>

    {(assessment.warnings.length > 0 || assessment.status !== 'complete') && <section className={`notice assessment-${assessment.status}`}>
      <b>Assessment: {assessment.status.replace('_', ' ')}</b>
      <p className="fine">Stage completion is not room safety or full-room coverage.</p>
      {assessment.warnings.map((w, i) => <p key={i}>{w}</p>)}</section>}

    {example?.answer_key && <AnswerKeyPanel example={example} objectOf={objectOf} />}

    {report.context?.occupant_narration && <details className="card"><summary>Room context supplied by the user</summary><p>{report.context.occupant_narration}</p><small>This is user context, not a visual observation.</small></details>}

    {verification && <section className={verification.fixed > 0 && verification.schema_version === 2 ? 'verified-card' : 'notice'}>
      <h3>{verification.schema_version === 2 ? 'Re-filming results' : 'Historical verification · current safeguards were not recorded'}</h3>
      <p><b>{verification.fixed}</b> {legacyVerification ? 'historical fix claims (current evidence checks unknown)' : 'visible changes confirmed'} · <b>{Object.values(verification.results).filter((r) => r.verdict === 'not_fixed').length}</b> still visible · <b>{Object.values(verification.results).filter((r) => r.verdict === 'cannot_verify').length}</b> not assessable</p>
      <p>{verification.unchecked_hazard_ids?.length ?? Math.max(0, hazards.length - Object.keys(verification.results).length)} findings not examined in this attempt. This is not whole-room verification.</p>
      <small>Re-filmed {new Date(verification.created_at).toLocaleString()}. Visible changes do not certify installation adequacy.</small>
    </section>}

    {hazards.length === 0 && <p>No visible hazards identified in the sampled views. Unseen areas and hidden attachments remain unknown.</p>}
    <ul className="hazards">{hazards.map((h, i) => <HazardCard key={`${h.id}/${verification?.verify_id ?? ''}`} hazard={h} scanId={report.scan_id} eager={i < 2}
      hasCard={fixcards.includes(h.id)} check={verification?.results[h.id]} legacy={legacyVerification} readOnly={readOnly} />)}</ul>

    <PipelinePanel report={report} />
    <p className="fine">{report.disclaimer}</p>

    <div className="action-bar no-print">
      {!!hazards.length && !readOnly && <button className="primary" onClick={() => go(`verify/${report.scan_id}`)}>Re-film to compare</button>}
      {readOnly && <button className="primary" onClick={() => go('capture')}>Scan your own room</button>}
      <button className="secondary" onClick={() => window.print()}>Save as PDF</button>
    </div>
    {!!hazards.length && !readOnly && <p className="fine">Re-filming is an experimental comparison: real-world physical-change validation is still pending.</p>}
  </article>
}

function SamplePlayer({ example }: { example: Example }) {
  return <section className="card sample-player portrait">
    {example.has_video && <video controls playsInline muted preload="metadata" poster={example.has_poster ? exampleMedia(example.id, 'poster.jpg') : undefined}
      src={exampleMedia(example.id, 'source.mp4')} aria-label={`${example.title}: source video`} />}
    <div>
      <span className="eyebrow">Sample report · opened without new model calls</span>
      <h2>{example.title}</h2>
      <p className="muted">{example.description}</p>
      <p className="fine">{example.synthetic ? 'Synthetic scene, not a real household. ' : ''}{example.license}{example.source_url && <> · <a href={example.source_url} target="_blank" rel="noreferrer">Source</a></>}</p>
      {example.has_replay && <div className="actions"><button className="secondary" onClick={() => go(`replay/${example.id}`)}>Watch the analysis replay</button></div>}
    </div>
  </section>
}

function AnswerKeyPanel({ example, objectOf }: { example: Example; objectOf: (id: string) => string }) {
  const key = example.answer_key!
  const missed = key.hazards.filter((h) => !h.matched_finding)
  return <section className="answer-key" aria-labelledby="key-title">
    <span className="eyebrow">Designed scene · answer key</span>
    <h2 id="key-title"><span className="score">{key.matched}/{key.designed}</span> designed hazards matched</h2>
    <p className="muted">These hazards were placed in the scene on purpose before any analysis. Matching is {key.method}; this is one designed scene, not an accuracy measurement for real homes.</p>
    <ul className="key-list">{key.hazards.map((h) => <li key={h.id} className={h.matched_finding ? 'hit' : 'miss'}>
      <span className="mark" aria-label={h.matched_finding ? 'Matched' : 'Missed'}>{h.matched_finding ? '✓' : '✕'}</span>
      <span><b>{h.label}</b><br />{h.matched_finding
        ? <button className="link-button" style={{ minHeight: 32, padding: 0 }} onClick={() => scrollToFinding(h.matched_finding!)}>Found as “{objectOf(h.matched_finding)}”</button>
        : <small className="muted">Not reported by RiskLens</small>}</span></li>)}</ul>
    {key.other_findings.length > 0 && <p className="fine">{key.other_findings.length} other finding{key.other_findings.length > 1 ? 's' : ''} not in the design: {key.other_findings.map(objectOf).join(', ')}. These may be real visible items in the generated images or over-flagging.</p>}
    {key.controls.length > 0 && <p className="fine">Control: {key.controls.map((c) => c.label).join('; ')}.</p>}
    {missed.length === 0 && key.note && <p className="fine">{key.note}</p>}
    {missed.length > 0 && key.note && <p className="fine">{key.note}</p>}
  </section>
}

function PipelinePanel({ report }: { report: Report }) {
  const t = report.timings_s ?? {}
  const models = report.provenance?.models ?? {}
  const role: Record<string, string> = {
    ingest: 'Checked the file and sampled keyframes', planner: 'Chose which objects matter in this room',
    sam: 'Tracked each object through the whole video', surveyor: 'Judged what could fall, tip, break or block the exit',
    fixer: 'Wrote next steps from the FEMA E-74 sections it read',
  }
  const modelFor: Record<string, string | null | undefined> = { planner: models.planner, sam: models.tracking, surveyor: models.surveyor, fixer: models.fixer }
  return <section className="card made" aria-labelledby="made-title">
    <h2 id="made-title">How this report was made</h2>
    <ol className="chain">{STAGES.map((s) => <li key={s.key}>
      <b>{s.label} · {s.key === 'ingest' ? s.model : (modelFor[s.key] ?? s.model)}</b>
      <small>{role[s.key]}</small><span className="t">{t[s.key] !== undefined ? fmtSeconds(t[s.key]) : ''}</span></li>)}
      <li><b>Optional · {MODELS.image}</b><small>Illustrates a source-linked recommendation on request, always labelled as AI-generated</small><span className="t" /></li>
    </ol>
    <p className="fine">Total {report.seconds ?? 'unknown'} s · recorded model cost {report.cost_usd?.total !== undefined ? `$${report.cost_usd.total.toFixed(3)}` : 'unknown'} (application usage record, not a provider invoice).</p>
    <details className="provenance"><summary>Audit trail</summary><dl>
      <dt>Schema / release</dt><dd>{report.schema_version ?? 1} / {report.provenance?.app_version ?? 'legacy/unknown'}</dd>
      <dt>Models</dt><dd>{Object.entries(models).map(([k, v]) => `${k}: ${v ?? 'unknown'}`).join(' · ')}</dd>
      <dt>Video SHA-256</dt><dd className="mono">{report.provenance?.source_sha256 ?? 'legacy/unknown'}</dd>
      <dt>Prompt hashes</dt><dd className="mono">{Object.entries(report.provenance?.prompts_sha256 ?? {}).map(([k, v]) => `${k}: ${v}`).join(' · ') || 'legacy/unknown'}</dd>
    </dl></details>
  </section>
}

type Check = Verification['results'][string]
const VERDICT = { fixed: 'Visible change confirmed', not_fixed: 'Still visible', cannot_verify: 'Need another view / Manual review needed' }
function sourceSupported(fix: Fix | null) {
  return !!fix && fix.source_status === 'verified' && fix.actions.length > 0 && fix.action_sources.length === fix.actions.length
    && fix.action_sources.every((ids) => ids.length > 0 && ids.every((id) => fix.fema_sections.some((s) => s.id === id)))
}

function HazardCard({ hazard, scanId, hasCard, check, readOnly, legacy = false, eager = false }:
  { hazard: Hazard; scanId: string; hasCard: boolean; check?: Check; readOnly: boolean; legacy?: boolean; eager?: boolean }) {
  const supported = sourceSupported(hazard.fix)
  const [card, setCard] = useState<{ image: string; before: string } | null>(hasCard && supported ? { image: `fixcards/${hazard.id}.jpg`, before: `fixcards/${hazard.id}_before.jpg` } : null)
  const [view, setView] = useState<'evidence' | 'illustration' | 'refilmed'>('evidence')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [zoom, setZoom] = useState(false)
  async function illustrate() {
    setBusy(true); setError('')
    try { setCard(await makeFixCard(scanId, hazard.id)); setView('illustration') } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const src = view === 'refilmed' && check ? check.after_image : view === 'illustration' && card ? card.image : hazard.evidence_image
  const views = [...(['evidence'] as const), ...(card && supported ? (['illustration'] as const) : []), ...(check?.after_image ? (['refilmed'] as const) : [])]
  const label = { evidence: 'Original evidence', illustration: 'AI fix illustration', refilmed: 'Re-filmed evidence' }
  const unknown = [hasRequest(hazard.next_view_request) ? hazard.next_view_request : '', !hazard.tracking_supported ? (hazard.tracking_note || 'No exact-frame tracking support recorded.') : ''].filter(Boolean)
  return <li className={`hazard sev-${hazard.severity}`} id={`finding-${hazard.id}`}>
    <div className="media">
      {src && <button className="zoom" onClick={() => setZoom(true)} aria-label={`Enlarge: ${label[view]}, ${hazard.object}`}>
        <img src={fileUrl(scanId, src)} alt={`${label[view]}: ${hazard.object}`} loading={eager ? 'eager' : 'lazy'} /></button>}
      {view === 'illustration' && <span className="media-tag">AI-generated illustration · not installation guidance or verification</span>}
      {view === 'evidence' && <span className="media-tag">{hazard.tracking_supported ? `Frame ${hazard.evidence_frame} · box from ${MODELS.sam}` : `Frame ${hazard.evidence_frame}`}</span>}
      {views.length > 1 && <div className="seg" role="tablist" aria-label="Evidence type">{views.map((v) => <button key={v} role="tab" aria-selected={view === v} className={view === v ? 'on' : ''} onClick={() => setView(v)}>{label[v]}</button>)}</div>}
    </div>
    {zoom && src && <Lightbox src={fileUrl(scanId, src)} alt={`${label[view]}: ${hazard.object}`} onClose={() => setZoom(false)} />}
    <div className="hazard-body">
      <div className="hazard-head"><SeverityBadge severity={hazard.severity} /><EvidenceStatus status={hazard.evidence_status} /></div>
      <h3>{hazard.object}</h3>
      <span className="relation">{RELATION_LABELS[hazard.relation] ?? hazard.relation}</span>
      <div className="split">
        <div><h4>What the video shows</h4><p>{hazard.evidence_observation || hazard.rationale}</p></div>
        <div className="unknown"><h4>Still unknown</h4>{unknown.length ? unknown.map((u, i) => <p key={i}>{u}</p>) : <p>Hidden attachments and anything outside the sampled frames.</p>}</div>
      </div>
      {hazard.evidence_observation && hazard.rationale && <p><b>Why it matters: </b>{hazard.rationale}</p>}
      <small className="tracking">{hazard.tracking_supported ? `Exact-frame tracking support · frame ${hazard.evidence_frame}` : 'Not tied to a tracking box at this frame.'}</small>
      {check && <p className={`verdict ${legacy ? 'cannot_verify' : check.verdict}`}><b>{legacy ? 'Historical result · current safeguards unknown' : VERDICT[check.verdict]}</b> · {check.what_changed}{check.rationale && check.rationale !== check.what_changed && <><br />{check.rationale}</>}{hasRequest(check.next_view_request) && <><br />{check.next_view_request}</>}</p>}
      {supported && hazard.fix ? <FixBlock fix={hazard.fix} storageKey={`risklens.done.${scanId}.${hazard.id}`} /> : <p className="notice">Source-linked recommendations are unavailable for this finding. No actionable instructions or AI illustration are offered.</p>}
      {!readOnly && <div className="card-actions">
        {!card && supported && <button className="secondary" disabled={busy} onClick={() => void illustrate()}>{busy ? 'Creating illustration…' : 'Illustrate recommendation'}</button>}
        <button className="ghost" onClick={() => go(`verify/${scanId}/${hazard.id}`)}>Re-film this item</button>
      </div>}
      {error && <p className="error">{error}</p>}
    </div>
  </li>
}

function readDone(key: string): number[] {
  try { const v: unknown = JSON.parse(localStorage.getItem(key) ?? '[]'); return Array.isArray(v) ? v.filter((x) => typeof x === 'number') : [] } catch { return [] }
}
function FixBlock({ fix, storageKey }: { fix: Fix; storageKey: string }) {
  const [done, setDone] = useState<number[]>(() => readDone(storageKey))
  function toggle(i: number) {
    const next = done.includes(i) ? done.filter((x) => x !== i) : [...done, i]
    setDone(next)
    try { localStorage.setItem(storageKey, JSON.stringify(next)) } catch { /* the checklist still works for this visit */ }
  }
  return <div className="fix">
    <div className="fix-head"><b>Next steps</b><span className={`pill ${fix.diy ? 'real' : ''}`}>{fix.diy ? 'DIY' : 'Professional'}</span><span className="pill">{fix.cost} · {fix.minutes} min</span></div>
    <ol>{fix.actions.map((action, i) => <li key={i} className={done.includes(i) ? 'done' : ''}><label>
      <input type="checkbox" checked={done.includes(i)} onChange={() => toggle(i)} />
      <span><span className="action">{action}</span>
        <small className="src">Source: {fix.action_sources[i].map((id) => { const section = fix.fema_sections.find((s) => s.id === id)!; return <a key={id} href={section.url} target="_blank" rel="noreferrer">FEMA E-74 §{id} (p. {section.pages}) </a> })}</small></span>
    </label></li>)}</ol>
    <small className="muted">Estimates are model-generated. Linked to sections the model read; not expert validation. Installation conditions and adequacy require appropriate assessment.</small>
  </div>
}

export function History({ scanId, verifyId }: { scanId: string; verifyId?: string }) {
  const [attempts, setAttempts] = useState<Attempt[]>([])
  const [error, setError] = useState('')
  useEffect(() => { let active = true; getAttempts(scanId).then((a) => { if (active) setAttempts(a) }).catch((e) => { if (active) setError((e as Error).message) }); return () => { active = false } }, [scanId, verifyId])
  if (!attempts.length && !error) return null
  return <details className="card provenance"><summary>Re-filming history ({attempts.length})</summary>{error && <p className="error">{error}</p>}<ul>{attempts.map((a) => <li key={a.verify_id}><button className="ghost" onClick={() => go(`scan/${scanId}/v/${a.verify_id}`)}>{a.created_at ? new Date(a.created_at).toLocaleString() : a.verify_id} · {a.status} · {a.hazard_id ? `Finding ${a.hazard_id}` : 'All findings'}</button></li>)}</ul></details>
}
