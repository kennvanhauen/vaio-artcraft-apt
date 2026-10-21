# Maintaining the VAIO ports on the Mac

`probes/maintain_updates.py` coordinates upstream checks, isolated builds,
rootless real-VAIO acceptance and signed APT publication for all eight apps and
the launcher. Python 3.12+ runs the coordinator on the current Apple silicon Mac;
the target runner supports the VAIO's Python 3.5. Existing Rust/Zig/Xenial inputs, Git, SSH, GnuPG
and GitHub CLI authentication are reused. No build is performed on the laptop.
Publication expects the existing clean checkout at `.build/apt-public` and the
private local signing home at `.build/apt-signing`. These and the verified cross
inputs must be restored explicitly when reconstructing a workspace from GitHub.

APT delivers packages **after this workflow publishes them**. It does not fetch
or compile upstream source. The actual VAIO update frontend remains Check &
Install Updates → uCareSystem → APT. The launcher uses the same signed archive.
This coordinator does not install a daemon, scheduled job or automatic publisher.
A credential-free GitHub unit-test workflow is supplied as a template under
`maintenance/github-workflows/`. It is not enabled: the current publication token
lacks GitHub workflow scope. The coordinator does not depend on that workflow.

## Routine workflow

Run from the project root:

```sh
python3 probes/maintain_updates.py check
```

This checks upstream HEAD and lists tags for every repository. The JSON report
is `.build/updates/upstream-report.json`; unavailable repositories are errors,
not “no changes.” A changed HEAD can contain unreleased development work. Choose
a source commit or tag deliberately. The published source/version baseline is
`maintenance/upstreams.json` and includes the launcher. Its separate
`port_base_revision` records the source against which the maintained port patch
and checked dependency overlay were authored; publication advances the source
baseline without pretending that old port inputs were regenerated.

```sh
python3 probes/maintain_updates.py prepare cadcraft --ref COMMIT_OR_TAG --version 0.9.0~vaio2
```

The command prints a new candidate directory, for example
`.build/updates/cadcraft-TIMESTAMP`. Use that path in the remaining commands:

```sh
python3 probes/maintain_updates.py build .build/updates/cadcraft-TIMESTAMP
python3 probes/maintain_updates.py host-check .build/updates/cadcraft-TIMESTAMP
python3 probes/maintain_updates.py verify .build/updates/cadcraft-TIMESTAMP --ssh VAIO_SSH_ALIAS
python3 probes/maintain_updates.py publish .build/updates/cadcraft-TIMESTAMP
```

`--identity /path/to/key` is optional; an existing SSH configuration works. Never
put a password in a command, manifest or chat. SSH host verification stays enabled.
`verify` needs the VAIO awake, with its normal Xorg desktop available. It raises
owned test windows and deactivates the approved screensaver; it leaves ordinary
apps and the launcher running. It never reboots, stops the desktop, installs a
package, changes the network or requests root. Installation of a published update
still goes through native APT and its normal local authentication.

For a selected source revision, the same stages can run in sequence:

```sh
python3 probes/maintain_updates.py run cadcraft --ref COMMIT_OR_TAG --version 0.9.0~vaio2 --ssh VAIO_SSH_ALIAS
```

That stops with a verified local candidate. Add `--publish` to include publication
after all checks pass. A failure stops the sequence and keeps its evidence. A local, unpublished built
candidate may be rebuilt after a recipe correction; this archives its old host/target
receipts and requires fresh acceptance. Published candidates cannot be rebuilt.

Before building, read the candidate's `UPSTREAM-INSTRUCTIONS.md`, upstream release
notes and source diff. The ignored upstream plans may be absent. Resolve relevant
instruction/licensing changes when reviewing the port. A version without an
upstream version bump still needs a higher `~vaioN` revision. Use a full new
upstream version plus `~vaio1` when appropriate; do not reuse a published filename.

## What the stages enforce

- **Prepare:** fetch into a separate source cache, pin a complete commit, clone a
  candidate source tree, apply the existing port patch strictly, preserve the new
  upstream Cargo lockfile while applying only VAIO dependency changes from the
  port-base lockfile, and stage the launcher adapter if selected. Original checkouts,
  working ports, installed packages and the public archive stay unchanged.
- **Build:** use the existing Atom/i386/glibc 2.23 cross recipes and `--locked`.
  Build targets and output packages are isolated. Tools/font/model inputs reuse
  the existing local setup, with Rust 1.95.0 and Zig 0.14.1 pinned and font hashes
  rechecked before compilation. No new toolchain is selected implicitly. The three
  packagers accept explicit candidate metadata and verify its source HEAD, instead of silently stamping old pins.
- **Host check:** a private Git index from the pinned upstream revision supplies
  tracked-file inventory for asset checks in the extracted port tree; source and
  enclosing repositories are not modified. Serial workspace tests excluding `xtask` and the GPU UI crate;
  application asset and layering gates also run (launcher lacks those commands).
  This is a scoped native maintenance gate, **not full upstream CI or WASM**.
- **VAIO verification:** verify transfer SHA, Xenial/Atom/i386 identity, package
  metadata, included build manifest, binary hashes, native dependency resolution,
  existing CLI/MCP and GUI editing/export tests and native dialogs. The launcher
  runs its eight actual Open actions using isolated installed-app profiles.
  Test paths are relocated under a unique private `/tmp/vaio-update-*` directory.
  Candidate wrappers force the extracted private XCB. DeckCraft audio stays off.
  Settled idle CPU must be at most 5% of one logical CPU and RSS at most 350 MiB;
  throttle counters must not increase. Temperatures must start below 75°C and
  finish below 80°C. These are conservative maintenance gates, not stress tests
  or a claim about the CPU's thermal specification. Existing occupied control
  ports cause a stop; unknown processes are never killed.
- **Publish:** require current successful host/target evidence bound to the exact
  package, source tree, recipes, patch, lockfile and current runner. Reject
  rehearsals, modified inputs, old/equal versions, an advanced archive baseline,
  dirty public staging or an existing package filename. Sign a separate APT
  staging tree locally; verify its signature/key and retain the prior package.
  Upload a draft binary/source release, back up signed metadata locally, commit
  the archive, the tested allowlisted recipes and a public result summary/baseline,
  push, then publish the
  release. The existing signed APT source delivers it normally.

One coordinator runs at a time. Failures have nonzero exits and retained logs;
there is no fallback that publishes an unchecked build. Look at `candidate.json`,
`build-*.log`, `package.log`, `host-*.log`, `target.log`, and `target-result.json`.
Build logs can be verbose. `/tmp` files remain for diagnosis; no watcher or
candidate app remains after a successful test. A new verification attempt
invalidates its previous receipt before contacting SSH, so a failed rerun cannot
reuse a previous success. Previous receipts remain under `target-history/`. Native dialog tests can be visible
for a minute or more on this slow machine.

A failed patch or locked dependency resolution requires an actual port update.
Do that in a candidate, regenerate the downstream patch and lockfile after review,
then create/build a fresh candidate. Do not bypass gates, substitute old results
or relax the graphics/CPU target just to get a build. Keep the public baseline at
the last working release until the replacement passes.

## Rehearsal and coverage limits

```sh
python3 probes/maintain_updates.py rehearse cadcraft --ssh VAIO_SSH_ALIAS
python3 -m unittest discover -s tests -p 'test_update*.py' -v
```

Rehearsal authenticates the existing archive/index and runs its already published
package through the transport/extraction/acceptance path. A rehearsal can never
be published. It does not claim to test a new source build. All nine applications
have adapters; only explicitly recorded real runs count as validated.

The automatic acceptance suite covers modest synthetic workflows. It does not
repeat every recovery, OCR, interoperability or long-running test from the first
ports. Changes in those subsystems require the existing app-specific advanced or
recovery probes and review before calling `publish`. External DWG/FIG fidelity,
large files, cloud features and hardware plotting remain outside these checks.
There is no claim that a script can automatically fix arbitrary upstream changes.

## Recovery and rollback

Preparation/build/test failures leave the installed apps and live archive alone.
For a failed publication, inspect the GitHub draft, public Git status, local
`apt-stage`, `previous-dists` and `publication.json` before retrying. A pushed Git
commit may already be deployed even if the final release API call failed; do not
blindly rerun the whole command. Finish the release/baseline bookkeeping after
verifying the pushed commit, or restore the prior signed metadata and commit it.
GitHub Pages deployment can lag a push; check its run before expecting the VAIO
to see a new candidate. The package pool retains all previous versions.

To roll back an installed app, download its recorded previous `.deb` from
`pool/main/` and install that exact local file with native APT authentication:

```sh
sudo apt-get install /path/to/previous-package_i386.deb
```

The archive index normally lists only the newest version, so a version-qualified
APT command may not find the retained older package. Existing documents and
settings remain. File-format changes may still require backups made before
opening a document in a newer version.

Private SSH details, diagnostics, user documents and signing credentials are not
public release inputs. `maintenance/public-files.json` is the explicit recipe
archive allowlist; the source archive additionally contains the selected public
upstream source commit. The signing directory stays private on the Mac and is
never linked into a candidate or uploaded.
