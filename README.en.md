# 📗 EPubCreator

A desktop **EPUB** book builder for **Windows**, written in **Python + PySide6**,
with first-class Arabic support: chapter editing, metadata, typography, covers,
live preview, and export conforming to **EPUB3** (with backward-compatible **EPUB2**).

> Open source and test-driven — the goal is polished Arabic e‑books through a
> simple UI, without heavyweight technology.

---

## ✨ Features

- **Multi-format import**: `TXT` · `Markdown` · `HTML` · `DOCX` · `RTF` — via file picker or drag & drop.
- **Automatic chapter detection** (Arabic/English headings) and splitting into editable chapters.
- **Chapter editor** with a navigation tree; edit each chapter independently.
- **Metadata**: title, author, translator, publisher, description, keywords, language,
  ISBN, series, part, rights, cover — with mandatory validation of the minimum required fields.
- **Multi-layer Arabic formatting**: preserves the author's line breaks instead of
  collapsing everything into one giant paragraph (blank line = new paragraph,
  short/verse/list lines stay separate, word-wrapped prose is merged intelligently).
- **5 ready-made templates**: Classic Novel · Poetry · Dark Classic · Modern · Kids, plus **custom CSS**.
- **Paragraph formatting**: alignment, line-height, spacing, first-line indent, size, margins, color.
- **Covers**: user image (resize/compress) or **auto-generated** cover using your
  template's colors and fonts, with **connected Arabic text shaping** for titles
  (no detached letters — shaping is built in).
- **Live RTL preview** of chapters before export.
- **EPUB2/EPUB3 export** on a background thread with progress — no UI freezes.
- **UI themes**: light / dark.
- **Non-blocking logging** (JSON Lines) via queue + listener.

---

## 🛠️ Tech Stack

| Layer             | Technology                                    |
|-------------------|-----------------------------------------------|
| Language          | Python 3.11+                                  |
| UI                | PySide6 (Qt) — QTextBrowser preview           |
| EPUB generation   | Lightweight in-house `zipfile` + `lxml`       |
| DOCX import       | `python-docx`                                 |
| RTF import        | `striprtf`                                    |
| Markdown import   | `markdown-it-py`                              |
| Images / covers   | `Pillow` + `arabic_reshaper` + `python-bidi`  |
| Paths             | `platformdirs`                                |
| Packaging         | PyInstaller                                   |
| Testing           | pytest                                        |

> No heavy dependencies: no `EbookLib` (AGPL), and no WebEngine in the bundle
> (Chromium is optional and far too large to ship).

---

## 📂 Project Layout

```
epubcreator/
├─ app/
│  ├─ main.py            # Application entry point
│  ├─ settings.py        # config.json (platformdirs) + logging
│  ├─ models.py          # dataclasses: Metadata, Chapter, EpubOptions, Book
│  ├─ state.py           # BookState (QObject) — book state signals
│  ├─ workers.py         # ImportJob / ExportJob (QThreadPool)
│  ├─ core/
│  │  ├─ importers.py    # txt/docx/rtf/html/md → Book
│  │  ├─ clean.py        # Arabic cleanup + chapter detection
│  │  ├─ format.py       # Multi-layer Arabic paragraph formatting
│  │  ├─ epub.py         # EPUB3/EPUB2 generator + CSS/OPF/nav
│  │  ├─ covergen.py     # Cover (Pillow + Arabic shaping) + user image
│  │  ├─ templates.py    # 5 CSS templates
│  │  └─ validate.py     # XHTML/OPF internal validation
│  └─ ui/
│     ├─ main_window.py  # Window + toolbar/pages + import/export
│     ├─ pages.py        # Pages: editor · metadata
│     ├─ preview.py      # QTextBrowser preview
│     ├─ dialogs.py      # Errors / progress
│     └─ themes.py       # Light/dark themes (QSS)
├─ tests/               # pytest (importers, clean, format, epub, cover, UI)
├─ dist/                # Final bundle (EPubCreator.exe)
└─ epubcreator.spec     # PyInstaller onefile spec
```

---

## ▶️ Run from Source

> Requires **Python 3.11** or newer.

```bash
# 1. Create a virtual environment
python -m venv .venv
.\.venv\Scripts\activate      # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python -m app.main
```

---

## 🧪 Tests

```bash
.\.venv\Scripts\python -m pytest tests -q
```

Coverage: importers, Arabic cleanup/encoding, paragraph formatting, EPUB generation,
covers (Arabic shaping + template colors), preview, UI (PySide6 offscreen), and validation.

---

## 🔨 Build the Executable (EXE)

```bash
.\.venv\Scripts\pyinstaller epubcreator.spec --noconfirm --clean
```

Output: **`dist\EPubCreator.exe`** (single file, ~57 MB, no console window).
The spec excludes heavy Qt modules (QtWebEngine…) to keep the size down and embeds
the cover dependencies (`arabic_reshaper`, `python-bidi`) in the bundle.

> Close any running instance before rebuilding so the file isn't locked in `dist`.

---

## 🚀 Usage Flow

1. **Import** files (or drag & drop) → type is detected and the book is built automatically.
2. **Editor**: edit chapters; each has a title and body. The preview updates live.
3. **Metadata**: fill in the title (required) and other metadata.
4. **Formatting/Template**: pick a template or custom CSS; tune paragraphs and fonts.
5. **Cover**: use an image or auto-generate (follows your template's colors/fonts).
6. **Export EPUB** → save the `.epub` (EPUB3 by default).

---

## 📄 License

Open source; the application license is up to you and your project.

---

*An Arabic version of this document is available in [README.md](README.md).*
