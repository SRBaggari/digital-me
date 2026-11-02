import { useCallback, useEffect, useState } from "react";

import type { ListeningDTO } from "../api/protocol";
import type { Api } from "../api/rest";

/** Voice-input settings from the server. `available` is false if the server cannot listen. */
export function useListening(api: Api) {
  const [listening, setListening] = useState<ListeningDTO | null>(null);
  const [available, setAvailable] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.listening().then(
      (dto) => !cancelled && setListening(dto),
      () => !cancelled && setAvailable(false),
    );
    return () => {
      cancelled = true;
    };
  }, [api]);

  const update = useCallback(
    async (change: Partial<ListeningDTO["settings"]>) => {
      setListening((current) => (current ? { ...current, settings: { ...current.settings, ...change } } : current));
      try {
        setListening(await api.updateListening(change));
      } catch {
        setListening(await api.listening().catch(() => null));
      }
    },
    [api],
  );

  return { listening, available, update };
}
