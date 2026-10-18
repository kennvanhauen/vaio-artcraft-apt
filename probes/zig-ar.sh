#!/bin/sh
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec "$project_root/.build/zig-aarch64-macos-0.14.1/zig" ar "$@"
