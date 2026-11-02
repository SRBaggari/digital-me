# Digital Me

A personal AI digital human that runs entirely on your own computer. You talk to it by text
(voice in Phase 3) and it answers in the voice and personality of the person it represents,
shown as an on-screen digital human.

**Personal-use project.** It is not a product or online service. Everything runs on
`localhost`; there are no accounts, no cloud services and no telemetry. The repository
contains only code: each person's profile, conversations, voice and avatar live in
`instances/`, which is git-ignored and blocked from commits by a pre-commit check.

The avatar is always labelled as AI-generated and never claims to be a real person
communicating live.

## Status

| Phase | What works | State |
|---|---|---|
| 1. Planning | Architecture, hardware review | ✅ [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 2. Text conversation | Persona, streaming replies, emotions, history, stop/interrupt, UI | ✅ |
| 3. Voice | **Spoken replies** (Kokoro, 12 voices, speed, preview, mute, stop) | ✅ |
| 3b. Voice input & cloning | Microphone speech-to-text; your own cloned voice | waiting for your recordings |
| 4. Avatar | 3D digital human, avatar upload, idle animation | planned |
| 5. Lip sync & emotion | Mouth sync, facial expressions | planned |
| 6. Memory | Approved long-term memory and its management UI | planned |
| 7. Integration & quality | End-to-end tests, latency, privacy audit | planned |

Until Phase 4, a breathing, emotion-tinted "presence" stands in for the 3D avatar.

## Requirements

* Windows 10/11 (other OSes should work but are untested)
* NVIDIA GPU with 4 GB+ VRAM recommended (CPU-only works, slower)
* 16 GB RAM, ~10 GB free disk
* [uv](https://docs.astral.sh/uv/) (installs Python 3.12 for you)
* [Node.js](https://nodejs.org/) 20+
* [Ollama](https://ollama.com/)

## Setup

```powershell
# 1. Get a local language model (about 2 GB)
ollama pull llama3.2:3b

# 2. Install dependencies
cd backend;  uv sync;     cd ..
cd frontend; npm ci;      cd ..

# 3. Turn on the privacy guard for commits (once per clone)
git config core.hooksPath .githooks

# 4. Create a private instance for the person
cd backend
uv run digital-me init alice
```

Edit `instances/alice/profile.yaml` with the person's details: name, personality,
communication style, interests, background and important facts. Only include information you
are allowed to use. Digital Me will say it doesn't know rather than invent anything else.

`instances/alice/settings.yaml` selects the model and its temperature. The settings only accept
local addresses.

## Run

```powershell
.\start.ps1 -Instance alice
```

This builds the interface on first run, starts the server on `http://127.0.0.1:8765` and
opens your browser.

**Development mode** (hot reload), in two terminals:

```powershell
cd backend;  uv run digital-me serve --instance alice
cd frontend; npm run dev        # http://127.0.0.1:5173
```

### Several people

Each person is a separate instance with its own folder, database, voice and avatar:

```powershell
uv run digital-me init bob
uv run digital-me list
.\start.ps1 -Instance bob
```

The server runs one instance at a time. Each database is stamped with its owner and refuses
to open under any other instance.

## Voice

Replies are spoken aloud with [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
(Apache-2.0), running on the CPU so the GPU stays free for the language model. The model
(about 330 MB) downloads once on first start and afterwards loads from the local cache with no
network access.

* **Speaker button** (top bar): mute or unmute.
* **Sliders button**: choose a voice (American or British English), set the speed and play a
  preview.
* **Stop** (or <kbd>Esc</kbd>): silences the reply immediately.

Long sentences are spoken in clause-sized pieces, so speech starts about 1.5 s after you send a
message. Subtitles and the avatar's expression follow the sentence you are hearing.

A cloned personal voice can be added later: the speech engine sits behind an interface
(`backend/digital_me/tts/base.py`). Only recordings of someone who has consented may be used.

## Choosing a model

```powershell
cd backend
uv run python scripts/eval_persona.py llama3.2:3b gemma3:4b qwen3:4b
```

This scores each installed model on recalling profile facts, admitting what it doesn't know,
disclosing that it is an AI, the emotion-tag format and response speed. It uses a fictional
profile. Change `llm.model` in the instance's `settings.yaml` to switch models.

Results on an RTX 3050 Laptop (4 GB):

| Model | Facts | Admits unknown | Emotion tags | Time per reply | Verdict |
|---|---|---|---|---|---|
| llama3.2:3b | 3/3 | 4/4 | 7–9/9 | 0.3 s | **Default**: fast enough for voice |
| gemma3:4b | 3/3 | 4/4 | 9/9 | 1.6 s | Good alternative, slower |
| qwen3:4b | 3/3 | 4/4 | 9/9 | ~50 s | Too slow: hidden "thinking" before each reply |

## Tests

Every part has **unit** and **integration** tests, each written as both **white-box**
(implementation-aware) and **black-box** (specification-only) tests. See
[docs/TESTING.md](docs/TESTING.md).

```powershell
cd backend;  uv run pytest --cov=digital_me      # live-model tests skip if Ollama is off
cd frontend; npm test
```

## Privacy safeguards

* The server binds to loopback only; settings reject any non-local address.
* A host-header allowlist blocks DNS rebinding, and a WebSocket origin allowlist stops other
  websites in your browser from connecting.
* Fonts are bundled; the UI makes no external requests.
* `instances/`, audio, avatar, model and database files are git-ignored. `.githooks/pre-commit`
  blocks them, along with anything that looks like a secret.

## Project layout

```
backend/            Python 3.12 · FastAPI
  digital_me/
    config/         P1  instances, profile, settings
    conversation/   P2  persona prompt, history, emotion tags, sentence streaming
    llm/            P2  Ollama client
    tts/            P5  text-to-speech engines and voice preferences
    server/         P8  session orchestrator, speech pipeline, WebSocket API, security
  tests/<part>/{unit,integration}/test_<feature>_{whitebox,blackbox}.py
frontend/           React · TypeScript · Vite
  src/              P10 user interface
  tests/p10_ui/{unit,integration}/<feature>.{whitebox,blackbox}.test.ts(x)
instance-template/  starting profile for new instances
instances/          YOUR PRIVATE DATA (git-ignored)
scripts/            commit privacy guard
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Ollama not running" | Start the Ollama app, or run `ollama serve` |
| "Model not installed" | `ollama pull <model>` using the name in `settings.yaml` |
| First reply is slow | The model loads into memory on first use; later replies are fast |
| No sound | Check the speaker button isn't muted. Browsers only play audio after you interact with the page, so send a message by typing or clicking |
| "The local model couldn't answer" once | Ollama's runner can crash when GPU memory is tight; Digital Me retries once automatically. Close GPU-heavy apps if it keeps happening |
| Port in use | `.\start.ps1 -Instance alice -Port 8800` |
