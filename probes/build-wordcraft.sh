#!/bin/sh
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export RUSTUP_HOME="$project_root/.build/rustup"
export CARGO_HOME="$project_root/.build/cargo"
export PATH="$CARGO_HOME/bin:$PATH"
export CARGO_TARGET_DIR="$project_root/.build/wordcraft-target"
export CARGO_TARGET_I686_UNKNOWN_LINUX_GNU_LINKER="$project_root/probes/zig-cc-xenial.sh"
export CARGO_TARGET_I686_UNKNOWN_LINUX_GNU_RUSTFLAGS="-C target-cpu=atom --remap-path-prefix=$project_root=/build/vaio-artcraft"
export CC_i686_unknown_linux_gnu="$project_root/probes/zig-cc-xenial.sh"
exec cargo build --locked --release --target i686-unknown-linux-gnu \
    --manifest-path "$project_root/.build/wordcraft-port/Cargo.toml" -p wordcraft -p wordcraft-cli "$@"
