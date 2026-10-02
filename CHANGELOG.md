# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.0] - 2026-10-02

### Changed
- Changed: Homepage and license URLs now point to github.com/jim60105/JimMonoTC; the corrected homepage is also stamped into the fonts' metadata.
- Changed: README intro, alignment sample, and download section were reworded and trimmed.
- Changed: The Python toolchain moved to `uv`: dependencies are declared in `pyproject.toml`, locked in `uv.lock`, and the build uses `.venv/bin/python` created by `uv sync` (Python 3.14, pinned via `.python-version`). `requirements.txt` is gone.
- Changed: The build scripts gained usage headers, colour-coded error reporting, fail-fast checks for missing tools and invalid options, and cleanup of partial downloads on failure.

### Added
- Added: A screenshot showcase of the font at the top of the README: a terminal window with a Chinese-identifier quicksort sample whose comments align purely on character cells, plus a box-drawing table, backfilled arrows, single-cell Nerd Font icons and Cascadia ligatures.
- Added: `uv.lock` with hashes, so every build uses an exact, auditable dependency set.
- Added: A CI dependency-audit job that runs `pip-audit --require-hashes` against the locked set and gates the build matrix, so packaging and release are skipped when a pinned build dependency has a known CVE.

### Security
- Security: Pinned the CI `setup-uv` action to the immutable tag `v10.2.0` (upstream stopped publishing floating major tags at v8).

### Removed
- Removed: Obsolete upgrade notes for versions 0.1.0 and 0.2.0 from the README.
- Removed: `requirements.txt` (replaced by `pyproject.toml` + `uv.lock`).

## [0.3.0] - 2026-10-02

### Changed
- Changed: The Latin base is now [Cascadia Code](https://github.com/microsoft/cascadia-code) 2407.24 (the static "NF" build) instead of Hack 3.003. **Breaking:** the cell is narrower (W = 1200 units instead of 1233 at 2048 UPM, two cells = 2400), glyph shapes change, and the Italic is Cascadia's true italic (10°, cursive forms in `ss01`); the CJK of Italic / Bold Italic is slanted by that angle.
- Changed: The programming ligatures are Cascadia Code's own (arrows such as `->` `=>` `<==>` `|->` `<-|` `->>`, and `!=` `===` `::` `&&` `||` `</>` `<!--` `www` and many more), replacing the 29 ligatures drawn for 0.1 / 0.2. Every ligature still keeps the width of the characters it replaces.
- Changed: Powerline symbols and Nerd Font icons are Cascadia Code's; the icons it lacks are added from the Nerd Fonts 3.4.0 glyph sets, scaled with Cascadia's own rule, so the complete set of `font-patcher --complete` is present in one consistent style. FontForge and `font-patcher` are no longer needed to build.
- Changed: Block elements, Symbols for Legacy Computing (and Supplement) and Powerline dividers fill exactly one line; the Windows metrics equal the line height, so line spacing is the same on every platform.
- Changed: East Asian Width comes from `unicodedata2` (current Unicode) in the build and the checks. U+2630 ☰ stays one cell; U+2B1B and U+2B1C (wide, one-cell in Cascadia) are left to the system emoji font like U+25FD, U+25FE and U+26A1.
- Changed: The web slices gain an `arabic-hebrew` group (upright styles only, Cascadia's italics have no Arabic / Hebrew); `box` now also holds Symbols for Legacy Computing, `symbols` the control pictures. Existing group names are unchanged.

### Added
- Added: Arrows that Cascadia lacks (↖ ↗ ↘ ↙ ⇐ ⇒ ⇔ ⇄ ⇅ ⇆ ⇦ ⇧ ⇨ ⇩ ⤴ ⤵ ⬅ ⬆ ⬇ ⮕ and more, 23 in all) from Noto Sans CJK TC Black, one cell wide and emboldened to the stroke of Cascadia's arrows in each style.
- Added: Greek, Cyrillic, Arabic, Hebrew, Vietnamese, Braille and Symbols for Legacy Computing coverage from Cascadia Code.
- Added: `scripts/verify.py` checks that block elements and Powerline dividers span exactly the line, and checks box drawing on the italic styles too.

### Removed
- Removed: Hack, `scripts/add-ligatures.py` and `licenses/Hack-LICENSE.txt`. Hack's Armenian and Georgian letters and most of its arrows are no longer in the font (system fonts render them).

## [0.2.0] - 2026-09-30

### Changed
- Changed: The web slices (`-web.zip`) are regrouped and every `.woff2` is now at most 64 KiB (65,536 bytes); the build fails otherwise. **Breaking for web users who referenced the old file names** (`latin`, `icons`, `cjk-common`, `cjk-big5`, `cjk-N` of v0.1.0 no longer exist). Per style the groups are `latin`, `latin-ext`, `greek-cyrillic`, `box`, `symbols` (one-cell characters), `icons-N` (private use), `cjk-N` (two-cell characters, N is the Noto Sans TC Google Fonts frequency range) and `cjk-xN` (the remaining two-cell characters). The group names are stable; take only the ones you need and update the `JimMonoTC.css` URLs.
- Changed: `scripts/build-web.py --slice-size` is replaced by `--max-bytes` (default 65,536); oversized chunks are halved automatically.

### Added
- Added: `sources/noto-sans-tc-web-ranges.txt`, the Google Fonts frequency ranges of Noto Sans TC that define `cjk-N`.
- Added: `scripts/verify.py` checks that the box drawing characters (`─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼`) reach the cell edges they connect to (upright styles), and has `--max-bytes` for slices.
- Added: `tests/check-web-zip.py`, a self-check of an assembled `-web.zip` (layout, size bound, disjoint and complete groups, `calt`, CSS, licences).

## [0.1.0] - 2026-09-30

First release.

### Added
- Added: Jim Mono TC, a monospace font in four styles (Regular, Bold, Italic, Bold Italic) where every CJK character is exactly two Latin cells wide.
- Added: Latin glyphs from Hack 3.003, Nerd Fonts icons (one cell each) and the full East Asian wide set of Noto Sans CJK TC 2.004 (about 43,000 code points) in a single OpenType/CFF font per style.
- Added: 29 programming ligatures (`==` `===` `!=` `!==` `=/=` `>=` `<=` `->` `<-` `=>` `-->` `<--` `==>` `<==` `<->` `<=>` `<==>` `::` `//` `||` `??` `/*` `*/` `>>` `<<` `>>>` `<<<` `|>` `<|`) that keep the width of the characters they replace.
- Added: Synthetic italic for CJK glyphs, slanted by Hack's italic angle, since Noto Sans CJK has no italic.
- Added: WOFF2 web fonts split into `unicode-range` slices, with a ready-made `JimMonoTC.css`.
- Added: Reproducible build from pinned, checksum-verified upstream sources (`scripts/build.sh`) and a verification suite covering cell widths, shaping and style metadata.
- Added: GitHub Actions workflow that builds every style on `master` pushes, keeps the fonts as artifacts, and publishes a GitHub release for `v*` tags.
- Added: Licence audit of all Nerd Fonts glyph sets, with `NOTICE.md` and the licence texts shipped in `licenses/`.
- Added: User-facing `README.md` and developer documentation in `docs/BUILDING.md`.

[Unreleased]: https://github.com/jim60105/JimMonoTC/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/jim60105/JimMonoTC/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jim60105/JimMonoTC/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/jim60105/JimMonoTC/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jim60105/JimMonoTC/releases/tag/v0.1.0
