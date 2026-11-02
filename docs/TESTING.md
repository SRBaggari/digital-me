# Testing strategy

Every project part is tested along two independent axes.

| | **White-box** (`@pytest.mark.whitebox`) | **Black-box** (`@pytest.mark.blackbox`) |
|---|---|---|
| **Unit** (`tests/<part>/unit/`) | Uses knowledge of internals: every branch and error path, internal state, internal dependencies replaced by fakes. Measured with coverage. | Uses only the public interface and the written spec: equivalence classes, boundary values, invalid input. No assumptions about the implementation. |
| **Integration** (`tests/<part>/integration/`) | Real components wired together, asserting on internal effects (database rows, call ordering, cancellation of tasks). | Real components wired together, driven only through the public API (HTTP / WebSocket / CLI). |

File naming:

* Backend: `backend/tests/<part>/{unit,integration}/test_<feature>_{whitebox,blackbox}.py`.
  Markers are applied automatically from the path, and `tests/test_structure_blackbox.py` fails
  if any part is missing one of the four kinds.
* Frontend: `frontend/tests/<part>/{unit,integration}/<feature>.{whitebox,blackbox}.test.ts(x)`.
* Tooling (the commit privacy guard): `backend/tests/tooling/`.

Persona quality (fact recall, refusing to invent, AI disclosure, emotion tags, speed) depends on
the model's sampling, so it is measured with `backend/scripts/eval_persona.py` instead of
pass/fail tests.

Tests that need a running local Ollama are additionally marked `@pytest.mark.live`
and are skipped automatically when Ollama is not reachable.

## Running

```powershell
cd backend
uv run pytest                       # everything (live tests skip without Ollama)
uv run pytest -m whitebox           # only white-box tests
uv run pytest -m blackbox           # only black-box tests
uv run pytest tests/p2_conversation # one part
uv run pytest -m "not live"         # no model needed
uv run pytest --cov=digital_me --cov-report=term-missing
```

```powershell
cd frontend
npm test                            # Vitest unit + integration tests
npm run test:coverage
```
