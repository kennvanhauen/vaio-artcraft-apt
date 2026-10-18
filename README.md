# VAIO ArtCraft APT archive

Unofficial ArtCraft previews for **Ubuntu 16.04 Xenial i386 / Sony VAIO P**.
Independent hardware adaptation; not an upstream ArtCraft release.

Packages are native `.deb` files managed by APT/dpkg. They preserve the operating
system and system libraries. WordCraft uses Glow software rendering, a steady
caret and reduced animations. Opening, UI typing, bold formatting, saving and
reopening synthetic DOCX documents were tested on an Atom Z540 with 2 GB RAM.
Large documents, printing and complex layouts remain unverified.

## Installation

Download `vaio-artcraft-archive-keyring.gpg` from this repository's Pages site and
verify its fingerprint against `KEY-FINGERPRINT.txt` in this repository. Install
the public key as `/usr/share/keyrings/vaio-artcraft-archive-keyring.gpg`.
Add `/etc/apt/sources.list.d/vaio-artcraft.list` containing:

```
deb [arch=i386 signed-by=/usr/share/keyrings/vaio-artcraft-archive-keyring.gpg] https://kennvanhauen.github.io/vaio-artcraft-apt xenial main
```

Then refresh APT and install `wordcraft-vaio`. Menu: **Office → WordCraft (VAIO
preview)**. Updates use the distribution's APT frontend. Removal:
`sudo apt-get remove wordcraft-vaio`; user documents/settings are not packaged.

The archive signs its index with RSA-3072/SHA-256. Package hashes are covered by
that signature. The private signing key remains on the maintainer's machine;
GitHub hosts only public files. Signing-key expiry is October 2028 and must be
renewed before then. This static archive has no short `Valid-Until` deadline.
It is signed again when packages change; it does not need daily signing jobs.

## Sources and builds

WordCraft upstream revision: `d6f20f93fd22deb441b2216ecfd65acb15ea8b64`
(https://github.com/storytold/wordcraft). MIT OR Apache-2.0; original icon retained.
The release includes the pinned upstream source archive. Downstream changes are
in `ports/wordcraft-xenial.patch`; build recipes and pinned download hashes are
included here. Private libxcb 1.17.0 comes from the official XCB source archive;
its permissive COPYING notices are included in the package.

The build host is Apple Silicon macOS with Python 3.12+, make/autoconf/pkg-config,
portable X11 headers and Git. Run `probes/setup-cross-tools.py` for project-local
Rust 1.95.0, i686 target, Zig 0.14.1 and checked XCB source archives. Obtain the
pinned upstream checkout under `upstream/wordcraft`. Copy the target Xenial
`libXau.so.6` (and its real soname file) and `libxkbcommon.so.0` into
`.build/sysroot/usr/lib/i386-linux-gnu/` without replacing host libraries.
The XCB build recipe expects X11 headers under `/opt/homebrew/include/X11`.

Run `probes/build-private-xcb.sh`, `probes/prepare-wordcraft-port.py`, then
`probes/build-wordcraft.sh`. Copy the resulting `wordcraft` and `wordcraft-cli`
from `.build/wordcraft-target/i686-unknown-linux-gnu/release/` into
`.build/test-runtime/bin/`. `probes/build_deb.py` builds the package. All work is
on the stronger build host; the VAIO is used for runtime checks.

`probes/build_public_apt.py PACKAGE --tag RELEASE_TAG --output STAGING` signs
metadata using a private `.build/apt-signing` GPG home (mode 0700). That directory
is ignored and must never be published. Keep a secure backup outside the public
repository. Packages and signed indexes are served together by Pages because Xenial APT
1.2 does not support absolute package URLs in indexes. Releases retain binary
and source backups. The Pages pool retains package files referenced by the
current index; archive size must remain within GitHub Pages limits. No personal laptop
logs, documents, SSH configuration or private keys are published.

## VAIO App Launcher preview

The modified launcher is called **VAIO App Launcher**, based on ArtCraft Launcher
upstream revision `9cef5d2a0f207da50d31547a726057ea40f7e5b4`. Original ArtCraft
trademark artwork is removed; a generic tile icon replaces it. The package name
is `artcraft-launcher-vaio`, command `vaio-app-launcher`. It currently offers only
the verified WordCraft preview. The original interface is retained, using Glow
and reduced motion. Install, update and remove go through a root-owned APT helper
with a visible administrator prompt and terminal confirmation. No user-owned or
downloaded helper is executed as root. The launcher itself is APT-managed.

Refresh reads the cached APT state. Use the system's existing **Check & Install
Updates** frontend to refresh repositories. The launcher does not run a system
upgrade silently. Settings are currently session-only; there is no tray or login
autostart. Additional applications remain outside this verified preview.

To build, obtain the pinned launcher checkout under `upstream/craft-launcher`,
then run `probes/prepare-launcher-port.py`, `probes/build-launcher.sh --locked`
and `python3 probes/build_launcher_deb.py`. It uses the same Atom/i386/glibc 2.23
toolchain and private XCB as WordCraft. The separate launcher patch and checked
workspace lockfile are retained under `ports/`. Font licenses, attribution and
upstream notices are included in the package.

## Publishing maintenance

Keep the private `.build/apt-signing` directory on the build Mac, mode 0700; it
is not part of this repository or GitHub Actions. Back it up securely to preserve
the archive identity. Before October 2028, extend key expiry, publish the updated
public key and update clients while the old certificate is still valid.

For an update, build a new Debian version, retain its source revision/patch and
checksums, test it on the VAIO, then regenerate this signed index and publish the
package under `pool/main/`. APT 1.2 requires a relative Filename here; absolute
GitHub Release URLs do not work. Publish the source/binary backup to Releases
too. Keep the preceding package available for clients with a cached older index.
GitHub Pages builds must finish before testing client downloads. Monitor Pages
size as more apps/versions are added; this is currently a small two-package
archive, not an unlimited binary store.

The source recipes and VAIO icon additions use MIT OR Apache-2.0 like the upstream
code. `ports/launcher-vaio/ATTRIBUTION.md` records the original generic tile icon.
