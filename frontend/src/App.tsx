import { useCallback, useEffect, useMemo, useState } from "react";

import { createApi, type Api } from "./api/rest";
import { Banner } from "./components/Banner";
import { ChatPanel } from "./components/ChatPanel";
import { HistoryDrawer } from "./components/HistoryDrawer";
import { Stage } from "./components/Stage";
import { TopBar } from "./components/TopBar";
import { useDigitalMe, type SocketFactory } from "./hooks/useDigitalMe";
import { useStatus } from "./hooks/useStatus";

interface Props {
  api?: Api;
  socketFactory?: SocketFactory;
  socketUrl?: string;
}

export function App({ api: injectedApi, socketFactory, socketUrl }: Props) {
  const api = useMemo(() => injectedApi ?? createApi(), [injectedApi]);
  const dm = useDigitalMe(socketFactory, socketUrl);
  const { status, unreachable } = useStatus(api);
  const [historyOpen, setHistoryOpen] = useState(false);
  const closeHistory = useCallback(() => setHistoryOpen(false), []);
  const [everConnected, setEverConnected] = useState(false);
  const { state } = dm;
  const name = status?.persona_name ?? "Digital Me";

  useEffect(() => {
    if (state.connection === "open") setEverConnected(true);
  }, [state.connection]);

  useEffect(() => {
    document.title = status ? `${status.persona_name} · Digital Me` : "Digital Me";
  }, [status]);

  return (
    <div className="app">
      <TopBar
        status={status}
        serverUnreachable={unreachable}
        onNewConversation={() => {
          dm.newConversation();
        }}
        onOpenHistory={() => setHistoryOpen(true)}
        disabled={state.connection !== "open"}
      />
      <Banner
        connection={state.connection}
        everConnected={everConnected}
        error={state.error}
        onDismiss={dm.dismissError}
      />
      <main className="layout">
        <Stage
          name={name}
          state={state.avatarState}
          emotion={state.emotion}
          caption={state.caption}
          pulse={state.draft?.text.length ?? 0}
        />
        <ChatPanel
          name={name}
          state={state}
          avatarState={state.avatarState}
          responding={dm.responding}
          onSend={dm.sendText}
          onStop={() => {
            dm.interrupt();
          }}
        />
      </main>
      <HistoryDrawer
        open={historyOpen}
        api={api}
        currentId={state.conversationId}
        onClose={closeHistory}
        onOpenConversation={(id) => {
          dm.openConversation(id);
        }}
        onDeletedCurrent={() => {
          dm.newConversation();
        }}
      />
    </div>
  );
}
