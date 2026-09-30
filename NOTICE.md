# Notice

**Jim Mono TC** is a modified, merged font built from the upstream works listed
below. It is distributed under the **SIL Open Font License 1.1**
([LICENSE-OFL.txt](LICENSE-OFL.txt)); the upstream copyright notices and licence
terms that must travel with it are reproduced here and in the licence files.

The family name is new on purpose: the Bitstream Vera License forbids modified
fonts from carrying the words "Bitstream" or "Vera", and the merged font should
not be mistaken for Hack, Noto Sans CJK or a Nerd Font. `scripts/verify.py`
fails the build if an upstream name leaks into the name table.

## Components

| Part | Upstream | Version | Licence |
| --- | --- | --- | --- |
| Latin, symbols, box drawing | [Hack](https://github.com/source-foundry/Hack) (Regular, Bold, Italic, Bold Italic) | 3.003 | MIT + Bitstream Vera License ([LICENSE-HACK.txt](LICENSE-HACK.txt)) |
| Icons | [Nerd Fonts](https://github.com/ryanoasis/nerd-fonts) `font-patcher` and glyph sets | 3.4.0 | per glyph set, see below |
| CJK, fullwidth punctuation, kana, bopomofo | [Noto Sans CJK TC](https://github.com/notofonts/noto-cjk) (Regular, Bold) | 2.004 | SIL OFL 1.1 |
| Programming ligatures | drawn for this project from Hack's `=` / `>` geometry (`scripts/add-ligatures.py`) | – | SIL OFL 1.1 (this project) |

Exact upstream files are pinned by URL/commit and SHA-256 in `sources/`.

### Hack

Hack is Copyright 2018 Source Foundry Authors (MIT License) and includes
Bitstream Vera Sans Mono, Copyright 2003 Bitstream, Inc. (Bitstream Vera
License). Keep [LICENSE-HACK.txt](LICENSE-HACK.txt) with every redistribution.
Note the Bitstream Vera clause that the font software "may be sold as part of a
larger software package but no copy of one or more of the Font Software
typefaces may be sold by itself".

### Noto Sans CJK

Copyright 2014-2021 Adobe (http://www.adobe.com/). Noto is a trademark of Google
Inc. Licensed under the SIL Open Font License 1.1. The name table of Noto Sans
CJK carries no Reserved Font Name and none of "Noto", "Source" or "Adobe" is used
in this font's names.

### Nerd Fonts glyph sets

`font-patcher --complete --mono` adds 14 icon sets (the patcher's disabled "Material legacy"
font is not used). Nerd Fonts' own summary of these sources is its
[licence audit](https://github.com/ryanoasis/nerd-fonts/blob/master/license-audit.md); the
table below was checked against the licence files in the pinned FontPatcher archive and the
copyright strings inside the glyph fonts. `scripts/audit-licenses.py` (run by
`scripts/build.sh`) parses the patcher's set table and **fails the build when a set has no entry**
in this list, so a patcher update cannot silently add an unreviewed source.

| Glyph set | Licence | Copyright | Written to | Licence text shipped |
| --- | --- | --- | --- | --- |
| Seti-UI + Custom ("Original Source") | MIT | Jesse Weed (Seti-UI); Nerd Fonts | U+E5FA–E6FF | `third-party/Seti-UI-MIT.txt` |
| Nerd Fonts extras: heavy angle brackets, box drawing, progress indicators | MIT (Nerd Fonts: sources outside licensed folders are MIT) | Nerd Fonts | U+276C–2771, U+2500–259F, U+EE00–EE0B | – (Nerd Fonts' MIT text is in the patcher repository) |
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
  single cell by `font-patcher`, then converted to the font's outline format); that is the change
  notice CC BY 4.0 §3(a)(1)(B) and Apache 2.0 §4(b) ask for.
* **Apache 2.0 (Material Design Icons)**: a copy of the licence is shipped
  (`third-party/Apache-2.0.txt`). The archive only contains a short Pictogrammers summary that
  refers to it; we know of no upstream `NOTICE` file for the font.
* **SIL OFL Reserved Font Names**: none of "Font Awesome", "Pomicons", "Weather Icons", "Noto", "Source",
  "Hack", "Bitstream", "Vera" or "Nerd" may appear in the font's names;
  `scripts/verify.py` checks this for every build.
* **Bitstream Vera (via Hack)**: renamed (see above); the font must not be sold by itself.

Open points, none of which the build can settle. This is documentation of what was found, not legal advice:

1. **Mixed licences in one font.** The font as a whole is offered under the OFL, whose terms
   include "no selling by itself". CC BY 4.0 forbids imposing additional terms that restrict what
   recipients may do with the CC-licensed material, so applying the OFL to the Codicons and
   Font Awesome glyphs is arguably a conflict. Nerd Fonts distributes patched fonts on the same
   basis. Until someone with the standing to decide has looked at it, the table above states
   the licence of every glyph range so that each part can be taken from its original source
   under its own terms; the OFL is applied to this project's own work and to the combination
   only as far as the component licences allow. If that is not acceptable, drop the
   affected set: run `font-patcher` with explicit `--material --octicons ...` flags instead of
   `--complete` (`scripts/audit-licenses.py` will then need the list updated).
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

No third-party ligature glyphs or OpenType code (e.g. from Fira Code) are used,
so no additional Reserved Font Name applies. If ligatures from another font are
adopted later, review that font's licence and Reserved Font Name first.

## Modifications

* Programming ligatures added as a `calt` feature.
* Nerd Fonts glyph sets added by `font-patcher --complete --mono` (single cell).
* Noto Sans CJK TC outlines scaled and centred into a cell of exactly twice the
  Hack advance width (kept as cubic curves in the OpenType/CFF build, converted to
  quadratics in the TrueType build).  For the Italic styles they are additionally
  slanted by Hack Italic's angle (Noto has no italic).
* Zero-advance combining marks that the patcher widened are restored to Hack's
  original zero advance.
* Emoji-width code points (East Asian Wide) that Nerd Fonts maps to one-cell
  glyphs (U+25FD, U+25FE, U+26A1) are unmapped so system emoji fonts render them.
* Name table replaced; `OS/2`/`post` metadata adjusted for terminals.
