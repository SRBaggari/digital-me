import type { ConversationDTO, ListeningDTO, StatusDTO, VoiceDTO, VoiceSettingsDTO } from "./protocol";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

type Fetch = typeof fetch;

async function request<T>(fetchImpl: Fetch, path: string, init?: RequestInit): Promise<T> {
  const response = await fetchImpl(path, init);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(response.status, detail || `HTTP ${response.status}`);
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export function createApi(fetchImpl: Fetch = (...args) => fetch(...args)) {
  return {
    status: () => request<StatusDTO>(fetchImpl, "/api/status"),
    conversations: () => request<ConversationDTO[]>(fetchImpl, "/api/conversations"),
    deleteConversation: (id: number) =>
      request<void>(fetchImpl, `/api/conversations/${id}`, { method: "DELETE" }),
    listening: () => request<ListeningDTO>(fetchImpl, "/api/listening"),
    updateListening: (change: Partial<ListeningDTO["settings"]>) =>
      request<ListeningDTO>(fetchImpl, "/api/listening", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(change),
      }),
    voice: () => request<VoiceDTO>(fetchImpl, "/api/voice"),
    updateVoice: (change: Partial<VoiceSettingsDTO>) =>
      request<VoiceDTO>(fetchImpl, "/api/voice", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(change),
      }),
    previewVoice: async (voice: string, speed: number): Promise<Blob> => {
      const response = await fetchImpl("/api/voice/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ voice, speed }),
      });
      if (!response.ok) throw new ApiError(response.status, "Could not preview the voice");
      return response.blob();
    },
  };
}

export type Api = ReturnType<typeof createApi>;
