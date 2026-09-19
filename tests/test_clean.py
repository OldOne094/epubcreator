"""اختبارات تنظيف النصوص العربية — هدف صارم: لا كسر لتشكيل/أرقام."""
from __future__ import annotations

from app.core.clean import (
    clean_arabic,
    detect_chapters,
    is_chapter_heading,
    strip_bom_and_invisible,
)


def test_strip_bom():
    assert strip_bom_and_invisible("\ufeffبسم الله") == "بسم الله"


def test_clean_keeps_tashkeel():
    src = "قالَ ﴿وَقُلْ رَبِّ زِدْنِي عِلْمًا﴾"
    assert clean_arabic(src) == src


def test_clean_keeps_arabic_indic_digits():
    src = "سنة ١٤٤٧ هـ والعدد 2026"
    assert clean_arabic(src) == src


def test_clean_removes_invisible():
    assert strip_bom_and_invisible("a\u200fb") == "ab"


def test_clean_preserves_zwnj_and_zwj():
    # ZWNJ حرف دلالي (فارسية/أردية) وZWJ يربط الإيموجي — لا يُحذفان
    assert strip_bom_and_invisible("ك\u200cلمة") == "ك\u200cلمة"
    assert strip_bom_and_invisible("نیم\u200cفاصله") == "نیم\u200cفاصله"
    assert clean_arabic("👨\u200d👩\u200d👧") == "👨\u200d👩\u200d👧"


def test_clean_normalizes_newlines():
    raw = "سطر1\r\n\r\n\r\n\r\nسطر2"
    assert clean_arabic(raw) == "سطر1\n\nسطر2"


def test_detect_arabic_chapters():
    text = (
        "الفصل الأول\n\nبداية القصة هنا.\n\n"
        "الفصل الثاني\n\nاستمرار الأحداث.\n\n"
        "الفصل ١٢٣\n\nفصل بأرقام هندية."
    )
    chunks = detect_chapters(text)
    assert len(chunks) == 3
    assert chunks[0].startswith("الفصل الأول")
    assert chunks[2].startswith("الفصل ١٢٣")


def test_detect_english_chapters():
    text = "Chapter 1\n\nintro text\n\nChapter 2\n\nmore text"
    assert len(detect_chapters(text)) == 2


def test_single_block_no_heading():
    text = "لا عناوين هنا، نص واحد متصل."
    assert detect_chapters(text) == [text]


def test_heading_heuristics():
    assert is_chapter_heading("الفصل الثالث")
    assert is_chapter_heading("الباب الأول")
    assert is_chapter_heading("Chapter 7")
    assert not is_chapter_heading("في يوم من الأيام كانت هناك قصة طويلة جدا جدا جدا.")


def test_heading_without_al():
    # ترتيب بلا "ال" شائع ويُكتشف
    assert is_chapter_heading("فصل أول")
    assert is_chapter_heading("باب ثانٍ")
    assert is_chapter_heading("الفصل - الأول")
    assert is_chapter_heading("الفصل 1: البداية")


def test_heading_rejects_narrative_sentence():
    # جملة سردية تبدأ بكلمة فصل لا تُقسَّم
    assert not is_chapter_heading("الباب 5 مفتوح والشباك مكسور منذ أيام طويلة")
    assert not is_chapter_heading("الباب 5 مفتوح")


def test_heading_long_title_accepted():
    long_title = "الفصل الأول: " + "حكاية طويلة " * 8
    assert len(long_title) > 60
    assert is_chapter_heading(long_title.strip())


def test_heading_standalone_without_al():
    assert is_chapter_heading("مقدمة")
    assert is_chapter_heading("خاتمة")
