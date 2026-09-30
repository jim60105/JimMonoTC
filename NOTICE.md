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

The icons come from several projects, each with its own licence. The licence
files shipped inside the Nerd Fonts `FontPatcher` archive are copied to
`dist/licenses/nerd-fonts/` by `scripts/build.sh`; redistribute them with the
font. See <https://github.com/ryanoasis/nerd-fonts#glyph-sets> for the full list
and check every glyph set that `--complete` includes before publishing a build.

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
