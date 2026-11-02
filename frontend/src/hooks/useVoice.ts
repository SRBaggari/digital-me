import { useCallback, useEffect, useState } from "react";

import type { VoiceDTO, VoiceSettingsDTO } from "../api/protocol";
import type { Api } from "../api/rest";

/** Voice settings from the server, with optimistic updates. `available` is false if the server has no voice. */
export function useVoice(api: Api) {
  const [voice, setVoice] = useState<VoiceDTO | null>(null);
  const [available, setAvailable] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.voice().then(
      (dto) => !cancelled && setVoice(dto),
      () => !cancelled && setAvailable(false),
    );
    return () => {
      cancelled = true;
    };
  }, [api]);

  const update = useCallback(
    async (change: Partial<VoiceSettingsDTO>) => {
      setVoice((current) => (current ? { ...current, settings: { ...current.settings, ...change } } : current));
      try {
        setVoice(await api.updateVoice(change));
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not save voice settings");
        setVoice(await api.voice().catch(() => null));
      }
    },
    [api],
  );

  return { voice, available, error, update };
}
