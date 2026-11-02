import { useCallback, useEffect, useState } from "react";

import type { StatusDTO } from "../api/protocol";
import type { Api } from "../api/rest";

/** Polls /api/status; faster while the model is unavailable so recovery shows up quickly. */
export function useStatus(api: Api, healthyIntervalMs = 60_000, unhealthyIntervalMs = 5_000) {
  const [status, setStatus] = useState<StatusDTO | null>(null);
  const [unreachable, setUnreachable] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setStatus(await api.status());
      setUnreachable(false);
    } catch {
      setUnreachable(true);
    }
  }, [api]);

  const healthy = !unreachable && !!status?.llm.reachable && status.llm.model_available;

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), healthy ? healthyIntervalMs : unhealthyIntervalMs);
    return () => clearInterval(timer);
  }, [refresh, healthy, healthyIntervalMs, unhealthyIntervalMs]);

  return { status, unreachable, healthy, refresh };
}
