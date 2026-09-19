"""Tests for the mixed-script Gujarati text sanitizer."""
from app.utils.text_sanitizer import sanitize_gujarati


class TestDevanagariToGujarati:
    def test_consonant(self):
        assert sanitize_gujarati("घर्षण") == "ઘર્ષણ"

    def test_word(self):
        assert sanitize_gujarati("कर") == "કર"

    def test_independent_vowels(self):
        assert sanitize_gujarati("एक") == "એક"
        assert sanitize_gujarati("ऐसे") == "ઐસે"

    def test_matras(self):
        assert sanitize_gujarati("किताब") == "કિતાબ"

    def test_nukta_letters(self):
        assert sanitize_gujarati("क़ीमत") == "કીમત"
        assert sanitize_gujarati("ज़रूरी") == "જરૂરી"

    def test_danda_kept(self):
        # Danda is legitimate Gujarati punctuation and must survive.
        assert sanitize_gujarati("આવો।") == "આવો।"


class TestBengaliToGujarati:
    def test_consonant(self):
        assert sanitize_gujarati("বিজ্ঞান") == "બિજ્ઞાન"

    def test_vowel(self):
        assert sanitize_gujarati("এক") == "એક"


class TestGurmukhiToGujarati:
    def test_consonant(self):
        assert sanitize_gujarati("ਪਾਣੀ") == "પાણી"

    def test_vowel(self):
        assert sanitize_gujarati("ਏਕ") == "એક"


class TestArabicScriptDropped:
    def test_urdu_word_dropped(self):
        assert sanitize_gujarati("વસ્તુઓ اپنی વર્તમાન") == "વસ્તુઓ  વર્તમાન"

    def test_arabic_digits_converted(self):
        assert sanitize_gujarati("૧૨૩ ٤٥") == "૧૨૩ 45"

    def test_arabic_punctuation_converted(self):
        assert sanitize_gujarati("કેમ છો؟") == "કેમ છો?"


class TestAsciiAndMarkdownPassthrough:
    def test_markdown_untouched(self):
        md = "**ઘર્ષણ** એટલે કે *friction*\n\n- `F = μN`\n- [link](http://x)\n```py\nprint(1)\n```"
        assert sanitize_gujarati(md) == md

    def test_ascii_untouched(self):
        assert sanitize_gujarati("F = m * a, v = u + at") == "F = m * a, v = u + at"

    def test_emoji_untouched(self):
        assert sanitize_gujarati("સારું! 🙂 🎯") == "સારું! 🙂 🎯"

    def test_english_terms_untouched(self):
        assert sanitize_gujarati("પરાવર્તન (Reflection)") == "પરાવર્તન (Reflection)"

    def test_empty_and_none(self):
        assert sanitize_gujarati("") == ""
        assert sanitize_gujarati(None) == ""


class TestMixedRealWorldAnswer:
    def test_realistic_answer(self):
        text = "એક આઇસ સ્કેટर જેમ કે घर्षण ઘટાડે છે, वस्तुओ اپنی বিজ্ঞান પ્રમાણે।"
        cleaned = sanitize_gujarati(text)
        for ch in cleaned:
            assert not (0x0900 <= ord(ch) <= 0x0963 or 0x0966 <= ord(ch) <= 0x097F), \
                f"Devanagari survived: {ch!r}"  # danda (0964/0965) is legit Gujarati punct
            assert not (0x0980 <= ord(ch) <= 0x09FF), f"Bengali survived: {ch!r}"
            assert not (0x0600 <= ord(ch) <= 0x06FF), f"Arabic survived: {ch!r}"
        assert "ઘર્ષણ" in cleaned
        assert "બિજ્ઞાન" in cleaned


class TestStreamingChunks:
    def test_chunked_equals_whole(self):
        full = "ગુજરાતी લખાણ घर्षण বিজ্ঞান اپنی 123 **bold**"
        chunks = [full[i:i + 7] for i in range(0, len(full), 7)]
        assert "".join(sanitize_gujarati(c) for c in chunks) == sanitize_gujarati(full)

    def test_idempotent(self):
        once = sanitize_gujarati("घर्षण اپنی બરાબર")
        assert sanitize_gujarati(once) == once
