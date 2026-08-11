"""خوارزمية تنسيق النص العربي متعددة الطبقات.

تحوّل نصًّا خامًّا إلى فقرات HTML دون إتلاف أسطر الكاتب:

الطبقة 1 - التطبيع: توحيد نهايات الأسطر والمسافات والسطور الفارغة المكررة.
الطبقة 2 - فكّ الأسطر إلى "كتل" تفصلها سطور فارغة (نسق فقرات صريح).
الطبقة 3 - داخل كل كتلة: قرار النوع —
          فقرة سردية طويلة (سطر ملفوف تلقائيًّا) تُدمج في سطر واحد،
          أم أسطر مستقلة (شعر / تعداد / أسطر قصيرة متعاقبة) تُحفظ كلٌّ
          منها فقرةً وحدها. بهذا لا تذوب أسطر الكاتب في فقرة عملاقة.
الطبقة 4 - توليد HTML آمن بفقرات <p> مع اتجاه RTL.

كل عنصر في ناتج split_paragraphs = فقرة واحدة تُغلّف بـ <p>، وبهذا
تتقاسم المعاينة ومولّد EPUB الناتج نفسه بلا ازدواج.
"""
from __future__ import annotations

import html as _html
import re

_NUMBERED = re.compile(r"^\s*[\dA-Za-z٠-٩]{1,3}\s*[.):\-–]\s*")
_WRAP_THRESHOLD = 120  # طول السطر الذي يعدّ النص ملفوفًا تلقائيًّا (نثرًا)


def normalize(text: str) -> str:
    """الطبقة 1: توحيد النهايات وضغط الفجوات دون تمزيق السطور."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    text = re.sub(r"[ \t]+\n", "\n", text)   # فراغات نهاية السطر
    text = re.sub(r"\n{3,}", "\n\n", text)   # ضغط ثلاث أسطر فارغة فأكثر
    return text


def split_blocks(body: str) -> list[list[str]]:
    """الطبقة 2: النص → كتل؛ كل كتلة قائمة أسطرها (بلا فراغات زائدة)."""
    blocks: list[list[str]] = []
    cur: list[str] = []
    for raw in normalize(body).split("\n"):
        line = raw.strip()
        if line:
            cur.append(line)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return blocks


def _is_verse_like(lines: list[str]) -> bool:
    """الطبقة 3: تصنيف الكتلة — أسطر مستقلة أم فقرة نثرية تُدمج.

    - سطر يبدأ بعدّ (رقم/حرف + فاصل) → تعداد/قائمة: أسطر مستقلة.
    - سطر طويل (> _WRAP_THRESHOLD) → نص ملفوف تلقائيًّا: يدمج.
    - غير ذلك → أسطر مستقلة محفوظة (شعر، رسالة، سطور قصيرة).
    """
    if any(_NUMBERED.match(ln) for ln in lines):
        return True
    if any(len(ln) > _WRAP_THRESHOLD for ln in lines):
        return False
    return True


def split_paragraphs(body: str) -> list[str]:
    """الطبقة 2+3: الجسم → قائمة الفقرات النهائية (محفوظة الأسطر)."""
    paras: list[str] = []
    for lines in split_blocks(body):
        if not lines:
            continue
        if len(lines) == 1 or not _is_verse_like(lines):
            paras.append(" ".join(lines))
        else:
            paras.extend(lines)
    return paras


def body_to_html(body: str, direction: str = "rtl") -> str:
    """الطبقة 4: الفقرات النهائية → HTML آمن داخل <p>."""
    return "\n".join(f"<p>{_html.escape(p)}</p>" for p in split_paragraphs(body))


def escape(text: str) -> str:
    """تهريب HTML آمن للعرض داخل الفقرات."""
    return _html.escape(text)
