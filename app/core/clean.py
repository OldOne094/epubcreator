"""أدوات معالجة النصوص العربية + اكتشاف الفصول (Chapter Detection).

قواعد ذهبية (لا تُكسر أبدًا):
- لا Normalize (NFKC/NFKD) قد يغيّر حرفًا/رقمًا عربيًا.
- لا حذف تشكيل/همزات/علامات وقوف.
- لا تحويل بين ١٢٣ و 123.
- RTL يُدار في طبقة HTML/CSS، وليس هنا في النص.
"""
from __future__ import annotations

import re

# محارف غير مرئية/تحكم تُمسح بأمان (غير عربية/تشكيل/أرقام).
# ملاحظة: ZWNJ ‏(U+200C) و ZWJ ‏(U+200D) مُستثنيان عمدًا — الأول حرف دلالي
# في الفارسية/الأردية (نيم‌فاصله)، والثاني يربط تسلسلات الإيموجي.
_INVISIBLE = (
    "\u200b"   # ZERO WIDTH SPACE
    "\u200e"   # LEFT-TO-RIGHT MARK
    "\u200f"   # RIGHT-TO-LEFT MARK
    "\u202a\u202b\u202c\u202d\u202e"  # حروف بوصلة الاتجاه
    "\u2060"   # WORD JOINER
    "\ufeff"   # BOM / ZWNBSP
)
_RE_INVISIBLE = re.compile(f"[{_INVISIBLE}]")
_RE_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_RE_TRIPLE_NL = re.compile(r"\n[ \t]*\n\s*\n+")

# ---------------------------------------------------------------- عناوين الفصول
# الكشف متسامح مع ما يلي (دون تغيير النص المخزَّن أصلًا):
#   - التشكيل/الحركات (الفصلُ الأولُ)
#   - حروف الألف/الهمزات المتنوعة (ا/أ/إ/آ/ٱ) والياء (ي/ى)
#   - صيغ عرض NFKC (اﻷول) والمدّة "ـ"
#   - فواصل بين الكلمة والترتيب: "الفصل - الأول"، "الفصل (الأول)"
#   - ترتيب لفظي أوسع: الحادي عشر، الثاني عشر، العشرون، الحادي والعشرون…
#   - كلمات فصل أخرى: الباب/الجزء/القسم/المبحث/المطلب + فصل/باب/قسم
#   - عناوين مستقلة: المقدمة/التمهيد/الخاتمة/الفهرس…

# حركات وتشكيل تُزال من "نسخة المطابقة" فقط
_DIACRITICS = "".join(
    [
        "\u064b", "\u064c", "\u064d", "\u064e", "\u064f",  # تنوين + فتحة/ضمة
        "\u0650", "\u0651", "\u0652",  # كسرة/شدة/سكون
        "\u0653", "\u0654", "\u0655", "\u0656", "\u0657", "\u0658",
        "\u0670", "\u0640",  # ألف خنجرية + مدّة
        "\u06d6", "\u06d7", "\u06d8", "\u06d9", "\u06da", "\u06db",
        "\u06dc", "\u06dd", "\u06de", "\u06df", "\u06e0", "\u06e1",
        "\u06e2", "\u06e3", "\u06e4", "\u06e5", "\u06e6", "\u06e7",
        "\u06e8", "\u06e9", "\u06ea", "\u06eb", "\u06ec", "\u06ed",
    ]
)
_RE_DIACRITICS = re.compile(f"[{_DIACRITICS}]")
_TR_A = str.maketrans("أإآٱ", "اااا")
_TR_Y = str.maketrans("ى", "ي")
_RE_SEPARATORS = re.compile(r"[-ـ:;–—()\[\]«»\"'.,،؛!؟]+")

# ترتيب لفظي عربي (واردات ككلمات) — بحروف مُطبّعة (ا/ي) لأن النص يُمرَّر
# عبر _norm_for_match قبل المطابقة.
_ORDINAL_BODY = (
    r"اول|ثاني|ثان|ثالث|رابع|خامس|سادس|سابع|ثامن|تاسع|عاشر|"
    r"حادي\s*عشر|ثاني\s*عشر|ثالث\s*عشر|رابع\s*عشر|خامس\s*عشر|"
    r"سادس\s*عشر|سابع\s*عشر|ثامن\s*عشر|تاسع\s*عشر|"
    r"عشرون|ثلاثون|اربعون|خمسون|ستون|سبعون|ثمانون|تسعون|"
    r"(?:حادي|ثاني|ثالث|رابع|خامس|سادس|سابع|ثامن|تاسع)\s*والعشرون|"
    r"مائة|مئة|اخر|اخير"
)
# "ال" اختيارية هنا (فصل أول/ثانٍ بلا تعريف شائع) — بحروف مُطبّعة (ا/ي).
_ORDINAL = rf"(?:ال)?(?:{_ORDINAL_BODY})"

_NUM = r"(?:[\u0660-\u0669]+|\d+)"

# فواصل مسموحة بين الكلمة والترتيب ("الفصل - الأول"، "الفصل (الأول)").
_SEP_BETWEEN = r"[\s\-ـ:;–—()\[\]«»\"'.,،؛!؟]*"

# بادئة عنوان الفصل فقط (بلا تثبيت للنهاية) — يُفحَص ما بعدها صراحةً في
# is_chapter_heading لمنع تقسيم الجمل السردية ("الباب 5 مفتوح…").
_RE_CHAPTER_LEAD = re.compile(
    rf"^(?:الفصل|الباب|الجزء|القسم|المبحث|المطلب|فصل|باب|قسم|"
    rf"Chapter|CHAPTER|Chap\.?|Ch\.?|Part|PART){_SEP_BETWEEN}"
    rf"(?:{_NUM}|{_ORDINAL})\b"
)

# عناوين مستقلة بلا رقم (تقديم/خاتمة…) — بحروف مُطبّعة (ا/ي)، مع صيغ بلا "ال".
_RE_STANDALONE = re.compile(
    r"^(?:المقدمة|التمهيد|الخاتمة|الفهرس|القائمة|المحتويات|"
    r"الاستهلال|الاهداء|كلمة الناشر|تمهيد|استهلال|"
    r"مقدمة|خاتمة|فهرس|اهداء)$"
)
_MAX_HEADING_LEN = 120  # سقف العنوان (روايات بعناوين فصول طويلة)

# ذيل بعد الرقم يُقبَل فقط إن بدأ بفاصل صريح (": البداية"، "(تتمة)").
_SEP_TAIL = frozenset("-ـ:;–—()[]«»\"'.,،؛!؟")


def _norm_for_match(line: str) -> str:
    """نسخة مبسطة للمطابقة فقط — لا تُكتب أبدًا إلى النص المخزَّن.

    تحويل صيغ العرض، ثم إزالة التشكيل والمدّة، وتوحيد الألف/الياء،
    وتحويل الفواصل إلى مسافات، وضغط المسافات.
    """
    import unicodedata

    s = unicodedata.normalize("NFKC", line)
    s = _RE_DIACRITICS.sub("", s)
    s = s.translate(_TR_A).translate(_TR_Y)
    s = _RE_SEPARATORS.sub(" ", s)
    return " ".join(s.split())


def _norm_keep_sep(line: str) -> str:
    """كـ _norm_for_match لكن مع إبقاء الفواصل لمعرفة موضعها بعد الرقم."""
    import unicodedata

    s = unicodedata.normalize("NFKC", line)
    s = _RE_DIACRITICS.sub("", s)
    s = s.translate(_TR_A).translate(_TR_Y)
    return " ".join(s.split())


def is_chapter_heading(line: str) -> bool:
    """هل السطر عنوان فصل محتمل؟ (متسامح مع التشكيل واختلاف الحروف).

    - بادئة (فصل/باب…) + رقم/ترتيب بلا ذيل → عنوان.
    - ذيل بعد الرقم يُقبَل فقط إن بدأ بفاصل صريح ("الفصل 1: البداية") وكان
      قصيرًا — جملة سردية ("الباب 5 مفتوح…") لا تُقسَّم.
    """
    s = line.strip()
    if not s or len(s) > _MAX_HEADING_LEN:   # العناوين عادة قصيرة
        return False
    norm = _norm_keep_sep(s)
    m = _RE_CHAPTER_LEAD.match(norm)
    if m:
        tail = norm[m.end():].strip()
        if not tail:
            return True
        # ذيل بفاصل صريح ("1: البداية") مسموح بطول العنوان؛ غيره سرد مرفوض
        return tail[0] in _SEP_TAIL
    return bool(_RE_STANDALONE.fullmatch(_norm_for_match(s)))


def strip_bom_and_invisible(text: str) -> str:
    """إزالة BOM والمحارف غير المرئية مع إبقاء النص حرفيًا."""
    return _RE_INVISIBLE.sub("", text.lstrip("\ufeff"))


def fix_whitespace(text: str) -> str:
    """توحيد نهاية الأسطر وإزالة الفراغات/الأسطر الفارغة الزائدة.

    تُحفَظ إزاحة بداية السطر (شعر/اقتباس) كما هي؛ الدمج يطال الفراغات
    الداخلية فقط حتى لا تتدمر المحاذاة المتعمدة.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for ln in text.split("\n"):
        m = re.match(r"[ \t]*", ln)
        lead = m.group(0).replace("\t", "    ")
        rest = _RE_MULTI_SPACE.sub(" ", ln[m.end():])
        lines.append(lead + rest)
    text = "\n".join(lines)
    text = _RE_TRIPLE_NL.sub("\n\n", text)
    return text.strip("\n")


def clean_arabic(text: str) -> str:
    """أنابيب تنظيف شاملة: BOM + invisibles + تقارب بين الأسطر. UTF-8 نقي."""
    return fix_whitespace(strip_bom_and_invisible(text))


def encode_utf8(value: str) -> bytes:
    """ترميز UTF-8 موحّد (يُستخدم عند الكتابة إلى ملفات EPUB)."""
    return value.encode("utf-8")


def _looks_like_body(line: str) -> bool:
    """هل السطر جزء من جسم الفصل (لا عنوانًا)؟"""
    return bool(line.strip()) and not is_chapter_heading(line)


def detect_chapters(text: str) -> list[str]:
    """تقسيم النص إلى فصول. إن لم يوجد أي عنوان فصل، يعيد النص كفصل واحد.

    تُحفظ الأسطر الفارغة **داخل** الكتلة كفواصل فقرات (سطر فارغ = فقرة
    جديدة) حتى لا يذوب النص في كومة واحدة عند التحرير/البناء.
    """
    lines = text.split("\n")
    chunks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        block = "\n".join(current).strip("\n")
        if block:
            chunks.append(block)
        current = []

    for line in lines:
        if is_chapter_heading(line):
            flush()
            current = [line.rstrip()]
        elif _looks_like_body(line):
            current.append(line.rstrip())
        elif current and current[-1] != "":
            # سطر فارغ داخل فصل: يُحفظ فاصل فقرات (دون تكرار الأسطر الفارغة)
            current.append("")
    flush()

    return chunks or ([text] if text.strip() else [])