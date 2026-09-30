#!/usr/bin/env python3
"""Merge Noto Sans CJK TC into the (ligature + Nerd Font) Hack build.

* Only full-width characters (East Asian Width W/F) that the base font lacks are
  added, so Latin / Nerd Font / box-drawing glyphs always come from Hack.
* CFF outlines are converted to TrueType quadratics, scaled to the base UPM and
  centred in a cell exactly 2 * W wide (W = Hack's half-width advance).
* Glyphs that Hack defines with zero advance (combining marks) get that back;
  the Nerd Fonts patcher widens them to W, which misplaces them when shaped.
"""

import argparse
import sys
import unicodedata

from fontTools.pens.cu2quPen import Cu2QuPen
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
    if charset in BIG5_LEADS:
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", help="Nerd-Font-patched Hack TTF")
    ap.add_argument("cjk", help="Noto Sans CJK TC OTF")
    ap.add_argument("output")
    ap.add_argument("--reference", required=True, help="original Hack TTF (source of zero-width glyphs)")
    ap.add_argument(
        "--charset",
        default="big5-common",
        help="big5-common (default), big5, or a text file of characters / U+XXXX[-YYYY] tokens",
    )
    ap.add_argument("--cjk-scale", type=float, default=1.0, help="size of CJK ink relative to the em (default 1.0)")
    ap.add_argument("--max-error", type=float, default=1.0, help="cubic->quadratic tolerance in font units")
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
    glyph_set = cjk.getGlyphSet()
    cjk_hmtx = cjk["hmtx"]

    order = font.getGlyphOrder()
    taken = set(order)
    glyf, hmtx = font["glyf"], font["hmtx"]
    new_names = {}  # noto glyph name -> our glyph name
    mapping = {}
    for cp in codepoints:
        src = cjk_cmap[cp]
        if src not in new_names:
            name = glyph_name_for(cp, taken)
            taken.add(name)
            new_names[src] = name
            src_advance = cjk_hmtx[src][0]
            # centre the scaled source cell inside the 2W cell
            dx = (wide - src_advance * scale) / 2
            glyph = convert_glyph(glyph_set, src, (scale, 0, 0, scale, dx, 0), args.max_error)
            order.append(name)
            glyf.glyphs[name] = glyph
            glyph.recalcBounds(glyf)
            hmtx.metrics[name] = (wide, getattr(glyph, "xMin", 0))
        mapping[cp] = new_names[src]

    font.setGlyphOrder(order)
    glyf.glyphOrder = order
    add_to_cmap(font, mapping)

    restored = restore_zero_width(font, reference)
    dropped = drop_wide_conflicts(font, cell)
    if dropped:
        print("unmapped 1-cell glyphs at wide code points: " + " ".join(f"U+{cp:04X}" for cp in dropped))
    font.save(args.output)
    print(
        f"merged {len(mapping)} codepoints / {len(new_names)} glyphs "
        f"(W={cell}, 2W={wide}, scale={scale:.4f}); restored {restored} zero-width glyphs -> {args.output}"
    )


if __name__ == "__main__":
    sys.exit(main())
