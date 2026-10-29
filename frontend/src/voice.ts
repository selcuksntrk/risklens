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
  const ctx = new AudioContext({ sampleRate: 24000 })
  const url = URL.createObjectURL(new Blob([WORKLET], { type: 'application/javascript' }))
  await ctx.audioWorklet.addModule(url)
  URL.revokeObjectURL(url)
  const source = ctx.createMediaStreamSource(new MediaStream(stream.getAudioTracks()))
  const node = new AudioWorkletNode(ctx, 'pcm-writer')
  let ready = false
  node.port.onmessage = (e) => { if (ready && ws.readyState === WebSocket.OPEN) ws.send(e.data) }
  source.connect(node)

  let closed: () => void = () => {}
  const done = new Promise<void>((resolve) => { closed = resolve })
  ws.onmessage = (e) => {
    const event = JSON.parse(e.data as string)
    if (event.type === 'ready') ready = true
    else if (event.type === 'transcript' && !event.final) h.onPartial(event.transcript)
    else if (event.type === 'speechComplete') { h.onTurn(event.transcript); h.onPartial('') }
    else if (event.type === 'error') h.onError(event.message)
  }
  ws.onclose = () => closed()
  ws.onerror = () => h.onError('Voice connection failed')

  return {
    async stop() {
      ready = false
      source.disconnect()
      node.disconnect()
      await ctx.close()
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('end')                                  // server sends endStream; final turns still arrive
        // the server closes the socket once Meta has flushed the last turn; closing first can drop it
        await Promise.race([done, new Promise((r) => setTimeout(r, 8000))])
      }
      ws.close()
    },
  }
}
