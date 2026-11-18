#!/bin/sh
set -eu
# Usage: ./linux.sh /path/to/extracted/runtime-source /path/to/new/build
s=$(realpath "$1"); b=$(realpath -m "$2"); kit=$(cd "$(dirname "$0")/.." && pwd)
[ -d "$s/assets" ] || cp -a "$kit/runtime/assets" "$s/assets"
if [ "${LOCAL_FFMPEG:-0}" != 1 ]; then python3 "$kit/rebuild/media.py" "$s" linux; fi
cmake -S "$s" -B "$b" -G Ninja -DCMAKE_BUILD_TYPE=Release \
 '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -g0 -DNDEBUG' '-DCMAKE_C_FLAGS_RELEASE=-O1 -g0 -DNDEBUG' \
 -DUSE_SYSTEM_FFMPEG=OFF -DFFMPEG_DIR="$s/ffmpeg/linux/x86_64" -DUSE_SYSTEM_LIBZIP=ON \
 -DUSE_SYSTEM_ZSTD=ON -DUSE_SYSTEM_SNAPPY=ON -DUSE_SYSTEM_MINIUPNPC=ON \
 -DUSE_SYSTEM_FREETYPE=ON -DUSE_SYSTEM_LIBPNG=ON -DUSE_DISCORD=OFF -DHEADLESS=OFF -DUNITTEST=OFF
[ "${CONFIG_ONLY:-0}" != 1 ] || exit 0
cmake --build "$b" --target PPSSPPSDL --parallel "${JOBS:-2}"
printf 'Built: %s/PPSSPPSDL\n' "$b"
