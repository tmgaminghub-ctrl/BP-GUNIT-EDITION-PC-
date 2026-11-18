# Rebuilding the PC play kit

These steps are for developers. **No rebuild of the host is needed to play on a supported PC.** A disc isn't needed to build the tools or the runtime. Actual per-game C code is produced only by `play.py` from your own disc.

## Contents and inputs

- `toolkit/`: modified `andyst-dev/psprecomp`, including the emitter. `rebuild/psprecomp.patch` is the delta from commit `caca7595251410ae7887aa209ba56397a835d0e1`.
- `source/runtime-source.tar.xz`: the corresponding modified PPSSPP **1.20.4** source, including the FFmpeg source and third-party source trees used by these builds. The runtime resources are provided once, in `runtime/assets/`; the scripts copy these back into the extracted source. Unrelated platform artifacts, large prebuilt libraries, tests not used for this target and duplicate runtime resources are not required to relink the host.
- `rebuild/runtime.patch`: independently applicable delta against the official **release source tarball** (not a rolling branch). It includes the AOT hook, module-attach and IR changes, the cross-compilation guard, cross version header and Discord build fix. The extracted source archive **already includes these changes**. From a clean upstream release use `patch -p1 < /path/to/rebuild/runtime.patch` instead. This patch was reapplied to the pristine files and compared byte-for-byte to the build inputs. `bridge/patch_runtime.py` is a narrower helper for the AOT hooks alone; it is not a substitute for the cross-build changes.
- The FFmpeg fork is pinned to `1e3b4965632f60b1d85360261d1b9dd45444bc71`. The host must use the matching codec stack. A build using the Debian system libavformat was observed to stall during the opening movies; do not use `USE_SYSTEM_FFMPEG=ON` for this release.

## Rebuild the runtime: Linux x86-64

From the kit root, with the normal Debian 13 build tools and headers:

```sh
sudo apt install build-essential cmake ninja-build pkg-config python3 xz-utils \
  libsdl2-dev libsdl2-ttf-dev libglew-dev libgl-dev libglu1-mesa-dev libvulkan-dev \
  libzip-dev libsnappy-dev libzstd-dev libminiupnpc-dev libfreetype-dev \
  libpng-dev libfontconfig-dev libasound2-dev zlib1g-dev libx11-dev libwayland-dev
mkdir -p /tmp/bp-rebuild
tar -xJf source/runtime-source.tar.xz -C /tmp/bp-rebuild
sh rebuild/linux.sh /tmp/bp-rebuild/runtime-source /tmp/bp-rebuild/linux-build
# When satisfied, back up the original first, then replace it:
cp /tmp/bp-rebuild/linux-build/PPSSPPSDL runtime/PPSSPPSDL
strip runtime/PPSSPPSDL
```

Default `JOBS=2` can be changed. `CONFIG_ONLY=1` stops after CMake generation. The script optionally downloads five upstream static archives, verifying each against `media-hashes.json`; it reuses matching files already present. **To use your own modified FFmpeg**: build the included `ffmpeg/` source using its `linux_x86-64.sh`/`windows_x64-build.sh` and toolchain, install its headers and five link libraries below `ffmpeg/linux/x86_64/` or `ffmpeg/Windows/x86_64/`, and set `LOCAL_FFMPEG=1` before invoking the host build script. This skips the downloads and digest substitution entirely. See `ffmpeg/PPSSPP-README.md` and the platform scripts in the source for those build steps. Replacing binaries naturally changes their package checksums.

## Rebuild the runtime: Windows x64, from Linux

The supplied PE32+ executable was cross-built with **Clang/LLVM 19** in MSVC mode, `lld-link`, LLVM RC, CMake 3.31.6, Ninja, and legitimately obtained Microsoft CRT/Windows SDK headers and link libraries. The shipped player has no development-tool dependency. The Microsoft SDK itself is not redistributed.

1. Install `clang-19`, `llvm-19`, `lld-19`, `cmake`, `ninja-build`, `python3`, and `xz-utils`. Use a Linux build workspace without spaces for the SDK/toolchain paths. Install [xwin 0.10.0](https://github.com/Jake-Shadle/xwin/releases/tag/0.10.0) or prepare equivalent licensed headers/libraries. The tested xwin packages were VC **14.44 / 17.14** x64 Desktop and Win11 SDK **10.0.26100**. In a fresh directory run xwin, review the Microsoft license, and proceed only if you accept it:

   ```sh
   export BP_ROOT=/tmp/bp-cross
   mkdir -p "$BP_ROOT"
   xwin --manifest-version 17 --arch x86_64 --cache-dir "$BP_ROOT/xwincache" splat --output "$BP_ROOT/winsdk"
   ```

   Use xwin's `--sdk-version` / `--crt-version` if your manifest defaults differ. Keep the unpacked cache as well as the splat: `overlay.py` uses both to supply case-insensitive header lookup on Linux. Expected locations include `winsdk/crt/include`, `winsdk/sdk/include/um`, `winsdk/sdk/lib/um/x86_64`.
2. In the kit directory, extract `source/runtime-source.tar.xz` and run:

   ```sh
   tar -xJf source/runtime-source.tar.xz -C "$BP_ROOT"
   sh rebuild/windows-cross.sh "$BP_ROOT/runtime-source" "$BP_ROOT/win-build"
   cp "$BP_ROOT/win-build/PPSSPPWindows.exe" runtime/PPSSPPWindows64.exe
   ```

   The script sets the case overlay, resource code page, Version.lib alias, system link libraries, static MSVC runtime and the upstream FFmpeg directory. It does not require running `.cmd` files on Linux. `JOBS`, `CONFIG_ONLY` and `LOCAL_FFMPEG` have the same meaning as above. A native Visual Studio build is an alternative development route, but was not the build used in the playtest.

## Rebuild psprecomp and the launchers

```sh
cmake -S toolkit -B /tmp/bp-emitter -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/bp-emitter
ctest --test-dir /tmp/bp-emitter --output-on-failure
cp /tmp/bp-emitter/tools/allegrexrecomp/allegrexrecomp bin/linux-x64/

# Windows emitter and campaign-launcher stub using MinGW-w64
cmake -S toolkit -B /tmp/bp-emitter-win -G Ninja -DCMAKE_SYSTEM_NAME=Windows \
  -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/bp-emitter-win --target allegrexrecomp
cp /tmp/bp-emitter-win/tools/allegrexrecomp/allegrexrecomp.exe bin/windows-x64/

# Stub EXE: icon + version resource, starts the bundled pythonw with campaign.py
x86_64-w64-mingw32-windres -I launcher launcher/launcher.rc -O coff -o /tmp/launcher.res
x86_64-w64-mingw32-gcc -O2 -s -municode -mwindows launcher/windows.c /tmp/launcher.res \
  -o 'Play Bulletproof.exe' -lshell32 -lole32
```

`launcher/campaign.py` (Tk) and `launcher/campaign_store.py` (disc verification, checkpoints, backups, snapshots, single-instance lock) are plain Python and run unchanged on both platforms; `launcher/windows.c` only resolves the kit folder and starts the bundled interpreter, so paths with spaces work and no console window is needed. On Windows the Tcl/Tk files from CPython 3.13.17's `tcltk.msi` are placed in `vendor/python-win64/` (`_tkinter.pyd`, `tcl86t.dll`, `tk86t.dll`, `tcl/`, `Lib/tkinter/`); `TCL_LIBRARY`/`TK_LIBRARY` are not required with that layout. The Linux launcher is a shell script that needs `python3-tk`. Windows uses CPython's embeddable distribution with an explicit `tools` path; TinyCC builds the local DLL. On Linux, TCC emits a PIC object linked by GNU `ld` with a non-executable stack, or `cc` compiles multiple translation units. `play.py --rebuild` regenerates a module after changes. Rebuilding tools on older Linux systems may also be necessary if the original emitter's glibc requirement isn't met.

## How the integration works

1. `tools/disc.py` uses bounded ISO9660/CISO reads. The boot SHA, disc ID/revision and associated support-module hashes gate the title. `tools/prx.py` fixes the two segment offsets, applies 32,891 relocations and gives the emitter a fixed-address ELF at `0x08804000`.
2. `allegrexrecomp emit` uses the corrected continuation handling and text-only discovery. `tools/leaves.py` selects typed, scalar, straight-line operations from **that emitted C**. It does not implement a second CPU translator. Complete functions must end in a return/delay slot. Additional sequences are bounded to 4–24 operations and have no branch, call, syscall, or VFPU action. Wrapper metadata includes every original word for exact matching. None of these local outputs ship here.
3. `bridge/host.inc` and the changes in `runtime.patch` attach at module load and use the existing PPSSPP register state, RAM and cycle accounting. Whole functions use the replacement dispatcher. IR block compilation can lower word-matched spans to calls into the local module. If a span is unsuitable or changes it stays with the normal host; debugger memory/PC breakpoints disable span selection. The launcher configures IR Interpreter (`CPUCore=3`) for hybrid mode, without disabling persistent settings.
4. Optional audit shadows the first invocation of each reached entry, compares register results and candidate written bytes to the interpreter, and quarantines a divergent entry. Reports include distinct entries, native calls, guest instruction positions traversed, failures and actual display vblank/flip counts. Statistics are scoped to the module, not the whole machine. Auditing is a diagnostic aid, not a proof that every possible game state works.

## Verification commands

```sh
python3 -B tests/test_disc.py
python3 -B tests/test_launcher.py
python3 -B tests/test_campaign.py     # launcher storage: config, saves, backups, snapshots, lock
python3 -B play.py '/path/to/disc.cso' --build-only
python3 -B tests/check_local_native.py Play-Data/native/linux-x64/engine-leaves.so
python3 -B play.py '/path/to/disc.cso' --audit
```

On Windows use the bundled `vendor\python-win64\python.exe` and `Play-Data\native\windows-x64\engine-leaves.dll`. The differential runner **loads native code**, so point it only at your own locally built module. No proprietary disc data is required for the synthetic reader and launcher unit tests. See [`guide/PLAYTEST.md`](../guide/PLAYTEST.md) for observed results, not just intended behavior.
