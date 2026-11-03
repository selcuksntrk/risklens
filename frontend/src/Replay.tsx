import { useEffect, useState } from 'react'
import { replaySpeed, useReplay } from './useReplay'
import { getExampleEvents, listExamples, type Example, type TimelineEvent } from './api'
import Stage from './Analysis'
import { go } from './routing'

export default function Replay({ exampleId }: { exampleId: string }) {
  const [example, setExample] = useState<Example | null>(null)
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    Promise.all([listExamples(), getExampleEvents(exampleId)])
      .then(([list, ev]) => { if (active) { setExample(list.find((e) => e.id === exampleId) ?? null); setEvents(ev) } })
      .catch((e) => { if (active) setError((e as Error).message) })
    return () => { active = false }
  }, [exampleId])
  const total = events.reduce((m, e) => Math.max(m, Number(e.t) || 0), 0)
  const speed = replaySpeed(total)
  const { clock, visible, finished } = useReplay(events, speed)
  const report = () => example && go(`scan/${example.scan_id}`)
  return <main className="page wide">
    <header className="bar"><button className="ghost" onClick={() => go('')}>‹ Home</button>
      <span className="muted">{example?.title ?? 'Sample'}</span></header>
    {error && <p className="error" role="alert">{error}</p>}
    {example && <Stage events={visible} scanId={example.scan_id} elapsed={clock}
      title={finished ? 'Analysis complete' : 'Replaying the analysis'}
      subtitle="The same events the Meta models produced during the recorded run, in their original order."
      banner={<div className="replay-banner" role="note">
        <span><b>Replay of a recorded run</b> · {Math.round(total)} s shown at {speed}× · no new model calls{example.synthetic ? ' · AI-generated scene' : ' · real home, photos blurred'}</span>
        <button className={finished ? 'primary' : 'ghost'} onClick={report}>{finished ? 'Open the report' : 'Skip to report'}</button>
      </div>} />}
  </main>
}
