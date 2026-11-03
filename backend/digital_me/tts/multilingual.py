"""Speaks each sentence with the engine for its language (English: Kokoro, Telugu: SYSPIN/MMS)."""

from __future__ import annotations

from ..language import DEFAULT_LANGUAGE, detect_language
from .base import Synthesis, TTSEngine, Voice


class LanguageRouter:
    """A TTSEngine that delegates by the script of the text.

    The voice the user picks (and lists in the UI) belongs to the default-language engine and is
    limited to `gender` when given; other languages use their engine's own voice.
    """

    def __init__(
        self,
        engines: dict[str, TTSEngine],
        default: str = DEFAULT_LANGUAGE,
        gender: str | None = None,
    ):
        if default not in engines:
            raise ValueError(f"No engine for the default language {default!r}")
        self._engines = engines
        self._default = default
        self.gender = gender
        self.name = "+".join(engine.name for engine in engines.values())

    @property
    def languages(self) -> list[str]:
        return list(self._engines)

    @property
    def ready(self) -> bool:
        return all(engine.ready for engine in self._engines.values())

    def voices(self) -> list[Voice]:
        voices = self._engines[self._default].voices()
        if self.gender:
            matching = [voice for voice in voices if voice.gender == self.gender]
            voices = matching or voices
        return voices

    def effective_voice(self, voice: str) -> str:
        """The requested voice if it is offered, else the first offered one (e.g. a male voice
        chosen before the instance was set to female voices)."""
        offered = self.voices()
        return voice if any(v.id == voice for v in offered) else offered[0].id

    def warm_up(self, voice: str | None = None) -> None:
        for language, engine in self._engines.items():
            if language == self._default:
                engine.warm_up(self.effective_voice(voice or self.voices()[0].id))
            else:
                engine.warm_up()

    def engine_for(self, text: str) -> tuple[str, TTSEngine]:
        language = detect_language(text) or self._default
        if language not in self._engines:
            language = self._default
        return language, self._engines[language]

    def synthesize(self, text: str, voice: str, speed: float) -> Synthesis:
        language, engine = self.engine_for(text)
        if language == self._default:
            voice = self.effective_voice(voice)
        else:
            voice = engine.voices()[0].id
        return engine.synthesize(text, voice, speed)
