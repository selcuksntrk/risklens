import { useEffect, useRef, useState } from 'react'
import { go } from './routing'
import { exampleMedia, fileUrl, findingCounts, getAttempts, newUploadKey, runExample, ROOM_LABELS,
  type Attempt, type Example, type Report, type Verification } from './api'
import { Fold, Limits, Severity } from './components'
import { MODELS, STAGES, cap, fmtSeconds, findingHref, sortFindings, VERDICT_WORD } from './ui'

export function ReportView({ report, verification, readOnly = false, example = null }:
  { report: Report; fixcards?: string[]; verification: Verification | null; readOnly?: boolean; example?: Example | null }) {
  const hazards = sortFindings(report.hazards)
  const counts = findingCounts(hazards)
  const room = ROOM_LABELS[report.room.type] ?? 'Room'
  const assessment = report.assessment ?? { status: 'legacy_unknown', warnings: ['This is an older report; we can’t tell whether every step finished.'] }
  const legacy = !!verification && verification.schema_version !== 2
  const results = verification ? Object.values(verification.results) : []
  const unchecked = verification ? verification.unchecked_hazard_ids?.length ?? Math.max(0, hazards.length - results.length) : 0
  const priorities = (['high', 'medium', 'low'] as const).filter((k) => counts[k]).map((k) => `${counts[k]} ${k}`).join(' · ')

  return <article className="report">
    {example && <SampleStrip example={example} />}
    <header className="report-head">
      <h1>{room}: {hazards.length ? `${hazards.length} ${hazards.length === 1 ? 'thing' : 'things'} to check` : 'nothing obvious to fix'}</h1>
      <p>{hazards.length ? `${priorities} priority. Start at the top.` : 'Nothing that could fall, tip over or block the way showed up in the frames we looked at. Parts of the room the video didn’t show may still need a look.'}</p>
    </header>

    {assessment.status !== 'complete' && <div className="note warn">
      <p><b>Part of the check didn’t finish, so something may be missing.</b></p>
      {assessment.warnings.map((w, i) => <p key={i}>{w}</p>)}</div>}

    {verification && <div className={verification.fixed > 0 && !legacy ? 'verdict fixed verified-card' : 'verdict'}>
      <p><b>{legacy ? 'Older comparison: today’s checks weren’t recorded for it.' : 'After your new video'}</b></p>
      <p>{verification.fixed} {verification.fixed === 1 ? 'change' : 'changes'} visible · {results.filter((r) => r.verdict === 'not_fixed').length} looks the same · {results.filter((r) => r.verdict === 'cannot_verify').length} can’t tell</p>
      <p className="fine">{unchecked} {unchecked === 1 ? 'item was' : 'items were'} not checked in this video. A visible change doesn’t prove something is fixed safely.</p>
    </div>}

    {hazards.length > 0 && <ol className="findings" aria-label="Things to check">{hazards.map((h, i) => {
      const check = verification?.results[h.id]
      return <li key={h.id}><a className="finding-row" href={findingHref(report.scan_id, h.id, verification?.verify_id)}>
        <span className="n">{i + 1}</span>
        <img src={fileUrl(report.scan_id, h.evidence_image)} alt="" loading={i < 4 ? 'eager' : 'lazy'} />
        <span><b>{cap(h.object)}</b><Severity severity={h.severity} relation={h.relation} />
          {check && <span className="verdict-word">{legacy ? 'Older result' : VERDICT_WORD[check.verdict]}</span>}</span>
        <span className="chev" aria-hidden>›</span></a></li>
    })}</ol>}

    <div className="actions-bar no-print">
      {!readOnly && hazards.length > 0 && <button className="btn primary" onClick={() => go(`verify/${report.scan_id}`)}>Film again after a fix</button>}
      {readOnly && <button className="btn primary" onClick={() => go('capture')}>Check your own room</button>}
      <button className="btn" onClick={() => window.print()}>Save as PDF</button>
    </div>

    {example?.answer_key && <AnswerKey example={example} report={report} />}
    <Fold title="What the model saw in this room">
      <p>{report.room.summary}</p>
      {report.context?.occupant_narration && <p className="fine">Your note: “{report.context.occupant_narration}” We used it as context, not as something seen in the video.</p>}
    </Fold>
    <MadeWith report={report} />
    <Limits />
  </article>
}

function SampleStrip({ example }: { example: Example }) {
  const [video, setVideo] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const key = useRef<string | null>(null)
  async function runLive() {
    if (busy) return
    setBusy(true); setError('')
    key.current ??= newUploadKey()
    try { go(`scan/${await runExample(example.id, key.current)}`) } catch (e) { setError((e as Error).message); setBusy(false) }
  }
  return <>
    <div className="sample-strip no-print">
      <b>{example.synthetic ? 'Example · AI-made test room' : 'Example · real video from a flat in Istanbul, photos blurred'}</b>
      {example.has_video && <button className="text-btn" onClick={() => setVideo((v) => !v)}>{video ? 'Hide video' : 'Watch the video'}</button>}
      {example.has_replay && <a href={`#/replay/${example.id}`}>Replay the analysis</a>}
      <button className="text-btn" disabled={busy} onClick={() => void runLive()}>{busy ? 'Starting…' : 'Run it again live'}</button>
    </div>
    {error && <p className="error" role="alert">{error} The example report below still works.</p>}
    {video && <div className="sample-video"><video controls autoPlay muted playsInline src={exampleMedia(example.id, 'source.mp4')} aria-label={`Video: ${example.title}`} /></div>}
  </>
}

function AnswerKey({ example, report }: { example: Example; report: Report }) {
  const key = example.answer_key!
  const name = (id: string) => report.hazards.find((h) => h.id === id)?.object ?? id
  return <Fold title={`Test room: ${key.matched} of ${key.designed} planted hazards found`}>
    <p className="fine">We built this room with Muse Image and placed these hazards on purpose before running RiskLens. It shows what the system catches on known content. It is one test room, not an accuracy score for real homes.</p>
    <ul className="key">{key.hazards.map((h) => <li key={h.id}>
      <span className={h.matched_finding ? 'yes' : 'no'} aria-label={h.matched_finding ? 'Found' : 'Missed'}>{h.matched_finding ? '✓' : '✕'}</span>
      <span>{h.label}{h.matched_finding
        ? <> · <a href={findingHref(report.scan_id, h.matched_finding)}>found as “{name(h.matched_finding).toLowerCase()}”</a></>
        : <span className="muted"> · missed</span>}</span></li>)}</ul>
    {key.other_findings.length > 0 && <p className="fine">Also flagged, though we didn’t plant it: {key.other_findings.map(name).join(', ')}.</p>}
    {key.controls.length > 0 && <p className="fine">We also added something already secured, to see whether it gets flagged: {key.controls.map((c) => c.label.replace(/ \(.*\)$/, '').toLowerCase()).join('; ')}. It was {key.controls.some((c) => c.flagged) ? '' : 'not '}flagged.</p>}
    <p className="fine">Matched by hand from each finding’s name and photo. <a href="#/about#examples">How the test rooms were made</a></p>
  </Fold>
}

function MadeWith({ report }: { report: Report }) {
  const t = report.timings_s ?? {}
  const models = report.provenance?.models ?? {}
  return <Fold title={`How this report was made · ${fmtSeconds(report.seconds)}`}>
    <ol className="progress">{STAGES.map((s) => <li key={s.key} className="done"><span>{s.label}<small>{s.model}{t[s.key] !== undefined ? ` · ${fmtSeconds(t[s.key])}` : ''}</small></span></li>)}</ol>
    <p className="fine">Model use cost about {report.cost_usd?.total !== undefined ? `$${report.cost_usd.total.toFixed(2)}` : 'an unknown amount'}. {MODELS.image} only runs if you ask for a picture of a fix.</p>
    <details><summary className="fine">Technical record</summary><p className="mono">
      Models: {Object.entries(models).map(([k, v]) => `${k} ${v ?? '?'}`).join(', ')}<br />
      Release: {report.provenance?.app_version ?? 'unknown'} · schema {report.schema_version ?? 1}<br />
      Video SHA-256: {report.provenance?.source_sha256 ?? 'unknown'}<br />
      Prompts: {Object.entries(report.provenance?.prompts_sha256 ?? {}).map(([k, v]) => `${k} ${v.slice(0, 12)}`).join(', ')}</p></details>
  </Fold>
}

export function History({ scanId, verifyId }: { scanId: string; verifyId?: string }) {
  const [attempts, setAttempts] = useState<Attempt[]>([])
  useEffect(() => { let active = true; getAttempts(scanId).then((a) => { if (active) setAttempts(a) }).catch(() => {}); return () => { active = false } }, [scanId, verifyId])
  if (!attempts.length) return null
  return <Fold title={`Earlier comparisons (${attempts.length})`}><ul>{attempts.map((a) => <li key={a.verify_id}>
    <a href={`#/scan/${scanId}/v/${a.verify_id}`}>{a.created_at ? new Date(a.created_at).toLocaleString() : a.verify_id}</a> · {a.status === 'done' ? `${a.fixed} visible ${a.fixed === 1 ? 'change' : 'changes'}` : a.status}</li>)}</ul></Fold>
}
