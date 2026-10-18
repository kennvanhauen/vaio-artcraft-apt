# VectorCraft 0.13.1 — VAIO revision 1

Unofficial downstream build for Ubuntu 16.04 Xenial i386 on Sony VAIO P,
Atom Z540, 2 GB RAM, Mesa 18 llvmpipe. Builds run on an Apple Silicon Mac;
target checks run on the actual laptop. No operating-system replacement.

## Source and adaptation

- VectorCraft: a466625c8987550635cda951ebf36e08e1e80a56.
- Optional craft-fonts: a71c20e30af613287c504f7e685ca8fad77752bc.
- Rust 1.95.0; Zig 0.14.1; i686 target, Atom CPU and glibc 2.23.
- New vaio feature selects eframe Glow while retaining accessibility. The
  upstream vello_cpu drawing engine and all format/command modules remain.
- Private libxcb 1.17.0 is package-owned; system libraries remain in place.
- Native desktop entry, Graphics category, .vectorcraft/.drawcraft MIME types,
  packaged CLI, original app icon and open-font/backend/profile notices.
- Eight optional native font faces are hash/notice verified; existing bundled
  open fonts follow the explicit upstream ASSETS.md provenance and licences.
- XZ data compression uses a modest decode dictionary supported by Xenial dpkg.

## Verified workflows

Original, bounded synthetic artwork only; no proprietary applications or files.
Headless checks remove DISPLAY, WAYLAND_DISPLAY and XAUTHORITY:

- SVG import, native save/reopen and SVG round trip.
- PDF/PNG/EPS/DXF export, plus SVGZ/JPEG/WebP/GIF/TIFF/BMP/TGA/PSD/AI/EMF/WMF/text.
- Reopening generated SVGZ/AI/PSD/EMF/WMF; legacy .drawcraft extension.
- Japanese/Arabic/Greek/Latin text with no missing font/glyph reports.
- Explicit headless MCP text editing/save and automation-root confinement.

The actual GUI passed text input, layers, rectangle/ellipse/star creation,
pathfinder union, undo/redo, two artboards, native save/reopen, PDF/SVG export
and PNG rendering. Its captured interface was visually inspected. Native Save As
adds the extension to a bare name, shows format options, and protects an existing
normalized destination when overwrite is cancelled.

A small 480×320 PNG export took about 0.34 s; short five-second GUI idle samples
were 1.0% CPU/105 MiB RSS while editing and 0.8%/112 MiB after reopening. CPU is
relative to one logical core. These are small-file measurements, not guarantees
for large illustrations or every upstream feature. The restored initial window
was 1440×640; the test explicitly resized it to 1100×650.

Selected upstream suites passed: 4,043 tests, six ignored, zero failures across
engine/format/SVG/render/text/MCP. Separate asset, brand, cursor, layer and PDF
dependency audits passed. Full upstream CI stops on a pre-existing Rust 1.95
Clippy nonminimal_bool warning at patterncmds.rs:494; no full CI/WASM pass is
claimed. A macOS-only unused teardown helper warns in the native Glow build.

## Limits and practical use

Use .vectorcraft for editable working copies. Export warnings matter: WMF flattens
gradients/transparency, EMF drops path transparency, and bidirectional SVG text
can be outlined to preserve its visual order. Generated-file checks do not
establish fidelity for arbitrary external AI/PSD/EPS/PDF/CAD files.

Heavy illustrations, 3D/live effects performance, colour-critical output,
physical printing and third-party plugins remain unverified on this VAIO.
All engine modules are included; individual features can still have upstream
alpha limitations. The desktop entry starts no control/MCP server.

Updates and removal use native APT through the existing update frontend.
The launcher adds a fifth allowlisted package and a narrower card minimum so
all five can fit across the 1600-pixel display. The privileged helper accepts
only the fixed five application package names; mock transaction tests pass.

Automatic GUI recovery passed: a one-minute idle snapshot appeared after about
59 seconds; after killing only the isolated test process, a restarted app
restored and saved the original unsaved text without warnings. Signed installation
verification follows publication.
