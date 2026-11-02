import { Loader2, Play, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { VoiceDTO, VoiceSettingsDTO } from "../api/protocol";

interface Props {
  open: boolean;
  voice: VoiceDTO | null;
  error: string | null;
  onClose: () => void;
  onChange: (change: Partial<VoiceSettingsDTO>) => void;
  onPreview: (voice: string, speed: number) => Promise<Blob>;
  /** Commit slider changes after the user pauses, so dragging does not spam the server. */
  debounceMs?: number;
}

export function speechStatusText(status: string | undefined): string {
  if (!status || status === "off") return "Voice engine is off";
  if (status === "loading") return "Loading voice engine…";
  if (status === "ready") return "Voice engine ready · runs on this PC";
  return `Voice engine problem: ${status.replace(/^error:\s*/, "")}`;
}

export function VoicePanel({ open, voice, error, onClose, onChange, onPreview, debounceMs = 300 }: Props) {
  const [speed, setSpeed] = useState(voice?.settings.speed ?? 1);
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);

  const serverSpeed = voice?.settings.speed;
  useEffect(() => {
    if (serverSpeed !== undefined) setSpeed(serverSpeed);
  }, [serverSpeed]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
      audio.current?.pause();
    },
    [],
  );

  const changeSpeed = (value: number) => {
    setSpeed(value);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => onChange({ speed: value }), debounceMs);
  };

  const preview = async () => {
    if (!voice) return;
    setPreviewing(true);
    setPreviewError(null);
    try {
      const blob = await onPreview(voice.settings.voice, speed);
      audio.current?.pause();
      const url = URL.createObjectURL(blob);
      const player = new Audio(url);
      player.onended = () => URL.revokeObjectURL(url);
      audio.current = player;
      await player.play();
    } catch (e) {
      setPreviewError(e instanceof Error ? e.message : "Preview failed");
    } finally {
      setPreviewing(false);
    }
  };

  const accents = voice ? [...new Set(voice.voices.map((v) => v.accent))] : [];

  return (
    <>
      <div className={`scrim ${open ? "scrim--open" : ""}`} onClick={onClose} aria-hidden />
      <aside className={`drawer ${open ? "drawer--open" : ""}`} aria-label="Voice settings" aria-hidden={!open} inert={!open}>
        <header className="drawer__header">
          <h2>Voice</h2>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close voice settings">
            <X size={18} />
          </button>
        </header>
        {!voice ? (
          <p className="drawer__empty">Voice settings are not available.</p>
        ) : (
          <div className="voice-panel">
            <label className="switch-row">
              <span>
                <span className="switch-row__title">Speak replies aloud</span>
                <span className="switch-row__hint">{speechStatusText(voice.status)}</span>
              </span>
              <input
                type="checkbox"
                role="switch"
                className="switch"
                checked={voice.settings.enabled}
                onChange={(event) => onChange({ enabled: event.target.checked })}
              />
            </label>

            {accents.map((accent) => (
              <fieldset key={accent} className="voice-group">
                <legend>{accent} English</legend>
                <div className="voice-grid">
                  {voice.voices
                    .filter((v) => v.accent === accent)
                    .map((v) => (
                      <label key={v.id} className={`voice-card ${v.id === voice.settings.voice ? "voice-card--selected" : ""}`}>
                        <input
                          type="radio"
                          name="voice"
                          value={v.id}
                          checked={v.id === voice.settings.voice}
                          onChange={() => onChange({ voice: v.id })}
                        />
                        <span className="voice-card__name">{v.name}</span>
                        <span className="voice-card__meta">{v.gender}</span>
                      </label>
                    ))}
                </div>
              </fieldset>
            ))}

            <div className="slider-row">
              <label htmlFor="voice-speed">Speaking speed</label>
              <output htmlFor="voice-speed">{speed.toFixed(2)}×</output>
              <input
                id="voice-speed"
                type="range"
                min={0.5}
                max={2}
                step={0.05}
                value={speed}
                onChange={(event) => changeSpeed(Number(event.target.value))}
              />
            </div>

            <button type="button" className="preview-button" onClick={() => void preview()} disabled={previewing}>
              {previewing ? <Loader2 size={16} className="spin" /> : <Play size={16} />}
              {previewing ? "Generating…" : "Preview voice"}
            </button>
            {(previewError || error) && <p className="drawer__error">{previewError ?? error}</p>}

            <p className="voice-panel__note">
              Built-in voices from Kokoro, generated on this computer. A personal cloned voice can be added later
              from recordings you provide.
            </p>
          </div>
        )}
      </aside>
    </>
  );
}
