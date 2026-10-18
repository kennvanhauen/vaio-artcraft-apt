# FigCraft VAIO port — installed and verified

User authorized autonomous FigCraft porting, following the six installed apps.
Upstream FigCraft 0.7.0 is pinned at `a0d1162976fac1e4a8b8fd49a3948e9d6bad6f40`.
The VAIO responded over SSH: i686, kernel 4.4.0-210, about 1618 MiB available RAM,
no swap use, ACPI 53°C. The existing six-app launcher was retained until the installed checks completed;
only its recorded process identity was then closed for the seven-app checks.

Committed AGENTS.md, roadmap/gaps and control/CLI documents were read. Ignored
`plan/` is absent. The referenced craftrules repository is not available locally;
its public clone returned “Repository not found”. The committed FigCraft rules
are followed; no incumbent app, personal documents or proprietary assets are used.

The optional craft-fonts input is pinned at `43913056ce82a3fdad0ef69f6b88d1dc922a8104`,
which includes FigCraft's required opt-in Latin manifest. Native embedded fonts
and their notices are hash-verified. Upstream defaults omit the large Hans font
unless explicitly requested; this port retains that default. Open-source Source
Sans/Serif fonts are included under their original OFL notices.

Initial changes select Glow through a separate native feature and fit the window
to the VAIO. The CPU canvas, engine, plugins, collaboration code and recovery are
retained. Desktop/headless builds and real-device workflows passed; signed APT delivery
and the seven-app launcher update are installed.

Known upstream limits: alpha, best-effort .fig exchange, preview collaboration,
and its own plugin API rather than Figma plugin compatibility. Nothing here claims
full Figma parity or validates external real-world Figma files.

## Verified before packaging

- Real i386 CLI, no DISPLAY/WAYLAND/XAUTHORITY: 562 commands available. An
  original two-screen Repair Club example exercised auto layout, a reusable
  button component/instance, a paint style, a number variable binding, prototype
  flow/links and undo/redo. Native reopen, seven exports (SVG/PDF/PNG/JPG/WebP/
  JSON/FIG), SVG vector round trip, own FIG text round trip, independent PDF text
  extraction and explicit automation read/write confinement passed.
- Actual Glow GUI opened the document, accepted text input/formatting, saved and
  reopened it, and followed prototype links forward/back through GUI clicks.
  The initial text-editing idle sample cost 94.83% of one logical CPU; settled
  non-editing was 0%, around 109 MiB RSS. A Linux i386 steady caret addresses
  this specific redraw source, with FIGCRAFT_STATIC_CARET=0 as a one-launch opt-out.
- Native Save As appended .figcraft and protected an existing normalized path.
  An automatic unsaved-draft snapshot appeared after 9.04 seconds without input;
  terminating only that owned process and restarting the isolated profile
  restored the dirty draft, which was saved successfully.
- The seven-card launcher fits 1540×650 in a 4×2 arrangement. Its fixed root APT
  helper accepts only the seven named app packages; mock invalid/batch cases pass.
- Pristine upstream full CI stopped at seven pre-existing collapsible_match
  Clippy style errors. Native i386 GUI Clippy passed with warnings denied and only
  that style lint explicitly allowed. Asset attribution and layering pass.
  The canonical-temp host functional rerun passed: 2,798 tests, eight ignored. WebAssembly target is absent;
  WASM checks are not claimed. Upstream source checkouts remain unchanged.

## Package change and rollback

Installed figcraft-vaio 0.7.0~vaio1 and upgraded artcraft-launcher-vaio to 0.5.1~vaio8
through the existing signed APT source and native administrator prompt. Expanded
its origin preference from seven package names to eight, retaining wildcard -1.
The old preference is backed up outside preferences.d at
/var/backups/vaio-artcraft/preferences.before-figcraft-20261018. No unrelated
packages are allowed by the install simulation and no global source refresh is run.

Rollback: remove figcraft-vaio with APT (user files/settings remain); if desired
download the retained old launcher .deb from the public pool and run
`sudo apt-get install /path/to/artcraft-launcher-vaio_0.5.1~vaio7_i386.deb`, then
restore the preference backup with sudo cp -p.
The archive indexes the newest launcher; direct old-deb APT installation is needed
if it is no longer in the local cache. Keep current working documents separately.

The final steady-caret build measured 14.98% in its first six-second editing
sample, then 0% in a second settled editing sample and 0% after leaving editing,
about 109 MiB RSS. UI render-worker settling was still present in the first
sample; these figures are recorded separately rather than claiming every idle
interval is zero. The actual editing screenshot and prototype screenshot were
visually inspected. Presentation Close and a populated floating preview were
also checked (Escape alone did not leave presentation through the control path).
The package is 63,277,030 bytes, SHA256
`e401e2f332377de8feb467e6bb8b10ff66609c2251e485044790e2268a8e9edd`;
Xenial dpkg-deb reads it successfully, with the same transfer hash.

The first pristine host functional run stopped at two error-message assertions
for dangling symlinks: macOS's /var temporary-directory spelling differed from
canonical /private/var. Both requests were denied, so this was not an observed
confinement bypass. The canonical /private/tmp rerun completed all test targets: 2,798 passed,
zero failed, eight ignored. Actual VAIO MCP outside-root read/write checks passed.


## Publication

Signed APT packages and recipes were published in commit
`16b34e3a09723b5fe2423434c0fbd7abcabd5f48`. GitHub Pages reports built; the live
InRelease signature and exact Packages bytes match local output. Releases:
https://github.com/kennvanhauen/vaio-artcraft-apt/releases/tag/figcraft-0.7.0-vaio1
and https://github.com/kennvanhauen/vaio-artcraft-apt/releases/tag/launcher-0.5.1-vaio8.
The GUI's highest required GLIBC symbol is 2.18 (target has 2.23); actual i386 GUI
and CLI execution already passed. The native installation subsequently completed successfully (details below).


## Native installation

Local administrator authentication completed. The project-source-only signed
APT transaction installed FigCraft 0.7.0~vaio1 and upgraded launcher 7→8; one new
package, one upgrade, no removals or unrelated packages. Installer status 0:
package integrity, desktop entries and application/x-figcraft MIME passed.
The unchanged scoped key and exact source were checked first; the preference now
allows the eight expected package names only. Its prior copy remains in the
recorded /var/backups/vaio-artcraft path. Installed-wrapper headless, GUI, native-dialog, recovery and integrity checks
passed on 19 October 2026 BST. The record retains its starting date.


Installed wrappers preserve all eight expected package versions; FigCraft's loaded
XCB path is /usr/lib/figcraft-vaio/lib/libxcb.so.1. The native MIME and exact
8-package origin preference passed. Installed editing samples were 14.98% during
initial render settling, then 0% settled while editing and 0% after editing,
112132–112300 KiB RSS (about 109.5–109.7 MiB). An automatic draft copy appeared
after 8.04 seconds and recovered successfully after the owned-process crash.
Post-check ACPI temperature was 69°C, with no swap use. This is a short workflow
measurement, not a sustained-load or thermal-failure test.


All seven installed launcher Open buttons passed in suite order: VectorCraft,
PdfCraft, DesignCraft, FigCraft, WordCraft, DeckCraft, GridCraft. Each child was
started with an isolated test profile, observed alive and reaped before the next;
only the owned test launcher/children were closed. The normal updated launcher
is left visible, measured separately.


Final normal launcher: seven installed versions equal APT candidates; all cards
fit the 1540×650 client at (21,59), inside the 1600×768 display. Its inspected
screenshot shows all seven installed/up-to-date cards. Seven-second settled idle
sample: 0% of one logical CPU, 70064 KiB RSS (68.4 MiB). Final ACPI temperature
fell to 57°C, both exposed core-throttle counts remained zero, available memory
was about 1614 MiB and swap use zero. No test control listeners remain. Only the
intended normal launcher remains from this task; there are no background builds or monitors.
These are short measurements, not a proof against future hardware faults.
