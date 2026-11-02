import { useCallback, useEffect, useMemo, useState } from "react";

import { createApi, type Api } from "./api/rest";
import { Banner } from "./components/Banner";
import { ChatPanel } from "./components/ChatPanel";
import { HistoryDrawer } from "./components/HistoryDrawer";
import { Stage } from "./components/Stage";
import { TopBar } from "./components/TopBar";
import { MicButton } from "./components/MicButton";
import { VoicePanel } from "./components/VoicePanel";
import { useDigitalMe, type MicFactory, type SocketFactory, type SpeakerFactory } from "./hooks/useDigitalMe";
import { useListening } from "./hooks/useListening";
import { useStatus } from "./hooks/useStatus";
import { useVoice } from "./hooks/useVoice";

interface Props {
  api?: Api;
  socketFactory?: SocketFactory;
  socketUrl?: string;
  speakerFactory?: SpeakerFactory;
  micFactory?: MicFactory;
}

type Drawer = "history" | "voice" | null;

export function App({ api: injectedApi, socketFactory, socketUrl, speakerFactory, micFactory }: Props) {
  const api = useMemo(() => injectedApi ?? createApi(), [injectedApi]);
  const dm = useDigitalMe(socketFactory, socketUrl, speakerFactory, micFactory);
  const { status, unreachable } = useStatus(api);
  const voice = useVoice(api);
  const listening = useListening(api);
  const canListen = listening.available && (listening.listening?.settings.enabled ?? false);
  const [drawer, setDrawer] = useState<Drawer>(null);
  const closeDrawer = useCallback(() => setDrawer(null), []);
  const [everConnected, setEverConnected] = useState(false);
  const { state, setVoiceEnabled } = dm;
  const name = status?.persona_name ?? "Digital Me";
  const voiceOn = voice.voice?.settings.enabled ?? false;

  useEffect(() => {
    if (state.connection === "open") setEverConnected(true);
  }, [state.connection]);

  useEffect(() => {
    document.title = status ? `${status.persona_name} · Digital Me` : "Digital Me";
  }, [status]);

  useEffect(() => setVoiceEnabled(voiceOn), [voiceOn, setVoiceEnabled]);

  // Switching voice input off in settings closes an open microphone.
  const { stopMic } = dm;
  useEffect(() => {
    if (!canListen && state.mic !== "off") stopMic();
  }, [canListen, state.mic, stopMic]);

  return (
    <div className="app">
      <TopBar
        status={status}
        serverUnreachable={unreachable}
        onNewConversation={() => {
          dm.newConversation();
        }}
        onOpenHistory={() => setDrawer("history")}
        disabled={state.connection !== "open"}
        voiceEnabled={voice.available && voice.voice ? voiceOn : null}
        onToggleVoice={() => void voice.update({ enabled: !voiceOn })}
        onOpenVoice={() => setDrawer("voice")}
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
          state={dm.avatarState}
          emotion={state.emotion}
          caption={state.caption}
          pulse={state.voiceEnabled ? 0 : (state.draft?.text.length ?? 0)}
          level={dm.level}
        />
        <ChatPanel
          name={name}
          state={state}
          avatarState={dm.avatarState}
          responding={dm.responding}
          onSend={dm.sendText}
          onStop={() => {
            dm.interrupt();
          }}
          micButton={
            canListen ? (
              <MicButton
                status={state.mic}
                onToggle={dm.toggleMic}
                disabled={state.connection !== "open"}
                level={dm.level}
              />
            ) : undefined
          }
        />
      </main>
      <HistoryDrawer
        open={drawer === "history"}
        api={api}
        currentId={state.conversationId}
        onClose={closeDrawer}
        onOpenConversation={(id) => {
          dm.openConversation(id);
        }}
        onDeletedCurrent={() => {
          dm.newConversation();
        }}
      />
      <VoicePanel
        open={drawer === "voice"}
        voice={voice.voice}
        error={voice.error}
        onClose={closeDrawer}
        onChange={(change) => void voice.update(change)}
        onPreview={api.previewVoice}
        listening={listening.listening}
        onListeningChange={(change) => void listening.update(change)}
      />
    </div>
  );
}
