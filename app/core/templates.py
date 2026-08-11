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
    return "\n".join(
        f"@font-face {{ font-family: '{name}'; src: url('fonts/{file}'); }}"
        for name, file in fonts
    )


def template_names() -> list[str]:
    return list(_TEMPLATES)


def template_label(name: str) -> str:
    return _TEMPLATES.get(name, {}).get("label", name)


def build_css(options) -> str:  # noqa: ANN001
    """CSS كامل = أساس (اتجاه/خط/فقرة) + أجزاء القالب إن وُجد.

    تُستخدم كل إعدادات الفقرة: المحاذاة، الهوامش، اللون، المسافات، الإزاحة.
    """
    pf = options.paragraph
    color_rule = f"color: {pf.color}; " if pf.color else ""
    base = f"""@namespace epub "http://www.idpf.org/2007/ops";
body {{ direction: {options.direction}; line-height: {pf.line_height};
       margin-top: {pf.margin_top}; margin-bottom: {pf.margin_bottom}; }}
p {{ text-align: {pf.alignment}; line-height: {pf.line_height}; margin: 0 0 {pf.spacing_after};
    text-indent: {pf.first_line_indent}; font-size: {pf.font_size}; {color_rule}}}
h1, h2, h3 {{ font-family: '{options.title_font}', serif; }}
body, p {{ font-family: '{options.body_font}', serif; }}
"""
    extra = _TEMPLATES.get(options.template or "", {}).get("css", "")
    if options.custom_css:
        extra += "\n" + options.custom_css
    return base + "\n" + extra if extra else base