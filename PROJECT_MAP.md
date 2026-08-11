# PROJECT_MAP — EPubCreator

وثيقة الذاكرة الخارجية (External Project Memory). تعكس **الحالة الحالية للمشروع** وفق
التحليل الهندسي الشامل. تُحدَّث عند أي تغيير معماري أو إضافة ميزة.

> ملاحظة: أُعيدت كتابة هذه الوثيقة لأن النسخة السابقة كانت تالفة الترميز ومتعارضة مع الكود.
> المصدر الوحيد للحقيقة هنا هو `app/`.

---

## [PROJECT_OVERVIEW]

تطبيق سطح مكتب (Windows) بـ Python 3.11 + PySide6 لإنشاء وتحرير وبناء كتب EPUB
(EPUB3 افتراضياً + استرجاع EPUB2 عبر toc.ncx) مع دعم عربي احترافي (RTL، محافظة على
التشكيل/الهمزات/الأرقام الهندية، تشكيل الغلاف يدوياً).

الحالة: كل شيء في الذاكرة — **لا حفظ/فتح مشروع**. لا قاعدة بيانات، لا شبكة، لا مستخدمين.

---

## [TECH_STACK]

- Python 3.11.9 (تحقق فعلي من .venv)
- PySide6 6.11.1 — الواجهة؛ المعاينة عبر QTextBrowser
- lxml 6.1.1 — تحليل HTML + تحقق XML
- python-docx 1.2.0 — استيراد DOCX
- striprtf 0.0.32 — استيراد RTF
- markdown-it-py 4.2.0 — استيراد Markdown
- Pillow 12.3.0 — الغلاف/الصور
- platformdirs 4.11.0 — مسارات config/log
- arabic_reshaper 3.0.1 + python-bidi 0.6.11 — تشكيل/ترتيب الغلاف
- PyInstaller 6.21.0 (build فقط) — الحزمة `dist\EPubCreator.exe` ≈ 57MB
- pytest — dev

لا يُستخدم: EbookLib (تفادي AGPL)، WebEngine (الحجم)، قاعدة بيانات، git، CI.

---

## [DEPENDENCIES]

| الحزمة | الإصدار | الدور |
|---|---|---|
| PySide6 | 6.11.1 | الواجهة الكاملة |
| lxml | 6.1.1 | HTML + XML |
| python-docx | 1.2.0 | DOCX |
| striprtf | 0.0.32 | RTF |
| markdown-it-py | 4.2.0 | MD |
| Pillow | 12.3.0 | صور |
| platformdirs | 4.11.0 | مسارات |
| arabic_reshaper | 3.0.1 | تشكيل الغلاف |
| python-bidi | 0.6.11 | ترتيب RTL للغلاف |
| pyinstaller | 6.21.0 | build-only |
| pytest | 9.1.1 | dev |

لا circular dependencies. ملاحظة: قائمتان متوازيتان `requirements.txt` و `pyproject.toml`.

---

## [ARCHITECTURE]

طبقتان:
- `app/ui` → PySide6 (صفحات مربوطه بـ BookState)
- `app/core` → منطق نقي بلا Qt، قابل للاختبار
- `app/state` → `BookState` dataclass نقي (بلا QObject) + undo/redo (deepcopy، سقف 50)
- `app/models` → dataclasses الحالة

اتجاه التبعيات: `ui → state/models → core`. لا `core → ui` إطلاقاً.

---

## [SYSTEM_FLOW]

```
User → QFileDialog / Drag&Drop
 → MainWindow._import_paths → ImportJob (QThreadPool) → import_file/import_batch
 → clean_arabic → detect_chapters → Book
 → signals.finished → _on_import_done → state.set_book → reload
 → [UI] تحرير/بيانات/تنسيق/غلاف عبر BookState + notify
 → ExportJob → EpubWriter.write → zip (mimetype أولاً STORED)
 → validate_epub (خيط الواجهة) → ExportPage.show_result
```

- التحقق الإلزامي: العنوان فقط (يدوي في export_page.py:133).
- معاينة الغلاف: كاش بصمة في cover_page.py:178.
- Logging: QueueHandler+Listener، JSON Lines، RotatingFileHandler (1MB×3).

---

## [DIRECTORY_STRUCTURE]

```
epubcreator/
├─ app/
│  ├─ main.py            # نقطة الإدخال (DPI + QApplication + MainWindow)
│  ├─ settings.py        # config.json (platformdirs) + Logging غير حاجز
│  ├─ models.py          # dataclasses: Metadata, Chapter, ParagraphFormat, EpubOptions, Book
│  ├─ state.py           # BookState (dataclass نقي) + undo/redo
│  ├─ workers.py         # ImportJob / ExportJob (QThreadPool)
│  ├─ core/
│  │  ├─ clean.py        # تنظيف عربي + كشف الفصول (regex متسامح)
│  │  ├─ format.py       # تنسيق فقرات عربي متعدد الطبقات
│  │  ├─ importers.py    # txt/docx/rtf/html/md → Book
│  │  ├─ epub.py         # مولّد EPUB3/EPUB2 (zipfile) + OPF/NAV/NCX
│  │  ├─ covergen.py     # الغلاف (Pillow + تشكيل يدوي) + صورة المستخدم
│  │  ├─ templates.py    # 5 قوالب CSS + build_css
│  │  └─ validate.py     # تحقق داخلي (lxml + zipfile)
│  ├─ ui/
│  │  ├─ main_window.py  # نافذة + رأس + استيراد/تصدير + سحب وإفلات
│  │  ├─ sidebar.py      # تنقّل جانبي + تبديل الثيم
│  │  ├─ home_page.py    # نظرة عامة + حالة البداية
│  │  ├─ pages.py        # ChapterEditor + MetadataPage
│  │  ├─ style_page.py   # قوالب/خطوط/فقرة/CSS مخصص
│  │  ├─ cover_page.py   # غلاف + معاينة فورية
│  │  ├─ preview.py      # معاينة QTextBrowser بنفس CSS المولّد
│  │  ├─ export_page.py  # تصدير + تقدم + تقرير تحقق
│  │  ├─ widgets.py      # Section/PageHeader/muted_label
│  │  ├─ dialogs.py      # error_dialog + ProgressDialog (غير مستخدم)
│  │  └─ themes.py       # ثيمات فاتح/داكن (QSS بتوكنات)
│  └─ assets/            # مجلدات فارغة (PLACEHOLDER) — تُضمَّن في الحزمة بلا فائدة
├─ tests/                # 154 اختباراً (pytest) — يمرّون جميعاً
├─ dist/EPubCreator.exe  # ~56.7MB
├─ epubcreator.spec      # مخطط PyInstaller النشط
├─ EPubCreatorOne.spec   # مخطط قديم (ينقصه arabic_reshaper/bidi)
├─ build/                # epubcreator/ + EPubCreatorOne/ (أثر بناء قديم)
├─ pyproject.toml + requirements.txt
└─ README.md + README.en.md + IMPROVEMENT_PLAN.md
```

---

## [FEATURES] (المطبّقة فعلياً)

- استيراد TXT/MD/HTML/DOCX/RTF + Drag & Drop + دفعة (كل ملف كتاب مستقل)
- كشف فصول عربي/إنجليزي متسامح (تشكيل/همزات/أرقام هندية/أتربة لفظية)
- محرر فصول: إضافة/حذف (بتأكيد)/إعادة ترتيب/تسمية + Undo/Redo
- بيانات وصفية (11 حقلاً) — **تُجمع لكن يخرج منها فقط title/language/author/isbn إلى EPUB**
- تنسيق فقرة (Alignment/Line-height/Spacing/Indent/Size/Margins/Color)
  — **الـ alignment/margins/color بلا أثر في CSS المخرَج**
- 5 قوالب CSS + CSS مخصص + خطوط (أسماء فقط؛ بلا تضمين فعلي رغم embed_fonts=True)
- غلاف: صورة مستخدم (resize/ضغط) أو توليد تلقائي + تشكيل عربي متصل؛ صيغ JPEG/PNG/WebP
- معاينة حية RTL/LTR بنفس CSS المولّد
- تصدير EPUB2/EPUB3 في خيط خلفي + تقدم + تحقق داخلي
- ثيمات فاتح/داكن، Logging غير حاجز

غير مطبّق: حفظ/فتح مشروع، صور داخل الفصول، تضمين خطوط، Footnotes، TOC شجري، بحث/استبدال، تصدير دفعة للكتب، إعدادات موحّدة، i18n.

---

## [STATE_MANAGEMENT]

`BookState` = dataclass نقي (`state.py:16`) مع callback `_on_change` وإشعار مركزي.
لا يستخدم QObject/إشارات Qt. مكدّس undo/redo بلقطات deepcopy (سقف 50).

---

## [FILE_PIPELINE]

نوع الملف → importer → clean → detect_chapters → Book (metadata + chapters + options).

- `_read_text_auto`: UTF-8/UTF-16/BOM/CP1256 مع errors="replace".
- HTML: يَعقّم (script/style/on* / javascript:) ثم يستخرج نصاً فقط → فصول.

---

## [EPUB_GENERATION_PIPELINE]

فصل → OEBPS/kN_title.xhtml → nav.xhtml (EPUB3) / toc.ncx (EPUB2) →
content.opf (manifest/spine) → style.css → cover → mimetype أولاً (STORED) →
META-INF/container.xml → zip.

---

## [CSS_PIPELINE]

`build_css` = قاعدة (اتجاه/خط/فقرة) + CSS القالب + CSS مخصص.
الفقرة: line-height / spacing_after / first_line_indent / font_size تُستخدم؛
الـ alignment / margin_top / margin_bottom / color **لا تُستخدم**.

---

## [FONT_PIPELINE]

بلا تضمين فعلي: القوالب تشير لأسماء خطوط (Amiri…) فقط. `embed_fonts=True` خيار وهمي.
الغلاف يعتمد خطوط Windows (`C:/Windows/Fonts/…`) مع بدائل.

---

## [VALIDATION_PIPELINE]

تحقق داخلي (validate.py): mimetype أول/غير مضغوط، container.xml، OPF (dc:title/lang/id،
manifest hrefs، spine idrefs، cover، XHTML well-formed). لا epubcheck خارجي.

---

## [ERROR_HANDLING]

كل ImportJob/ExportJob يلتقط Exception → `JobResult(ok, errors)` / signals.error → error_dialog.
مبدأ: لا تجميد GUI، لا انهيار في الخيط. الدفعة تفشل كاملة عند أول خطأ (بلا نتائج جزئية).

---

## [LOGGING]

stdlib QueueHandler + QueueListener (غير حاجز) + RotatingFileHandler (1MB × 3، JSON Lines).
حقل `context` معرّف في JsonFormatter لكن لا شيء يكتبه.

---

## [CONFIGURATION]

`config.json` عبر platformdirs (user_config_dir). DEFAULT_CONFIG: language, last_template,
last_css, last_folder, last_font, epub_version. مفتاح `theme` يُقرأ/يُكتب لكنه غير معرّف في
الافتراضيات. مفاتيح language/last_css/last_font/epub_version بلا قراءة فعلية.

---

## [TESTING]

pytest، 154 اختباراً يمرّون (تحقق: `154 passed in 24.76s`). تغطية: clean/format/importers
(5 صيغ)/epub/validate/cover (formats+shape)/preview/state/undo/workers/pages (offscreen)/themes.
ثغرات تغطية: تصدير الميتاداتا، alignment في CSS، استيراد دفعة عبر الواجهة، حفظ مشروع.

---

## [OPTIMIZATION]

regexes مسبقة الترجمة، معالجة خيوط للاستيراد/التصدير، كاش بصمة معاينة الغلاف.
نقاط التحسين: deepcopy كامل في undo، معاينة تبني الكتاب كاملاً، تحقق بعد التصدير على خيط الواجهة.

---

## [SECURITY]

تطبيق سطح مكتب بلا شبكة/SQL. HTML sanitize (drop script/style + on* + javascript:).
النصوص تُهرب قبل كتابة XHTML/OPF. لا أسرار في الكود/config. ملاحظات: فتح صور بلا حد
أبعاد صريح؛ EPubCreatorOne.spec القديم ينقصه reshaper/bidi (يُحذف).

---

## [PERFORMANCE]

GUI لا تتجمد (jobs على QThreadPool). ملاحظات: undo = deepcopy لكل عملية؛ المعاينة تعرض
الكتاب كاملاً عند الفهرس 0؛ validate بعد التصدير على خيط الواجهة.

---

## [SCALABILITY / RESILIENCE]

بلا Horizontal scaling (تطبيق محلي). لا حفظ/استعادة/نسخ احتياطي. لا Idempotency للتصدير
(يكتب فوق الوجهة). لا graceful shutdown لـ QueueListener. سباق بيانات محتمل بين التحرير
والتصدير (ExportJob يحمل مرجع الكتاب الحي).

---

## [KNOWN_ISSUES]

1. الميتاداتا (publisher/translator/description/keywords/series/part/rights) لا تصل إلى OPF.
2. alignment/margins/color في تنسيق الفقرة بلا أثر على CSS المخرَج.
3. استيراد عدة ملفات يحمّل الأول فقط (الباقي يُهمل).
4. `embed_fonts=True` بلا تنفيذ + `assets/fonts` فارغ.
5. `EPubCreatorOne.spec` قديم/مكرر (ينقصه reshaper/bidi).
6. PROJECT_MAP سابقاً تالف — أُعيدت كتابته.
7. EPUB2: عنصر الغلاف يستخدم خاصية `properties` الخاصة بـ EPUB3.

---

## [RISKS]

- فقدان عمل المستخدم (لا حفظ مشروع) — أولوية قصوى.
- ميتاداتا مفقودة من الكتاب النهائي.
- تنسيقات يعدّلها المستخدم بلا أثر.
- سباق بيانات أثناء التصدير.
- توثيق/أصول مكررة تسبب بناءً خاطئاً.

---

## [IMPROVEMENT_ROADMAP]

1. حفظ/فتح مشروع (.epubproj) + حفظ تلقائي + ملفات حديثة.
2. تصدير الميتاداتا كاملة إلى OPF + اختبار round-trip.
3. تفعيل alignment/margins/color في build_css والمعاينة.
4. إصلاح الاستيراد الدفعي (واجهة متعددة الكتب أو إشعار واضح).
5. نسخة آمنة من الكتاب عند بدء ExportJob (أو تعطيل المحرر).
6. توحيد specs وحذف القديم + تطهير build/.
7. تنفيذ embed_fonts (نسخ TTF + @font-face) أو إزالة الخيار.
8. خفض الحجم (UPX ثم PySide6-Essentials) مع قياس أثر مستقل.
9. تنظيف الكود الميت (حقول/معاملات/أسماء بديلة) بلا تغيير سلوك.
10. TOC شجري + landmarks + بحث/استبدال + إعدادات موحّدة.

---

## [UNKNOWNS]

- جودة التشكيل العربي في القرّاء الفعلية (تحتاج جهاز قارئ).
- أيّ spec بُني منه `dist/EPubCreator.exe` الحالية.
- توافق EPUB2 في القرّاء الخارجية (بلا epubcheck).
- سلوك QTextBrowser مع كتب ضخمة جداً (آلاف الفصول).

---

## [ASSUMPTIONS]

- مستهدف Windows فقط (DPI + مسارات Fonts + explorer).
- الـ .venv هو بيئة التطوير الوحيدة.
- لا متطلبات شبكة/متعددي مستخدمين.
