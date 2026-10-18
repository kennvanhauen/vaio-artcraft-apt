# DesignCraft VAIO port — in progress

User authorized the DesignCraft port. Upstream 0.9.0 is pinned at
`ecd7e5d063eb12fa5e61fe61c9b8a77bb3c9110a`. The optional native craft-fonts input
is pinned at `a71c20e30af613287c504f7e685ca8fad77752bc`; manifest hashes and notices
passed verification. Build work stays on the Mac; the VAIO retains Xenial.

Baseline: SSH responsive, about 1626 MiB available RAM, no swap use, ACPI 52°C.
The five existing apps and launcher remain installed. No system restart or desktop
session change is part of this port.

The i686 Atom-targeted headless build completed. Desktop adaptation adds a separate
Glow feature, retains the upstream CPU document renderer, and preserves save/quit
and recovery handling. Real-device headless workflows passed: three original pages, paragraph styles, image
placement, manual text threading, table cells, RTF import, undo/redo, preflight,
native/IDML save-reopen and PDF/EPUB/PPTX/HTML/TXT/RTF export. All three pages were
rendered to PNG; cover and two-column/table page were visually inspected. Poppler
independently extracted the expected PDF heading; ZIP containers passed integrity
checks. Explicit MCP read/write roots rejected paths outside the test directory.
Desktop idle, recovery and native-dialog tests are pending.

Upstream calls this pre-alpha software. Its known Smart Text Reflow / primary-frame
page-growth problem is a limitation; explicit pages and manual threading are the
initial practical workflow. No complete InDesign fidelity is claimed. The local
ignored `plan/` directory is absent; committed roadmap/gap and control docs are used.

Packaging, signed APT delivery, six-app launcher and installed validation are pending.

The synthetic RGB print document generated one expected RGB-colour preflight warning;
EPUB warned that the decorative gradient image lacked alt text. These are reported
conditions, not silent failures. No personal documents were opened.

## Measured issues and narrow fixes

Initial GUI editing, formatting, undo/redo, save/reopen and export passed. With a
blinking insertion caret the six-second sample used 150.9% of one logical CPU,
130168 KiB RSS; after leaving text editing it settled to 0%, 133672 KiB RSS.
A steady caret and reduced UI animation are therefore the Linux i386 defaults,
with `DESIGNCRAFT_STATIC_CARET=0` as a process-scoped opt-out. Final measurements
are pending.

An isolated unsaved draft made no automatic copy in 48.2 idle seconds against a
30-second upstream interval. The recovery check ran without control requests or
input during the wait. A scheduled wake for dirty documents is being added;
final automatic-snapshot/crash/restart verification is pending.

Native Zenity Save As passed bare-name extension and normalized-path overwrite
cancellation, preserving an existing synthetic target. No application change
was needed for native filenames; the probe uses the actual Save As menu action.

Parent-page text and a two-record synthetic data merge passed. Independent ZIP/XML
inspection found three editable PPTX slides with expected text/table content and
EPUB story text. RGB artwork failed the built-in PDF/X-4 validator under its CMYK
output intent. Ordinary PDF export remains verified; no professional prepress
compliance claim is made.

## Pre-install verification complete

The final GUI retest passed with 0.17% CPU / 130728 KiB RSS during text editing,
and 0% / 135352 KiB after leaving editing (six-second samples). Automatic recovery
appeared after 28.11 seconds, survived termination of the owned disposable process,
and reopened/saved after restart. The original default interval is retained.

The CMYK-swatch variant passed the built-in PDF/X-4 validator; the RGB example
failed it as recorded above. Independent certification was not performed.

Host upstream CI: fmt and workspace/all-target Clippy passed. Observed tests:
2839 passed, 2 failed, 5 ignored before stopping at the UI library. Failures in
unmodified source were a missing host wgpu adapter and clipping of an Arabic
new-document field. Later executables/doc tests were not run. PDF pin consistency,
all 58 asset attributions and layering (21 crates) passed separately. The modified
VAIO Glow/i686 build passed Clippy with warnings denied. WebAssembly checks were
not run: its target is absent. This is not a claim of a green full upstream CI.

Packages built: DesignCraft 0.9.0~vaio1 (81,483,934 bytes, SHA-256
`342e5b7a3d4226b40347695eebcfaf5fe1e091366f47efe78ab4aef60ce799f5`)
and launcher 0.5.1~vaio7. Both carry matching final patch hashes and i386 ELF
binaries; Mac home paths are absent. The restricted trademark outline was removed
from the modified executable and replaced by an original page glyph; upstream
contributor-original app icons and open font assets retain their notices.

Publication and installed checks are pending.
