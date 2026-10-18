# VAIO application ports and signed APT archive

Unofficial native ports of WordCraft, GridCraft, PdfCraft, DeckCraft and VectorCraft for Ubuntu 16.04
Xenial i386 on the Sony VAIO P. The VAIO App Launcher opens and manages all five
through APT. These are independent hardware adaptations of upstream alpha apps.

| Package | Version | Ordinary and advanced workflows checked on the VAIO |
|---|---|---|
| wordcraft-vaio | 0.8.0~vaio5 | Four-page editing, formatting, find/replace, tables, pictures, headers/footers, six exports, native dialogs, tracked changes, comments, footnotes, equations, contents, columns, mail merge, proofing and unsaved-draft recovery |
| gridcraft-vaio | 0.8.0~vaio1 | Formulas, GUI edits, recalculation, charts, XLSX save/reopen, CSV/PDF export, native Save As, sorting/filtering, validation, conditional formatting, frozen panes and PivotTables |
| pdfcraft-vaio | 0.9.0~vaio1 | Viewing/rendering, text extraction, extract/combine/rotate, comments, forms, applied redaction, AES-256 round trip and one-page OCR |
| deckcraft-vaio | 0.8.0~vaio1 | Three-slide editing, shapes/picture/chart/notes, PPTX round trip, PDF/outline export, silent fullscreen presentation, native Save As and unsaved-draft recovery |
| vectorcraft-vaio | 0.13.1~vaio1 | Headless CLI/MCP, GUI text editing, layers, shapes, pathfinder, undo/redo, two artboards, native/SVG round trip and broad format export |
| artcraft-launcher-vaio | 0.5.1~vaio6 | Five-app APT backend, signed metadata refresh, offline reporting, saved settings and fixed package-operation allowlist |

All five application engines retain their upstream features. This is a practical
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
Package: wordcraft-vaio gridcraft-vaio pdfcraft-vaio deckcraft-vaio vectorcraft-vaio artcraft-launcher-vaio
Pin: origin "kennvanhauen.github.io"
Pin-Priority: 500

Package: *
Pin: origin "kennvanhauen.github.io"
Pin-Priority: -1
```

Refresh APT, then install the six package names above. The four office apps appear in
Office and VectorCraft in Graphics; VAIO App Launcher appears in Utilities/System. Future updates use APT,
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
- Launcher: `9cef5d2a0f207da50d31547a726057ea40f7e5b4`

Original sources are at https://github.com/storytold/wordcraft,
https://github.com/storytold/gridcraft, https://github.com/storytold/pdfcraft and
https://github.com/storytold/craft-launcher and https://github.com/storytold/deckcraft and https://github.com/storytold/vectorcraft. Pinned upstream revisions identify the source; Releases carry source/build
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
