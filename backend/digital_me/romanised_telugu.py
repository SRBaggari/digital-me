"""Romanised Telugu ("ela unnavu?") -> Telugu script ("ఎలా ఉన్నావు?").

gemma3 understands Telugu script well but not romanised Telugu (measured: it echoed the words
back or said it did not understand). So romanised messages are converted before the model sees
them. Chat spellings are informal ("peru" for పేరు), so common words come from a dictionary and
anything else is transliterated with ITRANS plus a few casual-spelling fixes.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

# Common chat words and spelling variants -> correct Telugu spelling.
WORDS: dict[str, str] = {
    # people
    "nenu": "నేను", "neenu": "నేను", "nennu": "నేను", "memu": "మేము", "manam": "మనం", "manamu": "మనము",
    "meeru": "మీరు", "miru": "మీరు", "mee": "మీ", "mi": "మీ", "meeku": "మీకు", "miku": "మీకు", "meku": "మీకు",
    "nuvvu": "నువ్వు", "nuvu": "నువ్వు", "neeku": "నీకు", "niku": "నీకు", "nee": "నీ",
    "naaku": "నాకు", "naku": "నాకు", "naa": "నా", "na": "నా", "ninnu": "నిన్ను", "nannu": "నన్ను",
    "mimmalni": "మిమ్మల్ని", "vaadu": "వాడు", "aame": "ఆమె", "vallu": "వాళ్ళు",
    # being, having
    "ela": "ఎలా", "ella": "ఎలా", "elaa": "ఎలా", "yela": "ఎలా",
    "unnavu": "ఉన్నావు", "unnaavu": "ఉన్నావు", "unnava": "ఉన్నావా", "unnaru": "ఉన్నారు", "unnaaru": "ఉన్నారు",
    "unnara": "ఉన్నారా", "unnanu": "ఉన్నాను", "unnaanu": "ఉన్నాను", "unnam": "ఉన్నాం", "undi": "ఉంది",
    "undhi": "ఉంది", "unnadi": "ఉన్నది", "unnai": "ఉన్నాయి",
    "ledu": "లేదు", "ledhu": "లేదు", "leru": "లేరు", "kaadu": "కాదు", "kadu": "కాదు", "kaadhu": "కాదు",
    "avunu": "అవును", "avnu": "అవును", "aunu": "అవును", "sare": "సరే", "sarey": "సరే",
    # questions
    "emiti": "ఏమిటి", "enti": "ఏంటి", "enty": "ఏంటి", "entee": "ఏంటి", "em": "ఏం", "emi": "ఏమి",
    "emaina": "ఏమైనా", "emina": "ఏమైనా", "edaina": "ఏదైనా", "enduku": "ఎందుకు", "endhuku": "ఎందుకు",
    "ekkada": "ఎక్కడ", "ekkadiki": "ఎక్కడికి", "eppudu": "ఎప్పుడు", "evaru": "ఎవరు", "evari": "ఎవరి",
    "entha": "ఎంత", "enta": "ఎంత", "e": "ఏ",
    # doing, saying
    "cheppu": "చెప్పు", "cheppandi": "చెప్పండి", "chepandi": "చెప్పండి", "cheppava": "చెప్పవా",
    "chestunnav": "చేస్తున్నావ్", "chesthunnav": "చేస్తున్నావ్", "chestunnava": "చేస్తున్నావా",
    "chesthunnava": "చేస్తున్నావా", "chestunnaru": "చేస్తున్నారు", "chesthunnaru": "చేస్తున్నారు",
    "chestaaru": "చేస్తారు", "chestaru": "చేస్తారు", "chesthaaru": "చేస్తారు", "chestanu": "చేస్తాను",
    "chesthanu": "చేస్తాను", "chesava": "చేశావా", "chesaava": "చేశావా", "chesaru": "చేశారు",
    "chesindi": "చేసింది", "cheyyi": "చెయ్యి", "cheyandi": "చేయండి",
    "matladu": "మాట్లాడు", "matladandi": "మాట్లాడండి", "matladutava": "మాట్లాడుతావా",
    "telusu": "తెలుసు", "teliyadu": "తెలియదు", "teledu": "తెలీదు", "telidu": "తెలీదు",
    "vachava": "వచ్చావా", "vachaava": "వచ్చావా", "vacharu": "వచ్చారు", "vachindi": "వచ్చింది",
    "vastanu": "వస్తాను", "vasthanu": "వస్తాను", "velli": "వెళ్ళి", "vellava": "వెళ్ళావా",
    "tinnava": "తిన్నావా", "tinnaava": "తిన్నావా", "tinnara": "తిన్నారా", "padukunnava": "పడుకున్నావా",
    "kavali": "కావాలి", "kaavali": "కావాలి",
    # feelings, degree
    "bagunnava": "బాగున్నావా", "bagunnaava": "బాగున్నావా", "bagunnara": "బాగున్నారా",
    "bagunnaara": "బాగున్నారా", "bagunnanu": "బాగున్నాను", "bagunnaanu": "బాగున్నాను",
    "bagundi": "బాగుంది", "baagundi": "బాగుంది", "baga": "బాగా", "baaga": "బాగా",
    "chala": "చాలా", "chaala": "చాలా", "chaalaa": "చాలా", "inka": "ఇంకా", "inkaa": "ఇంకా",
    "kuda": "కూడా", "kooda": "కూడా", "koodaa": "కూడా", "mari": "మరి", "aithe": "అయితే", "ayithe": "అయితే",
    "ante": "అంటే", "antey": "అంటే", "antha": "అంత", "anta": "అంత",
    "istam": "ఇష్టం", "ishtam": "ఇష్టం", "istamu": "ఇష్టము", "ishtamu": "ఇష్టము", "istama": "ఇష్టమా",
    "ishtama": "ఇష్టమా", "ga": "గా", "lo": "లో", "ki": "కి", "tho": "తో", "to": "తో",
    # things
    "pilli": "పిల్లి", "kukka": "కుక్క", "peru": "పేరు", "perenti": "పేరేంటి", "illu": "ఇల్లు",
    "intlo": "ఇంట్లో", "pani": "పని", "udyogam": "ఉద్యోగం", "sangeetam": "సంగీతం", "sangeetham": "సంగీతం",
    "vaarantam": "వారాంతం", "varantam": "వారాంతం", "vaaranthamlo": "వారాంతంలో", "annam": "అన్నం",
    "abbayi": "అబ్బాయి", "ammayi": "అమ్మాయి", "amma": "అమ్మ", "nanna": "నాన్న", "anna": "అన్న",
    "akka": "అక్క", "tammudu": "తమ్ముడు", "chelli": "చెల్లి",
    "namaskaram": "నమస్కారం", "namaskaaram": "నమస్కారం", "dhanyavadalu": "ధన్యవాదాలు",
    # time and place
    "ippudu": "ఇప్పుడు", "ipudu": "ఇప్పుడు", "ikkada": "ఇక్కడ", "akkada": "అక్కడ", "repu": "రేపు",
    "ninna": "నిన్న", "eroju": "ఈరోజు", "eeroju": "ఈరోజు", "ivala": "ఇవాళ", "ivvala": "ఇవాళ",
    "roju": "రోజు", "ratri": "రాత్రి", "raatri": "రాత్రి", "podduna": "పొద్దున", "subharatri": "శుభరాత్రి",
    "vunnaru": "ఉన్నారు", "vunnavu": "ఉన్నావు", "vundi": "ఉంది", "ayyindi": "అయ్యింది",
}

_CONSONANTS = "కఖగఘఙచఛజఝఞటఠడఢణతథదధపఫబభమయరలవశషసహళ"
_TOKEN = re.compile(r"[A-Za-z]+|[^A-Za-z]+")
_SPELLINGS = [("th", "t"), ("dh", "d"), ("sh", "s"), ("kh", "k"), ("bh", "b"), ("ph", "p"),
              ("w", "v"), ("z", "j"), ("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u")]


def normalise(word: str) -> str:
    """Fold chat spelling variants together: chesthunaru / chestunnaru / chesthunnaaru."""
    word = word.lower()
    for written, simple in _SPELLINGS:
        word = word.replace(written, simple)
    word = re.sub(r"(.)\1+", r"\1", word)  # doubled letters: unnaru -> unaru
    return word.removesuffix("u") if word.endswith(("vu", "nu")) and len(word) > 4 else word


# Several spellings of one word share a normalised form; the first listed spelling wins.
NORMALISED_WORDS: dict[str, str] = {}
for _spelling, _telugu in WORDS.items():
    NORMALISED_WORDS.setdefault(normalise(_spelling), _telugu)


def lookup(word: str) -> str | None:
    """Telugu spelling of a romanised chat word, tolerant of spelling variants."""
    return WORDS.get(word.lower()) or NORMALISED_WORDS.get(normalise(word))


@lru_cache(maxsize=1)
def _english_words() -> frozenset[str]:
    """~90k English words from the lexicon that ships with Kokoro's phonemizer (misaki)."""
    import misaki

    path = Path(misaki.__file__).parent / "data" / "us_gold.json"
    try:
        return frozenset(word.lower() for word in json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return frozenset()


def is_english_word(word: str) -> bool:
    """People mix English into Telugu ("nenu chala happy ga unnanu"); those words stay as they are."""
    word = word.lower()
    words = _english_words()
    return word in words or (len(word) > 3 and word.endswith("s") and word[:-1] in words)


def _transliterate_word(word: str) -> str:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate

    telugu = transliterate(word.lower().replace("z", "j"), sanscript.ITRANS, sanscript.TELUGU)
    telugu = re.sub(r"మ్$", "ం", telugu)  # final m is written as anusvara: "istam" -> "ఇష్టం"
    other = _CONSONANTS.replace("న", "")
    return re.sub(rf"న్(?=[{other}])", "ం", telugu)  # "nt", "ng": "ante" -> "అంటే"


def _convert_word(word: str) -> str:
    exact = WORDS.get(word.lower())
    if exact:
        return exact
    if is_english_word(word):
        return word
    return lookup(word) or _transliterate_word(word)


def to_telugu_script(text: str) -> str:
    """Convert romanised Telugu to Telugu script, keeping English words, punctuation, digits
    and spacing as they are."""
    return "".join(
        _convert_word(token) if token[0].isalpha() else token for token in _TOKEN.findall(text)
    )
