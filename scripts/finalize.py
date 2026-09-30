#!/usr/bin/env python3
"""Give the merged font its own identity and tidy its tables.

* Replace every name record: the merged font is a modified version of Hack
  (Bitstream Vera licence forbids "Bitstream"/"Vera" in the name) and of Noto
  Sans CJK, so it ships under a new family name.
* Make cell-width metadata explicit for terminals (xAvgCharWidth = W, panose
  monospaced, isFixedPitch) and consistent vertical metrics.
* Drop tables that are stale or empty after FontForge / merging.
* OpenType/CFF input: keep the CFF font names in step with the name table and
  optionally subroutinize the charstrings (--subroutinize, compreffor; slow with
  ~55k glyphs) to shrink the file.
"""

import argparse
import sys

from fontTools.ttLib import TTFont

COPYRIGHT = (
    "Copyright (c) 2026 jim60105. "
    "Contains Hack (Copyright (c) 2018 Source Foundry Authors, MIT License; "
    "derived from Bitstream Vera Sans Mono, Copyright (c) 2003 Bitstream, Inc.), "
    "Noto Sans CJK (Copyright 2014-2021 Adobe (http://www.adobe.com/); Noto is a trademark of Google Inc.) "
    "and Nerd Fonts glyph sets (see NOTICE.md)."
)
LICENSE_DESCRIPTION = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
    "It also incorporates material under the MIT License and the Bitstream Vera License "
    "(Hack) and the licences of the Nerd Fonts glyph sets. See NOTICE.md."
)
LICENSE_URL = "https://openfontlicense.org"
HOMEPAGE = "https://github.com/jim60105/font"

DROP_TABLES = ("PfEd", "DSIG", "TTFA", "hdmx", "LTSH", "VDMX", "prop")
# style -> (usWeightClass, fsSelection style bits, head.macStyle)
STYLES = {
    "Regular": (400, 1 << 6, 0),
    "Bold": (700, 1 << 5, 1),
    "Italic": (400, 1 << 0, 2),
    "Bold Italic": (700, (1 << 5) | (1 << 0), 3),
}
FS_SELECTION_STYLE_MASK = (1 << 0) | (1 << 5) | (1 << 6)
FS_SELECTION_USE_TYPO_METRICS = 1 << 7
CODEPAGE_950_TRADITIONAL_CHINESE = 1 << 20  # bit 20 of ulCodePageRange1


def set_names(font, family, style, version, sources):
    ps_name = f"{family.replace(' ', '')}-{style.replace(' ', '')}"
    full = f"{family} {style}".strip()
    unique = f"{version};{ps_name}"
    records = {
        0: COPYRIGHT,
        1: family,
        2: style,
        3: unique,
        4: full,
        5: f"Version {version}; {sources}",
        6: ps_name,
        11: HOMEPAGE,
        13: LICENSE_DESCRIPTION,
        14: LICENSE_URL,
    }
    name = font["name"]
    name.names = []
    for name_id, text in sorted(records.items()):
        name.setName(text, name_id, 3, 1, 0x409)
    return ps_name


def finish_cff(font, family, style, ps_name, version, subroutinize):
    cff = font["CFF "].cff
    cff.fontNames = [ps_name]
    top = cff.topDictIndex[0]
    top.FullName = f"{family} {style}".strip()
    top.FamilyName = family
    top.Weight = style
    top.version = version
    top.Notice = COPYRIGHT
    if subroutinize:
        import compreffor

        compreffor.compress(font)


def drop_empty_layout_tables(font):
    for tag in ("GPOS", "GSUB"):
        if tag in font:
            table = font[tag].table
            if not table.FeatureList or not table.FeatureList.FeatureRecord:
                del font[tag]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--family", default="Jim Mono TC")
    ap.add_argument("--style", default="Regular", choices=sorted(STYLES))
    ap.add_argument("--version", default="0.1.0", help="major.minor.patch")
    ap.add_argument("--sources", default="", help="upstream version summary for the version string")
    ap.add_argument("--subroutinize", action="store_true", help="CFF only: compress charstrings with compreffor (slow)")
    args = ap.parse_args()

    font = TTFont(args.input)
    cmap = font.getBestCmap()
    cell = font["hmtx"][cmap[ord("A")]][0]

    for tag in DROP_TABLES:
        if tag in font:
            del font[tag]
    drop_empty_layout_tables(font)

    ps_name = set_names(font, args.family, args.style, args.version, args.sources)

    major, minor, *_ = (int(p) for p in args.version.split("."))
    font["head"].fontRevision = major + minor / 1000
    weight, fs_style, mac_style = STYLES[args.style]
    font["head"].macStyle = mac_style

    os2 = font["OS/2"]
    os2.fsType = 0
    os2.usWeightClass = weight
    os2.fsSelection = (os2.fsSelection & ~FS_SELECTION_STYLE_MASK) | fs_style
    os2.achVendID = "NONE"
    os2.xAvgCharWidth = cell  # terminals derive the cell width from this / from "0"
    os2.panose.bProportion = 9  # monospaced
    os2.fsSelection |= FS_SELECTION_USE_TYPO_METRICS
    os2.ulCodePageRange1 |= CODEPAGE_950_TRADITIONAL_CHINESE
    hhea = font["hhea"]
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = hhea.ascent, hhea.descent, hhea.lineGap
    os2.usWinAscent, os2.usWinDescent = hhea.ascent, -hhea.descent
    os2.recalcUnicodeRanges(font)

    font["post"].isFixedPitch = 1
    if not mac_style & 2:
        font["post"].italicAngle = 0.0
    if "CFF " in font:
        finish_cff(font, args.family, args.style, ps_name, args.version, args.subroutinize)

    font.save(args.output)
    print(f"finalized {ps_name}: {len(font.getGlyphOrder())} glyphs, W={cell} -> {args.output}")


if __name__ == "__main__":
    sys.exit(main())
