"""اختبارات القوالب (M5.4)."""
from __future__ import annotations

from zipfile import ZipFile

from app.core.epub import EpubWriter
from app.core.templates import build_css, template_label, template_names
from app.models import Book, Chapter, EpubOptions, Metadata


def test_five_templates():
    names = template_names()
    assert len(names) == 5
    assert "novel-ar" in names
    for n in names:
        assert template_label(n)  # لكل قالب وصف


def test_each_template_injects_unique_css():
    css = {n: build_css(EpubOptions(template=n)) for n in template_names()}
    # "novel-ar" يضيف المسافة البادئة؛ "poetry" يوسّط
    assert "text-indent: 2.5em" in css["novel-ar"]
    assert "text-align: center" in css["poetry"]
    assert "background: #1c1917" in css["classic"]


def test_writer_uses_template_css(tmp_path):
    b = Book(metadata=Metadata(title="t", language="ar"))
    b.add_chapter(Chapter(title="ف", body="ن."))
    b.options.template = "poetry"
    out = tmp_path / "t.epub"
    EpubWriter(b, tmp_path).write(out)
    with ZipFile(out) as zf:
        css = zf.read("OEBPS/style.css").decode("utf-8")
    assert "text-align: center" in css


def test_custom_css_appended(tmp_path):
    opts = EpubOptions(template="novel-ar")
    css = build_css(opts)
    assert "text-indent: 2.5em" in css  # قالب novel-ar حاضر رغم custom فارغ


def test_paragraph_alignment_center_in_css():
    opts = EpubOptions(template="novel-ar")
    opts.paragraph.alignment = "center"
    css = build_css(opts)
    assert "p { text-align: center;" in css


def test_paragraph_margins_and_color_in_css():
    opts = EpubOptions(template="novel-ar")
    opts.paragraph.margin_top = "1em"
    opts.paragraph.margin_bottom = "2em"
    opts.paragraph.color = "#b45309"
    css = build_css(opts)
    assert "margin-top: 1em;" in css
    assert "margin-bottom: 2em;" in css
    assert "color: #b45309;" in css


def test_no_color_rule_when_empty():
    opts = EpubOptions()
    opts.paragraph.color = ""
    css = build_css(opts)
    assert "color: #" not in css.split("body, p")[0]


def test_preview_reflects_paragraph_alignment():
    """المعاينة تستخدم نفس build_css → محاذاة الفقرة تنعكس على المعاينة."""
    from app.ui.preview import book_to_html
    from app.models import Book, Chapter, Metadata

    b = Book(metadata=Metadata(title="t", language="ar"))
    b.add_chapter(Chapter(title="ف", body="ن."))
    b.options.paragraph.alignment = "right"
    html = book_to_html(b, options=b.options)
    assert "text-align: right;" in html