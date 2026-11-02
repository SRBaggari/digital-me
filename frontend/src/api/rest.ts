import type { ConversationDTO, StatusDTO } from "./protocol";

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
  };
}

export type Api = ReturnType<typeof createApi>;
