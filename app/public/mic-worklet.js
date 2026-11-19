// Captures microphone audio, downsamples to 16 kHz and emits 16-bit PCM chunks (~100 ms).
class MicProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / 16000;
    this.buf = [];
    this.pos = 0;
    this.acc = 0;
    this.n = 0;
  }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    // Simple averaging decimator (anti-aliasing good enough for speech).
    for (let i = 0; i < ch.length; i++) {
      this.acc += ch[i];
      this.n++;
      this.pos += 1;
      if (this.pos >= this.ratio) {
        this.pos -= this.ratio;
        this.buf.push(this.acc / this.n);
        this.acc = 0;
        this.n = 0;
      }
    }
    if (this.buf.length >= 1600) {
      const out = new Int16Array(this.buf.length);
      let peak = 0;
      for (let i = 0; i < this.buf.length; i++) {
        const s = Math.max(-1, Math.min(1, this.buf[i]));
        peak = Math.max(peak, Math.abs(s));
        out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      this.port.postMessage({ pcm: out.buffer, level: peak }, [out.buffer]);
      this.buf = [];
    }
    return true;
  }
}
registerProcessor('mic-processor', MicProcessor);
