import { useEffect, useState } from 'react'
import { go } from './routing'
import { useScan } from './useScan'
import { deleteScan, listExamples, type Example, type TimelineEvent } from './api'
import Stage from './Analysis'
import FindingDetail from './FindingDetail'
import { History, ReportView } from './Report'
import { Top } from './components'

export { ReportView } from './Report'

export default function Scan({ scanId, verifyId, findingId }: { scanId: string; verifyId?: string; findingId?: string }) {
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
    if (!window.confirm('Delete this room, its videos and its report? This can’t be undone.')) return
    setDeleting(true)
    try { await deleteScan(scanId); go('') } catch (e) { setDeleteError((e as Error).message); setDeleting(false) }
  }
  const locked = readOnly || verifying
  return <main className="page">
    <Top />
    {error && <p className="error" role="alert">{error} <button className="text-btn" onClick={retryStatus}>Check again</button></p>}
    {!report && !error && <Stage events={events} scanId={scanId} elapsed={elapsed} partial={partial} />}
    {!report && partial && error && <div className="note warn"><p><b>The check stopped before the end. This is what it found so far:</b></p>
      <ul>{partial.hazards.map((h) => <li key={h.id}>{h.object}</li>)}</ul></div>}
    {report && verifying && <VerifyProgress events={events} />}
    {report && findingId && <FindingDetail report={report} hazardId={findingId} fixcards={fixcards} verification={verification} readOnly={locked} />}
    {report && !findingId && <ReportView report={report} fixcards={fixcards} verification={verification} readOnly={locked} example={example} />}
    {report && !findingId && !readOnly && <History scanId={scanId} verifyId={verification?.verify_id} />}
    {report && !findingId && !readOnly && <p><button className="text-btn danger no-print" disabled={deleting} onClick={() => void remove()}>{deleting ? 'Deleting…' : 'Delete this room and its videos'}</button></p>}
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

const WORD = { fixed: 'change visible', not_fixed: 'looks the same', cannot_verify: 'can’t tell from this video' }
function VerifyProgress({ events }: { events: TimelineEvent[] }) {
  const rows = events.filter((e) => e.step === 'verify.hazard')
  return <section className="note" aria-live="polite"><p><b>Comparing your new video with the first one…</b></p>
    <p className="fine">Is it the same object? Is there a change you can actually see?</p>
    {rows.map((e) => <p key={String(e.hazard_id)}>{String(e.object)}: {WORD[e.verdict as keyof typeof WORD]}</p>)}</section>
}
