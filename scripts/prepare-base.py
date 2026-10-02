#!/usr/bin/env python3
"""Prepare Cascadia Code NF as the base font: fit cell glyphs, complete the Nerd Font icons.

* Cell glyphs.  Cascadia draws its block elements, Symbols for Legacy Computing (and the
  Supplement) and the Powerline dividers for a cell as tall as its Windows metrics
  (usWinDescent .. usWinAscent = -480 .. 2226), while the line is hhea / typo
  (-480 .. 1900, USE_TYPO_METRICS).  Those glyphs are scaled vertically into the line so
  that they fill exactly one cell everywhere (finalize.py sets the Windows metrics to the
  line too).  Box drawing is left alone: it is centred on the line already and only
  overshoots it to join.
* Nerd Font icons.  Cascadia Code NF carries an older Nerd Fonts release.  The icons it
  lacks are added from the glyph sources of the pinned Nerd Fonts archive (the same sets
  as `font-patcher --complete`), scaled with Cascadia's own rule
  (cascadia-code/sources/nerdfonts/full/process.py: fit to the cell width minus a side
  bearing or to the cap height, centred on both), so they look like Cascadia's icons.
  Progress indicators (U+EE00-EE0B, Nerd Fonts' extraglyphs.sfd) are placed like
  font-patcher places them, so the bar pieces join.

Output is TrueType (glyf), like the input.
"""

import argparse
import re
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from nerd_sets import GLYPHS, patch_sets

# Blocks whose glyphs Cascadia draws relative to the Windows-metrics cell.
CELL_BLOCKS = [
    (0x2429, 0x2429),  # symbol for delete, medium shade form
    (0x2580, 0x259F),  # block elements
    (0xE0A0, 0xE0D7),  # Powerline (+ extra)
    (0x1CC00, 0x1CEBF),  # symbols for legacy computing supplement
    (0x1FB00, 0x1FBFF),  # symbols for legacy computing
]
SIDE_BEARING = 20  # process.py
CURVE_ERROR = 0.5  # cubic -> quadratic tolerance, font units
PROGRESS = range(0xEE00, 0xEE0C)
POWERLINE_OVERLAP = 100  # Cascadia's dividers reach this far past the cell edge they point to


def in_blocks(cp):
    return any(lo <= cp <= hi for lo, hi in CELL_BLOCKS)


def tt_glyph(draw, matrix, cubic):
    """Draw (a callable taking a pen) through matrix into a new glyf glyph (no instructions)."""
    pen = TTGlyphPen(None)
    target = Cu2QuPen(pen, CURVE_ERROR, reverse_direction=True) if cubic else pen
    draw(TransformPen(target, matrix))
    return pen.glyph(dropImpliedOnCurves=True)


def bounds_of(draw):
    pen = BoundsPen(None)
    draw(pen)
    return pen.bounds


def fit_cell_glyphs(font):
    """Scale the Windows-cell glyphs of CELL_BLOCKS vertically into the hhea line."""
    hhea, os2 = font["hhea"], font["OS/2"]
    top, bottom = hhea.ascent, hhea.descent
    win_top, win_bottom = os2.usWinAscent, -os2.usWinDescent
    if (win_top, win_bottom) == (top, bottom):
        return 0
    scale = (top - bottom) / (win_top - win_bottom)
    matrix = (1, 0, 0, scale, 0, bottom - win_bottom * scale)
    glyph_set = font.getGlyphSet()
    names = sorted({n for cp, n in font.getBestCmap().items() if in_blocks(cp)})
    new = {}
    for name in names:
        rec = DecomposingRecordingPen(glyph_set)
        glyph_set[name].draw(rec)
        box = bounds_of(rec.replay)
        # Glyphs inside the line (Powerline branch / lock, segmented digits) are ordinary symbols.
        if not box or (box[3] <= top and box[1] > win_bottom):
            continue
        new[name] = tt_glyph(rec.replay, matrix, cubic=False)
    install(font, new)
    return len(new)


def install(font, glyphs, advance=None):
    glyf, hmtx = font["glyf"], font["hmtx"]
    order = font.getGlyphOrder()
    for name, glyph in glyphs.items():
        if name not in glyf.glyphs:
            order.append(name)
        glyf.glyphs[name] = glyph
        glyph.recalcBounds(glyf)
        width = advance if advance is not None else hmtx[name][0]
        hmtx.metrics[name] = (width, getattr(glyph, "xMin", 0))
    font.setGlyphOrder(order)
    glyf.glyphOrder = order


def add_to_cmap(font, mapping):
    for table in font["cmap"].tables:
        if not table.isUnicode() or table.format not in (4, 12):
            continue
        for cp, name in mapping.items():
            if table.format == 4 and cp > 0xFFFF:
                continue
            table.cmap[cp] = name


def glyph_name(cp, taken):
    name = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}"
    while name in taken:
        name += ".nf"
    return name


def process_matrix(box, upm, cell, cap):
    """Cascadia's process.py default rule as one matrix (the source is in its own UPM)."""
    s0 = 2048 / upm  # process.py first scales every source to UPM 2048
    x0, y0, x1, y1 = (v * s0 for v in box)
    width, height = x1 - x0, y1 - y0
    k = (cell - 2 * SIDE_BEARING) / width if (cell - 20) / width < cap / height else cap / height
    s = s0 * k
    return (s, 0, 0, s, (cell - width * k) / 2 - x0 * k, (cap - height * k) / 2 - y0 * k)


def stretch_matrix(box, target):
    """Map box onto target (x0, y0, x1, y1), independently in x and y."""
    x0, y0, x1, y1 = box
    t0, u0, t1, u1 = target
    sx, sy = (t1 - t0) / (x1 - x0), (u1 - u0) / (y1 - y0)
    return (sx, 0, 0, sy, t0 - x0 * sx, u0 - y0 * sy)


def read_sfd(path, codepoints):
    """Outlines of some glyphs of a FontForge .sfd (cubic SplineSets) as pen-drawing callables."""
    text = Path(path).read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"StartChar: .*?\nEncoding: \d+ (-?\d+) .*?\nEndChar", text, re.S):
        cp = int(m.group(1))
        if cp not in codepoints:
            continue
        body = re.search(r"SplineSet\n(.*?)EndSplineSet", m.group(0), re.S)
        contours, current = [], None
        for line in body.group(1).splitlines():
            parts = line.split()
            op, nums = parts[-2], [float(v) for v in parts[:-2]]
            if op == "m":
                current = [("m", nums)]
                contours.append(current)
            else:
                current.append((op, nums))

        def draw(pen, contours=contours):
            for contour in contours:
                for op, nums in contour:
                    pts = list(zip(nums[0::2], nums[1::2]))
                    if op == "m":
                        pen.moveTo(pts[0])
                    elif op == "l":
                        pen.lineTo(pts[0])
                    else:
                        pen.curveTo(*pts)
                pen.closePath()

        out[cp] = draw
    return out


def progress_glyphs(sfd, cell, top, bottom):
    """U+EE00-EE0B placed like font-patcher 3.4.0 does (its scale groups and overlaps)."""
    src = read_sfd(sfd, set(PROGRESS) | {0xEDFF})
    height, mid = top - bottom, (top + bottom) / 2
    out = {}
    # Boxes: the group EDFF-EE05 (EDFF only pads it vertically) spans the line + 0.5 % on
    # both sides; end pieces overlap their neighbour by 5 % of a cell, middle pieces by 5 % on both sides.
    gx0, gy0, gx1, gy1 = bounds_of(src[0xEDFF])
    sy = height * 1.01 / (gy1 - gy0)
    ty = mid - (gy0 + gy1) / 2 * sy
    for cp in range(0xEE00, 0xEE06):
        piece = (cp - 0xEE00) % 3  # 0 left end, 1 middle, 2 right end
        sx = cell * (1.10 if piece == 1 else 1.05) / (gx1 - gx0)
        tx = 0 if piece == 0 else -0.05 * cell
        out[cp] = (src[cp], (sx, 0, 0, sy, tx, ty))
    # Circles: one uniform scale for the group, 97 % of a cell wide, centred in the cell.
    boxes = [bounds_of(src[cp]) for cp in range(0xEE06, 0xEE0C)]
    gx0, gy0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    gx1, gy1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    s = min(cell * 0.97 / (gx1 - gx0), height * 0.97 / (gy1 - gy0))
    tx = cell / 2 - (gx0 + gx1) / 2 * s
    ty = mid - (gy0 + gy1) / 2 * s
    for cp in range(0xEE06, 0xEE0C):
        out[cp] = (src[cp], (s, 0, 0, s, tx, ty))
    return out


def add_nerd_icons(font, nerd_dir):
    cmap = font.getBestCmap()
    cell = font["hmtx"][cmap[ord("A")]][0]
    cap = font["OS/2"].sCapHeight
    top, bottom = font["hhea"].ascent, font["hhea"].descent
    taken = set(font.getGlyphOrder())
    glyphs_dir = Path(nerd_dir) / GLYPHS
    new, mapping, per_set = {}, {}, {}

    def add(cp, draw, matrix, cubic, label):
        name = glyph_name(cp, taken)
        taken.add(name)
        new[name] = tt_glyph(draw, matrix, cubic)
        mapping[cp] = name
        per_set[label] = per_set.get(label, 0) + 1

    sources = {}
    for row in patch_sets(Path(nerd_dir) / "font-patcher"):
        if row["enabled"] == "False" or row["file"].endswith(".sfd"):
            continue  # disabled set; extraglyphs.sfd: Cascadia has its own brackets / box drawing
        if row["file"] not in sources:
            sources[row["file"]] = TTFont(glyphs_dir / row["file"])
        src = sources[row["file"]]
        src_cmap, src_set = src.getBestCmap(), src.getGlyphSet()
        cubic = "CFF " in src
        upm = src["head"].unitsPerEm
        for cp in range(row["src_lo"], row["src_hi"] + 1):
            dest = row["lo"] + (cp - row["src_lo"])
            if cp not in src_cmap or dest in cmap or dest in mapping:
                continue
            draw = src_set[src_cmap[cp]].draw
            box = bounds_of(draw)
            if not box:
                continue
            if row["file"].startswith("powerline"):
                # Full-cell dividers, extending past the side they point to like Cascadia's own.
                right = dest % 2  # E0D6 points left, E0D7 right
                target = (0 if right else -POWERLINE_OVERLAP, bottom,
                          cell + POWERLINE_OVERLAP if right else cell, top)
                matrix = stretch_matrix(box, target)
            else:
                matrix = process_matrix(box, upm, cell, cap)
            add(dest, draw, matrix, cubic, row["name"])

    for cp, (draw, matrix) in progress_glyphs(glyphs_dir / "extraglyphs.sfd", cell, top, bottom).items():
        if cp not in cmap:
            add(cp, draw, matrix, True, "Progress Indicators")

    install(font, new, advance=cell)
    add_to_cmap(font, mapping)
    return per_set


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", help="Cascadia Code NF static TTF")
    ap.add_argument("output")
    ap.add_argument("--nerd-fonts", required=True, help="unpacked Nerd Fonts FontPatcher archive")
    args = ap.parse_args()

    font = TTFont(args.base)
    fitted = fit_cell_glyphs(font)
    per_set = add_nerd_icons(font, args.nerd_fonts)
    font.save(args.output)
    added = ", ".join(f"{name} {n}" for name, n in per_set.items())
    print(f"fitted {fitted} cell glyphs into the line; added {sum(per_set.values())} Nerd Font icons ({added}) -> {args.output}")


if __name__ == "__main__":
    sys.exit(main())
