import { useEffect, useState } from 'react'
import type { TimelineEvent } from './api'

/** Plays stored events on a compressed clock. No model calls; the banner says so and states the real duration. */
export function useReplay(events: TimelineEvent[], speed: number) {
  const [clock, setClock] = useState(0)
  const total = events.reduce((m, e) => Math.max(m, Number(e.t) || 0), 0)
  useEffect(() => {
    if (!events.length) return
    const started = performance.now()
    const timer = window.setInterval(() => {
      const t = ((performance.now() - started) / 1000) * speed
      setClock(Math.min(t, total))
      if (t >= total) window.clearInterval(timer)
    }, 100)
    return () => window.clearInterval(timer)
  }, [events, speed, total])
  return { clock, total, visible: events.filter((e) => Number(e.t) <= clock), finished: !!events.length && clock >= total }
}

export const replaySpeed = (total: number) => Math.max(1, Math.round(total / 24))

