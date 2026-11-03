import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import Home from './Home'
import Capture from './Capture'
import * as api from './api'

vi.mock('./api', async (original) => ({ ...await original<typeof api>(),
  listScans: vi.fn().mockResolvedValue([]),
  listExamples: vi.fn().mockResolvedValue([{ id: 'hypersim-bedroom', scan_id: 'hypersimbedroom', title: 'A synthetic bedroom walkthrough',
    description: 'Sample', license: 'CC BY-SA 3.0', source_url: 'https://example.org', synthetic: true }]),
  runExample: vi.fn(), uploadScan: vi.fn().mockResolvedValue('newscan'), ensureSession: vi.fn().mockResolvedValue(undefined) }))

it('leads with recording or uploading your own video; the sample stays one tap away', async () => {
  render(<Home />)
  const record = screen.getByText('Record a room')
  const upload = screen.getByText('Upload a video')
  const sampleButton = await screen.findByText('Open sample report')
  // Own-video actions come before the sample in document order.
  expect(record.compareDocumentPosition(sampleButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(upload.compareDocumentPosition(sampleButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(screen.getByText('View sample report').getAttribute('href')).toBe('#/scan/hypersimbedroom')
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
  fireEvent.click(await screen.findByText(/Run the sample analysis/))
  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('Daily scan limit')
  expect(alert.closest('.sample')).not.toBeNull()
})
