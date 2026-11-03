import { useEffect, useState } from 'react'
import { go } from './routing'
import { useScan } from './useScan'
import { deleteScan, listExamples, type Example, type TimelineEvent } from './api'
import Stage from './Analysis'
import { History, ReportView } from './Report'

export { ReportView } from './Report'

export default function Scan({ scanId, verifyId }: { scanId: string; verifyId?: string }) {
  const { events, report, partial, fixcards, verification, verifying, readOnly, error, retryStatus } = useScan(scanId, verifyId)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [example, setExample] = useState<Example | null>(null)
  const elapsed = useElapsed(!report)
  useEffect(() => {
    if (!readOnly) return
    let active = true
    listExamples().then((list) => { if (active) setExample(list.find((e) => e.scan_id === scanId) ?? null) }).catch(() => {})
    return () => { active = false }
  }, [readOnly, scanId])
  async function remove() {
    if (!window.confirm('Delete this scan, its videos, report and all derived images? This cannot be undone.')) return
    setDeleting(true)
    try { await deleteScan(scanId); go('') } catch (e) { setDeleteError((e as Error).message); setDeleting(false) }
  }
  return <main className={report ? 'page' : 'page wide'}>
    <header className="bar"><button className="ghost" onClick={() => go('')}>‹ Home</button><span className="muted">{readOnly ? 'Sample report' : `Scan ${scanId.slice(0, 6)}`}</span></header>
    {readOnly && <p className="fine sample-label">Precomputed sample · no new model calls{example?.synthetic ? ' · AI-generated scene, not a real household' : example ? ' · real home, personal photos blurred' : ''} · not a physical-fix demonstration.</p>}
    {error && <p className="error" role="alert">{error} <button className="link-button" onClick={retryStatus}>Retry status</button></p>}
    {!report && !error && <Stage events={events} scanId={scanId} elapsed={elapsed} partial={partial} />}
    {!report && partial && error && <section className="notice"><h2>Partial findings · analysis is not complete</h2><p>{partial.room.summary}</p>
      <ul>{partial.hazards.map((h) => <li key={h.id}>{h.object}: {h.evidence_observation || h.rationale}</li>)}</ul></section>}
    {report && verifying && <VerifyTimeline events={events} />}
    {report && <ReportView report={report} fixcards={fixcards} verification={verification} readOnly={readOnly || verifying} example={example} />}
    {report && !readOnly && <History scanId={scanId} verifyId={verification?.verify_id} />}
    {report && !readOnly && <button className="ghost danger no-print" disabled={deleting} onClick={() => void remove()}>{deleting ? 'Deleting…' : 'Delete scan and all media'}</button>}
    {deleteError && <p className="error">{deleteError}</p>}
  </main>
}

function useElapsed(running: boolean) {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    if (!running) return
    const started = Date.now()
    const timer = window.setInterval(() => setElapsed((Date.now() - started) / 1000), 500)
    return () => window.clearInterval(timer)
  }, [running])
  return elapsed
}

const VERDICT = { fixed: 'Visible change confirmed', not_fixed: 'Still visible', cannot_verify: 'Need another view / Manual review needed' }
function VerifyTimeline({ events }: { events: TimelineEvent[] }) {
  return <section className="stage" aria-live="polite"><div className="stage-head"><div><h1>Comparing re-filmed evidence…</h1><p>Checking object identity and the relevant visible change.</p></div></div>
    <div className="log">{events.filter((e) => e.step === 'verify.hazard').map((e) => <div className="log-item" key={String(e.hazard_id)}><h3>{String(e.object)}</h3><p>{VERDICT[e.verdict as keyof typeof VERDICT]}</p></div>)}
      {!events.some((e) => e.step === 'verify.hazard') && <div className="log-item wait"><h3>Muse Spark is comparing views</h3><p>Same object? Relevant visible change? Before-condition visible?</p></div>}</div></section>
}
