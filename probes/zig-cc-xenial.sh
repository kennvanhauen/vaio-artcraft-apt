#!/bin/sh
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export ZIG_GLOBAL_CACHE_DIR="$project_root/.build/zig-cache"
export ZIG_LOCAL_CACHE_DIR="$project_root/.build/zig-local-cache"
exec "$project_root/.build/zig-aarch64-macos-0.14.1/zig" cc \
    -target x86-linux-gnu.2.23 -mcpu=atom \
    -L"$project_root/.build/sysroot/usr/lib/i386-linux-gnu" "$@"
