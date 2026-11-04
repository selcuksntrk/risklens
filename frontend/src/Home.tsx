import { useEffect, useState } from 'react'
import { go, startUpload, VIDEO_ACCEPT } from './routing'
import { listScans, listExamples, getExampleEvents, exampleMedia, fileUrl, ROOM_LABELS, type ScanRow, type Example, type TimelineEvent } from './api'
import { Top } from './components'
import { MODELS, PRIORITY, cap } from './ui'

const REPO = 'https://github.com/selcuksntrk/risklens'

export default function Home() {
  const [scans, setScans] = useState<ScanRow[]>([])
  const [examples, setExamples] = useState<Example[]>([])
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    Promise.all([listScans(), listExamples()]).then(([s, e]) => {
      if (!active) return
      setScans(s); setExamples(e)
      const real = e.find((x) => x.kind === 'real' && x.has_replay)
      if (real) getExampleEvents(real.id).then((ev) => { if (active) setEvents(ev) }).catch(() => {})
    }).catch((e) => { if (active) setError((e as Error).message) })
    return () => { active = false }
  }, [])
  const real = examples.find((e) => e.kind === 'real')

  return <main className="page wide">
    <Top />
    <section className="intro" aria-labelledby="title"><div>
      <h1 id="title">What in this room could fall when the ground shakes?</h1>
      <p>Film a room for about a minute. RiskLens points out what could fall, tip over or block your way out, shows you the exact frame, and tells you what to do next.</p>
      <div className="stack">
        <button className="btn primary block" onClick={() => go('capture')}>Record a room</button>
        <label className="btn block" style={{ cursor: 'pointer' }}>Upload a video
          <input className="visually-hidden" type="file" accept={VIDEO_ACCEPT} aria-label="Upload a video from this device"
            onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) startUpload(f) }} /></label>
      </div>
      <p className="fine">Takes 2–3 minutes. No account. Your video stays private to this browser.</p>
    </div>
      {real?.has_poster && <a className="intro-photo" href={`#/scan/${real.scan_id}`}>
        <img src={exampleMedia(real.id, 'poster.jpg')} alt="A frame from a real scan: a wardrobe with suitcases on top, boxed by SAM 3.1" fetchPriority="high" />
        <span>From a real scan in Istanbul: {real.top_finding ? cap(real.top_finding.object) : 'see the report'}{real.top_finding ? `, ${PRIORITY[real.top_finding.severity].toLowerCase()}` : ''} →</span>
      </a>}
    </section>

    {error && <p className="error" role="alert">{error}</p>}

    {scans.length > 0 && <section className="section" aria-labelledby="scans-title">
      <div className="section-title"><h2 id="scans-title">Your rooms</h2></div>
      <ul className="scans">{scans.map((s) => <li key={s.scan_id}><a href={`#/scan/${s.scan_id}`}>
        <span><b>{ROOM_LABELS[s.room] ?? 'Room'}</b><small>{s.hazards} {s.hazards === 1 ? 'thing' : 'things'} to check · {new Date(s.created_at).toLocaleDateString()}</small></span><span aria-hidden>›</span>
      </a></li>)}</ul>
    </section>}

    {examples.length > 0 && <section className="section" id="examples" aria-labelledby="examples-title">
      <div className="section-title"><h2 id="examples-title">Not ready to film? See an example</h2></div>
      <ul className="examples">{examples.map((e, i) => <li key={e.id}><ExampleCard example={e} eager={i < 2} /></li>)}</ul>
      <p className="fine">The first is a real flat in Istanbul. The other three are test rooms we made with Muse Image, with hazards placed on purpose so we know what should be found. <a href="#/about#examples">More about the examples</a></p>
    </section>}

    <Process real={real} events={events} />

    <footer className="foot">
      <span>Your rooms are private to this browser. Videos are deleted after 7 days, reports after 30, or whenever you choose.</span>
      <span><a href="#/about">How it works and its limits</a> · <a href={REPO} target="_blank" rel="noreferrer">Source code</a> · Built for the Meta AI Developer Hackathon · {import.meta.env.VITE_RISKLENS_VERSION ?? 'dev'}</span>
    </footer>
  </main>
}

function ExampleCard({ example, eager }: { example: Example; eager: boolean }) {
  const key = example.answer_key
  const name = example.kind === 'real' ? 'Real home, Istanbul' : ROOM_LABELS[example.room ?? ''] ?? example.title
  const line = key ? `${key.matched} of ${key.designed} planted hazards found` : `${example.findings ?? 0} things to check`
  return <a className="example" href={`#/scan/${example.scan_id}`}>
    <div className="example-photo">
      {example.has_poster && <img src={exampleMedia(example.id, 'poster.jpg')} alt="" loading={eager ? 'eager' : 'lazy'} decoding="async" />}
    </div>
    <b>{name}</b><span>{line}</span>
  </a>
}

/** What each Meta model does, told with the numbers and frames of the real recorded run. */
function Process({ real, events }: { real?: Example; events: TimelineEvent[] }) {
  const find = (step: string) => events.find((e) => e.step === step)
  const ingest = find('ingest.done'), planner = find('planner.done'), marks = find('marks.done')
  const concepts = (planner?.concepts as string[] | undefined) ?? []
  const tracked = Object.keys((marks?.objects as Record<string, string> | undefined) ?? {}).length
  const keyframes = (ingest?.keyframes as number[] | undefined)?.length
  const marked = (marks?.images as string[] | undefined) ?? []
  const frame = marked[Math.min(2, marked.length - 1)]
  return <section className="section" id="how" aria-labelledby="how-title">
    <div className="section-title"><h2 id="how-title">What happens to your video</h2>
      {real?.has_replay && <a href={`#/replay/${real.id}`}>Watch a real run</a>}</div>
    <ol className="process">
      <li>
        <div><b>{MODELS.spark} decides what to look at</b>
          <p>It studies {keyframes ?? 'about ten'} still frames and picks the objects that matter in this kind of room.
            {concepts.length > 0 && <> In the real example: {concepts.slice(0, 5).join(', ')}.</>}</p></div>
      </li>
      <li>
        {frame && real && <img src={fileUrl(real.scan_id, frame)} alt="A frame where SAM 3.1 has boxed the objects it is following" loading="lazy" />}
        <div><b>{MODELS.sam} follows each object through the video</b>
          <p>Every object gets a box on the exact frames where it appears{tracked ? ` (${tracked} objects in the real example)` : ''}, so each finding points to something you can see.</p></div>
      </li>
      <li>
        {real?.has_poster && <img src={exampleMedia(real.id, 'poster.jpg')} alt="The frame behind the top finding in the real example" loading="lazy" />}
        <div><b>{MODELS.spark} checks what could fall, tip over or block the way</b>
          <p>It keeps what it could see apart from what it couldn't, like whether a wardrobe is fixed to the wall.</p></div>
      </li>
      <li>
        <div><b>Next steps from FEMA E-74</b>
          <p>Spark looks up the US guide to non-structural earthquake hazards and links each step to the section it read. If the source check fails, no step is shown.</p></div>
      </li>
      <li>
        <div><b>{MODELS.image}, when you want a picture</b>
          <p>It can show what a fix might look like, always labelled as AI-made. We also used it to build the three test rooms above.</p></div>
      </li>
    </ol>
  </section>
}
