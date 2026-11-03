import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import Home from './Home'
import Capture from './Capture'
import * as api from './api'

vi.mock('./api', async (original) => ({ ...await original<typeof api>(),
  listScans: vi.fn().mockResolvedValue([]),
  listExamples: vi.fn().mockResolvedValue([
    { id: 'real-home', scan_id: 'realhome', kind: 'real', title: 'A real home in Istanbul', description: 'Real', license: 'Author', source_url: null, synthetic: false,
      has_poster: true, has_replay: true, top_finding: { id: 'h1', object: 'Wardrobe', severity: 'high', relation: 'tall_tip_over', evidence_status: 'needs_check' } },
    { id: 'designed-living', scan_id: 'designedliving', kind: 'synthetic', title: 'Designed scene: living room', description: 'Designed', license: 'Muse Image',
      source_url: null, synthetic: true, has_replay: false, answer_key: { designed: 5, matched: 4, hazards: [], controls: [], other_findings: [], method: 'author-matched', note: '' } }]),
  runExample: vi.fn(), uploadScan: vi.fn().mockResolvedValue('newscan'), ensureSession: vi.fn().mockResolvedValue(undefined) }))

it('leads with recording or uploading your own video; the sample stays one tap away', async () => {
  render(<Home />)
  const record = screen.getByText('Record a room')
  const upload = screen.getByText('Upload a video')
  const sampleButton = (await screen.findAllByText('Open report'))[0]
  // Own-video actions come before the sample in document order.
  expect(record.compareDocumentPosition(sampleButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(upload.compareDocumentPosition(sampleButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  // The real home leads the gallery and is labelled as real; designed scenes are labelled as AI-generated.
  expect(screen.getAllByText('Real home · Istanbul').length).toBeGreaterThan(0)
  expect(screen.getByText('AI-generated scene')).toBeDefined()
  expect(screen.getByText('Answer key: 4 of 5 designed hazards matched')).toBeDefined()
  fireEvent.click(screen.getByText('Watch analysis replay'))
  expect(location.hash).toBe('#/replay/real-home')
})

it('a file chosen on the home screen opens the capture preview ready to send', async () => {
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:home'), revokeObjectURL: vi.fn() }))
  const { unmount } = render(<Home />)
  const file = new File(['video'], 'bedroom.mp4', { type: 'video/mp4' })
  fireEvent.change(screen.getByLabelText('Upload a video from this device'), { target: { files: [file] } })
  expect(location.hash).toBe('#/capture')
  unmount()
  render(<Capture />)
  fireEvent.click(await screen.findByText('Use video'))
  await waitFor(() => expect(api.uploadScan).toHaveBeenCalledTimes(1))
  expect(vi.mocked(api.uploadScan).mock.calls[0].slice(0, 2)).toEqual([file, 'bedroom.mp4'])
  vi.unstubAllGlobals()
})

it('shows a failed sample run next to the sample, not at the top of the page', async () => {
  vi.mocked(api.runExample).mockRejectedValueOnce(new Error('Daily scan limit for this network reached.'))
  render(<Home />)
  fireEvent.click((await screen.findAllByText(/Run it live/))[0])
  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('Daily scan limit')
  expect(alert.closest('.sample')).not.toBeNull()
})
