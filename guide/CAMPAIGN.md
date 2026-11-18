# The campaign: what is in this player, and what has been observed running

Short version: the player boots the **unmodified retail story campaign** from your own disc. The complete disc is checked byte for byte by the launcher, every level, movie, audio bank and data file is present, and there is no unlock, chapter skip, content patch or substitute game. Save files are ordinary PSP saves, so progress carries over between sessions and between machines.

Whether that whole campaign has been *watched running end to end by me* is a different question, and the honest answer is **no**. This page separates the two clearly so you can judge the kit on evidence rather than adjectives.

## 1. Completeness of the game data

The launcher's **Verify entire disc** reads all **823,360 sectors** (1,686,241,280 logical bytes, 869 files) through the kit's own CISO/ISO9660 reader and compares the result with a known-good USA v1.02 image:

| Check | Value |
|---|---|
| Disc ID / revision | `ULUS10128` / `1.02` |
| Logical size | 1,686,241,280 bytes |
| SHA-256 over all decoded sectors | `8004fc87f627b193b23f51614caa082b0f3c3d8d5ae78e449ed683d34ced7498` |
| Files on the disc | 869, including 78 `.pmf` movies, 650 `.r4s` and 120 `.r4m` level/model/audio containers, 6 `.prx` modules |
| Boot program (plain) | SHA-256 `3db80280dbfcac7bba87160c00e7bcc94686a96e804d00cdd4ad6cbcd0ca5fc8` |

The engine's own level table (`PSP_GAME/USRDIR/LEVELS.TXT`) describes the full story campaign; the areas it names are all present on the disc:

Industrial District (80_16) · The Hood (80_17–80_26, 80_29 “The Hood – Final”) · Theatre (80_01) · Mansion ext./floor 1 (80_02, 80_03, 80_32) · Junkyard and Meth Lab (80_04, 80_05, 80_30) · Chinatown and boss (80_06, 80_31) · Parking Garage (80_07) · Subway 1 and Subway Cars (80_08, 80_09) · Waterfront / warehouse (80_10, 80_27) · Morgue (80_11) · Meat Packing Plant (80_12, 80_28) · Boat Docks and Boat Interior (80_13, 80_14) · plus the chapter transitions and the ending/credits movies (78_40 “Ending”, 78_61 “Credits”).

If a sector of your image differs, the launcher refuses to label it verified rather than letting you discover a broken level later.

## 2. What has actually been played

| Where | What happened |
|---|---|
| **Tutorial Theater** (Linux and Windows/Wine) | New Game → tutorial, movement, camera, pause/phone menu, save creation, restart and **Load Game → Tutorial Theater → Load completed → Resume Game**. |
| **Industrial District, opening story mission** (Linux and Windows/Wine) | Opening movies, first mission, in-level HUD, mission prompt, movement, minimap, Tasks menu, checkpoint save, full player restart and reload. First-call audits: 100.9M and 78.3M native calls, **0 differences, 0 invalid accesses**. |
| **Late campaign: “Endgame” checkpoint in The Hood** (Linux) | Loaded an independent, publicly posted 100 % save for this title into a scratch profile (not included in the kit; deleted afterwards). The game reported **Load completed — “Endgame”**, opened The Hood, and posted its post-final-mission objective: *“With that joke Spinosa out of the way, you're free to hit the shops… And if you need to score more cash, you can hit the subway to revisit missions.”* Moved through the district (police car, crossing, minimap), saved again, and resumed: **374,325,330 native calls**, 5,090 distinct entries, **0 audit differences, 0 invalid accesses**. |

Together those runs use the same engine binary, the same compiled module and the same data files as a start-to-credits game. They exercise the tutorial, the first chapter, a finished campaign state, late-game map, HUD state (money, ammo, health), menus, save writes and save reads. The extra persistence, backup and snapshot features were exercised too: automatic save backup ZIP, snapshot creation and `--state` resume.

## 3. What has *not* been shown

- A single continuous playthrough from New Game to the credits, chapter by chapter, with every boss fight and every movie. That would take many hours of human playing; automated key-driving is not a substitute for it.
- Every chapter transition and movie in sequence, and every shop/upgrade interaction.
- Physical Windows hardware (the Windows build was run under Wine 10), physical gamepads, Steam Deck, macOS/ARM.
- Ad-hoc or cheat-modified saves. Unusual data may expose paths the retail campaign never takes.

## 4. How to see a late mission yourself in minutes

1. Use a save you own (or one from a public save archive you trust) and copy its `ULUS101280000/` folder into `Play-Data/config/ppsspp/PSP/SAVEDATA/`.
2. Start the launcher. The checkpoint list should show the save's description. **PLAY CAMPAIGN**.
3. **Load Game** → slot → **X** after *Load completed* → **Resume Game**.
4. To jump straight back to a moment you have already reached, save a snapshot in the player (**Esc → Save state**) and later pick it under **Resume snapshot** in the launcher.

## 5. If something fails

Keep `Play-Data/logs/session-*.txt` and `Play-Data/native/<platform>/compile.txt`. A useful report says which chapter, what you did, and whether the last session log's `stop` line has positive `calls=` (native code ran) or which `invalid_accesses`/`mismatches` count is non-zero. Comparing the same moment with **Compatibility only** tells us whether an issue is in the locally compiled code or in the shared runtime settings.
