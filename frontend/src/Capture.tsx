import { useEffect, useRef, useState } from 'react'
import { go, takePendingUpload, VIDEO_ACCEPT } from './routing'
import { uploadScan, uploadVerify, getScan, fileUrl, newUploadKey, ensureSession, type Hazard } from './api'
import { startVoice, type VoiceSession } from './voice'
import { Fold } from './components'

const MAX_SECONDS = 60
function pickMime(): string {
  for (const type of ['video/mp4;codecs=avc1', 'video/mp4', 'video/webm;codecs=vp9', 'video/webm'])
    if (MediaRecorder.isTypeSupported(type)) return type
  return ''
}
type Phase = 'ready' | 'recording' | 'finishing' | 'preview' | 'uploading'
type Selected = { blob: Blob; filename: string; url: string; key: string }

export default function Capture({ verifyScanId, hazardId }: { verifyScanId?: string; hazardId?: string }) {
  const video = useRef<HTMLVideoElement>(null)
  const stream = useRef<MediaStream | null>(null)
  const microphone = useRef<MediaStream | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const voice = useRef<VoiceSession | null>(null)
  const mounted = useRef(true)
  const resourceEpoch = useRef(0)
  const selectedRef = useRef<Selected | null>(null)
  const stopRef = useRef<() => Promise<void>>(async () => {})
  const stopping = useRef(false)
  const sending = useRef(false)
  const starting = useRef(false)
  const turns = useRef<string[]>([])
  const submittedContext = useRef<string | null>(null)
  const [attempted, setAttempted] = useState(false)
  const [phase, setPhase] = useState<Phase>('ready')
  const [selected, setSelected] = useState<Selected | null>(null)
  const [cameraReady, setCameraReady] = useState(false)
  const [error, setError] = useState('')
  const [seconds, setSeconds] = useState(0)
  const [context, setContext] = useState('')
  const [partial, setPartial] = useState('')
  const [narrationEnabled, setNarrationEnabled] = useState(false)
  const [target, setTarget] = useState<Hazard | null>(null)
  const [startingCamera, setStartingCamera] = useState(false)

  function stopTracks() {
    stream.current?.getTracks().forEach((t) => t.stop()); stream.current = null
    microphone.current?.getTracks().forEach((t) => t.stop()); microphone.current = null
  }
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false; resourceEpoch.current += 1
      const rec = recorder.current
      if (rec && rec.state !== 'inactive') { rec.onstop = null; rec.stop() }
      void voice.current?.stop().catch(() => {})
      stopTracks()
      if (selectedRef.current) URL.revokeObjectURL(selectedRef.current.url)
    }
  }, [])
  useEffect(() => {
    if (!verifyScanId || !hazardId) return
    let active = true
    getScan(verifyScanId).then((s) => { if (active && s.status === 'done') setTarget(s.report.hazards.find((h) => h.id === hazardId) ?? null) })
      .catch((e) => { if (active) setError((e as Error).message) })
    return () => { active = false }
  }, [verifyScanId, hazardId])
  useEffect(() => {
    if (phase !== 'recording') return
    const start = Date.now()
    const timer = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - start) / 1000)
      setSeconds(elapsed)
      if (elapsed >= MAX_SECONDS) void stopRef.current()
    }, 250)
    return () => window.clearInterval(timer)
  }, [phase])

  async function enableCamera() {
    if (startingCamera) return
    const epoch = resourceEpoch.current
    setStartingCamera(true); setError('')
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') throw new Error('Camera recording is unavailable. Upload a video instead.')
      const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false })
      if (!mounted.current || epoch !== resourceEpoch.current) { s.getTracks().forEach((t) => t.stop()); return }
      stream.current = s
      if (video.current) { video.current.srcObject = s; await video.current.play().catch(() => {}) }
      setCameraReady(true)
    } catch (e) { if (mounted.current) setError((e as Error).message) }
    finally { if (mounted.current) setStartingCamera(false) }
  }
  function select(blob: Blob, filename: string) {
    resourceEpoch.current += 1
    void voice.current?.stop().catch(() => {}); voice.current = null
    if (selectedRef.current) URL.revokeObjectURL(selectedRef.current.url)
    const next = { blob, filename, url: URL.createObjectURL(blob), key: newUploadKey() }
    selectedRef.current = next; submittedContext.current = null; setAttempted(false)
    setSelected(next); setPhase('preview'); setCameraReady(false)
    stopTracks()
    if (video.current) video.current.srcObject = null
  }
  useEffect(() => {
    const file = takePendingUpload()
    if (file) { if (!file.size) setError('The video is empty.'); else select(file, file.name) }
    else if (selectedRef.current) {
      // StrictMode re-mount in development: the cleanup above revoked the preview URL.
      const again = { ...selectedRef.current, url: URL.createObjectURL(selectedRef.current.blob) }
      selectedRef.current = again; setSelected(again)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  async function start() {
    if (!stream.current || starting.current) return
    starting.current = true; setError(''); setSeconds(0)
    const epoch = resourceEpoch.current
    turns.current = []; stopping.current = false
    try {
      if (narrationEnabled && !verifyScanId) {
        try {
          await ensureSession()
          const mic = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
          if (!mounted.current || epoch !== resourceEpoch.current) { mic.getTracks().forEach((t) => t.stop()); return }
          microphone.current = mic
          const session = await startVoice(mic, {
            onPartial: (s) => { if (mounted.current) setPartial(s) },
            onTurn: (s) => { turns.current.push(s); if (mounted.current) setContext((old) => `${old} ${s}`.trim()) },
            onError: (s) => { if (mounted.current) setError(`Narration: ${s}. Video is still available.`) },
          })
          if (!mounted.current || epoch !== resourceEpoch.current) { await session.stop(); return }
          voice.current = session
        } catch { microphone.current?.getTracks().forEach((t) => t.stop()); microphone.current = null; if (mounted.current) setError('Narration unavailable. You can still record and type room context.') }
      }
      if (!mounted.current || !stream.current || epoch !== resourceEpoch.current) return
      const mimeType = pickMime()
      const rec = new MediaRecorder(stream.current, { ...(mimeType ? { mimeType } : {}), videoBitsPerSecond: 4_000_000 })
      rec.onerror = () => { if (mounted.current) setError('The recorder stopped unexpectedly. Review any captured video or retry.') }
      const chunks: Blob[] = []
      rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
      rec.onstop = () => {
        const type = (rec.mimeType || 'video/webm').split(';')[0]
        void (async () => {
          await voice.current?.stop().catch(() => {}); voice.current = null
          if (!mounted.current) return
          const blob = new Blob(chunks, { type })
          if (!blob.size) { stopTracks(); setCameraReady(false); setError('No video was captured. Please retry or upload a file.'); setPhase('ready'); return }
          select(blob, `room.${type.includes('mp4') ? 'mp4' : 'webm'}`)
        })()
      }
      recorder.current = rec; rec.start(1000); setPhase('recording')
    } catch (e) {
      if (mounted.current) setError(`Recording unavailable: ${(e as Error).message}. Upload a video instead.`)
      await voice.current?.stop().catch(() => {}); voice.current = null
      microphone.current?.getTracks().forEach((t) => t.stop())
    } finally { starting.current = false }
  }
  async function stop() {
    const rec = recorder.current
    if (stopping.current || !rec || rec.state === 'inactive') return
    stopping.current = true; setPhase('finishing'); rec.stop()
  }
  useEffect(() => { stopRef.current = stop })
  async function send() {
    if (!selected || sending.current) return
    sending.current = true; setAttempted(true); setPhase('uploading'); setError('')
    // A retry must send identical content with its key, even if the previous response was lost.
    submittedContext.current ??= context
    try {
      if (verifyScanId) {
        const id = await uploadVerify(verifyScanId, selected.blob, selected.filename, selected.key, hazardId)
        if (mounted.current) go(`scan/${verifyScanId}/v/${id}`)
      } else {
        const id = await uploadScan(selected.blob, selected.filename, submittedContext.current, selected.key)
        if (mounted.current) go(`scan/${id}`)
      }
    } catch (e) { if (mounted.current) { setPhase('preview'); setError((e as Error).message) } }
    finally { sending.current = false }
  }
  function retake() {
    resourceEpoch.current += 1
    if (selectedRef.current) URL.revokeObjectURL(selectedRef.current.url)
    selectedRef.current = null; submittedContext.current = null; setAttempted(false); setSelected(null)
    setPhase('ready'); setError(''); setCameraReady(false)
  }
  const busy = phase === 'uploading' || phase === 'finishing'
  const tip = COACH[Math.floor(seconds / 6) % COACH.length]
  return <main className="page">
    <header className="top"><a className="back" href={`#/${verifyScanId ? `scan/${verifyScanId}` : ''}`}>‹ Back</a></header>
    <h1>{verifyScanId ? (target ? `Film the ${target.object.toLowerCase()} again` : 'Film the room again') : selected ? 'Does the video look right?' : 'Film one room'}</h1>
    {target && <div className="target"><img src={fileUrl(verifyScanId!, target.evidence_image)} alt="" />
      <p>{target.next_view_request || 'Show the item, how it is fixed or where it now stands, and a bit of what is around it.'}</p></div>}
    {verifyScanId && !target && <p className="muted">After you’ve fixed something, film it again. We compare the new video with the first one and tell you what visibly changed.</p>}
    {!selected && !verifyScanId && phase === 'ready' && <ul className="tips">
      <li>Start at the door and turn slowly, for 30–60 seconds.</li>
      <li>Show tall furniture, shelves and the wall above the bed.</li>
      <li>If you can, show where things are fixed to the wall.</li>
    </ul>}
    <div className={`camera${selected ? ' has-file' : ''}`}>
      <video ref={video} src={selected?.url} autoPlay={!selected} playsInline muted={!selected} controls={!!selected} />
      {!selected && !cameraReady && <span className="hint" aria-hidden>{startingCamera ? 'Opening the camera…' : 'Your camera will show here. Only video is recorded.'}</span>}
      {phase === 'recording' && <><span className="tip" aria-hidden key={tip}>{tip}</span>
        <span className="rec" role="status">{seconds} s of {MAX_SECONDS}</span>
        <span className="bar" style={{ width: `${Math.min(100, (seconds / MAX_SECONDS) * 100)}%` }} aria-hidden /></>}
    </div>
    {selected && <p className="fine">{selected.filename}. Make sure the room is in view, then continue.</p>}
    {partial && <p className="muted">Hearing: {partial}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {phase === 'ready' && <div className="stack">
      {!cameraReady ? <button className="btn primary block" disabled={startingCamera} onClick={() => void enableCamera()}>{startingCamera ? 'Opening the camera…' : 'Turn on the camera'}</button>
        : <button className="record-btn" onClick={() => void start()}><span className="visually-hidden">Start recording</span></button>}
      <label className="btn block" style={{ cursor: 'pointer' }}>Upload a video instead<input aria-label="Upload a video" type="file" accept={VIDEO_ACCEPT} hidden
        onChange={(e) => { const f = e.target.files?.[0]; if (f) { if (!f.size) setError('That video file is empty.'); else select(f, f.name) } e.target.value = '' }} /></label>
    </div>}
    {phase === 'recording' && <button className="record-btn stop" onClick={() => void stop()}><span className="visually-hidden">Stop recording</span></button>}
    {phase === 'preview' && <div className="stack"><button className="btn primary block" onClick={() => void send()}>{attempted ? 'Try uploading again' : verifyScanId ? 'Compare with the first video' : 'Check this room'}</button>
      <button className="btn block" onClick={retake}>Choose a different video</button></div>}
    {busy && <p role="status">{phase === 'uploading' ? 'Uploading…' : 'Finishing the recording…'}</p>}
    {!verifyScanId && (selected || phase === 'ready') && <div style={{ marginTop: 16 }}><Fold title="Add a note (optional)">
      <label className="field">Anything we can’t see in the video, like “my son sleeps here”
        <textarea maxLength={4000} value={context} disabled={busy || attempted} onChange={(e) => setContext(e.target.value)} placeholder="This is my children’s room…" /></label>
      {phase === 'ready' && <label className="checkbox"><input type="checkbox" checked={narrationEnabled} onChange={(e) => setNarrationEnabled(e.target.checked)} /> Say it out loud while filming instead</label>}
      <p className="fine">Your note helps the models understand the room. It is never treated as something seen in the video.</p>
    </Fold></div>}
    <p className="fine" style={{ marginTop: 16 }}>Try not to film people, documents or screens. Your video is processed by Meta’s AI models and stays private to this browser. <a href="#/about">Privacy details</a></p>
  </main>
}

const COACH = ['Turn slowly', 'Show the top of tall furniture', 'Show the wall above the bed', 'Show shelves and hanging lights', 'Finish facing the door']
