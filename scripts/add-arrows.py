#!/usr/bin/env python3
"""Add the Unicode arrows Cascadia lacks, drawn from Noto Sans CJK and matched to Cascadia.

Cascadia Code has only the basic arrows (← ↑ → ↓ ↔ ↕ …).  The other arrows of the arrow
blocks that Noto Sans CJK has (↖ ⇒ ⇄ ⤴ ⬅ …) are added as one-cell glyphs: they are East
Asian Ambiguous / Neutral, so a terminal gives them one cell.

Noto draws them full-width, so fitting one into a cell shrinks its strokes to well under
Cascadia's.  To keep the look of Cascadia's own arrows each glyph is

  * scaled uniformly into the box of Cascadia's arrows (the width of "→", the height of "↕"),
    centred in the cell on the axis of "→",
  * emboldened (outline offset, mitred joins) until its shaft is as thick as the shaft of
    Cascadia's "→" in the same style, so Bold arrows are bolder,
  * slanted by the style's italic angle, as Cascadia's own arrows are in the italics.

Take the heaviest Noto weight (Black) as the source: it needs the least offset.
"""

import argparse
import math
import sys

import pathops
import unicodedata2 as ud
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

ARROW_BLOCKS = [(0x2190, 0x21FF), (0x27F0, 0x27FF), (0x2900, 0x297F), (0x2B00, 0x2BFF), (0x1F800, 0x1F8FF)]
CURVE_ERROR = 0.5
MITER_LIMIT = 4


def arrow_codepoints(base_cmap, noto_cmap):
    out = []
    for lo, hi in ARROW_BLOCKS:
        for cp in range(lo, hi + 1):
            ch = chr(cp)
            if (
                "ARROW" in ud.name(ch, "")
                and ud.east_asian_width(ch) not in ("W", "F")
                and cp in noto_cmap
                and cp not in base_cmap
            ):
                out.append(cp)
    return out


def skia_path(glyph_set, name, matrix=(1, 0, 0, 1, 0, 0)):
    path = pathops.Path()
    glyph_set[name].draw(TransformPen(path.getPen(glyphSet=glyph_set), matrix))
    path.simplify()  # resolve overlaps / winding once, so later operations are well defined
    return path


def thickness_at(path, x):
    """Vertical extent of the ink crossing a thin vertical slit at x (= shaft of a horizontal arrow)."""
    slit = pathops.Path()
    x0, y0, x1, y1 = path.bounds
    pen = slit.getPen()
    pen.moveTo((x - 1, y0 - 1))
    pen.lineTo((x + 1, y0 - 1))
    pen.lineTo((x + 1, y1 + 1))
    pen.lineTo((x - 1, y1 + 1))
    pen.closePath()
    cut = pathops.op(path, slit, pathops.PathOp.INTERSECTION)
    if not cut.bounds or cut.bounds == (0, 0, 0, 0):
        raise SystemExit(f"no ink at x={x}")
    return cut.bounds[3] - cut.bounds[1]


def embolden(path, delta):
    if delta <= 0:
        return path
    outline = pathops.Path()
    outline.addPath(path)
    outline.stroke(2 * delta, pathops.LineCap.BUTT_CAP, pathops.LineJoin.MITER_JOIN, MITER_LIMIT)
    return pathops.op(path, outline, pathops.PathOp.UNION)


def tt_glyph(path):
    area = AreaPen()
    path.draw(area)
    pen = TTGlyphPen(None)
    target = Cu2QuPen(pen, CURVE_ERROR)
    # TrueType outer contours run clockwise (negative area in fontTools' convention).
    path.draw(ReverseContourPen(target) if area.value > 0 else target)
    return pen.glyph(dropImpliedOnCurves=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", help="TTF from prepare-base.py")
    ap.add_argument("noto", help="Noto Sans CJK OTF to draw the arrows from (Black)")
    ap.add_argument("output")
    args = ap.parse_args()

    font = TTFont(args.base)
    noto = TTFont(args.noto, lazy=True)
    cmap, noto_cmap = font.getBestCmap(), noto.getBestCmap()
    glyph_set, noto_set = font.getGlyphSet(), noto.getGlyphSet()
    cell = font["hmtx"][cmap[ord("A")]][0]

    # Cascadia's arrows: box, axis and shaft.
    right = skia_path(glyph_set, cmap[0x2192])
    rx0, ry0, rx1, ry1 = right.bounds
    box_w = rx1 - rx0
    box_h = skia_path(glyph_set, cmap[0x2195]).bounds[3] - skia_path(glyph_set, cmap[0x2195]).bounds[1]
    axis = (ry0 + ry1) / 2
    stroke = thickness_at(right, rx0 + 0.3 * box_w)
    # Noto's: shaft of its "←", per unit of scale.
    left = skia_path(noto_set, noto_cmap[0x2190])
    lx0, _, lx1, _ = left.bounds
    noto_stroke = thickness_at(left, lx0 + 0.6 * (lx1 - lx0))

    shear = math.tan(math.radians(-font["post"].italicAngle))
    codepoints = arrow_codepoints(cmap, noto_cmap)
    glyf, hmtx = font["glyf"], font["hmtx"]
    order = font.getGlyphOrder()
    mapping = {}
    for cp in codepoints:
        src = skia_path(noto_set, noto_cmap[cp])
        x0, y0, x1, y1 = src.bounds
        delta = 0.0
        for _ in range(4):  # the offset grows the ink: leave room for it, then re-measure
            scale = min((box_w - 2 * delta) / (x1 - x0), (box_h - 2 * delta) / (y1 - y0))
            delta = max(0.0, (stroke - noto_stroke * scale) / 2)
        dx = cell / 2 - (x0 + x1) / 2 * scale
        dy = axis - (y0 + y1) / 2 * scale
        path = skia_path(noto_set, noto_cmap[cp], (scale, 0, 0, scale, dx, dy))
        path = embolden(path, delta)
        if shear:
            path.transform(1, 0, shear, 1, -shear * axis, 0)
        name = f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}"
        while name in glyf.glyphs:
            name += ".noto"
        glyph = tt_glyph(path)
        glyf.glyphs[name] = glyph
        glyph.recalcBounds(glyf)
        hmtx.metrics[name] = (cell, getattr(glyph, "xMin", 0))
        order.append(name)
        mapping[cp] = name

    font.setGlyphOrder(order)
    glyf.glyphOrder = order
    for table in font["cmap"].tables:
        if table.isUnicode() and table.format in (4, 12):
            for cp, name in mapping.items():
                if table.format == 12 or cp <= 0xFFFF:
                    table.cmap[cp] = name
    font.save(args.output)
    added = "".join(chr(cp) for cp in mapping)
    print(f"added {len(mapping)} arrows from Noto ({added}); stroke {stroke:.0f} (Noto {noto_stroke:.0f}/unit scale) -> {args.output}")


if __name__ == "__main__":
    sys.exit(main())
