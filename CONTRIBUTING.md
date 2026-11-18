# Contributing

Thanks for looking. This is an unofficial, offline **hybrid** player for one specific disc revision; the project's value depends on being precise about what it does, so the rules below are mostly about evidence.

## Ground rules

1. **No game data, ever.** Do not add or attach ISO/CSO images, `BOOT.BIN`/`EBOOT.BIN`, `KEVLAR.BIN`, saves, save states, `LEVELS.TXT` dumps, extracted `r4s`/`r4m`/`.pmf` assets, or locally generated `engine-leaves.*` modules. `scripts/check_source_only.py` enforces this in CI.
2. **No overclaiming.** The kit is a hybrid: locally recompiled engine code plus a PSP runtime. A change or a sentence that presents it as emulator-free, fully native or a standalone port will be rejected. See [guide/UPSTREAM.md](guide/UPSTREAM.md) for what a standalone build would actually require.
3. **No prebuilt binaries in git.** The player, the runtime, vendored Python/TinyCC and the modified-runtime source are release assets built by `rebuild/package.py`.
4. **Keep one disc revision supported.** `ULUS10128` v1.02 with the documented boot hash. Other regions/revisions are out of scope; don't weaken the checks to make an image fit.

## Development

```sh
python3 -m compileall -q play.py launcher tools tests scripts
python3 tests/test_disc.py          # synthetic CISO/ISO reader and PRX checks
python3 tests/test_launcher.py      # runtime settings + generated-code partitioning
python3 tests/test_campaign.py      # launcher config/display/saves/backups/snapshots
python3 scripts/check_source_only.py
python3 scripts/check_docs.py
```

All of these run without the game, without the disc and without any proprietary file. If you have your own image, the end-to-end checks are:

```sh
python3 play.py '/path/to/disc.cso' --build-only     # disc gate + local build
python3 play.py '/path/to/disc.cso' --audit          # first-call differential audit
python3 tests/check_local_native.py Play-Data/native/linux-x64/engine-leaves.so
```

## Pull requests

- One topic per PR; say which file/behaviour changed and how you verified it.
- Paste the relevant lines from `Play-Data/logs/session-*.txt` (`calls=`, `distinct=`, `mismatches=`, `invalid_accesses=`) when your change touches the bridge, selection or display settings.
- UI changes: include a screenshot with the launcher on both a small window and a 4K/full-screen setting if you can.
- New display or runtime options must be optional, must write through `campaign_store.apply_display`/`ini_set`, and must not break an existing `ppsspp.ini`.

## Reporting issues

Use the issue template. Useful reports include: platform, kit version (from `Play-Data/campaign-launcher.json`), what you did, what happened, whether `--compat` behaves differently, and the tail of the session log. Do not attach the disc image or a save you didn't create.

## Licensing

Contributions are accepted under the project's [LICENSE.txt](LICENSE.txt). Files derived from PPSSPP or other upstream code keep their original licenses — state that in the PR. Game assets and trademarks remain their owners'.
