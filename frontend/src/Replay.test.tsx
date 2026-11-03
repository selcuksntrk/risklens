import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { replaySpeed, useReplay } from './useReplay'
import type { TimelineEvent } from './api'

afterEach(() => vi.useRealTimers())
it('replays recorded events in order on a compressed clock and finishes at the recorded end', () => {
  vi.useFakeTimers()
  const events: TimelineEvent[] = [{ step: 'ingest.done', t: 1 }, { step: 'planner.done', t: 12 }, { step: 'fixer.done', t: 96 }]
  const speed = replaySpeed(96)
  expect(speed).toBe(4)
  const { result } = renderHook(() => useReplay(events, speed))
  expect(result.current.visible).toHaveLength(0)
  act(() => { vi.advanceTimersByTime(3500) })
  expect(result.current.visible.map((e) => e.step)).toEqual(['ingest.done', 'planner.done'])
  expect(result.current.finished).toBe(false)
  act(() => { vi.advanceTimersByTime(30000) })
  expect(result.current.finished).toBe(true)
  expect(result.current.visible).toHaveLength(3)
})
