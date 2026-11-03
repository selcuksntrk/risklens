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
  fireEvent.click(screen.getByText('Re-film this item'))
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

it('shows a same-file guard reason once, not as both change and rationale', () => {
  const reason = 'This is the original video. It cannot demonstrate a new physical change.'
  const check = { verdict: 'cannot_verify', what_changed: reason, rationale: reason, next_view_request: 'Show the original object' }
  const verification = { schema_version: 2, fixed: 0, verify_id: 'v1', created_at: '2026-11-03', results: { h1: check }, unchecked_hazard_ids: [] } as unknown as api.Verification
  const { container } = render(<ReportView report={report} fixcards={[]} verification={verification} />)
  expect(container.querySelector('.verdict')!.textContent!.split(reason).length - 1).toBe(1)
})

it('hides placeholder requested views such as "none"', async () => {
  const { hasRequest } = await import('./api')
  expect(hasRequest('none')).toBe(false)
  expect(hasRequest(' None. ')).toBe(false)
  expect(hasRequest('N/A')).toBe(false)
  expect(hasRequest('Film the wardrobe top')).toBe(true)
})

it('shows the designed-scene answer key with misses, and labels it as one designed scene', () => {
  const example = { id: 'd', scan_id: 'room', title: 'Designed', description: '', license: 'Muse Image', source_url: null, synthetic: true, kind: 'synthetic',
    answer_key: { designed: 2, matched: 1, method: 'author-matched', note: '', controls: [{ object: 'dresser', label: 'Strapped dresser' }], other_findings: [],
      hazards: [{ id: 'L1', object: 'vitrin', label: 'Glass cabinet', relation: 'tall_tip_over', matched_finding: 'h1' },
                { id: 'L2', object: 'tv', label: 'Unstrapped TV', relation: 'tall_tip_over', matched_finding: null }] } } as api.Example
  render(<ReportView report={report} fixcards={[]} verification={null} readOnly example={example} />)
  expect(screen.getByText('1/2')).toBeDefined()
  expect(screen.getByText('Found as “Cabinet”')).toBeDefined()
  expect(screen.getByText('Not reported by RiskLens')).toBeDefined()
  expect(screen.getByText(/not an accuracy measurement for real homes/)).toBeDefined()
  expect(screen.getByText('AI-generated scene')).toBeDefined()
  expect(screen.queryByText('Re-film this item')).toBeNull()
})
