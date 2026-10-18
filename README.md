# VAIO application ports and signed APT archive

Unofficial native ports of WordCraft, GridCraft and PdfCraft for Ubuntu 16.04
Xenial i386 on the Sony VAIO P. The VAIO App Launcher opens and manages all three
through APT. These are independent hardware adaptations of upstream alpha apps.

| Package | Version | Ordinary and advanced workflows checked on the VAIO |
|---|---|---|
| wordcraft-vaio | 0.8.0~vaio5 | Four-page editing, formatting, find/replace, tables, pictures, headers/footers, six exports, native dialogs, tracked changes, comments, footnotes, equations, contents, columns, mail merge, proofing and unsaved-draft recovery |
| gridcraft-vaio | 0.8.0~vaio1 | Formulas, GUI edits, recalculation, charts, XLSX save/reopen, CSV/PDF export, native Save As, sorting/filtering, validation, conditional formatting, frozen panes and PivotTables |
| pdfcraft-vaio | 0.9.0~vaio1 | Viewing/rendering, text extraction, extract/combine/rotate, comments, forms, applied redaction, AES-256 round trip and one-page OCR |
| artcraft-launcher-vaio | 0.5.1~vaio4 | Three-app APT backend, signed metadata refresh, offline reporting, saved settings and fixed package-operation allowlist |

All three application engines retain their upstream features. This is a practical
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
Package: wordcraft-vaio gridcraft-vaio pdfcraft-vaio artcraft-launcher-vaio
Pin: origin "kennvanhauen.github.io"
Pin-Priority: 500

Package: *
Pin: origin "kennvanhauen.github.io"
Pin-Priority: -1
```

Refresh APT, then install the four package names above. The three apps appear in
Office; VAIO App Launcher appears in Utilities/System. Future updates use APT,
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
- Launcher: `9cef5d2a0f207da50d31547a726057ea40f7e5b4`

Original sources are at https://github.com/storytold/wordcraft,
https://github.com/storytold/gridcraft, https://github.com/storytold/pdfcraft and
https://github.com/storytold/craft-launcher. Pinned source archives accompany
Releases. Owned downstream patches, lockfiles, helper sources and recipes are
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
