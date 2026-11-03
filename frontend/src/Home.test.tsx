import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import Home from './Home'
import Capture from './Capture'
import * as api from './api'

vi.mock('./api', async (original) => ({ ...await original<typeof api>(),
  listScans: vi.fn().mockResolvedValue([]),
  listExamples: vi.fn().mockResolvedValue([
    { id: 'real-home', scan_id: 'realhome', kind: 'real', room: 'bedroom', title: 'A real home', description: '', license: 'Author', source_url: null, synthetic: false,
      findings: 3, has_poster: true, has_replay: true, seconds: 100, cost_usd: 0.28 },
    { id: 'designed-living', scan_id: 'designedliving', kind: 'synthetic', room: 'living_room', title: 'Designed', description: '', license: 'Muse Image',
      source_url: null, synthetic: true, findings: 6, answer_key: { designed: 5, matched: 4, hazards: [], controls: [], other_findings: [], method: '', note: '' } }]),
  getExampleEvents: vi.fn().mockResolvedValue([
    { step: 'ingest.done', t: 1, keyframes: [1, 2, 3] }, { step: 'planner.done', t: 12, concepts: ['wardrobe', 'suitcase'] },
    { step: 'marks.done', t: 30, objects: { 1: 'wardrobe', 2: 'suitcase' }, images: ['marked/1.jpg'] }]),
  runExample: vi.fn(), uploadScan: vi.fn().mockResolvedValue('newscan'), ensureSession: vi.fn().mockResolvedValue(undefined) }))

it('leads with filming your own room; examples follow, with the test rooms explained once', async () => {
  render(<Home />)
  const record = screen.getByText('Record a room')
  const example = await screen.findByText('Real home, Istanbul')
  expect(record.compareDocumentPosition(example) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(screen.getByText(/The other three are test rooms we made with Muse Image/)).toBeDefined()
  expect(screen.getByText('4 of 5 planted hazards found')).toBeDefined()
  expect(example.closest('a')!.getAttribute('href')).toBe('#/scan/realhome')
})

it('explains each Meta model with the numbers of the real recorded run', async () => {
  render(<Home />)
  expect(await screen.findByText(/In the real example: wardrobe, suitcase/)).toBeDefined()
  expect(screen.getByText('SAM 3.1 follows each object through the video')).toBeDefined()
  expect(screen.getByText(/2 objects in the real example/)).toBeDefined()
  expect(screen.getByText('Muse Image 1.0, when you want a picture')).toBeDefined()
  expect(screen.getByText('Watch a real run').getAttribute('href')).toBe('#/replay/real-home')
})

it('a file chosen on the home screen opens the capture preview ready to send', async () => {
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:home'), revokeObjectURL: vi.fn() }))
  const { unmount } = render(<Home />)
  const file = new File(['video'], 'bedroom.mp4', { type: 'video/mp4' })
  fireEvent.change(screen.getByLabelText('Upload a video from this device'), { target: { files: [file] } })
  expect(location.hash).toBe('#/capture')
  unmount()
  render(<Capture />)
  fireEvent.click(await screen.findByText('Check this room'))
  await waitFor(() => expect(api.uploadScan).toHaveBeenCalledTimes(1))
  expect(vi.mocked(api.uploadScan).mock.calls[0].slice(0, 2)).toEqual([file, 'bedroom.mp4'])
  vi.unstubAllGlobals()
})
