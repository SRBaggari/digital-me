"""Real MMS Telugu model: Telugu text becomes Telugu speech of plausible length."""

import pytest

from digital_me.tts import KokoroEngine, LanguageRouter, MmsEngine

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def mms():
    engine = MmsEngine()
    try:
        engine.warm_up()
    except Exception as exc:
        pytest.skip(f"MMS Telugu not available: {exc}")
    return engine


def test_telugu_sentence_is_spoken(mms):
    synthesis = mms.synthesize("నా పిల్లి పేరు మిసో.", "te_mms", 1.0)
    assert 0.8 < synthesis.duration < 5.0
    assert synthesis.sample_rate == 16_000


def test_faster_speed_is_shorter(mms):
    text = "నాకు రాక్ క్లైంబింగ్ అంటే చాలా ఇష్టం."
    assert mms.synthesize(text, "te_mms", 1.5).duration < mms.synthesize(text, "te_mms", 1.0).duration


def test_bilingual_router_speaks_both(mms, real_kokoro):
    router = LanguageRouter({"en": real_kokoro, "te": mms})
    english = router.synthesize("Hello there.", "af_heart", 1.0)
    telugu = router.synthesize("నమస్కారం.", "af_heart", 1.0)
    assert english.sample_rate == 24_000 and telugu.sample_rate == 16_000
    assert english.duration > 0.3 and telugu.duration > 0.3
