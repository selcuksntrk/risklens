import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useScan } from './useScan'
import * as api from './api'
vi.mock('./api', async (original) => ({ ...await original<typeof api>(), getScan: vi.fn(), getVerification: vi.fn() }))
class Source {
  static last: Source
  onerror: (() => void) | null = null
  onmessage = null
  constructor() { Source.last = this }
  addEventListener() {}
  close() {}
}
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })
it('polls the verification after SSE disconnect without showing the old result', async () => {
  vi.stubGlobal('EventSource', Source)
  vi.mocked(api.getScan).mockResolvedValue({ status: 'done', report: {} as api.Report,
    verification: { verify_id: 'old' } as api.Verification })
  vi.mocked(api.getVerification).mockResolvedValueOnce({ status: 'running' })
    .mockResolvedValue({ status: 'done', verification: { verify_id: 'new' } as api.Verification })
  const { result } = renderHook(() => useScan('scan', 'new'))
  await waitFor(() => expect(Source.last).toBeDefined())
  expect(result.current.verification).toBeNull()
  await act(async () => Source.last.onerror?.())
  await waitFor(() => expect(result.current.verification?.verify_id).toBe('new'))
  expect(result.current.verifying).toBe(false)
})
it('stops verifying on a persistent terminal error and preserves the original report', async () => {
  vi.mocked(api.getScan).mockResolvedValue({ status: 'done', report: {} as api.Report })
  vi.mocked(api.getVerification).mockResolvedValue({ status: 'interrupted', message: 'The job was interrupted.' })
  const { result } = renderHook(() => useScan('scan', 'failed'))
  await waitFor(() => expect(result.current.error).toBe('The job was interrupted.'))
  expect(result.current.verifying).toBe(false)
  expect(result.current.verification).toBeNull()
  expect(result.current.report).toBeDefined()
})
