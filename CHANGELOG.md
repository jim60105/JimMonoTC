# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/jim60105/JimMonoTC/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/jim60105/JimMonoTC/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jim60105/JimMonoTC/releases/tag/v0.1.0
