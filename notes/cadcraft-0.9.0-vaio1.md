# CADCraft VAIO port — in progress

User explicitly authorized autonomous CADCraft porting, following the seven
installed apps. Upstream 0.9.0 is pinned at
`0cc66ad3066e71f2c3d4cacb7de905e79ba1c95b`.

VAIO baseline over SSH at 00:28 BST: i686, kernel 4.4.0-210-generic, uptime 2:14,
about 1614 MiB available memory, swap use zero, ACPI 58°C. Launcher revision 8 is
installed. No reboot, desktop restart or networking change is planned.

Committed AGENTS.md, ROADMAP, gaps, manifests and control/MCP documentation were
read. Ignored plan/ is absent. Referenced craftrules remains unavailable locally
and its earlier public clone returned Repository not found; committed CADCraft
instructions are followed. No AutoCAD installation, assets or files are used.

Upstream already has a CPU drawing fallback when no wgpu state is installed.
The native VAIO feature selects Glow, retains this fallback, keeps normal default
wgpu for other builds, and fits the window to the display. The command/format
engine, DWG bridge and existing autosave are retained.

Optional craft-fonts is pinned at a71c20e30af613287c504f7e685ca8fad77752bc. Seven
native faces (24.3 MiB) and their notices are verified; the verifier follows the
upstream font-family exclusion policy, including Noto Sans CJK. The original
CADCraft stroke font remains. No Chinese-font coverage claim is made.

Known upstream limits are substantial: pre-alpha, no full 3D modeler, approximate
ellipse/spline operations, incomplete command options, plotting/external-file
limits, and DWG saves can drop unsupported content. Use DXF working copies and
synthetic fixtures; no production DWG safety or AutoCAD parity is claimed.
The unmodified acadrust 0.6.4 dependency is MPL-2.0; preserve its licence and source
availability information alongside the upstream notices.


## Verified pre-package workflows

The real i386 CLI/MCP passed without DISPLAY, WAYLAND_DISPLAY or XAUTHORITY:
426 commands, original 120×80 mm rounded mounting plate, four block inserts,
layers, horizontal constraint, two dimensions, TEXT/MTEXT, a LISP expression,
move/undo/redo, DXF save/reopen, SVG/PDF/PNG exports, its own small DWG round trip,
and a paper-space A4 viewport plot. Independent ASCII DXF groups and Poppler page
metadata passed. Script mistakes (LINE returns handles; text-prompt words need a
separate input; Poppler whitespace varies) were corrected; no engine change was
needed. These synthetic checks do not validate external DWG fidelity.

The actual desktop uses CPU drawing through Glow. Interactive circle placement,
command-line text, undo/redo, DXF reopen and PDF output passed. Three six-second
idle samples: 0.17%, 0.17%, 0.33% of one logical CPU, 115684–117384 KiB RSS.
The 1440×650 screenshot was inspected. No speculative caret/animation change is
needed. Command history floats over part of the drawing; zoom/pan or F2/history
controls remain upstream behaviors, not an assertion of polished CAD parity.

A native chooser test reproduced bare filenames saved without .dxf. The adaptation
adds the suggested DXF/DWG suffix and asks a native Yes/No question if that resolves
to an existing path; explicit export suffixes stay unchanged. A focused regression
test passed. Actual native-save/overwrite-cancel verification passed on the VAIO.

Default SAVETIME remains ten minutes. In an isolated test profile, SAVETIME=1
produced a snapshot after 61.12 seconds without input. Only that process was killed.
The upstream five-minute lock lease is being allowed to expire naturally before
restarting for recovery; no test timestamp is altered.

Pristine full CI stopped at an unchanged xtask collapsible_match style lint.
Native i386 GUI Clippy passed with warnings denied except existing nonminimal_bool
and collapsible_match style lints. Asset attribution and layering pass. Host
functional tests are running with --no-fail-fast; one closed-port test failed in
the parallel host run. The actual VAIO closed-port check correctly failed startup
without emitting MCP output; an isolated host rerun follows. WASM is not claimed
(the target is absent). Upstream source checkouts remain unmodified.


The complete GUI/CLI package is 45,563,926 bytes, SHA256
`b106ca156e52584e09140dd279726c3b18fdd5e34a4590abce8aaaa8e2ba62b3`.
It includes the unmodified acadrust MPL licence and exact source download/checksum
notice, font notices and original icon attribution. The eight-card launcher uses
the existing 4×2 layout; its fixed helper's eight-package batch/rejection checks
passed. CAD's native DXF type is image/vnd.dxf on the target.

## Package installation and rollback

Planned: install cadcraft-vaio 0.9.0~vaio1 and update the launcher to 0.5.1~vaio9
through the existing signed APT source/native administrator prompt. Expand the
origin preference to nine package names, keeping wildcard priority -1. Back up
the old preference outside preferences.d to
/var/backups/vaio-artcraft/preferences.before-cadcraft-20261019. Simulate first and
reject unrelated installs or removals; refresh only the project source.

Rollback: remove cadcraft-vaio with APT (user drawings/settings remain). If desired,
download the retained launcher revision 8 .deb from the public pool and run
`sudo apt-get install /path/to/artcraft-launcher-vaio_0.5.1~vaio8_i386.deb`, then
restore the preference backup with sudo cp -p. The index lists the newest launcher,
so use the old .deb directly rather than assuming an old version stays indexed.


Recovery succeeded after the natural lock lease expired. The automatically saved
unsaved text was restored as a dirty copy and saved to DXF. Its actual Drawing
Recovery modal was captured and inspected; the actual Open button passed after focusing the window and polling for the
asynchronous input result. The default ten-minute interval is unchanged.
The eight-card launcher preview was inspected and fits in the original 1540×650
4×2 layout, with all labels and actions visible.

The pristine full host functional run completed 2,015 passing tests and two
failures: an ephemeral closed-port startup assertion and a GPU viewport test
without a wgpu adapter. Native CPU/Glow drawing and A4 paper-space output passed
on the VAIO. The isolated serial host MCP rerun passed all four tests; no full CI/WASM
pass is claimed. Native assets/layers and scoped Clippy checks passed separately.
