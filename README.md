# VAIO application ports and signed APT archive

Unofficial native ports of WordCraft, GridCraft, PdfCraft, DeckCraft, VectorCraft, DesignCraft, FigCraft and CADCraft for Ubuntu 16.04
Xenial i386 on the Sony VAIO P. The VAIO App Launcher opens and manages all eight
through APT. These are independent hardware adaptations of upstream alpha apps.

| Package | Version | Ordinary and advanced workflows checked on the VAIO |
|---|---|---|
| wordcraft-vaio | 0.9.0~vaio1 | Four-page editing, formatting, find/replace, tables, pictures, headers/footers, six exports, native dialogs, tracked changes, comments, footnotes, equations, contents, columns, mail merge, proofing and unsaved-draft recovery |
| gridcraft-vaio | 0.10.0~vaio1 | Formulas, GUI edits, recalculation, charts, XLSX save/reopen, CSV/PDF export, native Save As, sorting/filtering, validation, conditional formatting, frozen panes and PivotTables |
| pdfcraft-vaio | 0.9.0~vaio1 | Viewing/rendering, text extraction, extract/combine/rotate, comments, forms, applied redaction, AES-256 round trip and one-page OCR |
| deckcraft-vaio | 0.9.0~vaio1 | Three-slide editing, shapes/picture/chart/notes, PPTX round trip, PDF/outline export, silent fullscreen presentation, native Save As and unsaved-draft recovery |
| vectorcraft-vaio | 0.13.1~vaio1 | Headless CLI/MCP, GUI text editing, layers, shapes, pathfinder, undo/redo, two artboards, native/SVG round trip, broad format export, native Save As and draft recovery |
| designcraft-vaio | 0.9.0~vaio1 | Three-page styles/images/threading/table/RTF workflow, GUI editing, native/IDML round trip, PDF/PNG/EPUB/PPTX/HTML/text export, parent pages, data merge, native Save As and automatic idle recovery |
| figcraft-vaio | 0.9.0~vaio1 | Two-screen UI design, auto layout, components/instances, styles/variables, GUI text editing, prototype click navigation/preview, native/SVG/own-FIG round trips, seven exports, native Save As and idle draft recovery |
| cadcraft-vaio | 0.10.0~vaio1 | Metric 2D drafting, rounded outline, layers, blocks, constraints, dimensions, TEXT/MTEXT, LISP, interactive editing, DXF save/reopen, own DWG round trip, SVG/PNG/PDF, A4 viewport plot, native Save As and autosave |
| artcraft-launcher-vaio | 0.5.1~vaio9 | Eight-app APT backend, signed metadata refresh, offline reporting, saved settings and fixed package-operation allowlist |

All eight application engines retain their upstream features. This is a practical
port, not a claim that every feature or external file works. Complex documents,
large workbooks/scans, physical printing, real signing identities, complex scripts
and external integrations need further validation. PdfCraft's optional Japanese
font build input is absent. No user documents are included in this archive.

## Installation and updates

Download `vaio-artcraft-archive-keyring.gpg` from this repository's Pages site and
verify its fingerprint against `KEY-FINGERPRINT.txt`. Install the key as
`/usr/share/keyrings/vaio-artcraft-archive-keyring.gpg`. The dedicated fingerprint is
`441616C65AAB69B996E367BDA07F27EC0F124F87`.

Add `/etc/apt/sources.list.d/vaio-artcraft.list`:

```
deb [arch=i386 signed-by=/usr/share/keyrings/vaio-artcraft-archive-keyring.gpg] https://kennvanhauen.github.io/vaio-artcraft-apt xenial main
```

The target VAIO uses `/etc/apt/preferences.d/vaio-artcraft` to allow only these
packages from this archive:

```
Package: wordcraft-vaio gridcraft-vaio pdfcraft-vaio deckcraft-vaio vectorcraft-vaio designcraft-vaio figcraft-vaio cadcraft-vaio artcraft-launcher-vaio
Pin: origin "kennvanhauen.github.io"
Pin-Priority: 500

Package: *
Pin: origin "kennvanhauen.github.io"
Pin-Priority: -1
```

Refresh APT, then install the nine package names above. The five office apps appear in
Office and VectorCraft/FigCraft/CADCraft in Graphics; VAIO App Launcher appears in Utilities/System. Future updates use APT,
including the VAIO's existing **Check & Install Updates** frontend. Its wider
system-maintenance operation was not run during targeted package tests.

Launcher Refresh verifies project metadata in an unprivileged cache. Package
changes use a root-owned helper, local authentication and terminal confirmation.
Update All queues the selected applications through a shared APT transaction.
The launcher itself updates through APT. No separate updater, login autostart,
control server or MCP server starts automatically.

Removal uses `sudo apt-get remove` and the relevant package names. Documents and
settings are not packaged and are retained. Removing the source, preference and
scoped public-key files disconnects the archive without removing applications.

## Hardware and builds

Verified target: Atom Z540 (SSE3/SSSE3, no SSE4/AVX), 2 GB RAM, i686, kernel 4.4,
glibc 2.23, LXDE/X11, GMA500 display and Mesa 18 llvmpipe software OpenGL. No Vulkan.
Build work stays on Apple Silicon macOS; runtime checks use the actual laptop.

The ports select Glow, fit the display and keep idle redraw low. WordCraft uses a
steady caret and reduced motion. GridCraft defaults to reduced motion. PdfCraft
selects OpenGL explicitly. Each package carries its own private libxcb 1.17.0;
the operating system's libraries remain in place. Ordinary settled idle samples
were 0% CPU, roughly 100 MiB WordCraft and 86 MiB each for GridCraft/PdfCraft.
These are short samples on synthetic files, not performance guarantees.

Pinned upstream revisions:

- WordCraft: `d6f20f93fd22deb441b2216ecfd65acb15ea8b64`
- GridCraft: `c30fa3f1cf324603f3bfc0171689b1d4083b40e5`
- PdfCraft: `98cbd38a8e0f5afe685258aa0fcab0f0012f7a8b`
- DeckCraft: `cb78440a1618e6a2c1df55dd7bff74719685518c`
- VectorCraft: `a466625c8987550635cda951ebf36e08e1e80a56`
- DesignCraft: `ecd7e5d063eb12fa5e61fe61c9b8a77bb3c9110a`
- FigCraft: `a0d1162976fac1e4a8b8fd49a3948e9d6bad6f40`
- CADCraft: `0cc66ad3066e71f2c3d4cacb7de905e79ba1c95b`
- Launcher: `9cef5d2a0f207da50d31547a726057ea40f7e5b4`

Original sources are at https://github.com/storytold/wordcraft,
https://github.com/storytold/gridcraft, https://github.com/storytold/pdfcraft and
https://github.com/storytold/craft-launcher and https://github.com/storytold/deckcraft and https://github.com/storytold/vectorcraft and https://github.com/storytold/designcraft and https://github.com/storytold/figcraft and https://github.com/storytold/cadcraft. Pinned upstream revisions identify the source; Releases carry source/build
recipe archives and links. Owned downstream patches, lockfiles, helper sources and recipes are
in `ports/` and `probes/`. App/license/font/icon notices are included in packages.
Original ArtCraft trademark graphics are removed from modified UI releases;
original attribution remains. The replacement launcher icon is contributor-original.

Build host prerequisites: Python 3.12+, git, make/autoconf/pkg-config and portable
X11 headers. `setup-cross-tools.py` prepares project-local Rust 1.95.0, the i686
target, Zig 0.14.1 and checked XCB sources. Populate the target sysroot with the
actual Xenial libXau/libxkbcommon runtime libraries, without replacing host ones.
`build-private-xcb.sh` expects X11 headers under `/opt/homebrew/include/X11`.

Run each `prepare-*-port.py`, then its `build-*.sh` with `--locked`. Office apps use
`prepare-office-ports.py` and `build-office-app.sh gridcraft|pdfcraft --locked`.
`fetch-pdfcraft-models.py` verifies both OCR models and their CC-BY-SA-4.0 licence
against upstream-pinned hashes. Their unmodified data is packaged with attribution.
Zig's target archiver is required for the unchanged upstream crypto libraries.
`build_office_deb.py gridcraft|pdfcraft` creates the corresponding native package.
WordCraft uses `build_deb.py`; the launcher uses `build_launcher_deb.py`.

`build_public_apt.py PACKAGE --tag RELEASE_TAG --output STAGING` signs index and
package hashes with RSA-3072/SHA-256. Pages serves relative package URLs because
Xenial APT 1.2 cannot use absolute package URLs in its index. Releases retain backups.
The private `.build/apt-signing` home is never published. Back it up securely;
renew the key before October 2028. This static archive has no short Valid-Until;
it is signed again whenever packages change.


## DeckCraft build and VAIO profile

DeckCraft uses the same Atom/glibc 2.23 toolchain and Glow, with a steady text
caret. A controlled same-deck comparison measured about 148% of one logical CPU
with blinking and 0% with a steady caret. AutoRecover has an explicit dirty-work
timer so idle repaint suppression does not prevent snapshots. Native Save As
normalizes missing extensions and confirms existing corrected destinations.

Fetch craft-fonts commit `43913056ce82a3fdad0ef69f6b88d1dc922a8104` into
`upstream/craft-fonts`, then run `verify-deckcraft-fonts.py`. The upstream font
policy excludes Adobe-authored families; 48 allowed faces are embedded with
licence/attribution notices. Run `prepare-deckcraft-sysroot.py` for hash-pinned
Xenial ALSA headers on the build host, and copy the VAIO's actual
`/usr/lib/i386-linux-gnu/libasound.so.2.0.0` into that sysroot. No target development
package is installed. Then `prepare-deckcraft-port.py`,
`build-deckcraft.sh --locked`, and `build_office_deb.py deckcraft` produce the port.
The native .deckcraft MIME definition and Office menu entry belong to dpkg.

DeckCraft's audio/media code is retained, but the wrapper defaults audio output
off because this VAIO previously stalled HDA playback. Set
`DECKCRAFT_ENABLE_AUDIO=1` for an explicit per-launch opt-in. Output audio and
embedded-video performance are unverified. Silent manual and timed slideshow operation was tested. Presenter View defaults
off for this single-screen VAIO but remains available. Static slides and the
editor measured 0% CPU in short settled samples, at about 108 MiB RSS. A process-scoped
XScreenSaver keepalive runs only during a presentation.
This is not a promise of smooth heavy animation or complete PowerPoint fidelity.

## VectorCraft build and scope

See [the VectorCraft port record](notes/vectorcraft-0.13.1-vaio1.md) for actual
VAIO checks and limits. Use native `.vectorcraft` working copies; older
`.drawcraft` files remain readable. The command is `vectorcraft-vaio-cli`;
`mcp --headless` explicitly selects an in-process session without a display.
Neither the desktop entry nor launcher starts an automation server.

Clone VectorCraft at its pinned revision under `upstream/vectorcraft`. Run
`prepare-vectorcraft-fonts.py` for its pinned optional font input, then
`prepare-vectorcraft-port.py`. `build-vectorcraft.sh --locked` builds the CLI;
`build-vectorcraft.sh -p vectorcraft --no-default-features --features vaio,accessibility --locked`
builds both executables with Glow and accessibility. `build_office_deb.py vectorcraft`
produces an i386 package with an XZ data member (Xenial-compatible). The drawing
engine remains vello_cpu; only the interface's graphics backend is changed.

The eight optional native font faces and notices are hash-verified; existing
bundled open fonts retain their upstream ASSETS.md provenance and OFL notices.
The native build does not need the newer families listed for web-only fetching.
Selected upstream tests passed (4,043 passed, six ignored). Full upstream CI stops
at an existing Rust 1.95 Clippy nonminimal_bool warning in patterncmds.rs:494;
this is not represented as a complete CI/WASM pass.

The [five-app usage guide](notes/VAIO-Apps-Guide.md) explains working formats,
headless commands, recovery and the verified limits. Installed wrapper and all
five launcher Open-button checks passed.


## DesignCraft build and scope

See [the DesignCraft record](notes/designcraft-0.9.0-vaio1.md) and
[usage guide](notes/VAIO-Apps-Guide.md). The port retains the upstream page-layout
engine and uses Glow for the interface. Linux i386 defaults to a steady caret and
reduced animation; `DESIGNCRAFT_STATIC_CARET=0` opts out for one launch. Idle draft
recovery has an explicit scheduled wake. No server starts in a normal launch.

Clone the pinned upstream revision into `upstream/designcraft`, then run:

```sh
python3 probes/prepare-designcraft-fonts.py
python3 probes/prepare-designcraft-port.py
sh probes/build-designcraft.sh --locked
DESIGNCRAFT_BUILD=gui sh probes/build-designcraft.sh --locked
python3 probes/build_office_deb.py designcraft
```

The optional craft-fonts input is pinned at
`a71c20e30af613287c504f7e685ca8fad77752bc`; its eight native faces and notices are
verified. Existing Source Sans/Serif, Inter and JetBrains Mono open-font assets
remain, as explicitly allowed by upstream attribution. The modified trademark
outline is replaced by an original page glyph. XZ package compression is supported
by Xenial dpkg and keeps the complete GUI/CLI package below GitHub's file limit.

The original three-page brochure passed real-VAIO checks. Initial blinking-caret
idle use was 150.9% of one logical CPU; the revised six-second samples measured
0.17% while editing and 0% after leaving editing, about 128–132 MiB RSS. An automatic
snapshot appeared after 28 seconds and recovered after an owned-process crash.
These are short synthetic-file checks, not large-document performance promises.

Use explicit pages/manual threading: upstream primary-frame Smart Text Reflow has
a known page-growth problem. External INDD/IDML fidelity, physical printing and
professional prepress remain unverified. The CMYK-swatch example passed the built-in
PDF/X-4 check; RGB fills failed under its CMYK output intent. Host full CI is not
green: fmt/Clippy passed, but one test lacked a wgpu adapter and one unchanged Arabic
dialog test clipped a field (2839 tests passed before the stop). VAIO Glow/i686
Clippy with warnings denied, asset attribution, PDF pin consistency and layering
passed separately. WebAssembly checks were not run (target absent).


### Installed DesignCraft checkpoint

Signed APT installed DesignCraft revision 1 and launcher revision 7, changing only
those two packages. Installed headless/GUI, native-dialog and idle-draft recovery
checks passed. All six Open buttons passed. The normal six-card launcher is left
visible, fits the screen and measured 0% CPU / 67.7 MiB RSS after settling.
Installed DesignCraft samples measured 0% CPU / about 128–132 MiB. Package hashes,
private-library ownership, MIME registration, scoped key and seven-package APT
preference passed; no test control listeners remained. See
[installed evidence](notes/designcraft-installed-result.json),
[the final port record and rollback](notes/designcraft-0.9.0-vaio1.md) and
[the original brochure example](https://github.com/kennvanhauen/vaio-artcraft-apt/releases/download/designcraft-0.9.0-vaio1/designcraft-brochure-example.zip).


## FigCraft build and scope

See [the FigCraft record](notes/figcraft-0.7.0-vaio1.md) and
[usage guide](notes/VAIO-Apps-Guide.md). The desktop uses Glow and retains the
CPU canvas, 562-command engine, metered WASM plugin interpreter and collaboration
code. Linux i386 defaults to a steady caret; `FIGCRAFT_STATIC_CARET=0` opts out.
No control/MCP/collaboration listener starts during an ordinary launch.

Clone the pinned upstream revision into `upstream/figcraft`, then run:

```sh
python3 probes/prepare-figcraft-fonts.py
python3 probes/prepare-figcraft-port.py
sh probes/build-figcraft.sh --locked
FIGCRAFT_BUILD=gui sh probes/build-figcraft.sh --locked
python3 probes/build_office_deb.py figcraft
```

The craft-fonts input is pinned at
`43913056ce82a3fdad0ef69f6b88d1dc922a8104`: both native and Latin manifests, all 56
embedded faces and their notices are checked against the pinned Git tree. The
large opt-in Hans font is omitted, following upstream native defaults. XZ
compression keeps the full GUI/CLI package within GitHub's file-size limit.

FigCraft remains alpha. External .fig exchange is best effort/experimental;
its own FIG round trip does not establish external Figma-file fidelity. Its
plugins are not Figma plugins. Large files, plugins, cloud/team integrations and
live collaboration remain unverified on this VAIO. No hosted service is set up.


FigCraft's pristine host functional suite passed 2,798 tests (eight ignored) with
canonical `/private/tmp` paths. Full CI still stops at seven pre-existing style
lint errors; i386 GUI Clippy passed with only `collapsible_match` allowed. Asset
attribution, layering and owned-file formatting passed. WebAssembly checks were
not run because the target is absent. See the linked verification record.


FigCraft and launcher revision 8 are installed through signed APT. Installed
headless, GUI text/prototype, native Save As, recovery and package-integrity checks
passed, including the package-local XCB library and native MIME type. All seven
launcher Open buttons passed. The origin preference allows these eight package
names only; no unrelated packages were selected. The ordinary launcher is left
visible after testing. The [verification record](notes/figcraft-0.7.0-vaio1.md)
contains measurements and rollback steps.


Final normal launcher measured 0% idle CPU and 68.4 MiB RSS, with all seven
installed versions matching APT candidates. The laptop settled to 57°C, with
zero exposed core-throttle counts and no swap use. Only the intended normal
launcher remains from the task; no test listeners, builds or monitors remain.
Screenshots: [FigCraft editing](notes/figcraft-ui.png) and
[the seven-app launcher](notes/launcher-seven.png). Measurements are short
synthetic-workflow checks, not long-term stability guarantees.


## CADCraft build and scope

[CADCraft verification](notes/cadcraft-0.9.0-vaio1.md) and
[usage guide](notes/VAIO-Apps-Guide.md). The port keeps the upstream CPU drawing
fallback and engine, using Glow for the native window. Native Save As adds the
suggested DXF/DWG suffix and confirms existing normalized paths separately.

```sh
python3 probes/prepare-cadcraft-fonts.py
python3 probes/prepare-cadcraft-port.py
sh probes/build-cadcraft.sh --locked
CADCRAFT_BUILD=gui sh probes/build-cadcraft.sh --locked
python3 probes/build_office_deb.py cadcraft
```

Clone pinned upstream CADCraft into upstream/cadcraft before those commands.
The craft-fonts input is pinned at a71c20e30af613287c504f7e685ca8fad77752bc;
seven embedded native faces and notices are verified, following upstream's font
exclusion policy. The original stroke font remains. The unmodified acadrust 0.6.4
DWG library is MPL-2.0; its licence and exact corresponding-source download and
checksum are included in the package. No proprietary CAD assets or drawings
are used or published.

This is pre-alpha 2D CAD. External DWG saving can discard unsupported content;
use DXF working copies and preserve originals. Full 3D, external-file fidelity,
physical plotters and demanding geometry are unverified/incomplete. The real
VAIO small drawing measured about 0.2–0.3% idle CPU and 113–115 MiB RSS. No power,
thermal or kernel parameters were changed. Automation is opt-in and has the
account's file access; ordinary launches start no control/MCP listener.


Pristine host functional suite: 2,015 passed, two failed. The MCP connection
suite then passed all four cases serially; the other failure had no wgpu adapter.
Full CI still stops at an unchanged xtask style lint. Native i386 Clippy passed
with warnings denied except two unchanged style lints; assets/layers and the
save-name regression passed. WebAssembly was not checked (target absent).


CADCraft revision 1 and launcher revision 9 are installed through signed APT.
Installed GUI/headless, native Save As/overwrite cancellation, package integrity,
binary hashes, scoped key, native MIME and nine-package origin-preference checks
passed. All eight actual launcher Open buttons passed with isolated profiles.
The inspected normal launcher is left visible, fitting all eight cards; all
versions match APT candidates. Installed CAD idle samples were 0.17–0.33% of one
logical CPU, about 114–115 MiB RSS. Launcher idle was 0.0%, 68.9 MiB RSS.
Final temperature was 58°C, exposed core-throttle counters zero and swap unused.
No test listeners, builds or monitors remain. These are short workflow checks,
not long-term stability guarantees. See [installed evidence](notes/cadcraft-installed-proof-result.json),
[CAD editing](notes/cadcraft-ui.png), [eight-app launcher](notes/launcher-eight.png)
and [final runtime](notes/cadcraft-final-runtime-result.json).


## Continuing upstream development

The [Mac update coordinator](maintenance/README.md) checks all eight apps and the
launcher, prepares isolated source/port trees, builds Xenial i386 candidates,
runs scoped host checks and rootless real-VAIO workflow tests, and publishes
passing packages through this signed APT archive. Previous packages remain available in GitHub Releases for rollback.
Older unindexed Pages copies may be retired after verifying downloaded backups;
[retired-packages.json](retired-packages.json) records their URLs and SHA256 hashes. APT delivers published VAIO builds; it does not compile
new upstream commits by itself.

```sh
python3 probes/maintain_updates.py check
```

Use the guide's staged commands or `run APP --ref COMMIT_OR_TAG --version VERSION
--ssh VAIO_SSH_ALIAS`; add `--publish` only when publication is intended. Failed
patches, locked dependencies, workflow tests or resource checks stop the sequence.
No unattended publisher, scheduled task or signing credential is installed on
GitHub or the VAIO. A credential-free GitHub Actions template is included; it is not enabled because
the current publication token lacks workflow scope.


Coordinator validation: 21 unit checks passed on the Mac; all eight app adapters
and the launcher passed rootless real-VAIO package rehearsals. A fresh CADCraft
source candidate built for Atom/i386/glibc 2.23 and passed the VAIO workflow checks.
Its release gate correctly rejects publication until its separate host checks
pass. This tooling update publishes no new app package or APT metadata. See
[the validation record](notes/update-coordinator.md), [adapter evidence](notes/update-coordinator-rehearsals.json)
and [clean-build evidence](notes/update-coordinator-clean-build.json).
