# Upstream maintenance coordinator — 19 October 2026

The user asked for ongoing upstream maintenance to be part of this project and
authorized implementation. This adds a Mac coordinator, manifest, operator guide,
release gates, rootless VAIO runner and credential-free GitHub unit-workflow template.
The existing signed APT delivery/frontend remains the installation mechanism.
There is no new scheduled job, unattended publisher or VAIO service.

`probes/maintain_updates.py` provides check, prepare, build, host-check, verify,
publish, run and rehearse. `maintenance/README.md` documents operation, prerequisites,
coverage, failure handling and rollback. All eight apps and the launcher are mapped.

Verified implementation checks:

- Twenty-one unit checks pass: source/package/patch/runner binding, failed or stale
  evidence rejection, non-publishable rehearsals, concurrency, safe remote naming,
  failed-reverification invalidation, preserved new upstream dependencies,
  Python 3.5 runner syntax, synthetic PDF, source-bound package metadata and
  patch isolation from an enclosing Git checkout.
- First upstream check found seven changed repository HEADs; FigCraft and
  VectorCraft matched their published source commits. This is a timestamped
  development-head comparison, not a claim that seven stable releases exist.
- Initial CADCraft patch application against 62329310d751f97d3dadffee530752f24bec4531
  passed. The first build stopped at --locked because preparation incorrectly
  replaced upstream's new lockfile with the old checked port copy. Fixed:
  retain the upstream lock and apply only the VAIO lock diff. A separate
  port_base_revision keeps that overlay anchored even after publication advances
  the published source baseline. A real-file regression proves new upstream
  dependencies survive. A fresh cross-build subsequently passed: CLI 1m12s, GUI 2m10s, followed by
  native i386 packaging with the new source/version in its manifest.
- Actual rootless package rehearsals are tracked below. These authenticate the
  existing signed index, verify package SHA, extract the .deb, check native
  loading, run existing synthetic workflows and native dialogs, measure idle use
  and leave installed packages alone. Rehearsals cannot be published.

Harness issues found and fixed during real tests:

- Unshifted XTEST path typing lowercased timestamps; remote paths are now lowercase
  and regression-tested.
- Python 3.5 shutil needs string paths; WordCraft's fixture copy uses them.
- WordCraft's old native-dialog probe expected a separate edited.docx and a
  particular marker. The adapter now supplies both fixtures and parameterizes the
  expected marker/CLI, using the candidate CLI. It also checks bare-name Save As
  and cancelled overwrite.
- DeckCraft's screensaver activation could race slideshow teardown. Retry is
  bounded and still requires observing the actual blanked state; no app setting
  or screensaver configuration was changed.
- VectorCraft's portal-to-zenity fallback could outlast the 12-second picker
  timeout. The probe allows 30 seconds; it still requires the owned native chooser.

The three existing packagers accept an explicit candidate source/version and
verify source HEAD. Default historical recipes remain available. CAD packaging
refuses to reuse its acadrust MPL source notice if the dependency version changes.
The launcher probe additionally measures settled idle CPU/RAM.

Publication is a separate stage (or explicit --publish on run): require current
host/target success for the exact immutable candidate, reject equal/older versions
and reused filenames, sign separately on the Mac, retain previous packages, attach
source/recipes to a draft release, commit/push APT and publish the release. Private
keys never enter candidates or GitHub; only explicit source/recipe paths enter
archives. Failed publication recovery is documented rather than silently retried.

Coverage limits: host maintenance tests exclude xtask and the GPU UI test crate;
application assets/layers and launcher helper checks run separately. This does
not claim full upstream CI/WASM. Modest workflow acceptance does not replace
recovery/interoperability/OCR checks when those systems change. No claim that
arbitrary upstream conflicts, dependencies or format regressions can be fixed
without port maintenance. No installed app version, APT index, OS, network,
thermal control or power parameter was changed by this coordinator validation.

All nine rootless package rehearsals passed after the recorded harness fixes.
The machine's installed versions remain unchanged. Summary evidence is in
`update-coordinator-rehearsals.json`; complete diagnostics remain private under
`.build/updates` and the owned remote test directories.

| Package adapter | Settled idle CPU, one logical CPU | RSS MiB |
|---|---:|---:|
| cadcraft | 0.33% | 114.9 |
| deckcraft | 0.0% | 106.7 |
| designcraft | 0.0% | 130.8 |
| figcraft | 0.17% | 108.9 |
| gridcraft | 0.2% | 86.5 |
| launcher | 0.0% | 68.7 |
| pdfcraft | 0.2% | 84.9 |
| vectorcraft | 1.2% | 110.8 |
| wordcraft | 0.0% | 97.9 |

A clean candidate for CADCraft source 62329310d751f97d3dadffee530752f24bec4531,
version 0.9.0~vaio2, built through the coordinator with seven font faces reverified,
Rust 1.95.0, Zig 0.14.1, Atom/i386 and glibc 2.23. This is a local coordinator
build exercise, not an installed or published app update. Its package SHA256 is
`398bf6364cebd83fe681b7242097143ba32a0368974bab330d1014cf49a41023`. Real-VAIO acceptance passed: native loading, headless drawing/export, CPU/Glow
GUI editing/save/reopen/PDF and native bare-name saving/overwrite cancellation.
The host maintenance gate has not been run for this newer source, so publication
must remain blocked even if the target check passes.

The clean-build result is recorded in `update-coordinator-clean-build.json`.
The actual publication gate was exercised read-only against that candidate and
correctly rejected it for missing host acceptance. The experimental package stays
local; no unqualified source update was published. All nine existing .deb files
and the signed APT metadata remain unchanged.

Final VAIO check: CADCraft remains 0.9.0~vaio1 and launcher 0.5.1~vaio9.
Temperature settled to 58°C, exposed core-throttle counters remain zero and no
candidate processes remain. The recorded normal launcher was raised after checking
its boot identity, command and start time. No test/build/monitor is left running.
The public-source allowlist now includes all acceptance dependencies, with a
regression check preventing incomplete recipe archives.

The first code push was rejected because enabling the optional .github workflow
requires OAuth workflow scope, which the existing token lacks. Removed that active
file from the unpublished commit and retained its ordinary-file template under
maintenance/github-workflows. No account permission change was requested or made.
The Mac's 21 unit checks and real-VAIO checks are verified; GitHub CI is not enabled.
