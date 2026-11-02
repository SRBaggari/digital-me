import type { Emotion, WordTimingDTO } from "../api/protocol";

export interface SpeechClip {
  index: number;
  text: string;
  emotion: Emotion;
  words: WordTimingDTO[];
  /** base64-encoded WAV */
  data: string;
}

/** What the queue needs from an audio implementation (Web Audio in the browser, a fake in tests). */
export interface AudioBackend<Buffer = unknown> {
  /** Must be called from a user gesture (click/keypress) to satisfy browser autoplay rules. */
  unlock(): void;
  decode(wav: ArrayBuffer): Promise<Buffer>;
  /** Start playback now; `onEnded` fires once when it finishes naturally. */
  play(buffer: Buffer, onEnded: () => void): { stop(): void };
  /** Current loudness 0..1 of what is playing. */
  level(): number;
}

export interface SpeechQueueEvents {
  onClipStart?: (clip: SpeechClip) => void;
  onIdle?: () => void;
  onError?: (error: unknown) => void;
}

export function base64ToArrayBuffer(data: string): ArrayBuffer {
  const binary = atob(data);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

/**
 * Plays clips strictly in arrival order, one after another, without gaps caused by decoding
 * (each clip starts decoding as soon as it arrives). stop() discards everything immediately.
 */
export class SpeechQueue<Buffer = unknown> {
  private queue: { clip: SpeechClip; decoded: Promise<Buffer> }[] = [];
  private current: { stop(): void } | null = null;
  private generation = 0;
  private busy = false;

  constructor(
    private readonly backend: AudioBackend<Buffer>,
    private readonly events: SpeechQueueEvents = {},
  ) {}

  get playing(): boolean {
    return this.busy;
  }

  unlock(): void {
    this.backend.unlock();
  }

  level(): number {
    return this.busy ? this.backend.level() : 0;
  }

  enqueue(clip: SpeechClip): void {
    const decoded = this.backend.decode(base64ToArrayBuffer(clip.data));
    decoded.catch(() => {}); // handled when the clip's turn comes
    this.queue.push({ clip, decoded });
    if (!this.busy) void this.playNext(this.generation);
  }

  stop(): void {
    this.generation += 1;
    this.queue = [];
    const current = this.current;
    this.current = null;
    current?.stop();
    if (this.busy) {
      this.busy = false;
      this.events.onIdle?.();
    }
  }

  private async playNext(generation: number): Promise<void> {
    const next = this.queue.shift();
    if (!next) {
      if (this.busy) {
        this.busy = false;
        this.events.onIdle?.();
      }
      return;
    }
    this.busy = true;
    let buffer: Buffer;
    try {
      buffer = await next.decoded;
    } catch (error) {
      if (generation !== this.generation) return;
      this.events.onError?.(error);
      return this.playNext(generation);
    }
    if (generation !== this.generation) return; // stopped while decoding
    this.events.onClipStart?.(next.clip);
    this.current = this.backend.play(buffer, () => {
      if (generation !== this.generation) return;
      this.current = null;
      void this.playNext(generation);
    });
  }
}
