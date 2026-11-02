import pytest

from digital_me.config import LLMSettings, Profile
from digital_me.conversation import ConversationEngine, ConversationStore
from digital_me.db import Database


@pytest.fixture
def profile() -> Profile:
    return Profile(
        name="Sam",
        short_bio="A software engineer.",
        personality_traits=["calm", "curious"],
        communication_style="Warm and concise.",
        interests=["chess", "hiking"],
        background=["Grew up in Pune."],
        important_facts=["Has a dog called Pixel."],
        expressions=["to be honest"],
    )


@pytest.fixture
def database():
    db = Database(":memory:", "test")
    yield db
    db.close()


@pytest.fixture
def store(database) -> ConversationStore:
    return ConversationStore(database)


@pytest.fixture
def make_engine(profile, store):
    def make(llm, **settings) -> ConversationEngine:
        return ConversationEngine(profile, store, llm, LLMSettings(**settings))

    return make


@pytest.fixture
def collect():
    async def collect_events(stream):
        return [event async for event in stream]

    return collect_events
