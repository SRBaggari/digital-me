"""FastAPI application: REST for history and status, one WebSocket for live conversation."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ..config import Instance, Profile, Settings, load_profile, load_settings
from ..config.instance import REPO_ROOT
from ..conversation import ConversationEngine, ConversationNotFoundError, ConversationStore
from ..db import Database
from ..llm import LLMClient, OllamaClient
from ..config import ListeningSettings
from ..stt import (
    BilingualTranscriber,
    ListeningPreferences,
    ListeningUpdate,
    SileroVAD,
    Transcriber,
    WhisperTranscriber,
    telugu_model,
)
from ..stt.whisper import _default_model_factory
from ..tts import (
    KokoroEngine,
    LanguageRouter,
    MmsEngine,
    TTSEngine,
    TTSError,
    VoicePreferences,
    VoiceUpdate,
    to_wav_bytes,
)
from .listener import Hearing
from .protocol import conversation_to_dict, message_to_dict
from .security import LOCAL_HOSTNAMES, is_origin_allowed
from .session import Session
from .speech import Speech

log = logging.getLogger(__name__)
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
AI_DISCLOSURE = "AI-generated digital human. Not a real person communicating live."
PREVIEW_TEXT = "Hi! This is how I sound. Nice to meet you."


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voice: str | None = Field(default=None, max_length=64)
    speed: float | None = Field(default=None, ge=0.5, le=2.0)
    text: str = Field(default=PREVIEW_TEXT, min_length=1, max_length=300)


@dataclass
class AppContext:
    instance_name: str
    profile: Profile
    settings: Settings
    store: ConversationStore
    llm: LLMClient
    database: Database | None = None
    speech: Speech | None = None
    hearing: Hearing | None = None
    engine: ConversationEngine = field(init=False)
    speech_status: str = field(default="off", init=False)  # off | loading | ready | error: ...
    hearing_status: str = field(default="off", init=False)

    def __post_init__(self) -> None:
        self.engine = ConversationEngine(self.profile, self.store, self.llm, self.settings.llm)


def build_context(
    instance: Instance,
    llm: LLMClient | None = None,
    tts: TTSEngine | None = None,
    hearing: Hearing | None = None,
) -> AppContext:
    profile = load_profile(instance.profile_path)
    settings = load_settings(instance.settings_path)
    database = Database(instance.database_path, instance.name)
    listening = settings.listening
    return AppContext(
        instance_name=instance.name,
        profile=profile,
        settings=settings,
        store=ConversationStore(database),
        llm=llm or OllamaClient(settings.llm.base_url, settings.llm.model),
        database=database,
        speech=Speech(tts or _speech_engine(listening.languages), VoicePreferences(database, settings.voice)),
        hearing=hearing
        or Hearing(_transcriber(listening), SileroVAD, ListeningPreferences(database, listening)),
    )


def _speech_engine(languages: list[str]) -> TTSEngine:
    """Kokoro for English, MMS for Telugu; each sentence is voiced in its own language."""
    engines: dict[str, TTSEngine] = {"en": KokoroEngine()}
    if "te" in languages:
        engines["te"] = MmsEngine()
    return LanguageRouter(engines) if len(engines) > 1 else engines["en"]


def _transcriber(listening: ListeningSettings) -> Transcriber:
    transcribers: dict[str, WhisperTranscriber] = {}
    if "en" in listening.languages:
        transcribers["en"] = WhisperTranscriber(listening.model, "en")
    if "te" in listening.languages:
        size = listening.telugu_model
        transcribers["te"] = WhisperTranscriber(
            f"telugu-{size}",
            "te",
            model_factory=lambda _name: _default_model_factory(str(telugu_model.ensure_model(size))),
        )
    if len(transcribers) == 1:
        return next(iter(transcribers.values()))
    return BilingualTranscriber(transcribers)


async def _warm_up_hearing(context: AppContext) -> None:
    hearing = context.hearing
    if hearing is None:
        return
    context.hearing_status = "loading"
    try:
        await asyncio.to_thread(hearing.transcriber.warm_up)
        await asyncio.to_thread(hearing.vad_factory)  # loads the VAD model once
        context.hearing_status = "ready"
    except Exception as exc:
        log.exception("Speech recognition failed to load")
        context.hearing_status = f"error: {exc}"


async def _warm_up_llm(context: AppContext) -> None:
    """Load the model and cache the persona prompt (skipped for clients without warm_up)."""
    warm_up = getattr(context.llm, "warm_up", None)
    if warm_up is None:
        return
    messages = [
        {"role": "system", "content": context.engine.system_prompt},
        {"role": "user", "content": "Hi"},
    ]
    try:
        await warm_up(messages, num_ctx=context.settings.llm.num_ctx)
    except Exception:  # Ollama may simply not be running yet; replies will report it
        log.warning("Could not pre-load the language model", exc_info=True)


async def _warm_up(context: AppContext) -> None:
    # The model loads on the GPU while speech models load on the CPU.
    llm = asyncio.create_task(_warm_up_llm(context))
    # One after the other: both are CPU-heavy, and the voice matters first.
    await _warm_up_speech(context)
    await _warm_up_hearing(context)
    await llm


async def _warm_up_speech(context: AppContext) -> None:
    speech = context.speech
    if speech is None:
        return
    context.speech_status = "loading"
    try:
        await asyncio.to_thread(speech.engine.warm_up, speech.preferences.get().voice)
        context.speech_status = "ready"
    except Exception as exc:  # report in /api/status instead of crashing the server
        log.exception("Voice engine failed to load")
        context.speech_status = f"error: {exc}"


def _voice_payload(speech: Speech, status: str) -> dict:
    current = speech.preferences.get()
    return {
        "settings": {"enabled": current.enabled, "voice": current.voice, "speed": current.speed},
        "voices": [asdict(v) for v in speech.engine.voices()],
        "engine": speech.engine.name,
        "status": status,
    }


def create_app(context: AppContext, frontend_dist: Path | None = FRONTEND_DIST) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        warm_up = asyncio.create_task(_warm_up(context))
        yield
        warm_up.cancel()

    app = FastAPI(title="Digital Me", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=LOCAL_HOSTNAMES)
    app.state.context = context
    port = context.settings.server.port

    def require_speech() -> Speech:
        if context.speech is None:
            raise HTTPException(status_code=404, detail="Voice is not available")
        return context.speech

    def listening_payload() -> dict:
        if context.hearing is None:
            raise HTTPException(status_code=404, detail="Voice input is not available")
        current = context.hearing.preferences.get()
        return {
            "settings": {"enabled": current.enabled, "barge_in": current.barge_in},
            "model": current.model,
            "language": current.language,
            "status": context.hearing_status,
        }

    @app.get("/api/listening")
    def get_listening() -> dict:
        return listening_payload()

    @app.put("/api/listening")
    def update_listening(change: ListeningUpdate) -> dict:
        listening_payload()  # 404 if unavailable
        context.hearing.preferences.update(change)
        return listening_payload()

    @app.get("/api/voice")
    def get_voice() -> dict:
        return _voice_payload(require_speech(), context.speech_status)

    @app.put("/api/voice")
    def update_voice(change: VoiceUpdate) -> dict:
        speech = require_speech()
        if change.voice is not None and change.voice not in {v.id for v in speech.engine.voices()}:
            raise HTTPException(status_code=422, detail=f"Unknown voice {change.voice!r}")
        speech.preferences.update(change)
        return _voice_payload(speech, context.speech_status)

    @app.post("/api/voice/preview")
    async def preview_voice(request: PreviewRequest) -> Response:
        speech = require_speech()
        current = speech.preferences.get()
        voice = request.voice or current.voice
        if voice not in {v.id for v in speech.engine.voices()}:
            raise HTTPException(status_code=422, detail=f"Unknown voice {voice!r}")
        try:
            synthesis = await asyncio.to_thread(
                speech.engine.synthesize, request.text, voice, request.speed or current.speed
            )
        except TTSError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None
        return Response(to_wav_bytes(synthesis.audio, synthesis.sample_rate), media_type="audio/wav")

    @app.get("/api/status")
    async def status() -> dict:
        health = await context.llm.health()
        return {
            "instance": context.instance_name,
            "persona_name": context.profile.name,
            "model": context.llm.model,
            "llm": {
                "reachable": health.reachable,
                "model_available": health.model_available,
                "detail": health.detail,
            },
            "disclosure": AI_DISCLOSURE,
            "speech": context.speech_status,
            "hearing": context.hearing_status,
        }

    @app.get("/api/conversations")
    def list_conversations() -> list[dict]:
        return [conversation_to_dict(c) for c in context.store.list_conversations()]

    @app.get("/api/conversations/{conversation_id}")
    def get_conversation(conversation_id: int) -> dict:
        try:
            messages = context.store.get_messages(conversation_id)
        except ConversationNotFoundError:
            raise HTTPException(status_code=404, detail="Conversation not found") from None
        return {"conversation_id": conversation_id, "messages": [message_to_dict(m) for m in messages]}

    @app.delete("/api/conversations/{conversation_id}", status_code=204)
    def delete_conversation(conversation_id: int) -> Response:
        if not context.store.delete_conversation(conversation_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        return Response(status_code=204)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        if not is_origin_allowed(websocket.headers.get("origin"), port):
            log.warning("Rejected WebSocket from origin %s", websocket.headers.get("origin"))
            await websocket.close(code=1008)
            return
        await websocket.accept()
        session = Session(
            context.engine, context.store, websocket.send_json, context.speech, context.hearing
        )
        await session.start()
        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    break
                if message.get("bytes") is not None:  # microphone audio
                    await session.handle_audio(message["bytes"])
                else:
                    await session.handle(json.loads(message.get("text") or ""))
        except WebSocketDisconnect:
            pass
        except ValueError:  # non-JSON text frame
            await websocket.close(code=1003)
        finally:
            await session.close()

    if frontend_dist is not None and (frontend_dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app
