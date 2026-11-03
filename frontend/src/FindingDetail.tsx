import { useState } from 'react'
import { go } from './routing'
import { fileUrl, hasRequest, makeFixCard, type Fix, type Hazard, type Report, type Verification } from './api'
import { Fold, Lightbox, Limits, Severity } from './components'
import { MODELS, cap, findingHref, sortFindings, VERDICT_WORD } from './ui'

type Check = Verification['results'][string]

function sourceSupported(fix: Fix | null) {
  return !!fix && fix.source_status === 'verified' && fix.actions.length > 0 && fix.action_sources.length === fix.actions.length
    && fix.action_sources.every((ids) => ids.length > 0 && ids.every((id) => fix.fema_sections.some((s) => s.id === id)))
}

/** One finding per screen: the photo, one honest sentence about what we couldn't see, and what to do. */
export default function FindingDetail({ report, hazardId, fixcards, verification, readOnly }:
  { report: Report; hazardId: string; fixcards: string[]; verification: Verification | null; readOnly: boolean }) {
  const list = sortFindings(report.hazards)
  const index = list.findIndex((h) => h.id === hazardId)
  const hazard = list[index]
  const listHref = `#/scan/${report.scan_id}${verification ? `/v/${verification.verify_id}` : ''}`
  if (!hazard) return <p>That item isn’t in this report. <a href={listHref}>Back to the list</a></p>
  const prev = list[index - 1], next = list[index + 1]
  const href = (h: Hazard) => findingHref(report.scan_id, h.id, verification?.verify_id)
  return <article className="detail">
    <nav className="pager" aria-label="Findings">
      <a className="back" href={listHref}>‹ All {list.length}</a>
      <span className="count">{index + 1} of {list.length}</span>
      <span className="nav">{prev ? <a href={href(prev)} aria-label="Previous">‹</a> : <span aria-hidden>‹</span>}
        {next ? <a href={href(next)} aria-label="Next">›</a> : <span aria-hidden>›</span>}</span>
    </nav>
    <Finding key={hazard.id} hazard={hazard} scanId={report.scan_id} hasCard={fixcards.includes(hazard.id)} check={verification?.results[hazard.id]}
      legacy={!!verification && verification.schema_version !== 2} readOnly={readOnly} />
    {next && <a className="btn block" href={href(next)}>Next: {cap(next.object)}</a>}
    <Limits />
  </article>
}

export function Finding({ hazard, scanId, hasCard, check, readOnly, legacy = false }:
  { hazard: Hazard; scanId: string; hasCard: boolean; check?: Check; readOnly: boolean; legacy?: boolean }) {
  const supported = sourceSupported(hazard.fix)
  const [card, setCard] = useState<{ image: string } | null>(hasCard && supported ? { image: `fixcards/${hazard.id}.jpg` } : null)
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
  const viewName = { evidence: 'Your video', illustration: 'Possible fix (AI picture)', refilmed: 'New video' }
  const caption = view === 'illustration' ? `AI-made picture by ${MODELS.image}. Not proof anything was fixed, and not installation instructions.`
    : view === 'refilmed' ? 'From your new video'
    : hazard.tracking_supported ? `Frame ${hazard.evidence_frame} · box by ${MODELS.sam}` : `Frame ${hazard.evidence_frame}`
  const unknown = hasRequest(hazard.next_view_request) ? hazard.next_view_request : ''

  return <>
    <figure className="photo" style={{ margin: undefined }}>
      {src && <button onClick={() => setZoom(true)} aria-label={`Enlarge photo: ${hazard.object}`}><img src={fileUrl(scanId, src)} alt={`${viewName[view]}: ${hazard.object}`} /></button>}
      <figcaption className="caption">{caption}</figcaption>
    </figure>
    {zoom && src && <Lightbox src={fileUrl(scanId, src)} alt={hazard.object} onClose={() => setZoom(false)} />}
    {views.length > 1 && <div className="views" role="tablist" aria-label="Photo">{views.map((v) =>
      <button key={v} role="tab" aria-selected={view === v} onClick={() => setView(v)}>{viewName[v]}</button>)}</div>}

    <h1>{cap(hazard.object)}</h1>
    <Severity severity={hazard.severity} relation={hazard.relation} />
    <p className="unknown">{hazard.evidence_status === 'observed'
      ? <>Clearly visible in your video.{unknown && <> To be sure: {lower(unknown)}</>}</>
      : hazard.evidence_status === 'needs_check'
        ? <>Needs a closer look: {unknown ? lower(unknown) : 'the video doesn’t show how it is held in place.'}</>
        : <>From an older report; we don’t know how sure the model was.</>}</p>

    {check && <p className={`verdict ${legacy ? 'cannot_verify' : check.verdict}`}><b>{legacy ? 'Older result; today’s checks weren’t recorded' : VERDICT_WORD[check.verdict]}.</b> {check.what_changed}
      {check.rationale && check.rationale !== check.what_changed && <><br />{check.rationale}</>}
      {hasRequest(check.next_view_request) && <><br />{check.next_view_request}</>}</p>}

    <h2>What to do</h2>
    {supported && hazard.fix ? <Steps fix={hazard.fix} storageKey={`risklens.done.${scanId}.${hazard.id}`} />
      : <p className="note">We couldn’t link this one to a FEMA section, so we’re not suggesting steps. Take a closer look yourself, or ask someone who installs furniture restraints.</p>}

    {!readOnly && <div className="stack no-print" style={{ margin: '16px 0' }}>
      {!card && supported && <button className="btn block" disabled={busy} onClick={() => void illustrate()}>{busy ? 'Drawing it… (about 20 s)' : 'Show what the fix could look like'}</button>}
      <button className="btn block" onClick={() => go(`verify/${scanId}/${hazard.id}`)}>Film this item again</button>
    </div>}
    {error && <p className="error">{error}</p>}

    <Fold title="What the video shows"><p>{hazard.evidence_observation || 'No description recorded.'}</p>
      <p className="fine">{hazard.tracking_supported ? `${MODELS.sam} had a box on this object in frame ${hazard.evidence_frame}.` : 'This finding isn’t tied to a tracking box in this frame.'}</p></Fold>
    {hazard.rationale && <Fold title="Why it matters"><p>{hazard.rationale}</p></Fold>}
  </>
}

const lower = (s: string) => s.charAt(0).toLowerCase() + s.slice(1)

function readDone(key: string): number[] {
  try { const v: unknown = JSON.parse(localStorage.getItem(key) ?? '[]'); return Array.isArray(v) ? v.filter((x) => typeof x === 'number') : [] } catch { return [] }
}
function Steps({ fix, storageKey }: { fix: Fix; storageKey: string }) {
  const [done, setDone] = useState<number[]>(() => readDone(storageKey))
  function toggle(i: number) {
    const next = done.includes(i) ? done.filter((x) => x !== i) : [...done, i]
    setDone(next)
    try { localStorage.setItem(storageKey, JSON.stringify(next)) } catch { /* still works for this visit */ }
  }
  return <>
    <ul className="todo">{fix.actions.map((action, i) => <li key={i} className={done.includes(i) ? 'done' : ''}><label>
      <input type="checkbox" checked={done.includes(i)} onChange={() => toggle(i)} />
      <span><span className="what">{action}</span>
        <span className="src">{fix.action_sources[i].map((id, j) => { const s = fix.fema_sections.find((x) => x.id === id)!; return <span key={id}>{j > 0 && ' · '}<a href={s.url} target="_blank" rel="noreferrer">FEMA E-74 §{id}, p. {s.pages}</a></span> })}</span></span>
    </label></li>)}</ul>
    <p className="fine">{fix.diy ? 'Usually something you can do yourself' : 'Usually a job for a professional'} · rough estimate {fix.cost}, about {fix.minutes} min. Steps are written by {MODELS.spark} from the linked FEMA sections, not checked by an engineer.</p>
  </>
}
