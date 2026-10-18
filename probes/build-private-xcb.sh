#!/bin/sh
# Sources are the official libxcb/xcb-proto 1.17.0 release archives in .build.
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_root="$project_root/.build"
mkdir -p "$build_root/pkgconfig" "$build_root/sysroot/usr/include/X11"
for header in Xauth.h Xfuncproto.h Xfuncs.h Xosdefs.h; do
    cp "/opt/homebrew/include/X11/$header" "$build_root/sysroot/usr/include/X11/$header"
done
ln -sf libXau.so.6 "$build_root/sysroot/usr/lib/i386-linux-gnu/libXau.so"
cat > "$build_root/pkgconfig/xau.pc" <<EOF
Name: Xau
Description: Xenial runtime Xau with portable X11 headers
Version: 1.0.8
Libs: -L$build_root/sysroot/usr/lib/i386-linux-gnu -lXau
Cflags: -I$build_root/sysroot/usr/include
EOF
cat > "$build_root/pkgconfig/xcb-proto.pc" <<EOF
xcbincludedir=$build_root/xcb-proto-1.17.0/src
pythondir=$build_root/xcb-proto-1.17.0
Name: XCB Proto
Description: XCB protocol descriptions
Version: 1.17.0
Libs:
Cflags:
EOF
export PKG_CONFIG_LIBDIR="$build_root/pkgconfig"
export PKG_CONFIG_PATH="$build_root/pkgconfig"
export PYTHONPATH="$build_root/xcb-proto-1.17.0"
export PYTHON=/opt/homebrew/bin/python3
export CC="$project_root/probes/zig-cc-xenial.sh"
export AR="$build_root/zig-aarch64-macos-0.14.1/zig ar"
export RANLIB="$build_root/zig-aarch64-macos-0.14.1/zig ranlib"
cd "$build_root/libxcb-1.17.0"
./configure --build=aarch64-apple-darwin --host=i686-linux-gnu \
    --prefix=/usr/lib/artcraft --disable-static --enable-shared \
    --disable-devel-docs --without-doxygen CFLAGS='-O2 -fPIC'
# The release's libtool detects Apple's ld on this host. Compile with its
# generated make rules, then link the Linux shared object explicitly with Zig.
make -C src -j8 xcb_conn.lo xcb_out.lo xcb_in.lo xcb_ext.lo xcb_xid.lo \
    xcb_list.lo xcb_util.lo xcb_auth.lo xproto.lo bigreq.lo xc_misc.lo
mkdir -p "$build_root/private-lib"
"$CC" -shared -Wl,--no-undefined -Wl,-soname,libxcb.so.1 \
    -o "$build_root/private-lib/libxcb.so.1" \
    src/.libs/xcb_conn.o src/.libs/xcb_out.o src/.libs/xcb_in.o \
    src/.libs/xcb_ext.o src/.libs/xcb_xid.o src/.libs/xcb_list.o \
    src/.libs/xcb_util.o src/.libs/xcb_auth.o src/.libs/xproto.o \
    src/.libs/bigreq.o src/.libs/xc_misc.o -lXau -lpthread
