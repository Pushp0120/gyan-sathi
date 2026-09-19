"""Normalize mixed-script AI output into clean Gujarati text.

Why this exists: the tutor LLM occasionally slips Devanagari (Hindi), Bengali,
Gurmukhi or Arabic-script (Urdu) characters into Gujarati answers. Browsers
render those words with a fallback font, so they look broken/garbled next to
the surrounding Gujarati ("text not showing properly in some places").

Devanagari, Bengali and Gurmukhi share Gujarati's phonetic code-point layout:
each block is a near-uniform offset from the Gujarati block, and the few
letters Gujarati lacks (nukta variants, Vedic tones, etc.) have explicit
overrides. Arabic-script (Urdu) words have no mechanical transliteration and
are dropped; their digits/punctuation are converted to ASCII so numbers and
questions survive.

``sanitize_gujarati`` is idempotent and ASCII-safe (Markdown, math, code, emoji
and Latin text pass through untouched), so it is safe to apply to streaming
deltas as well as whole answers. The character map is built from
``unicodedata`` so unassigned codepoints are never emitted.
"""

from __future__ import annotations

import unicodedata

# ---------------------------------------------------------------------------
# Block layout: (source_start, source_end, offset_to_gujarati, overrides)
# ---------------------------------------------------------------------------
_DEV_OVERRIDES: dict[int, str] = {
    0x0900: "\u0A81",  # ँ (inverted candrabindu) → ઁ (Gujarati candrabindu)
    0x0929: "\u0AA8",  # ऩ → ન (target unassigned)
    0x0931: "\u0AB0",  # ऱ → ર (target unassigned)
    0x0934: "\u0AB3",  # ऴ → ળ (target unassigned)
    0x093A: "",        # rare vowel-sign variants → drop
    0x093B: "",
    0x093C: "",        # nukta (dot) → drop (Gujarati has no nukta letters)
    0x094A: "\u0ACB",  # ॊ (short o sign; target unassigned) → ો
    0x094E: "",        # rare vowel signs → drop
    0x094F: "",
    0x0951: "", 0x0952: "", 0x0953: "", 0x0954: "",  # Vedic tone marks → drop
    0x0958: "\u0A95",  # क़ → ક
    0x0959: "\u0A96",  # ख़ → ખ
    0x095A: "\u0A97",  # ग़ → ગ
    0x095B: "\u0A9C",  # ज़ → જ
    0x095C: "\u0AA1",  # ड़ → ડ
    0x095D: "\u0AA2",  # ढ़ → ઢ
    0x095E: "\u0AAB",  # फ़ → ફ
    0x095F: "\u0AAF",  # य़ → ય
    0x0964: "\u0964",  # । danda — keep (legitimate Gujarati punctuation too)
    0x0965: "\u0965",  # ॥ double danda — keep
    0x0970: ".",       # ॰ abbreviation sign → plain dot
    0x0972: "", 0x0973: "", 0x0974: "", 0x0975: "", 0x0976: "",  # rare vowels → drop
    0x0977: "", 0x0978: "", 0x0979: "", 0x097A: "",  # rare nukta letters → drop
    0x097B: "", 0x097C: "", 0x097E: "", 0x097F: "",
}

_BEN_OVERRIDES: dict[int, str] = {
    0x0980: "",              # Bengali candrabindu variant → drop
    0x09BC: "",              # nukta → drop
    0x09DC: "\u0AA1",        # ড় → ડ
    0x09DD: "\u0AA2",        # ঢ় → ઢ
    0x09CE: "\u0AA4\u0ACD",  # ৎ (khanda ta) → ત્
    0x09DF: "\u0AAF",        # য় → ય
    0x09F0: "\u20B9",        # ৲ rupee mark → ₹
    0x09F1: "\u20B9",        # ৳ rupee sign → ₹
    0x09F2: "", 0x09F3: "", 0x09F4: "", 0x09F5: "",  # currency/fractions → drop
    0x09F6: "", 0x09F7: "", 0x09F8: "", 0x09F9: "",
    0x09FA: "", 0x09FB: "", 0x09FC: "", 0x09FD: "", 0x09FE: "", 0x09FF: "",
}

_GUR_OVERRIDES: dict[int, str] = {
    0x0A3C: "",        # nukta → drop
    0x0A51: "",        # ੑ rare sign → drop
    0x0A59: "\u0A96",  # ਖ਼ → ખ
    0x0A5A: "\u0A97",  # ਗ਼ → ગ
    0x0A5B: "\u0A9C",  # ਜ਼ → જ
    0x0A5C: "\u0AA1",  # ੜ → ડ
    0x0A5E: "\u0AAB",  # ਫ਼ → ફ
    0x0A70: "\u0A82",  # ਂ tippi → ં anusvara (target unassigned)
    0x0A71: "",        # ੱ addak → drop
    0x0A72: "",        # ੲ iri → drop
    0x0A73: "",        # ੳ ura → drop
    0x0A74: "\u0AD0",  # ੴ ik onkar → ૐ
    0x0A75: "",        # rare sign → drop
}

_BLOCKS = (
    (0x0900, 0x097F, 0x0180, _DEV_OVERRIDES),  # Devanagari
    (0x0980, 0x09FF, 0x0100, _BEN_OVERRIDES),  # Bengali
    (0x0A00, 0x0A7F, 0x0080, _GUR_OVERRIDES),  # Gurmukhi
)

# Arabic/Urdu script has no mechanical Gujarati mapping → dropped entirely
# (Arabic-Indic digits and a few punctuation marks are converted instead, see
# _EXTRA_MAP). Vedic/Devanagari-extended and Kaithi ranges are dropped too.
_STRIP_RANGES = (
    (0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF), (0xFE70, 0xFEFF),
    (0x1CD0, 0x1CFF), (0xA8E0, 0xA8FF),
    (0x11080, 0x110CF),
)

# Conversions outside the Indic blocks.
_EXTRA_MAP: dict[int, str] = {
    # Arabic-Indic / Persian digits → ASCII (so numbers survive Urdu slips)
    **{0x0660 + d: chr(ord("0") + d) for d in range(10)},
    **{0x06F0 + d: chr(ord("0") + d) for d in range(10)},
    0x060C: ",",  # ، Arabic comma
    0x061B: ";",  # ؛ Arabic semicolon
    0x061F: "?",  # ؟ Arabic question mark
}


def _is_unassigned(cp: int) -> bool:
    return unicodedata.category(chr(cp)) == "Cn"


def _build_char_map() -> dict[int, str]:
    cmap: dict[int, str] = dict(_EXTRA_MAP)
    for start, end, offset, overrides in _BLOCKS:
        for cp in range(start, end + 1):
            if cp in overrides:
                cmap[cp] = overrides[cp]
            elif _is_unassigned(cp):
                cmap[cp] = ""  # unassigned source → nothing to preserve
            else:
                target = cp + offset
                cmap[cp] = chr(target) if not _is_unassigned(target) else ""
    return cmap


_CHAR_MAP: dict[int, str] = _build_char_map()


def sanitize_gujarati(text: str | None) -> str:
    """Remap Devanagari/Bengali/Gurmukhi slips to Gujarati, drop Arabic script.

    Idempotent and safe on partial streaming deltas: every mapping is a pure
    per-codepoint rewrite, so chunk boundaries never matter.
    """
    if not text:
        return text or ""
    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        if cp < 0x0600:  # fast path: Latin, ASCII, Gujarati, emoji < U+0600
            out.append(ch)
            continue
        mapped = _CHAR_MAP.get(cp)
        if mapped is not None:
            if mapped:
                out.append(mapped)
            continue
        if any(lo <= cp <= hi for lo, hi in _STRIP_RANGES):
            continue
        out.append(ch)
    return "".join(out)
