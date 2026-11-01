import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { ReportView } from './Scan'
import Capture from './Capture'
import * as api from './api'
vi.mock('./api', async (original) => ({ ...await original<typeof api>(), uploadScan: vi.fn(), ensureSession: vi.fn().mockResolvedValue(undefined) }))
const hazard = { id: 'h1', mark: '1', evidence_frame: '0', track: null, object: 'Cabinet', severity: 'high', relation: 'tall_tip_over', evidence_status: 'needs_check',
  evidence_observation: 'Attachment is hidden', evidence_image: 'evidence/h1.jpg', rationale: 'Check the attachment',
  next_view_request: 'Show the rear attachment', tracking_supported: false, fix: { source_status: 'source_unverified',
    actions: ['Do not show this instruction'], action_sources: [], fema_sections: [], diy: true, cost: '$10', minutes: 5, priority: 1 },
} as api.Hazard
const report = { scan_id: 'room', schema_version: 2, room: { type: 'office', summary: 'Room', risk_score: 0 },
  hazards: [hazard], assessment: { status: 'incomplete', warnings: ['Tracking failed'] }, disclaimer: 'Prototype',
} as api.Report
it('withholds unsupported instructions, DIY and image generation, and never displays the old risk score', () => {
  render(<ReportView report={report} fixcards={['h1']} verification={null} />)
  expect(screen.queryByText('Do not show this instruction')).toBeNull()
  expect(screen.queryByText('DIY')).toBeNull()
  expect(screen.queryByText('Illustrate recommendation')).toBeNull()
  expect(screen.queryByText('AI fix illustration')).toBeNull()
  expect(screen.queryByText(/\/100|Low risk/)).toBeNull()
  expect(screen.getByText('Tracking failed')).toBeDefined()
  fireEvent.click(screen.getByText('Show this detail'))
  expect(location.hash).toBe('#/verify/room/h1')
})
it('shows zero confirmations neutrally and explicitly identifies unchecked findings', () => {
  const verification = { schema_version: 2, fixed: 0, verify_id: 'v1', created_at: '2026-10-31', results: {}, unchecked_hazard_ids: ['h1'] } as api.Verification
  const { container } = render(<ReportView report={report} fixcards={[]} verification={verification} />)
  expect(container.querySelector('.verified-card')).toBeNull()
  expect(screen.getByText(/1 findings not examined/)).toBeDefined()
})
it('keeps gallery filename, MIME, blob and idempotency key when retrying an upload', async () => {
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:test'), revokeObjectURL: vi.fn() }))
  vi.mocked(api.uploadScan).mockRejectedValueOnce(new Error('Network interrupted')).mockResolvedValueOnce('newscan')
  const { unmount } = render(<Capture />)
  const file = new File(['video'], 'holiday.MOV', { type: 'video/quicktime' })
  fireEvent.change(screen.getByLabelText('Upload video'), { target: { files: [file] } })
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Bedroom context' } })
  expect(api.uploadScan).not.toHaveBeenCalled()
  fireEvent.click(screen.getByText('Use video'))
  await screen.findByText('Network interrupted')
  fireEvent.click(screen.getByText('Retry upload'))
  await waitFor(() => expect(api.uploadScan).toHaveBeenCalledTimes(2))
  const [first, retry] = vi.mocked(api.uploadScan).mock.calls
  expect(first).toEqual(retry)
  expect(first.slice(0, 3)).toEqual([file, 'holiday.MOV', 'Bedroom context'])
  expect(first[0].type).toBe('video/quicktime')
  unmount()
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test')
  vi.unstubAllGlobals()
})

it('microphone denial does not block video, stop is single-use and tracks are released', async () => {
  const stopTrack = vi.fn()
  const camera = { getTracks: () => [{ stop: stopTrack }] }
  const getUserMedia = vi.fn().mockResolvedValueOnce(camera).mockRejectedValueOnce(new Error('Microphone denied'))
  vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } })
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:recording'), revokeObjectURL: vi.fn() }))
  const stopped = vi.fn()
  class Recorder {
    static isTypeSupported() { return true }
    mimeType = 'video/mp4'; state = 'inactive'
    ondataavailable: ((e: { data: Blob }) => void) | null = null
    onstop: (() => void) | null = null
    start() { this.state = 'recording' }
    stop() { stopped(); this.state = 'inactive'; this.ondataavailable?.({ data: new Blob(['video']) }); this.onstop?.() }
  }
  vi.stubGlobal('MediaRecorder', Recorder)
  const { unmount } = render(<Capture />)
  fireEvent.click(screen.getByText('Optional live narration'))
  fireEvent.click(screen.getByText('Enable camera'))
  await screen.findByText('Record')
  expect(getUserMedia.mock.calls[0][0].audio).toBe(false)
  fireEvent.click(screen.getByText('Record'))
  await screen.findByText('Narration unavailable. You can still record and type room context.')
  const stop = screen.getByText('Stop recording')
  fireEvent.click(stop); fireEvent.click(stop)
  await screen.findByText('Use video')
  expect(stopped).toHaveBeenCalledTimes(1)
  expect(stopTrack).toHaveBeenCalled()
  unmount()
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:recording')
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})
