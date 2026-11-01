// Live narration: mic audio -> 24 kHz PCM s16le -> /api/voice (server proxy to Muse Voice Transcribe).

const WORKLET = `
class PcmWriter extends AudioWorkletProcessor {
  constructor() { super(); this.buf = new Int16Array(1920); this.n = 0 }   // 80 ms at 24 kHz
  process(inputs) {
    const ch = inputs[0][0]
    if (!ch) return true
    for (let i = 0; i < ch.length; i++) {
      const s = Math.max(-1, Math.min(1, ch[i]))
      this.buf[this.n++] = s < 0 ? s * 0x8000 : s * 0x7fff
      if (this.n === this.buf.length) { this.port.postMessage(this.buf.buffer.slice(0)); this.n = 0 }
    }
    return true
  }
}
registerProcessor('pcm-writer', PcmWriter)`

export interface VoiceHandlers {
  onPartial: (text: string) => void
  onTurn: (text: string) => void
  onError: (message: string) => void
}

export interface VoiceSession { stop: () => Promise<void> }

export async function startVoice(stream: MediaStream, h: VoiceHandlers): Promise<VoiceSession> {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/api/voice`)
  ws.binaryType = 'arraybuffer'
  let ctx: AudioContext | null = null
  let source: MediaStreamAudioSourceNode | null = null
  let node: AudioWorkletNode | null = null
  let ready = false
  let stopped = false
  let stopPromise: Promise<void> | null = null
  let closed: () => void = () => {}
  const done = new Promise<void>((resolve) => { closed = resolve })
  const cleanup = async () => {
    ready = false
    source?.disconnect(); node?.disconnect()
    if (node) node.port.onmessage = null
    stream.getTracks().forEach((t) => t.stop())
    if (ctx && ctx.state !== 'closed') await ctx.close().catch(() => {})
  }
  ws.onclose = () => { closed(); void cleanup() }
  ws.onerror = () => { h.onError('Voice connection failed'); ws.close(); void cleanup() }
  ws.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data as string)
      if (event.type === 'ready') ready = !stopped
      else if (event.type === 'transcript' && !event.final) h.onPartial(event.transcript)
      else if (event.type === 'speechComplete') { h.onTurn(event.transcript); h.onPartial('') }
      else if (event.type === 'error') { h.onError(event.message); ws.close(); void cleanup() }
    } catch { h.onError('Invalid narration response') }
  }
  const url = URL.createObjectURL(new Blob([WORKLET], { type: 'application/javascript' }))
  try {
    ctx = new AudioContext({ sampleRate: 24000 })
    await ctx.audioWorklet.addModule(url)
    if (ws.readyState === WebSocket.CLOSED) throw new Error('Narration connection closed')
    source = ctx.createMediaStreamSource(new MediaStream(stream.getAudioTracks()))
    node = new AudioWorkletNode(ctx, 'pcm-writer')
    node.port.onmessage = (e) => { if (ready && ws.readyState === WebSocket.OPEN) ws.send(e.data) }
    source.connect(node)
    await ctx.resume()
  } catch (e) { await cleanup(); ws.close(); throw e }
  finally { URL.revokeObjectURL(url) }
  return { stop() {
    if (stopPromise) return stopPromise
    stopped = true
    stopPromise = (async () => {
      await cleanup()
      let timer = 0
      try {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('end')
          await Promise.race([done, new Promise<void>((resolve) => { timer = window.setTimeout(resolve, 8000) })])
        }
      } finally { window.clearTimeout(timer); ws.close() }
    })()
    return stopPromise
  } }
}
