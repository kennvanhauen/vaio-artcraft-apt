#!/bin/sh
# Pinned project-local Rust/Zig tools; no compilation on the VAIO.
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export RUSTUP_HOME="$project_root/.build/rustup"
export CARGO_HOME="$project_root/.build/cargo"
export RUSTUP_TOOLCHAIN=1.95.0
export PATH="$CARGO_HOME/bin:$PATH"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$project_root/.build/soundcraft-target}"
export CARGO_TARGET_I686_UNKNOWN_LINUX_GNU_LINKER="$project_root/probes/zig-cc-xenial.sh"
export CARGO_TARGET_I686_UNKNOWN_LINUX_GNU_RUSTFLAGS="-C target-cpu=atom --remap-path-prefix=$project_root=/build/vaio-artcraft"
export CC_i686_unknown_linux_gnu="$project_root/probes/zig-cc-xenial.sh"
export AR_i686_unknown_linux_gnu="$project_root/probes/zig-ar.sh"
export RANLIB_i686_unknown_linux_gnu="$project_root/probes/zig-ranlib.sh"
export PKG_CONFIG_ALLOW_CROSS=1
export PKG_CONFIG_SYSROOT_DIR="$project_root/.build/sysroot"
export PKG_CONFIG_LIBDIR="$project_root/.build/sysroot/usr/lib/i386-linux-gnu/pkgconfig"
case "${SOUNDCRAFT_BUILD:-cli}" in
  cli) set -- -p soundcraft-cli "$@" ;;
  output) set -- -p soundcraft-playback --example vaio_output "$@" ;;
  gui) set -- -p soundcraft -p soundcraft-cli "$@" ;;
  *) echo 'SOUNDCRAFT_BUILD must be cli, output or gui' >&2; exit 1 ;;
esac
case "${SOUNDCRAFT_ACTION:-build}" in build|clippy) action=${SOUNDCRAFT_ACTION:-build} ;; *) exit 1 ;; esac
exec cargo "$action" --locked --release --target i686-unknown-linux-gnu \
  --manifest-path "$project_root/.build/soundcraft-port/Cargo.toml" \
  "$@"
