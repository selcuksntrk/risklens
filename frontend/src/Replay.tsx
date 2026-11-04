import { useEffect, useState } from 'react'
import { replaySpeed, useReplay } from './useReplay'
import { getExampleEvents, listExamples, type Example, type TimelineEvent } from './api'
import Stage from './Analysis'
import { go } from './routing'
import { Top } from './components'

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
  return <main className="page">
    <Top />
    {error && <p className="error" role="alert">{error}</p>}
    {example && <Stage events={visible} scanId={example.scan_id} elapsed={clock}
      title={finished ? 'Done' : example.synthetic ? 'Replay: an AI-made test room' : 'Replay: a real flat in Istanbul'}
      subtitle="This is a recording of an earlier run, played back faster. Nothing new is sent to the models."
      banner={<div className="replay" role="note">
        <span>Recorded run · {Math.round(total)} s shown {speed}× faster</span>
        <button className={finished ? 'btn primary small' : 'text-btn'} onClick={report}>{finished ? 'See the report' : 'Skip to the report'}</button>
      </div>} />}
  </main>
}
