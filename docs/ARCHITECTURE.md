# Digital Me — Architecture

Personal-use AI digital human that runs entirely on one local machine.
No public deployment, no accounts, no cloud processing.

## Hardware target

| Component | Spec | Consequence |
|---|---|---|
| GPU | RTX 3050 Laptop, 4 GB VRAM | GPU is reserved for the LLM |
| CPU | Ryzen 7 5800H (8C/16T) | STT and TTS run on CPU |
| RAM | 16 GB | 3–4B parameter LLMs |
| Disk | ~20 GB for models and assets | |

## Stack

| Part | Choice | License | Runs on |
|---|---|---|---|
| LLM | Ollama, 3–4B model (default `llama3.2:3b`) | per model | GPU |
| STT | faster-whisper + Silero VAD | MIT | CPU |
| TTS | Kokoro-82M (phoneme timings) — pluggable for cloning later | Apache-2.0 | CPU |
| Avatar | Three.js, user-uploaded GLB with ARKit blendshapes + visemes | MIT | Browser |
| Lip sync | TTS phoneme timings → viseme timeline; amplitude fallback | — | Browser |
| Emotion | LLM emotion tags → subtle blended expressions | — | Backend + browser |
| Memory | SQLite (+ FTS5), approval-gated long-term memory | public domain | CPU |
| Backend | Python 3.12, FastAPI, WebSocket, bound to 127.0.0.1 | MIT | CPU |
| Frontend | Vite + React + TypeScript | MIT | Browser |

```
Browser (localhost)                                Python backend (127.0.0.1)
┌───────────────────────────────┐  WebSocket   ┌────────────────────────────────────┐
│ Avatar stage (Three.js)       │◄────────────►│ Session orchestrator               │
│ Chat panel · composer         │  JSON events │  idle / listening / thinking /     │
│ Mic + VAD                     │  + audio     │  speaking, interruption            │
│ Settings · memory manager     │              ├──────┬──────┬──────┬───────┬───────┤
└───────────────────────────────┘              │ STT  │ LLM  │ TTS  │LipSync│Memory │
                                               └──────┴──────┴──────┴───────┴───────┘
                                                instances/<name>/  (git-ignored)
```

## Instance isolation

Every Digital Me instance is a separate directory under `instances/<name>/`
(git-ignored) holding its `profile.yaml`, `settings.yaml`, SQLite database,
voice and avatar files. The server serves exactly one instance per process.
Each database stores the instance name in a `meta` table and refuses to open
under a different instance.

## Privacy guarantees (enforced in code and tested)

* The HTTP server only binds to loopback addresses.
* The LLM endpoint must be a loopback address (local-only mode).
* Host-header allowlist (blocks DNS-rebinding) and WebSocket Origin allowlist
  (blocks other websites in the same browser from connecting).
* All personal data stays in `instances/`, which is never committed.

## Project parts

| # | Part | Location |
|---|---|---|
| P1 | Config & instance isolation | `backend/digital_me/config/` |
| P2 | Conversation engine | `backend/digital_me/conversation/`, `backend/digital_me/llm/` |
| P3 | Memory | `backend/digital_me/memory/` |
| P4 | Speech-to-text | `backend/digital_me/stt/` |
| P5 | Text-to-speech | `backend/digital_me/tts/` |
| P6 | Lip sync | `frontend/src/avatar/lipsync/` |
| P7 | Emotion | `backend/digital_me/conversation/emotion.py`, `frontend/src/avatar/` |
| P8 | Session orchestrator & API | `backend/digital_me/server/` |
| P9 | Avatar renderer | `frontend/src/avatar/` |
| P10 | User interface | `frontend/src/` |

## Phases

1. Research & planning (this document)
2. Text conversation — P1, P2, P8, P10 (chat)
3. Voice — P4, P5, interruption
4. Avatar — P9, avatar upload, idle animation, expressions
5. Lip sync & emotion — P6, P7
6. Memory — P3 and its management UI
7. Integration & quality — end-to-end tests, latency, privacy checks

See [TESTING.md](TESTING.md) for the test strategy.
