# Using the VAIO ports

Open **VAIO App Launcher** in Utilities/System. Its six cards open WordCraft,
GridCraft, PdfCraft, DeckCraft, VectorCraft and DesignCraft. The five office apps also appear
under Office; VectorCraft appears under Graphics. The launcher
checks signed APT metadata. Applications remain usable during a slow check.
Install/update/remove operations use local administrator authentication and APT.
The usual **Check & Install Updates** frontend also updates these packages.

## WordCraft

Write in DOCX; Ctrl+O opens, Ctrl+S saves, F12 chooses another name/format.
Ctrl+F finds, Ctrl+Z/Ctrl+Y undo/redo. Use the ribbon for styles, lists, tables,
pictures, references, review and mail merge. The advanced engine is included.

- **Review:** comments and tracked changes; accept/reject before distributing
  a final copy if appropriate. Saving with review markup was tested.
- **References:** footnotes, contents and page-number fields were tested.
- **Equations:** use Insert > Equation or Alt+=. Editing and DOCX persistence passed.
- **Mailings:** a two-recipient synthetic merge passed.
- **Recovery:** normal desktop sessions periodically keep unsaved draft copies.
  File > Recover restores an unsaved copy; use Save As afterwards. The latest
  edits can precede the last snapshot. A disposable-process recovery test passed.
- **Sharing:** ODT, RTF, HTML, Markdown, plain text and PDF exports passed. Keep
  an original copy when exchanging complex documents with other applications.

The steady caret and reduced animation keep this CPU-rendered VAIO quiet at idle.
They do not remove the editing engine. Physical printing has no configured printer
to verify. Read Aloud requires an optional speech engine, currently absent; audio
was not retried after the earlier HDA/login-sound problem.

## GridCraft

Use XLSX as the working format. GUI cell editing, formulas, recalculation, charts,
sort/filter, validation, conditional formatting, frozen panes and PivotTables
passed small synthetic checks. Use the ribbon for those features; save/reopen and
CSV/PDF export passed. A bare Save As name gets the suggested extension, with a
separate confirmation if that corrected name already exists. Complex Excel files,
macros and large-workbook performance remain outside the verified set.

## PdfCraft

Open a PDF, then use the page organizer, comments, form, redaction and OCR tools.
Viewing, page extraction/combine/rotation, saved comments, basic form fields,
applied redaction and an AES-256 password round trip passed. Save As adds .pdf to
a bare name and protects an existing corrected destination.

OCR models are included and run locally. One small image-only page took about
16 seconds and recognized its text, with a spurious graphic character; check OCR
results. The models focus on English/Latin text. Large scans can be much slower.
Optional Japanese authoring fonts are absent. Digital signatures with real
identities, complex forms and physical printing remain unverified.

## DeckCraft

Use native .deckcraft for working copies or PPTX for exchange. Ctrl+O opens,
Ctrl+S saves, and Save As chooses another filename. Slides, layouts, text,
shapes, pictures, tables, charts, notes, review, transitions and animations are
available in the ribbon. Present starts the show; Escape returns to editing.
Presenter View is initially off on this single-screen VAIO; its toggle remains.
PDF export also offers notes pages and handouts. The command line is
`deckcraft-vaio-cli`.

Real-VAIO checks covered three-slide creation, GUI text editing, shapes, a
picture, chart and notes, PPTX round trip, PDF/outline export, rendering, manual
and timed full-screen shows, native Save As and automatic draft recovery.
The steady caret and static slides avoid continuous software rendering. Draft
recovery runs even when the editor is otherwise idle. Save As adds the suggested
extension to a bare name and confirms an existing corrected destination.

The five-minute star screensaver remains enabled while editing. During a show,
DeckCraft sends it an awake reminder every 45 seconds; reminders stop when the
show ends or DeckCraft exits. No screensaver preference is changed.

Audio output defaults off because of this VAIO's earlier HDA playback fault.
`DECKCRAFT_ENABLE_AUDIO=1 deckcraft-vaio` opts in for one launch; this has not been
validated. Media code is included. Complex external PPTX fidelity, video, heavy
animation, second-monitor placement and physical printing remain unverified.
48 allowed bundled font faces include Japanese and Arabic fallback.

## VectorCraft

Use native .vectorcraft for editable illustrations; older .drawcraft files also
open. Ctrl+O opens and Ctrl+S saves. Choose Save As for a new name or format;
a bare name gains the format extension, followed by format options when needed.
The overwrite question protects an existing corrected filename.

Use the left toolbar for drawing and type, and Properties/Layers for appearance
and organization. With the Type tool, click existing text before typing. Layers,
shapes, pathfinder union, undo/redo, two artboards and native save/reopen passed
on the VAIO. Small SVG/PDF/PNG workflows and broad additional format export also
passed. Japanese, Arabic, Greek and Latin font resolution was checked.

Data Recovery is enabled by upstream defaults every two minutes; its interval
and folder are under Preferences > File Handling. A one-minute isolated test
restored and saved an unsaved draft after a disposable-process crash. The latest
edits can still postdate the last snapshot.

`vectorcraft-vaio-cli` runs headlessly. For example:

```
vectorcraft-vaio-cli info illustration.vectorcraft
vectorcraft-vaio-cli convert illustration.vectorcraft illustration.pdf
vectorcraft-vaio-cli mcp --headless
```

MCP can additionally restrict automation read/write roots. No server starts from
the desktop entry. Keep native working copies: WMF flattens gradients and
transparency, EMF drops path transparency, and bidirectional SVG text may become
outlines to preserve its appearance. Export warnings identify these tradeoffs.

Small-file idle samples were about 1% CPU and 105–112 MiB RAM. Larger artwork,
heavy effects, arbitrary external AI/PSD/EPS/PDF fidelity, colour-critical output,
plugins and physical printing remain unverified. All upstream engine modules
remain included; this is a practical port of alpha software.

## DesignCraft

Use DesignCraft for flyers, brochures and page layout. Work in `.designcraft`;
Ctrl+O opens, Ctrl+S saves, and File > Save As chooses a new filename. A bare name
gets `.designcraft`; cancelling the corrected-name overwrite question preserves
an existing file. IDML provides another editable exchange format.

Use text frames, paragraph/character styles, images, layers, parent pages, tables
and the Pages panel. A three-page original brochure passed styles, image placement,
manual text threading, tables, RTF import, native/IDML reopening and GUI editing.
Parent-page content and two-record data merge passed. PDF, PNG, EPUB, PPTX, HTML,
plain text and RTF export were checked. Keep originals and inspect exchanged files.

Prefer explicit pages and manual threading. Primary-frame Smart Text Reflow has
an upstream page-growth problem. Complex external INDD/IDML files, large layouts,
physical printing and colour-critical prepress remain unverified. A CMYK-swatch
example passed the built-in PDF/X-4 check; the RGB-swatch example failed its
CMYK-output-intent check. This is not independent prepress certification.

The VAIO build uses Glow and keeps its caret steady to reduce software rendering.
`DESIGNCRAFT_STATIC_CARET=0 designcraft-vaio` restores blinking for one launch.
Preferences/recovery default to upstream paths; `DESIGNCRAFT_CONFIG_DIR` selects
an isolated root containing settings, logs and Recovery. Automatic idle recovery (30-second default) reopened an unsaved draft after a
disposable-process crash in testing. Drafts can postdate the latest snapshot; save
working copies regularly.

The command line runs these checked workflows without a display:

```sh
designcraft-vaio-cli run --in Brochure.designcraft --export Brochure.pdf
designcraft-vaio-cli run --in Brochure.designcraft --all-pages rendered-pages
designcraft-vaio-cli mcp --automation-read-root /path/to/work --automation-write-root /path/to/work
```

The MCP server is in-process unless `--connect PORT` is requested. Explicit roots
confine its file access. Desktop `--control PORT` is opt-in, loopback only and has
no authentication; enable it only while needed. It is not confined by CLI roots.
The normal desktop and launcher start no automation listener.

## Practical scope

These are broad ports of upstream alpha applications. All upstream engines and
commands are retained, with native desktop integration and Atom-compatible builds.
Successful synthetic checks do not establish fidelity for every external file.
No application starts a control/MCP server unless explicitly launched for it.
All tests used synthetic files and isolated settings, without opening personal work.
