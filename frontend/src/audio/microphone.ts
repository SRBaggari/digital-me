import workletUrl from "./mic-processor.js?url";

export const TARGET_RATE = 16_000;
export const FRAME_SIZE = 512;

export interface MicrophoneHandlers {
  onFrame: (pcm: ArrayBuffer) => void;
  onLevel?: (level: number) => void;
}

/** What the app needs from a microphone (the browser one below, a fake in tests). */
export interface Mic {
  start(handlers: MicrophoneHandlers): Promise<void>;
  stop(): void;
  level(): number;
}

export class MicrophoneError extends Error {
  constructor(
    readonly reason: "denied" | "unavailable" | "unsupported",
    message: string,
  ) {
    super(message);
  }
}

export function explainMicError(error: unknown): MicrophoneError {
  if (error instanceof MicrophoneError) return error;
  const name = error instanceof DOMException ? error.name : "";
  if (name === "NotAllowedError" || name === "SecurityError")
    return new MicrophoneError("denied", "Microphone access was blocked. Allow it in the browser's address bar.");
  if (name === "NotFoundError" || name === "NotReadableError" || name === "OverconstrainedError")
    return new MicrophoneError("unavailable", "No working microphone was found.");
  return new MicrophoneError("unavailable", `Could not start the microphone: ${String(error)}`);
}

/** Browser microphone with echo cancellation, captured off the main thread by an AudioWorklet. */
export class BrowserMicrophone implements Mic {
  private stream: MediaStream | null = null;
  private context: AudioContext | null = null;
  private currentLevel = 0;

  async start({ onFrame, onLevel }: MicrophoneHandlers): Promise<void> {
    this.stop();
    if (!navigator.mediaDevices?.getUserMedia || typeof AudioWorkletNode === "undefined") {
      throw new MicrophoneError("unsupported", "This browser cannot record audio.");
    }
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      // Prefer a 16 kHz context (the browser resamples). Some browsers (Firefox) refuse to
      // connect a microphone to it; then use the default rate and let the worklet resample.
      let lastError: unknown;
      for (const options of [{ sampleRate: TARGET_RATE }, {}]) {
        try {
          await this.connect(new AudioContext(options), onFrame, onLevel);
          return;
        } catch (error) {
          lastError = error;
          void this.context?.close().catch(() => {});
          this.context = null;
        }
      }
      throw lastError;
    } catch (error) {
      this.stop();
      throw explainMicError(error);
    }
  }

  private async connect(context: AudioContext, onFrame: MicrophoneHandlers["onFrame"], onLevel?: (l: number) => void) {
    this.context = context;
    await context.audioWorklet.addModule(workletUrl);
    const source = context.createMediaStreamSource(this.stream!);
    const node = new AudioWorkletNode(context, "mic-capture", {
      numberOfOutputs: 0,
      processorOptions: { targetRate: TARGET_RATE, frameSize: FRAME_SIZE },
    });
    node.port.onmessage = (event: MessageEvent<{ pcm: ArrayBuffer; level: number }>) => {
      this.currentLevel = event.data.level;
      onLevel?.(event.data.level);
      onFrame(event.data.pcm);
    };
    source.connect(node);
  }

  stop(): void {
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    void this.context?.close().catch(() => {});
    this.context = null;
    this.currentLevel = 0;
  }

  level(): number {
    return this.currentLevel;
  }
}
