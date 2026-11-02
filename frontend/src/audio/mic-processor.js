// AudioWorklet (runs on the audio thread): microphone -> 16 kHz 16-bit PCM frames.
// Resamples with linear interpolation when the browser runs the context at another rate.

class MicCapture extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const { targetRate = 16000, frameSize = 512 } = options.processorOptions || {};
    this.step = sampleRate / targetRate; // input samples per output sample
    this.frameSize = frameSize;
    this.position = 0; // fractional read position into `carry`
    this.carry = new Float32Array(0);
    this.frame = new Int16Array(frameSize);
    this.filled = 0;
    this.sumSquares = 0;
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (!channel) return true;
    const input = new Float32Array(this.carry.length + channel.length);
    input.set(this.carry);
    input.set(channel, this.carry.length);

    let pos = this.position;
    while (pos + 1 < input.length) {
      const i = Math.floor(pos);
      const t = pos - i;
      const sample = input[i] * (1 - t) + input[i + 1] * t;
      const clipped = Math.max(-1, Math.min(1, sample));
      this.frame[this.filled++] = clipped < 0 ? clipped * 32768 : clipped * 32767;
      this.sumSquares += clipped * clipped;
      if (this.filled === this.frameSize) {
        const level = Math.min(1, Math.sqrt(this.sumSquares / this.frameSize) * 4);
        const pcm = this.frame.buffer.slice(0);
        this.port.postMessage({ pcm, level }, [pcm]);
        this.filled = 0;
        this.sumSquares = 0;
      }
      pos += this.step;
    }
    const keepFrom = Math.floor(pos);
    this.carry = input.slice(keepFrom);
    this.position = pos - keepFrom;
    return true;
  }
}

registerProcessor("mic-capture", MicCapture);
