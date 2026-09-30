#!/usr/bin/env python3
"""Merge Noto Sans CJK TC into the (ligature + Nerd Font) Hack build.

* Only full-width characters (East Asian Width W/F) that the base font lacks are
  added, so Latin / Nerd Font / box-drawing glyphs always come from Hack.
* Noto's outlines are scaled to the base UPM and centred in a cell exactly 2 * W
  wide (W = Hack's half-width advance).
* --format otf (default) writes an OpenType/CFF font: Noto's cubic curves are
  copied as they are and Hack / Nerd Fonts quadratics are raised to cubics
  (exact), so no curve is approximated.  --format ttf converts Noto to
  quadratics (Cu2Qu) and keeps Hack's TrueType hinting.
* Noto has no italic.  When the reference Hack is italic (post.italicAngle != 0) the CJK
  glyphs are slanted by the same angle, about the middle of the line, which keeps their
  ink inside the 2W cell.
* Glyphs that Hack defines with zero advance (combining marks) get that back;
  the Nerd Fonts patcher widens them to W, which misplaces them when shaped.
"""

import argparse
import math
import sys
import unicodedata

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

# Extra blocks always requested on top of the Big5 repertoire.
EXTRA_RANGES = [
    (0x3000, 0x303F),  # CJK symbols and punctuation
    (0x3040, 0x309F),  # Hiragana
    (0x30A0, 0x30FF),  # Katakana
    (0x3100, 0x312F),  # Bopomofo
    (0x31A0, 0x31BF),  # Bopomofo extended
    (0xFF01, 0xFF60),  # Fullwidth ASCII variants
    (0xFFE0, 0xFFE6),  # Fullwidth signs
]

# Big5 lead bytes: A1-A3 symbols, A4-C6 frequently used hanzi (5401),
# C9-F9 less frequently used hanzi (7652).
BIG5_LEADS = {
    "big5-common": range(0xA1, 0xC7),
    "big5": range(0xA1, 0xFA),
}


def big5_characters(leads):
    trails = list(range(0x40, 0x7F)) + list(range(0xA1, 0xFF))
    chars = set()
    for lead in leads:
        for trail in trails:
            try:
                chars.add(ord(bytes([lead, trail]).decode("big5")))
            except UnicodeDecodeError:
                pass
    return chars


def read_charset_file(path):
    """Plain text; every non-comment character (or U+XXXX / U+XXXX-YYYY token) counts."""
    cps = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            for token in line.split():
                if token.upper().startswith("U+"):
                    lo, _, hi = token[2:].partition("-")
                    cps.update(range(int(lo, 16), int(hi or lo, 16) + 1))
                else:
                    cps.update(ord(c) for c in token)
    return cps


def is_wide(cp):
    return unicodedata.east_asian_width(chr(cp)) in ("W", "F")


def select_codepoints(charset, base_cmap, cjk_cmap):
    if charset == "all":
        wanted = set(cjk_cmap)
    elif charset in BIG5_LEADS:
        wanted = big5_characters(BIG5_LEADS[charset])
    else:
        wanted = read_charset_file(charset)
    for lo, hi in EXTRA_RANGES:
        wanted.update(range(lo, hi + 1))
    # Combining marks (e.g. U+302A, U+3099) are zero-advance by nature: skip them.
    return sorted(
        cp
        for cp in wanted
        if is_wide(cp)
        and not unicodedata.category(chr(cp)).startswith("M")
        and cp in cjk_cmap
        and cp not in base_cmap
    )


def glyph_name_for(cp, taken):
    name = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}"
    while name in taken:
        name += ".cjk"
    return name


def convert_glyph(glyph_set, src_name, matrix, max_err):
    pen = TTGlyphPen(None)
    glyph_set[src_name].draw(TransformPen(Cu2QuPen(pen, max_err, reverse_direction=True), matrix))
    return pen.glyph(dropImpliedOnCurves=True)


def keep_in_cell(glyph_set, src_name, matrix, wide):
    """Slanting can push ink of glyphs that fill their cell (e.g. U+FFE3) past 0..2W: slide it back."""
    bounds = BoundsPen(None)
    glyph_set[src_name].draw(TransformPen(bounds, matrix))
    if not bounds.bounds:
        return matrix
    x0, _, x1, _ = bounds.bounds
    fix = -x1 + wide if x1 > wide else (-x0 if x0 < 0 else 0)
    return matrix[:4] + (matrix[4] + fix, matrix[5])


def restore_zero_width(font, reference):
    """Give back advance 0 to glyphs that Hack itself defines with zero advance."""
    cmap, ref_cmap = font.getBestCmap(), reference.getBestCmap()
    hmtx, ref_hmtx = font["hmtx"], reference["hmtx"]
    fixed = 0
    for cp, name in cmap.items():
        ref_name = ref_cmap.get(cp)
        if ref_name and ref_hmtx[ref_name][0] == 0 and hmtx[name][0] != 0:
            hmtx.metrics[name] = (0, hmtx[name][1])
            fixed += 1
    return fixed


def drop_wide_conflicts(font, cell):
    """Unmap East Asian Wide code points whose glyph is not 2W wide.

    Terminals allot two cells to these (mostly emoji, e.g. U+26A1); a one-cell
    glyph would misalign the line, so let the system emoji font handle them.
    """
    hmtx = font["hmtx"]
    dropped = []
    for table in font["cmap"].tables:
        if not table.isUnicode():
            continue
        for cp in [c for c, n in table.cmap.items() if is_wide(c) and hmtx[n][0] != 2 * cell]:
            del table.cmap[cp]
            dropped.append(cp)
    return sorted(set(dropped))


def add_to_cmap(font, mapping):
    for table in font["cmap"].tables:
        if not table.isUnicode():
            continue
        for cp, name in mapping.items():
            if table.format == 4 and cp > 0xFFFF:
                continue
            if table.format in (4, 12):
                table.cmap[cp] = name


def charstring(recording, width, cell, wide):
    """Type 2 charstring; the width is stored relative to nominalWidthX (= 2W), omitted for W."""
    pen = T2CharStringPen(None if width == cell else width - wide, None)
    recording.replay(pen)
    return pen.getCharString()


def convert_base_to_cff(font, order, cell, wide):
    """Charstrings for every glyph already in the base TrueType font (quadratic -> cubic)."""
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"]
    strings = {}
    for name in order:
        flat = DecomposingRecordingPen(glyph_set)
        glyph_set[name].draw(flat)
        reversed_ = RecordingPen()  # TrueType outer contours run clockwise, CFF's counter-clockwise
        flat.replay(ReverseContourPen(reversed_))
        strings[name] = charstring(reversed_, hmtx[name][0], cell, wide)
    return strings


def install_cff(font, order, strings, cell, wide):
    for tag in ("glyf", "loca", "fpgm", "prep", "cvt "):
        if tag in font:
            del font[tag]
    font.setGlyphOrder(order)
    builder = FontBuilder(font=font)  # no glyf any more -> CFF flavour
    builder.setupMaxp()
    builder.setupCFF(
        "JimMonoTC-Regular",
        {"FullName": "Jim Mono TC Regular", "FamilyName": "Jim Mono TC", "Weight": "Regular"},
        strings,
        {"defaultWidthX": cell, "nominalWidthX": wide, "BlueValues": []},
    )
    font["post"].formatType = 3.0  # names live in the CFF charset


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", help="Nerd-Font-patched Hack TTF")
    ap.add_argument("cjk", help="Noto Sans CJK TC OTF")
    ap.add_argument("output")
    ap.add_argument("--reference", required=True, help="original Hack TTF (source of zero-width glyphs)")
    ap.add_argument(
        "--charset",
        default="all",
        help="all (default: every wide code point Noto has), big5-common, big5, "
        "or a text file of characters / U+XXXX[-YYYY] tokens",
    )
    ap.add_argument("--format", choices=("otf", "ttf"), default="otf", help="outline format (default otf = CFF)")
    ap.add_argument("--cjk-scale", type=float, default=1.0, help="size of CJK ink relative to the em (default 1.0)")
    ap.add_argument("--max-error", type=float, default=1.0, help="ttf only: cubic->quadratic tolerance in font units")
    args = ap.parse_args()

    font = TTFont(args.base)
    reference = TTFont(args.reference)
    cjk = TTFont(args.cjk, lazy=True)

    upm = font["head"].unitsPerEm
    cell = font["hmtx"][font.getBestCmap()[ord("A")]][0]  # W
    wide = 2 * cell

    base_cmap = font.getBestCmap()
    cjk_cmap = cjk.getBestCmap()
    codepoints = select_codepoints(args.charset, base_cmap, cjk_cmap)
    if not codepoints:
        raise SystemExit("no CJK codepoints selected")

    scale = upm / cjk["head"].unitsPerEm * args.cjk_scale
    shear = math.tan(math.radians(-reference["post"].italicAngle))  # italicAngle is negative for a right slant
    pivot = (font["hhea"].ascent + font["hhea"].descent) / 2
    glyph_set = cjk.getGlyphSet()
    cjk_hmtx = cjk["hmtx"]
    is_cff = args.format == "otf"

    order = font.getGlyphOrder()
    strings = convert_base_to_cff(font, list(order), cell, wide) if is_cff else None
    taken = set(order)
    glyf, hmtx = font["glyf"], font["hmtx"]
    new_names = {}  # noto glyph name -> our glyph name
    mapping = {}
    # Glyphs shared by several code points are named after the most ordinary one:
    # unified ideographs before Kangxi / CJK radicals and compatibility ideographs.
    def naming_rank(cp):
        return (0x2E80 <= cp <= 0x2FDF or 0xF900 <= cp <= 0xFAFF or 0x2F800 <= cp <= 0x2FA1F, cp)

    for cp in sorted(codepoints, key=naming_rank):
        src = cjk_cmap[cp]
        if src not in new_names:
            name = glyph_name_for(cp, taken)
            taken.add(name)
            new_names[src] = name
            src_advance = cjk_hmtx[src][0]
            # centre the scaled source cell inside the 2W cell
            dx = (wide - src_advance * scale) / 2
            # x' = scale*x + shear*(y' - pivot) + dx,  y' = scale*y
            matrix = (scale, 0, shear * scale, scale, dx - shear * pivot, 0)
            if shear:
                matrix = keep_in_cell(glyph_set, src, matrix, wide)
            order.append(name)
            if is_cff:
                rec = RecordingPen()
                glyph_set[src].draw(TransformPen(rec, matrix))
                bounds = BoundsPen(None)
                rec.replay(bounds)
                strings[name] = charstring(rec, wide, cell, wide)
                hmtx.metrics[name] = (wide, round(bounds.bounds[0]) if bounds.bounds else 0)
            else:
                glyph = convert_glyph(glyph_set, src, matrix, args.max_error)
                glyf.glyphs[name] = glyph
                glyph.recalcBounds(glyf)
                hmtx.metrics[name] = (wide, getattr(glyph, "xMin", 0))
        mapping[cp] = new_names[src]

    if is_cff:
        install_cff(font, order, strings, cell, wide)
    else:
        font.setGlyphOrder(order)
        glyf.glyphOrder = order
    add_to_cmap(font, mapping)

    restored = restore_zero_width(font, reference)
    dropped = drop_wide_conflicts(font, cell)
    if dropped:
        print("unmapped 1-cell glyphs at wide code points: " + " ".join(f"U+{cp:04X}" for cp in dropped))
    font.save(args.output)
    print(
        f"merged {len(mapping)} codepoints / {len(new_names)} glyphs as {args.format} "
        f"(W={cell}, 2W={wide}, scale={scale:.4f}, slant={math.degrees(math.atan(shear)):.1f} deg); restored {restored} zero-width glyphs -> {args.output}"
    )


if __name__ == "__main__":
    sys.exit(main())
