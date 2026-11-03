from digital_me.conversation import SentenceSplitter, build_chat_messages, build_system_prompt
from digital_me.config import Profile
from digital_me.language import DEFAULT_LANGUAGE, detect_language


def test_threshold_is_thirty_percent_telugu_letters():
    # 3 Telugu letters, 7 Latin letters -> exactly 30% -> Telugu
    assert detect_language("అఆఇ abcdefg") == "te"
    assert detect_language("అఆ abcdefgh") == "en"


def test_telugu_vowel_signs_and_digits_count_as_telugu():
    assert detect_language("ి ో ౧౨") == "te"


def test_default_language_is_english():
    assert DEFAULT_LANGUAGE == "en"


async def test_no_letters_falls_back_to_default(make_engine, store, fake_llm_factory, collect):
    llm = fake_llm_factory()
    await collect(make_engine(llm).respond(store.create_conversation(), "123"))
    assert "English" in llm.calls[0]["messages"][-2]["content"]


def test_instruction_sits_right_before_the_new_message():
    messages = build_chat_messages("SYS", [], "hi", instruction="Reply in English.")
    assert [m["role"] for m in messages] == ["system", "system", "user"]


def test_no_instruction_no_extra_message():
    assert len(build_chat_messages("SYS", [], "hi")) == 2


def test_system_prompt_mentions_both_languages():
    prompt = build_system_prompt(Profile(name="Sam"))
    assert "Telugu" in prompt and "English" in prompt


def test_danda_ends_sentences():
    splitter = SentenceSplitter()
    assert splitter.feed("నమస్కారం। మీరు ఎలా ఉన్నారు? ") == ["నమస్కారం।", "మీరు ఎలా ఉన్నారు?"]
