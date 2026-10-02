# Notice

**Jim Mono TC** is a modified, merged font built from the upstream works listed
below. It is distributed under the **SIL Open Font License 1.1**
([LICENSE](LICENSE)); the upstream copyright notices and licence
terms that must travel with it are reproduced here and in the licence files.

The family name is new on purpose: Cascadia Code's licence reserves the font name
"Cascadia Code", and the merged font should not be mistaken for Cascadia Code,
Noto Sans CJK or a Nerd Font. `scripts/verify.py` fails the build if an upstream
name leaks into the name table.

## Components

| Part | Upstream | Version | Licence |
| --- | --- | --- | --- |
| Latin, Greek, Cyrillic, Arabic, Hebrew, symbols, box drawing, block elements, legacy computing, programming ligatures, Powerline and most Nerd Font icons | [Cascadia Code](https://github.com/microsoft/cascadia-code) NF (static Regular, Bold, Italic, Bold Italic) | 2407.24 | SIL OFL 1.1, Reserved Font Name "Cascadia Code" ([licenses/CascadiaCode-LICENSE.txt](licenses/CascadiaCode-LICENSE.txt)); its Nerd Font icons keep their glyph-set licences, see below |
| Nerd Font icons Cascadia lacks | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) glyph sets (FontPatcher archive) | 3.4.0 | per glyph set, see below |
| CJK, fullwidth punctuation, kana, bopomofo | [Noto Sans CJK TC](https://github.com/notofonts/noto-cjk) (Regular, Bold) | 2.004 | SIL OFL 1.1 |
| Arrows Cascadia lacks (↖ ⇒ ⇄ ⤴ ⬅ …) | [Noto Sans CJK TC](https://github.com/notofonts/noto-cjk) (Black) | 2.004 | SIL OFL 1.1 |

Exact upstream files are pinned by URL/commit and SHA-256 in `sources/`.

### Cascadia Code

Copyright (c) 2019 - Present, Microsoft Corporation, with Reserved Font Name
Cascadia Code. Licensed under the SIL Open Font License 1.1; keep
[licenses/CascadiaCode-LICENSE.txt](licenses/CascadiaCode-LICENSE.txt) with every redistribution.
"Cascadia Code" is a trademark of the Microsoft group of companies; neither it, "Cascadia"
nor "Microsoft" is used in this font's names (the name table, including Microsoft's
trademark and licence-description records, is replaced).

### Noto Sans CJK

Copyright 2014-2021 Adobe (http://www.adobe.com/). Noto is a trademark of Google
Inc. Licensed under the SIL Open Font License 1.1. The name table of Noto Sans
CJK carries no Reserved Font Name and none of "Noto", "Source" or "Adobe" is used
in this font's names.

### Nerd Fonts glyph sets

The icons come from two places: Cascadia Code NF, which carries Microsoft's own build of the
Nerd Fonts glyph sets (an earlier Nerd Fonts release), and, for the about 1,190 icons it lacks,
the same glyph sets in the pinned Nerd Fonts 3.4.0 FontPatcher archive (`scripts/prepare-base.py`;
`font-patcher` itself is not run). Together they are exactly the 14 icon sets of
`font-patcher --complete` (the patcher's disabled "Material legacy" font is not used). Nerd Fonts' own summary of these sources is its
[licence audit](https://github.com/ryanoasis/nerd-fonts/blob/master/license-audit.md); the
table below was checked against the licence files in the pinned FontPatcher archive and the
copyright strings inside the glyph fonts. `scripts/audit-licenses.py` (run by
`scripts/build.sh`) parses the patcher's set table and **fails the build when a set has no entry**
in this list, so a patcher update cannot silently add an unreviewed source.

| Glyph set | Licence | Copyright | Written to | Licence text shipped |
| --- | --- | --- | --- | --- |
| Seti-UI + Custom ("Original Source") | MIT | Jesse Weed (Seti-UI); Nerd Fonts | U+E5FA–E6FF | `third-party/Seti-UI-MIT.txt` |
| Nerd Fonts extras: progress indicators (heavy angle brackets and box drawing are Cascadia's own) | MIT (Nerd Fonts: sources outside licensed folders are MIT) | Nerd Fonts | U+EE00–EE0B | – (Nerd Fonts' MIT text is in the patcher repository) |
| Devicons | MIT | konpa | U+E700–E8EF | `third-party/Devicon-MIT.txt` |
| Powerline Symbols | MIT (text in archive; Nerd Fonts' audit says "Free License") | Kim Silkebækken and contributors | U+E0A0–E0A2, U+E0B0–E0B3 | `nerd-fonts/powerline-symbols-LICENSE.txt` |
| Powerline Extra Symbols | MIT | Ryan L McIntyre | U+E0A3, U+E0B4–E0C8, U+E0CA, U+E0CC–E0D7, U+2630 | `nerd-fonts/powerline-extra-LICENSE` |
| Pomicons | SIL OFL 1.1, Reserved Font Name "Pomicons" | Gabriele Lana | U+E000–E00A | `nerd-fonts/pomicons-LICENSE` |
| Font Awesome Free (icons, CC BY 4.0 side of its licence) | CC BY 4.0 | Fonticons, Inc. | U+ED00–F2FF | `nerd-fonts/font-awesome-LICENSE.txt` |
| Font Awesome Extension | MIT (Nerd Fonts audit only) | AndreLZGava | U+E200–E2A9 | none available |
| IEC Power Symbols | MIT (Nerd Fonts audit only) | unicodepowersymbol.com | U+23FB–23FE, U+2B58 | none available |
| Material Design Icons | Apache 2.0 | Pictogrammers | U+F0001–F1AF0 | `third-party/Apache-2.0.txt`, `nerd-fonts/materialdesign-LICENSE` |
| Weather Icons | SIL OFL 1.1 (font); Erik Flowers, v1 art Lukas Bischoff | Erik Flowers | U+E300–E3EB | `nerd-fonts/weather-icons-OFL.txt` (an unfilled template, see below) |
| Font Logos | Unlicense (public domain) | Lukas W | U+F300–F381 | `third-party/Font-Logos-Unlicense.txt` |
| Octicons | MIT | GitHub Inc. | U+F400–F505, U+F4A9–F533, U+2665, U+26A1 (U+26A1 is unmapped here) | `nerd-fonts/octicons-LICENSE` |
| Codicons | CC BY 4.0 | Microsoft Corporation | U+EA60–EC1E | `nerd-fonts/codicons-LICENSE.txt` |

Obligations and how they are met:

* **Attribution (CC BY 4.0: Codicons, Font Awesome; MIT; Apache 2.0)**: this table, the copyright
  string of the font (name ID 0) and the licence files in `dist/licenses/` name the authors,
  give the licence and link to its text. The icons were modified (scaled and moved into a
  single cell by Cascadia's build or by `scripts/prepare-base.py` with Cascadia's rule, then converted
  to the font's outline format); that is the change
  notice CC BY 4.0 §3(a)(1)(B) and Apache 2.0 §4(b) ask for.
* **Apache 2.0 (Material Design Icons)**: a copy of the licence is shipped
  (`third-party/Apache-2.0.txt`). The archive only contains a short Pictogrammers summary that
  refers to it; we know of no upstream `NOTICE` file for the font.
* **SIL OFL Reserved Font Names**: none of "Cascadia", "Font Awesome", "Pomicons", "Weather Icons", "Noto",
  "Source" or "Nerd" (nor "Microsoft", "Caskaydia") may appear in the font's names;
  `scripts/verify.py` checks this for every build.

Open points, none of which the build can settle. This is documentation of what was found, not legal advice:

1. **Mixed licences in one font.** The font as a whole is offered under the OFL, whose terms
   include "no selling by itself". CC BY 4.0 forbids imposing additional terms that restrict what
   recipients may do with the CC-licensed material, so applying the OFL to the Codicons and
   Font Awesome glyphs is arguably a conflict. Nerd Fonts distributes patched fonts on the same
   basis. Until someone with the standing to decide has looked at it, the table above states
   the licence of every glyph range so that each part can be taken from its original source
   under its own terms; the OFL is applied to this project's own work and to the combination
   only as far as the component licences allow. If that is not acceptable, drop the
   affected set: its code points must then be removed from Cascadia's glyphs too, and
   `scripts/prepare-base.py` / `scripts/audit-licenses.py` need the list updated.
2. **Weather Icons' `OFL.txt` is the blank OFL template** (`Copyright (c) <dates>, <Erik Flowers>`,
   `Reserved Font Name <Reserved Font Name>`), so the real copyright line and Reserved Font Name
   are not stated in the archive. The font's own name table says "Weather Icons licensed under SIL OFL 1.1"
   (Erik Flowers, Lukas Bischoff). We avoid the name "Weather Icons" in any case.
3. **Font Awesome Extension and IEC Power Symbols** have no licence text in the archive or, as far
   as we could find, upstream; MIT is taken from Nerd Fonts' audit alone (secondary source).
   Together they contribute about 175 code points.
4. **Font Awesome**: the archive licence gives icons CC BY 4.0 and font files OFL 1.1 with Reserved
   Font Name "Font Awesome". Nerd Fonts' font is "custom created from the Font Awesome release SVGs",
   so we treat the glyphs as CC BY 4.0 (as Nerd Fonts does) and still keep the name out of ours.
5. The upstream licence texts under `licenses/third-party/` were fetched from each project's default
   branch, not from the release Nerd Fonts bundles (see `licenses/third-party/README.md`).

### Ligatures

The programming ligatures and their `calt` code are Cascadia Code's own, covered by its
licence above. No ligatures from other fonts are used.

## Modifications

* Cascadia's block elements, Symbols for Legacy Computing (and Supplement) and Powerline dividers,
  drawn for the taller Windows-metrics cell, are scaled vertically to fill exactly one line.
* Nerd Font icons that Cascadia Code NF lacks are added from the Nerd Fonts 3.4.0 glyph sets,
  scaled and centred with Cascadia's own rule (`process.py` of its repository).
* Arrows that Cascadia lacks are taken from Noto Sans CJK TC Black, scaled into one cell,
  emboldened to the stroke of Cascadia's arrows and, in the italics, slanted.
* Noto Sans CJK TC outlines scaled and centred into a cell of exactly twice the
  Cascadia advance width (kept as cubic curves in the OpenType/CFF build, converted to
  quadratics in the TrueType build).  For the Italic styles they are additionally
  slanted by Cascadia Italic's angle (Noto has no italic).
* Emoji-width code points (East Asian Wide) that Cascadia maps to one-cell glyphs
  (U+25FD, U+25FE, U+26A1, U+2B1B, U+2B1C) are unmapped so system emoji fonts render
  them; U+2630 ☰ (wide since Unicode 16) is kept one cell.
* Name table replaced; `OS/2`/`post` metadata adjusted for terminals (Windows metrics set
  to the line, so the line height is the same on every platform).
