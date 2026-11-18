# Play validation • Bulletproof PC hybrid

**Result:** booted from the disc into interactive 3D gameplay, moved the character, opened the game's own menus, recorded non-silent stereo, saved and loaded a checkpoint after restarting the player. These are observations from the **modified runtime with local AOT enabled**. They are not results from a stock PPSSPP baseline or from the non-playable standalone diagnostic.

## What was played

| Run | Direct observations |
|---|---|
| **Linux x86-64, Industrial District** | Autosave notice → logos → New Game → skip tutorial → opening movie → Industrial District. Selected a new save slot; the save dialog identified the mission and reported completion. Dismissed the mission prompt, moved with the analog keys, saw the camera and minimap follow, paused, opened **Tasks → Locate K-Dog**, then returned to play. This session used first-call auditing. |
| **Linux, full player restart** | Reopened the same ISO/CSO with the verified cached module; selected **Load Game → Industrial District**. Saw **Load completed**, then **Resume Game** returned to the mission. Dismissed the prompt and moved again. The separate 14-second demonstration capture is from this run, at 960×544 with stereo audio; it is not inside the game-free kit. |
| **Windows x64 build, Tutorial Theater (Wine 10)** | Started the packaged EXE launcher from a folder with spaces and an empty build cache. It built the DLL, launched the custom PE host, rendered the Theater, created an ordinary save, accepted analog movement, displayed the in-game pause/phone menu, and resumed. After a full process restart, **Load Game → Tutorial Theater → Load completed → Resume Game** returned to the Theater, with responsive input. No emulator save state used. |
| **Windows x64 build, Industrial District (Wine 10)** | Independent first-call-audited run from a fresh native build: opening movie and the opening story area rendered. The Windows story audit below covers the boot, level load and initial in-level HUD/prompt. Save/reload and movement on Windows were independently confirmed in the Theater run above. |
| **Linux, late campaign — “Endgame” checkpoint, The Hood** | Loaded a third-party complete save (public archive; used in a scratch profile only, not redistributed) and resumed the **finished** campaign state. The game showed *Load completed* for the save described as *Endgame*, rendered The Hood with late-game HUD ($58,635, task updated), and delivered the post-final-mission objective about revisiting missions from the subway. Walked the district, wrote a new checkpoint, then exited cleanly. See `guide/evidence-late/` and `guide/CAMPAIGN.md`. |
| **Campaign launcher (both platforms)** | Linux: launcher → choose image → automatic full-disc verification (823,360 sectors) → **PLAY CAMPAIGN** → compiled the local module in a fresh folder and booted the game; settings, checkpoint list and backup switch persisted. Windows/Wine: the packaged **Play Bulletproof.exe** opened the campaign launcher, its native file dialog selected the disc, verification ran, and **PLAY CAMPAIGN** started the custom host and reached the game's autosave notice. |

The ordinary save directory was `PSP/SAVEDATA/ULUS101280000` on each platform. The two distinct checkpoint descriptions in the load dialogs were **Industrial District** and **Tutorial Theater**, both displayed as 647 KB. The actual `KEVLAR.BIN` payload was 12,356 bytes alongside the save's PSP metadata/preview files. No save or game data is redistributed.

## Native execution, not just code generation

Local compile: **659 whole functions** (3,325 positions) + **11,021 bounded sequences** (81,443 positions) = **11,680 non-overlapping ranges**, 84,768 guest instruction positions. At engine load 659 whole and 11,020 span entries installed with exact matching words. One compiled range was left on the normal host path. The static selection is 42.58% of the engine text. It does not measure the fraction of a frame executed natively.

End-of-session counters from the actual hosts:

| Session | Native calls | Distinct entries | Guest instructions via those entries | Audited entries | Audit differences | Invalid bridge accesses | Vblanks / flips |
|---|---:|---:|---:|---:|---:|---:|---:|
| Linux, story | 100,897,656 | 5,174 | 730,736,510 | 5,174 | 0 | 0 | 12,804 / 7,279 |
| Linux, story reload | 92,247,746 | 5,158 | 658,665,452 | off | — | 0 | 12,435 / 6,689 |
| Windows/Wine, Theater | 86,073,877 | 4,949 | 619,727,657 | off | — | 0 | 10,848 / 5,894 |
| Windows/Wine, Theater reload | 48,795,262 | 4,938 | 335,087,983 | off | — | 0 | 10,171 / 5,556 |
| Windows/Wine, story | 78,272,997 | 5,067 | 563,747,754 | 5,067 | 0 | 0 | 10,389 / 5,847 |
| Linux, “Endgame” late-campaign checkpoint | 374,325,330 | 5,090 | 2,753,114,594 | 5,090 | 0 | 0 | 31,011 / 16,080 |

These are scoped counts, not performance benchmarks. “Audited” means the **first live call per distinct entry**, not every invocation. Flip counts include menus and movies. Full counter logs are in `guide/evidence/`.

## Audio, compiler and integrity checks

- Captured the players' **separate output-device monitors** while in-level, as 48 kHz signed 16-bit stereo. Linux: 144,060 frames, peak 24,400, RMS 4,185.31. Windows/Wine: 143,896 frames, peak 16,323, RMS 4,142.89. These were non-silent decoded samples, not just successful device opens. Additional Linux opening-movie capture was non-silent. This is not a claim of perfect sound or sync throughout the game.
- Independent scalar reference vs. locally compiled bodies: **35,040 synthetic register/memory comparisons on each target**, including alias-heavy and boundary-value inputs; zero differences on Linux (TCC and GCC builds) and Win64 (bundled TCC, run under Wine). See `native-differential-*.txt` and `evidence/linux-gcc-build.txt`.
- Synthetic reader tests: 8/8. Launcher/settings tests: 4/4. The modified toolkit's original QA suite passed on both targets. The runtime source delta reapplied cleanly against the pinned release and yielded matching build inputs; both host CMake configurations generated from the supplied source archive.
- Test image: full USA `.cso`, 1,607,568,523 bytes; SHA-1 `e2cd59a42d5ee263f94248483b57d7248b99ec94`. The image is a test input, not part of the release. Equivalent raw ISO is supported by the reader; the interactive runs in this table used CSO.

## Limits

Playtesting covered the tutorial, the opening story area, and a finished-campaign checkpoint in a late area. A continuous start-to-credits playthrough, multiplayer, physical Windows hardware, physical controller, Steam Deck or a specific GPU performance target was not verified. `guide/CAMPAIGN.md` describes what that does and does not imply, and how to reach a late level yourself in minutes. The Linux host was exercised on Debian 13 with SDL2/OpenGL under a virtual display; the Windows **PE32+ build** was run with Wine 10 in a separate display. These are normal player binaries, not headless mocks. The complete campaign may expose code or services not exercised here. The emulator-free standalone port remains incomplete; this release is the practical hybrid play path.
