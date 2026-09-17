"""القوالب الجاهزة (5): CSS لكل قالب يُدرج في ملف EPUB."""
from __future__ import annotations

# كل قالب: أجزاء CSS تُضاف فوق الأساس. المفاتيح نصوص صالحة كسلاسل CSS.
_TEMPLATES: dict[str, dict[str, str]] = {
    "novel-ar": {
        "label": "رواية كلاسيكية",
        "css": """body { background: #faf7f0; color: #26221c; }
h1 { text-align: center; margin: 2em 0 1.5em; }
p { text-indent: 2.5em; }
""",
    },
    "poetry": {
        "label": "شعر",
        "css": """body { background: #fffef9; color: #1f1a14; }
h1 { text-align: center; }
p { text-align: center; text-indent: 0; line-height: 2.4; }
""",
    },
    "classic": {
        "label": "كلاسيكي داكن",
        "css": """body { background: #1c1917; color: #ece5d8; }
h1 { text-align: center; color: #d6b478; }
p { text-indent: 2em; }
""",
    },
    "modern": {
        "label": "عصري",
        "css": """body { background: #ffffff; color: #111318; }
h1 { text-align: right; font-family: 'Amiri', sans-serif; }
p { text-indent: 0; margin-bottom: 1.2em; }
""",
    },
    "kids": {
        "label": "أطفال",
        "css": """body { background: #fff8ec; color: #4a3a1e; }
h1 { text-align: center; color: #b45309; }
p { text-indent: 0; line-height: 2.2; font-size: 1.15em; }
""",
    },
}

_TEMPLATE_NAMES = tuple(_TEMPLATES)


def build_font_faces(fonts: list[tuple[str, str]]) -> str:
    """قواعد @font-face للخطوط المضمّنة.

    كل عنصر (اسم العائلة، اسم الملف داخل OEBPS/fonts/). تُبنى القواعد قبل
    قواعد الجسم حتى تتفوّق عائلة الخط المضمّن عند المطابقة.
    """
    if not fonts:
        return ""
    from urllib.parse import quote as _quote

    rules = []
    for name, file in fonts:
        safe_name = "".join(ch for ch in str(name) if ch.isalnum() or ch in (" ", "-", "_"))[:64] or "font"
        safe_file = _quote(str(file), safe="")
        rules.append(f"@font-face {{ font-family: '{safe_name}'; src: url('fonts/{safe_file}'); }}")
    return "\n".join(rules)


def template_names() -> list[str]:
    return list(_TEMPLATES)


def template_label(name: str) -> str:
    return _TEMPLATES.get(name, {}).get("label", name)


def _sanitize_css_value(value: str, allowed: set[str], fallback: str) -> str:
    v = (value or "").strip().lower()
    return v if v in allowed else fallback


def _sanitize_font_name(value: str, fallback: str = "Amiri") -> str:
    v = "".join(ch for ch in (value or "") if ch.isalnum() or ch in (" ", "-", "_")).strip()[:64]
    return v or fallback


def build_css(options) -> str:  # noqa: ANN001
    """CSS كامل = أساس (اتجاه/خط/فقرة) + أجزاء القالب إن وُجد.

    تُستخدم كل إعدادات الفقرة: المحاذاة، الهوامش، اللون، المسافات، الإزاحة.
    """
    import re as _re

    pf = options.paragraph
    alignment = _sanitize_css_value(pf.alignment, {"left", "right", "center", "justify", "start", "end"}, "justify")
    direction = _sanitize_css_value(options.direction, {"rtl", "ltr"}, "rtl")
    title_font = _sanitize_font_name(options.title_font)
    body_font = _sanitize_font_name(options.body_font)
    # قيم القياس: رقم + وحدة آمنة فقط
    def _measure(v: str, fb: str) -> str:
        v = (v or "").strip().lower()
        return v if _re.fullmatch(r"\d+(\.\d+)?(em|rem|px|pt|%|)", v) else fb
    line_height = _measure(pf.line_height, "1.8")
    spacing_after = _measure(pf.spacing_after, "1em")
    first_indent = _measure(pf.first_line_indent, "1.5em")
    font_size = _measure(pf.font_size, "1em")
    margin_top = _measure(pf.margin_top, "0")
    margin_bottom = _measure(pf.margin_bottom, "0")
    color = (pf.color or "").strip()
    color_rule = f"color: {color}; " if _re.fullmatch(r"#[0-9a-fA-F]{3,8}|[a-z]+", color) else ""
    base = f"""@namespace epub "http://www.idpf.org/2007/ops";
body {{ direction: {direction}; line-height: {line_height};
       margin-top: {margin_top}; margin-bottom: {margin_bottom}; }}
p {{ text-align: {alignment}; line-height: {line_height}; margin: 0 0 {spacing_after};
    text-indent: {first_indent}; font-size: {font_size}; {color_rule}}}
h1, h2, h3 {{ font-family: '{title_font}', serif; }}
body, p {{ font-family: '{body_font}', serif; }}
"""
    extra = _TEMPLATES.get(options.template or "", {}).get("css", "")
    if options.custom_css:
        extra += "\n" + options.custom_css
    return base + "\n" + extra if extra else base