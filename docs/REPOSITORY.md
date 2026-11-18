# Repository layout and releases

This repository is **source-only**. It contains everything that is ours to publish: the launcher, the host-side recompilation glue, the disc reader, the rebuild scripts, the documentation and the tests. It deliberately does *not* contain game data, generated code, saves, or the prebuilt player.

## What is where

| Path | Contents |
|---|---|
| `launcher/` | Campaign launcher (`campaign.py`), storage layer (`campaign_store.py`), Windows stub `windows.c` + `launcher.rc`, artwork |
| `play.py` | Headless entry point: disc gate, local compile, display settings, spawn the runtime, session counters |
| `bridge/` | Host-side ABI (`bp_abi.h`), the PPSSPP integration include (`host.inc`, GPL-2.0-or-later), runtime patcher |
| `tools/` | `disc.py` (bounded CISO/ISO9660 reader), `prx.py` (PRX → fixed ELF, relocations), `leaves.py` (selection of typed straight-line operations from emitted C), `verify_files.py` |
| `tests/` | Synthetic unit tests (no game data) and `check_local_native.py` (loads *your* locally built module) |
| `toolkit/include/psprecomp/` | Public headers the generated code compiles against |
| `rebuild/` | Build scripts and patches: Linux/Windows host builds, cross-build overlay, media fetch with pinned hashes, `package.py`, `psprecomp.patch`, `runtime.patch` |
| `guide/` | Play evidence and counters, `CAMPAIGN.md` (what was and wasn't played), `UPSTREAM.md` (what emulator-free would require), third-party notices |
| `docs/screenshots/` | Launcher screenshot and the short demo clip |

## What is a release asset, not a commit

`rebuild/package.py` builds the distributable ZIP from a staged kit. That ZIP contains files that must not live in git:

- the modified PPSSPP runtime binaries and its **corresponding source** (`runtime-source.tar.xz`, GPL-2.0-or-later),
- vendored CPython 3.13.17 (embeddable, incl. Tcl/Tk) and TinyCC 0.9.27 for Windows, with their license texts,
- the Windows launcher EXE,
- `SHA256SUMS.txt` for the shipped files.

Each release attaches that ZIP plus its SHA-256. The source in this repository is what the ZIP's scripts and launcher are built from; the third-party components keep their own upstream licenses as listed in [THIRD-PARTY.md](../THIRD-PARTY.md).

## Never in git or in a release

The game itself, any disc image, `BOOT.BIN`/`EBOOT.BIN`, `KEVLAR.BIN`, saves, save states, `LEVELS.TXT` or asset dumps, and any `engine-leaves.*` module generated from a disc. `scripts/check_source_only.py` enforces this on every push.

## CI

`.github/workflows/ci.yml` runs, on Linux, Windows and macOS with Python 3.11–3.13: the source-only guard, a full `compileall`, the three unit-test suites, a parse check of the launcher, `sh -n` on the Linux entry point, and `scripts/check_docs.py`, which fails if a local docs link is broken or if any sentence presents the project as emulator-free without denying it.

## Suggested repository metadata

- **Description:** `Unofficial offline PC campaign player for 50 Cent: Bulletproof – G-Unit Edition (PSP, ULUS10128 v1.02): hybrid static recompilation + PPSSPP runtime. No game data included.`
- **Topics:** `psp`, `static-recompilation`, `ppsspp`, `reverse-engineering`, `gamedev-tools`, `emulation`, `hybrid`, `windows`, `linux`
- **License:** see `LICENSE.txt` (project code), plus upstream licenses for `bridge/host.inc` and third-party components.
- **Do not** enable GitHub Discussions for support unless you are ready to triage “does it run on my phone” questions; issues with the template are more useful.
