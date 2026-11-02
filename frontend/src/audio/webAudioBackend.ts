import type { AudioBackend } from "./speechQueue";

/** Web Audio implementation with a loudness meter (drives the presence now, lip sync later). */
export class WebAudioBackend implements AudioBackend<AudioBuffer> {
  private context: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private samples: Float32Array<ArrayBuffer> | null = null;

  static get supported(): boolean {
    return typeof globalThis.AudioContext === "function";
  }

  private ensure(): { context: AudioContext; analyser: AnalyserNode } {
    if (!WebAudioBackend.supported) throw new Error("This browser cannot play audio (no Web Audio API)");
    if (!this.context || !this.analyser) {
      this.context = new AudioContext();
      this.analyser = this.context.createAnalyser();
      this.analyser.fftSize = 1024;
      this.analyser.connect(this.context.destination);
      this.samples = new Float32Array(this.analyser.fftSize);
    }
    return { context: this.context, analyser: this.analyser };
  }

  unlock(): void {
    if (!WebAudioBackend.supported) return;
    const { context } = this.ensure();
    if (context.state === "suspended") void context.resume();
  }

  async decode(wav: ArrayBuffer): Promise<AudioBuffer> {
    return this.ensure().context.decodeAudioData(wav);
  }

  play(buffer: AudioBuffer, onEnded: () => void): { stop(): void } {
    const { context, analyser } = this.ensure();
    if (context.state === "suspended") void context.resume();
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(analyser);
    let stopped = false;
    source.onended = () => {
      if (!stopped) onEnded();
    };
    source.start();
    return {
      stop: () => {
        stopped = true;
        try {
          source.stop();
        } catch {
          /* already stopped */
        }
        source.disconnect();
      },
    };
  }

  level(): number {
    if (!this.analyser || !this.samples) return 0;
    this.analyser.getFloatTimeDomainData(this.samples);
    let sum = 0;
    for (const s of this.samples) sum += s * s;
    const rms = Math.sqrt(sum / this.samples.length);
    return Math.min(1, rms * 4); // speech RMS is ~0.05-0.25; scale into a useful 0..1 range
  }
}
