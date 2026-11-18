Late-campaign verification (Linux x86-64 hybrid, first-call audit on)

Input: an independent public 100% save for ULUS10128 ("Endgame"), copied into a
scratch profile's PSP/SAVEDATA/ULUS101280000/ only for testing. It is NOT part of
this kit and is not redistributed. Disc: the complete USA v1.02 image
(SHA-1 e2cd59a42d5ee263f94248483b57d7248b99ec94).

Observed, in order:
  1. title -> Load Game -> slot ("Endgame", 647 KB) -> "Load completed"
  2. loading screen for The Hood (map banner), then The Hood street.
  3. post-final-mission objective text about shops and revisiting missions on
     the subway; late-game HUD (money $58,635, ammo/health bars, minimap).
  4. walked north/east across the district (police car, crossing, minimap
     updated), opened and dismissed the save prompt, wrote a new checkpoint.
  5. exited with SIGTERM; counters below were written by the host.

Errors: none. See late-campaign-hood-session.txt for the stop line:
  calls=374325330 distinct=5090 audited=5090 mismatches=0 invalid_accesses=0
  guest_instructions=2753114594 span_calls=337426567 vblanks=31011 flips=16080

Campaign launcher, exercised from a fresh extraction of this very ZIP, with the
kit path containing a space and non-ASCII characters, and an empty data folder:
  choose image -> automatic full-disc verification, all 823,360 sectors,
  SHA-256 8004fc87f627b193b23f51614caa082b0f3c3d8d5ae78e449ed683d34ced7498
  -> PLAY CAMPAIGN -> local module compiled into the new data folder
  -> game boot -> autosave notice -> publisher logos -> clean exit
  (calls=11109060, invalid_accesses=0).

Windows/Wine: the packaged Play Bulletproof.exe (icon + version resource) opened
the same campaign launcher with the bundled Python 3.13.17 and Tcl/Tk 8.6; its
native file dialog selected the disc; full-disc verification ran; PLAY CAMPAIGN
started the custom PPSSPPWindows64 host and reached the autosave notice.
