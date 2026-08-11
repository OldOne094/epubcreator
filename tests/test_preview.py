"""اختبارات المعاينة والتنسيق (M3.3): HTML آمن متعدد الطبقات من فصل وكتاب."""
from __future__ import annotations

from app.models import Book, Chapter
from app.core.format import split_blocks, split_paragraphs
from app.ui.preview import body_to_html, chapter_to_html, book_to_html


def test_split_paragraphs_preserves_single_newline():
    # أسطر قصيرة مُتعاقبة بلا سطر فارغ → تُحفظ كل منها مستقلة (لا دمج في فقرة ضخمة)
    assert split_paragraphs("سطر أ.\nسطر ب.\n\nفقرة أخرى.") == ["سطر أ.", "سطر ب.", "فقرة أخرى."]


def test_split_paragraphs_full_lines_merge_wrapped():
    # سطر طويل (ملفوف تلقائيًّا) يُدمج في فقرة نثرية واحدة متصلة
    long_line = ("بالنصوص العربية التي تُلفّ تلقائيًّا يُفضَّل جمع السطور الممتدة "
                 "في فقرة سردية واحدة كي لا تتشظّى الجملة إلى أسطر مستقلّة. ") + "نهاية."
    body = long_line + "\n" + long_line
    assert split_paragraphs(body) == [long_line + " " + long_line]

def test_split_paragraphs_verse_kept_lines():
    # شعر: أسطر قصيرة متعاقبة تبقى أسطرًا مستقلة
    poem = "يا قلبُ جدِّد\nما قد مضى\nمن الحنين"
    assert split_paragraphs(poem) == ["يا قلبُ جدِّد", "ما قد مضى", "من الحنين"]


def test_split_paragraphs_numbered_list_kept():
    lines = "الأول.\nالثاني.\nالثالث."
    paras = split_paragraphs(lines)
    assert paras == ["الأول.", "الثاني.", "الثالث."]
    assert len(paras) == 3


def test_split_blocks_blank_separators():
    blocks = split_blocks("نص أ.\n\nنص ب.\nبب\n\nنص ج")
    assert blocks == [["نص أ."], ["نص ب.", "بب"], ["نص ج"]]


def test_body_to_html_escapes():
    html = body_to_html("نص <b>خیط</b> & أمبير")
    assert "<b>" not in html
    assert "&lt;b&gt;" in html
    assert "&amp;" in html


def test_chapter_to_html_dir_rtl():
    html = chapter_to_html(Chapter(title="عنوان", body="نص."), "rtl")
    assert "dir='rtl'" in html
    assert "<h1>عنوان</h1>" in html
    assert "<p>نص.</p>" in html


def test_book_to_html_renders_all():
    b = Book()
    b.chapters = [Chapter(title="أ", body="نص أ."), Chapter(title="ب", body="نص ب.")]
    html = book_to_html(b)
    assert "<h1>أ</h1>" in html
    assert "<h1>ب</h1>" in html
    assert "text-align: justify" in html


def test_book_to_html_slice():
    b = Book()
    b.chapters = [Chapter(title=str(i)) for i in range(3)]
    html = book_to_html(b, start=1, count=1)
    assert "<h1>1</h1>" in html
    assert "<h1>0</h1>" not in html
    assert "<h1>2</h1>" not in html