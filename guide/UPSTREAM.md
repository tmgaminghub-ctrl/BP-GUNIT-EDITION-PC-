# “Emulator-free”: what that would actually take

This kit is a **hybrid**. It recompiles part of the game engine to native x64 on your machine, and a modified PPSSPP runtime executes the rest of the code and provides every PSP service. Calling it “emulator-free” would be false, so this page explains what “emulator-free” means for this title, what is already in place, and what is still missing. No wording in the launcher or README claims a standalone port.

## What is already native

| Piece | Status |
|---|---|
| Engine PRX → fixed-address MIPS ELF, 32,891 relocations applied | Done (`tools/prx.py`) |
| Emitter (`allegrexrecomp`) producing C for the engine's 199,087 instruction words | Working |
| Local x64 code, exact-word dispatch, cycle/GPR/RAM ABI, first-call auditor | Working; **84,768 of 199,087 positions (42.58%)** selected, 11,680 ranges |
| Executable host integration (replace-table + IR lowering) | Working, in the modified runtime |

Everything below that line is still the emulator: the rest of the engine's instructions, the other CPU on the die (the Allegrex VFPU paths that were not emitted), threads, graphics, audio, input, files, saves.

## What “emulator-free” would require

1. **Full-code recompilation, not 42%.** The remaining 114,319 instruction positions include branch/delay-slot flows, VFPU vector code, and the game's other modules (`sc_sascore.prx`, `audiocodec.prx`, `mpegbase.prx`, `videocodec.prx`, `libatrac3plus.prx`, `mpeg.prx` — all present on your disc with known hashes). Each needs emitted, ABI-correct native code, including indirect call targets: the engine has **226 imports across 27 libraries** and **17,107 dispatch addresses** that appear at run time.
2. **A Geometry Engine renderer.** The game writes display lists straight into GPU memory. A standalone build must implement the GE's command stream (vertices, texture swizzle/CLUT, blending, depth, skinning, fog, splines…), a shader pipeline and a window — tens of thousands of lines. Today the runtime's GPU does this.
3. **The kernel surface the game actually touches.** Threads/semaphores/event flags and callbacks, `sceIo` with UMD reads from your ISO/CSO, memory-stick saves and the save UI, RTC, power/utility stubs, and the audio output path. The first diagnostic kit implemented 101 of 226 imports and stopped exactly here.
4. **Codec modules.** SPU/audio-codec (SAS), ATRAC3+, MPEG-PS video. The honest options are native decoders (FFmpeg already provides the matching ATRAC/MPEG support) or recompiled Sony modules; the early standalone attempt died at `audiocodec.prx` (`NID 0x977DE386`, stub `0x088C6874`, return address `0x08857F1C`) after 6,864 bytes of engine execution, with 23,059 markers, 13 firmware calls, no GE traffic and no video frames.
5. **Timing and input parity.** Frame pacing, vblank behaviour and controller mapping must be re-created, because the game's logic is timed by them.

Evidence that step 1 alone is not the finish line: the standalone diagnostic booted the engine, executed 13 firmware calls and produced **no pixels, no vblanks and no disc I/O**. Code generation was never the only missing piece.

## Why this cannot be honest shorthand

- A build that still links the emulator core is not emulator-free, whatever percentage is recompiled.
- The recompiled output is **game-derived**: it can only be produced on your machine from your disc. Any “standalone port” also has to be generated locally, which is why this kit ships the toolchain instead of game binaries.
- Reaching parity means reimplementing a whole GPU and kernel on a title nobody has done this for before. It is a project, not a setting.

## What this kit gives you instead

- A **launcher-driven campaign player** that plays the real game, with full-disc verification, checkpoints, backups and snapshots.
- A **measurable native path**: `Play-Data/logs/session-*.txt` records native calls, distinct entries, guest instructions executed through them, and any divergence (`--audit`). `--compat` runs the same game with local code disabled, so the difference between the two modes is observable rather than asserted.
- An honest label: *hybrid static recompilation*.

## If you want to push toward standalone

The realistic next milestones, in dependency order, are (a) raise whole-function coverage and add VFPU-aware lowering, (b) recompile the six support modules, (c) build a GE command-stream backend against a real level, (d) replace kernel services one subsystem at a time, keeping the emulator available as a differential reference. Each milestone is testable on its own with the auditor that already exists. Steps (c) and (d) are the long ones, and I would not present a partial result as an emulator-free port. Say the word and I will start at (a) plus a progress report, which is the piece that can be measured honestly in short iterations.
