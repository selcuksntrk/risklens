import { useEffect, useRef, useState } from 'react'
import { go } from './App'
import { uploadScan, uploadVerify } from './api'
import { startVoice, type VoiceSession } from './voice'

const MAX_SECONDS = 60
const TIPS = [
  'Start at the door, then pan slowly around the room.',
  'Show the wall above the bed and the tops of tall furniture.',
  'Say what the room is: "bedroom, kids sleep here".',
]

function pickMime(): string {
  for (const type of ['video/mp4;codecs=avc1', 'video/mp4', 'video/webm;codecs=vp9', 'video/webm']) {
    if (MediaRecorder.isTypeSupported(type)) return type
  }
  return ''
}

export default function Capture({ verifyScanId }: { verifyScanId?: string }) {
  const video = useRef<HTMLVideoElement>(null)
  const stream = useRef<MediaStream | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const voice = useRef<VoiceSession | null>(null)
  const chunks = useRef<Blob[]>([])
  const turnsRef = useRef<string[]>([])
  const [cameraReady, setCameraReady] = useState(false)
  const [error, setError] = useState('')
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [turns, setTurns] = useState<string[]>([])
  const [partial, setPartial] = useState('')
  const [busy, setBusy] = useState('')

  useEffect(() => {
    navigator.mediaDevices?.getUserMedia({
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: { echoCancellation: true, noiseSuppression: true },
    }).then((s) => {
      stream.current = s
      if (video.current) video.current.srcObject = s
      setCameraReady(true)
    }).catch((e) => setError(`Camera unavailable (${e.name}). You can upload a video instead.`))
    return () => stream.current?.getTracks().forEach((t) => t.stop())
  }, [])

  useEffect(() => {
    if (!recording) return
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(timer)
  }, [recording])

  useEffect(() => { if (recording && seconds >= MAX_SECONDS) void stop() }, [recording, seconds])

  async function start() {
    if (!stream.current) return
    chunks.current = []
    turnsRef.current = []
    setTurns([]); setPartial(''); setSeconds(0)
    const rec = new MediaRecorder(stream.current, { mimeType: pickMime(), videoBitsPerSecond: 4_000_000 })
    rec.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data) }
    rec.start(1000)
    recorder.current = rec
    setRecording(true)
    try {
      voice.current = await startVoice(stream.current, {
        onPartial: setPartial,
        onTurn: (t) => { turnsRef.current = [...turnsRef.current, t]; setTurns(turnsRef.current) },
        onError: (m) => setError(`Narration: ${m}`),
      })
    } catch (e) {
      setError(`Narration unavailable: ${(e as Error).message}`)
    }
  }

  async function stop() {
    const rec = recorder.current
    if (!rec || rec.state === 'inactive') return
    setRecording(false)
    setBusy('Finishing narration…')
    const stopped = new Promise((r) => { rec.onstop = r })
    rec.stop()
    await Promise.all([stopped, voice.current?.stop()])
    const type = (rec.mimeType || 'video/webm').split(';')[0]
    await send(new Blob(chunks.current, { type }), type, turnsRef.current.join(' '))
  }

  async function send(blob: Blob, type: string, narration: string) {
    setBusy('Uploading…')
    try {
      const name = `room.${type.includes('mp4') ? 'mp4' : 'webm'}`
      if (verifyScanId) {
        const vid = await uploadVerify(verifyScanId, blob, name)
        go(`scan/${verifyScanId}/v/${vid}`)
      } else {
        go(`scan/${await uploadScan(blob, name, narration)}`)
      }
    } catch (e) {
      setBusy(''); setError((e as Error).message)
    }
  }

  async function onFile(file: File | undefined) {
    if (!file) return
    await send(file, file.type, '')
  }

  return (
    <main className="capture">
      <video ref={video} autoPlay playsInline muted />
      <div className="capture-top">
        <button className="ghost" onClick={() => go(verifyScanId ? `scan/${verifyScanId}` : '')} aria-label="Back">‹ Back</button>
        {recording && <span className="rec">● {seconds}s / {MAX_SECONDS}s</span>}
      </div>
      <div className="capture-bottom">
        {!recording && !busy && (verifyScanId
          ? <p className="tip"><b>Verify your fixes.</b> Film the same room again, slowly, showing each fixed item and where it is attached.</p>
          : <p className="tip">{TIPS[0]} {TIPS[1]} {TIPS[2]}</p>)}
        {(turns.length > 0 || partial) && (
          <p className="narration">
            <span className="tag">Muse Voice Transcribe</span>
            {turns.join(' ')} <em>{partial}</em>
          </p>
        )}
        {error && <p className="error">{error}</p>}
        {busy ? <p className="busy">{busy}</p> : (
          <div className="controls">
            <label className="ghost file">
              Upload video
              <input type="file" accept="video/*" onChange={(e) => onFile(e.target.files?.[0])} hidden />
            </label>
            <button className={`shutter ${recording ? 'on' : ''}`} disabled={!cameraReady}
              onClick={recording ? stop : start} aria-label={recording ? 'Stop' : 'Record'} />
            <span className="spacer" />
          </div>
        )}
      </div>
    </main>
  )
}
