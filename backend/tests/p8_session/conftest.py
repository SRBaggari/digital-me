import pytest
from fastapi.testclient import TestClient

from digital_me.config import Profile, Settings
from digital_me.conversation import ConversationStore
from digital_me.db import Database
from digital_me.server import AppContext, Session, create_app


@pytest.fixture
def database():
    db = Database(":memory:", "test")
    yield db
    db.close()


@pytest.fixture
def store(database):
    return ConversationStore(database)


@pytest.fixture
def make_context(store, fake_llm_factory):
    def make(llm=None) -> AppContext:
        return AppContext(
            instance_name="test",
            profile=Profile(name="Sam"),
            settings=Settings(),
            store=store,
            llm=llm or fake_llm_factory(),
        )

    return make


class Recorder:
    def __init__(self):
        self.events = []

    async def __call__(self, event):
        self.events.append(event)

    def types(self):
        return [e["type"] for e in self.events]

    def of(self, kind):
        return [e for e in self.events if e["type"] == kind]


@pytest.fixture
def recorder():
    return Recorder()


@pytest.fixture
def make_session(make_context, store, recorder):
    def make(llm=None) -> Session:
        return Session(make_context(llm).engine, store, recorder)

    return make


@pytest.fixture
def make_client(make_context):
    def make(llm=None) -> TestClient:
        return TestClient(create_app(make_context(llm), frontend_dist=None), base_url="http://localhost")

    return make


ORIGIN = {"origin": "http://localhost:5173"}


@pytest.fixture
def origin_header():
    return ORIGIN
