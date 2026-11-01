import { useEffect, useState } from 'react'
import { ApiError, getScan, getVerification, type PartialReport, type Report, type TimelineEvent, type Verification } from './api'

export function useScan(scanId: string, verifyId?: string) {
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [partial, setPartial] = useState<PartialReport | null>(null)
  const [fixcards, setFixcards] = useState<string[]>([])
  const [verification, setVerification] = useState<Verification | null>(null)
  const [verifying, setVerifying] = useState(!!verifyId)
  const [readOnly, setReadOnly] = useState(false)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let source: EventSource | null = null
    let timer = 0
    let cancelled = false
    let polling = false
    let terminal = false
    let attempts = 0
    const fail = (message: string) => { terminal = true; source?.close(); setError(message); setVerifying(false) }
    const poll = async () => {
      if (cancelled || terminal || polling) return
      window.clearTimeout(timer)
      polling = true
      try {
        const scan = await getScan(scanId)
        if (cancelled) return
        if (scan.status !== 'done') {
          setPartial(scan.partial ?? null)
          if (scan.status === 'error' || scan.status === 'interrupted') { fail(scan.message); return }
        } else {
          setReport(scan.report); setReadOnly(!!scan.read_only); setFixcards(scan.fixcards ?? []); setPartial(null)
          if (!verifyId) { setVerification(scan.verification ?? null); terminal = true }
          else {
            const check = await getVerification(scanId, verifyId)
            if (cancelled) return
            if (check.status === 'error' || check.status === 'interrupted') { fail(check.message); return }
            if (check.status === 'done') { setVerification(check.verification); setVerifying(false); terminal = true }
          }
        }
        setError('')
        if (terminal) source?.close()
        else if (!source) {
          source = new EventSource(`/api/scans/${verifyId ?? scanId}/events`)
          source.onmessage = (e) => {
            if (cancelled) return
            try { const event = JSON.parse(e.data) as TimelineEvent; if (event.step !== 'heartbeat') setEvents((all) => [...all.slice(-249), event]) } catch { /* polling is authoritative */ }
          }
          source.addEventListener('end', () => { source?.close(); void poll() })
          source.onerror = () => { source?.close(); void poll() }
        }
      } catch (e) {
        if (!cancelled) {
          if (e instanceof ApiError && [401, 403, 404, 410].includes(e.status)) { fail(e.message); return }
          setError((e as Error).message)
        }
      } finally {
        polling = false
        if (!cancelled && !terminal) {
          if (++attempts >= 240) fail('Status could not be confirmed. Retry checking; do not upload again.')
          else timer = window.setTimeout(() => void poll(), 3000)
        }
      }
    }
    void poll()
    return () => { cancelled = true; source?.close(); window.clearTimeout(timer) }
  }, [scanId, verifyId, retry])
  return { events, report, partial, fixcards, verification, verifying, readOnly, error, retryStatus: () => { setVerifying(!!verifyId); setError(''); setRetry((n) => n + 1) } }
}
