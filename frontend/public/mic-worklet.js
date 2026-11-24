// Captures mono Float32 mic samples at the AudioContext rate (16 kHz) and posts 100 ms Int16 PCM chunks.
class MicCapture extends AudioWorkletProcessor {
  constructor() { super(); this.buf = new Int16Array(1600); this.n = 0 }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0]
    if (ch) {
      for (let i = 0; i < ch.length; i++) {
        const s = Math.max(-1, Math.min(1, ch[i]))
        this.buf[this.n++] = s < 0 ? s * 0x8000 : s * 0x7fff
        if (this.n === this.buf.length) { this.port.postMessage(this.buf.buffer.slice(0)); this.n = 0 }
      }
    }
    return true
  }
}
registerProcessor('mic-capture', MicCapture)
