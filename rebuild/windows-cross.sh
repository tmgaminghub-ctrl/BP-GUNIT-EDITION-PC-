#!/bin/sh
# Build the packaged Win64 host from Linux. See BUILDING.md for SDK preparation.
set -eu
: "${BP_ROOT:?Set BP_ROOT to the working directory containing your licensed winsdk and xwincache.}"
export BP_ROOT=$(realpath "$BP_ROOT")
s=$(realpath "$1"); b=$(realpath -m "$2"); kit=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
[ -f "$BP_ROOT/winsdk/sdk/lib/um/x86_64/version.lib" ] || { echo 'Missing x64 MSVC/SDK splat. See BUILDING.md.' >&2; exit 2; }
mkdir -p "$BP_ROOT/win-llvm"
for f in clang-cl res cross.cmake late.cmake overlay.py; do cp "$kit/rebuild/$f" "$BP_ROOT/win-llvm/$f"; done
chmod +x "$BP_ROOT/win-llvm/clang-cl" "$BP_ROOT/win-llvm/res"
python3 "$BP_ROOT/win-llvm/overlay.py"
[ -e "$BP_ROOT/winsdk/sdk/lib/um/x86_64/Version.lib" ] || ln -s version.lib "$BP_ROOT/winsdk/sdk/lib/um/x86_64/Version.lib"
[ -d "$s/assets" ] || cp -a "$kit/runtime/assets" "$s/assets"
if [ "${LOCAL_FFMPEG:-0}" != 1 ]; then python3 "$kit/rebuild/media.py" "$s" windows; fi
cmake -S "$s" -B "$b" -G Ninja -DCMAKE_TOOLCHAIN_FILE="$BP_ROOT/win-llvm/cross.cmake" \
 -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="$BP_ROOT/win-llvm/late.cmake" \
 -DCMAKE_BUILD_TYPE=Release '-DCMAKE_C_FLAGS_RELEASE=/O1 /DNDEBUG' '-DCMAKE_CXX_FLAGS_RELEASE=/O1 /DNDEBUG' \
 -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded -DCMAKE_POLICY_DEFAULT_CMP0091=NEW \
 -DCMAKE_DISABLE_FIND_PACKAGE_PkgConfig=ON -DCMAKE_HAVE_LIBC_PTHREAD=0 -DCMAKE_HAVE_PTHREADS_CREATE=0 -DCMAKE_HAVE_PTHREAD_CREATE=0 \
 -DOPENGL_LIBRARIES=opengl32 -DOPENGL_gl_LIBRARY:STRING=opengl32 -DOPENGL_glu_LIBRARY:STRING=glu32 \
 -DFFMPEG_DIR="$s/ffmpeg/Windows/x86_64" -DUSE_SYSTEM_FFMPEG=OFF -DUSE_MINIUPNPC=OFF -DUSE_DISCORD=OFF -DHEADLESS=OFF -DUNITTEST=OFF
[ "${CONFIG_ONLY:-0}" != 1 ] || exit 0
cmake --build "$b" --target PPSSPPWindows --parallel "${JOBS:-2}"
printf 'Built: %s/PPSSPPWindows.exe (copy to runtime/PPSSPPWindows64.exe)\n' "$b"
