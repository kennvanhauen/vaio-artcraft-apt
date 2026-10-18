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
repository. Packages are immutable GitHub Release assets; only small signed
indexes and public source recipes are stored in Git history. No personal laptop
logs, documents, SSH configuration or private keys are published.
