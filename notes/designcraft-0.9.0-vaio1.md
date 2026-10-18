# DesignCraft VAIO port — installed and verified

DesignCraft **0.9.0~vaio1** and launcher **0.5.1~vaio7** are installed through the
signed GitHub APT archive. Installed headless/GUI workflows, native Save As,
automatic idle draft recovery and all six launcher Open buttons passed. Final
package/launcher measurements follow the progress record below.

The port retains the upstream page-layout features and optional open fonts,
uses Glow, and avoids blinking-caret redraws on the Atom. Installed editing and
settled samples measured 0% CPU at about 128–132 MiB RSS. This is a practical
adaptation of upstream pre-alpha software, with documented reflow, interoperability,
prepress and full-CI limits; it is not InDesign feature-parity certification.

## Scope and progress record

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

## Rollback

Remove the new app with `sudo apt-get remove designcraft-vaio`; documents and
profiles remain. Restore the archive preference with:

```sh
sudo cp -p /var/backups/vaio-artcraft/preferences.before-designcraft-20261018 /etc/apt/preferences.d/vaio-artcraft
```

The previous launcher package `artcraft-launcher-vaio_0.5.1~vaio6_i386.deb` is
retained in the public pool and the earlier release. To restore its exact UI,
install that verified earlier package with native dpkg (`sudo dpkg -i /path/to/that.deb`).
The new app can also be removed while retaining launcher revision 7. The existing
software-update frontend, SSH/networking, desktop session and screensaver policy
are unchanged. The process-scoped caret opt-out requires no rollback operation.

## Publication

Binary/index commit: `3986874a51063c0674a4d83c71ee1fc8f9aacaeb`.
GitHub release backups:

- https://github.com/kennvanhauen/vaio-artcraft-apt/releases/tag/designcraft-0.9.0-vaio1
- https://github.com/kennvanhauen/vaio-artcraft-apt/releases/tag/launcher-0.5.1-vaio7

GitHub's uploaded DesignCraft asset digest equals the local package SHA-256. The
signed index contains seven package records with checked relative pool paths,
lengths and SHA-256 hashes. Local `gpgv` verifies the archive signature. The signing
home is not in public staging. Pages deployment/live index verification and native
installation are still pending at this checkpoint.

Pages deployment for the binary/index commit succeeded. The live InRelease and
seven-package index were fetched over HTTPS and matched local bytes exactly;
InRelease SHA-256 is `be98032034c786ff6067a166b4e52b0d3e14d54412b05ece2435aa66c75b7bfc`.
Launcher package SHA-256 is
`7329c1189987e54e642a4ddde8775fb79209e40811b385f0b1288d8a3cc3b44e`;
GitHub's release-asset digest also matches it. The six-card launcher preview was
visually checked at 1540×650, including unobscured version labels and actions.
Native installation was started through the VAIO's gksu/uxterm prompt.

## Native installation

Installation completed successfully with status 0 through gksu/uxterm. APT fetched
88.3 MB from the signed Pages archive and installed only DesignCraft 0.9.0~vaio1
and launcher 0.5.1~vaio7; no removals, dependency changes or unrelated upgrades.
Package integrity, exact versions, desktop validation and native .designcraft MIME
identification passed. The archive allowlist now has seven package names; the
previous preference is backed up outside the preferences directory.

Installed-wrapper headless/GUI, native-dialog/recovery and all-six-Open checks
are being completed before leaving the normal launcher visible.

Installed wrappers passed the complete no-display headless workflow and the
independent format/parent/data-merge checks. Installed GUI editing, formatting,
undo/redo, native reopening and PDF/PNG export passed again. Six-second installed
samples were 0% CPU during editing (130576 KiB RSS) and after leaving editing
(134764 KiB). The loaded private XCB path was `/usr/lib/designcraft-vaio/lib/libxcb.so.1`.

Evidence files (original synthetic documents only):

- [Headless workflow](designcraft-headless-result.json)
- [Format/parent/data-merge checks](designcraft-formats-result.json)
- [GUI measurements](designcraft-gui-result.json)
- [Native dialogs](designcraft-native-dialogs-result.json)
- [Draft recovery](designcraft-recovery-result.json)
- [Host checks and full-CI limits](designcraft-host-checks-result.json)
- [Installed summary](designcraft-installed-result.json)

Installed native dialogs passed again. Installed automatic recovery saved after
27.11 seconds, reopened the original unsaved marker after termination of the
owned test process, and saved a recovered working copy. The older normal launcher
is being replaced only after matching its recorded project PID and executable;
other applications and the graphical session remain running.

All six installed launcher Open actions passed using an isolated launcher/profile
and only its disposable child processes: VectorCraft, PdfCraft, DesignCraft,
WordCraft, DeckCraft and GridCraft. The test launcher and its children exited.
The updated normal six-card launcher is being left visible after final sampling.
An [original brochure example](https://github.com/kennvanhauen/vaio-artcraft-apt/releases/download/designcraft-0.9.0-vaio1/designcraft-brochure-example.zip) is retained
locally with native/IDML/PDF/EPUB/PPTX/HTML and three rendered pages.

Final installed integrity passed: all seven expected versions, dpkg verification,
manifest executable hashes, package ownership of private XCB, unchanged scoped
public key, seven-name APT preference, native MIME type and no leftover test
control listeners. About 1610 MiB RAM remained available, with no swap use.

The first post-test ACPI sample was 71°C; a later idle read cooled to 56°C.
Both exposed core-throttle counters were zero. The ACPI passive/critical trip
points are 90/100°C. These are observed samples, not a retrospective explanation
for the earlier audio/freezing investigation. No thermal setting was changed.

## Final state

The normal six-card launcher is visible at 1540×650 and fully fits the 1600×768
screen. All six installed versions equal their signed APT candidates. After settling,
its seven-second sample measured 0% CPU and 69368 KiB RSS (about 67.7 MiB).
No test application, monitoring command or administrator terminal is left running.
The intended normal launcher remains open. SSH remained responsive throughout.

[All six Open results](launcher-six-open-result.json) and
[final launcher measurements](launcher-six-visible-result.json) supplement the
installed summary above. Future updates use the existing native Check & Install
Updates → uCareSystem/APT route and the permanent signed archive.
