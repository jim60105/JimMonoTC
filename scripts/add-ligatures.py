#!/usr/bin/env python3
"""Add programming ligatures to Hack as a `calt` feature.

The ligature outlines are drawn here from Hack's own `=`, `>` geometry, so no
third-party ligature glyphs (e.g. Fira Code) are involved.

Every ligature keeps one glyph per source character, each `W` wide:

    =>  ->  [lig.spacer (empty, W)] [equal_greater.liga (W, outline spans 2W)]

The outline lives in the *last* cell and reaches back into the previous cells
with negative x coordinates.  Total advance therefore stays N * W both with
and without shaping, which is what cell-based terminals need.
"""

import argparse
import sys

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables

SPACER = "lig.spacer"

# ---------------------------------------------------------------------------
# geometry helpers (all coordinates are font units, y up)
# ---------------------------------------------------------------------------


def signed_area(poly):
    return sum(
        x0 * y1 - x1 * y0
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1])
    ) / 2


def clockwise(poly):
    """TrueType outer contours are clockwise."""
    return poly[::-1] if signed_area(poly) > 0 else poly


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]


def shift(poly, dx=0, dy=0):
    return [(x + dx, y + dy) for x, y in poly]


def mirror_x(poly, axis):
    return [(2 * axis - x, y) for x, y in poly]


def clip_left(poly, xc):
    """Sutherland-Hodgman: keep the part of `poly` with x >= xc."""
    out = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        in0, in1 = x0 >= xc, x1 >= xc
        if in0 != in1:
            t = (xc - x0) / (x1 - x0)
            out.append((xc, y0 + t * (y1 - y0)))
        if in1:
            out.append((x1, y1))
    return out


def polygons(font, codepoint):
    """Outline of a simple, straight-edged glyph as a list of polygons."""
    name = font.getBestCmap()[codepoint]
    pen = RecordingPen()
    font.getGlyphSet()[name].draw(pen)
    polys, cur = [], []
    for op, args in pen.value:
        if op in ("moveTo", "lineTo"):
            cur.append(args[0])
        elif op == "closePath":
            polys.append(cur)
            cur = []
        else:
            raise SystemExit(f"U+{codepoint:04X} has curves; geometry helpers expect lines")
    return polys


class Geometry:
    """Measurements taken from Hack so the ligatures match its weight."""

    HEAD_CUT = 300  # arrow head starts this far right of the chevron's open end

    def __init__(self, font):
        cmap = font.getBestCmap()
        self.width = font["hmtx"][cmap[ord("=")]][0]

        bars = sorted(polygons(font, ord("=")), key=lambda p: min(y for _, y in p))
        self.bar_lo = (min(y for _, y in bars[0]), max(y for _, y in bars[0]))
        self.bar_hi = (min(y for _, y in bars[1]), max(y for _, y in bars[1]))
        self.xmin = min(x for p in bars for x, _ in p)
        self.xmax = max(x for p in bars for x, _ in p)
        self.mid_y = (self.bar_lo[0] + self.bar_hi[1]) / 2

        (chevron,) = polygons(font, ord(">"))
        tip = sorted(y for x, y in chevron if x == self.xmax)
        self.tip_y = (tip[0], tip[-1])  # flat end of the chevron tip
        self.head = clockwise(clip_left(chevron, self.xmin + self.HEAD_CUT))
        self.head_left = clockwise(mirror_x(self.head, (self.xmin + self.xmax) / 2))

        # Chevron arms fully cover a `=` bar end at this x (see =>).
        self.bar_join_x = 620

    def left(self, n):
        """x of the leftmost ink for an n-cell ligature (last-cell frame)."""
        return self.xmin - (n - 1) * self.width

    def bars(self, n, y_ranges=None, x1=None):
        y_ranges = y_ranges or [self.bar_lo, self.bar_hi]
        return [rect(self.left(n), y0, x1 or self.xmax, y1) for y0, y1 in y_ranges]

    def three_bars(self, n):
        t, span = 140, 682
        centre = self.mid_y
        lo, hi = centre - span / 2, centre + span / 2
        mid = centre - t / 2
        return self.bars(n, [(lo, lo + t), (mid, mid + t), (hi - t, hi)])

    def slash(self, n):
        """A '/' crossing the bars, centred on the whole ligature."""
        cx = (self.left(n) + self.xmax) / 2
        y0, y1, dx, w = 150, 1130, 170, 170
        return [(cx - dx - w / 2, y0), (cx + dx - w / 2, y1), (cx + dx + w / 2, y1), (cx - dx + w / 2, y0)]


def build_eq2(g):
    return g.bars(2)


def build_eq3(g):
    return g.three_bars(3)


def build_ne2(g):
    return g.bars(2) + [g.slash(2)]


def build_ne3(g):
    return g.three_bars(3) + [g.slash(3)]


def build_arrow_r(g):
    return [g.head, rect(g.left(2), g.tip_y[0], g.xmax, g.tip_y[1])]


def build_arrow_l(g):
    head = shift(g.head_left, -g.width)
    return [head, rect(g.left(2), g.tip_y[0], g.xmax, g.tip_y[1])]


def build_fat_arrow(g):
    return [g.head] + g.bars(2, x1=g.bar_join_x)


# (source text, outline builder).  Longer sequences first: first match wins.
LIGATURES = [
    ("===", build_eq3),
    ("!==", build_ne3),
    ("==", build_eq2),
    ("!=", build_ne2),
    ("->", build_arrow_r),
    ("<-", build_arrow_l),
    ("=>", build_fat_arrow),
]

# ---------------------------------------------------------------------------
# glyph + feature construction
# ---------------------------------------------------------------------------


def make_glyph(polys):
    pen = TTGlyphPen(None)
    for poly in polys:
        pts = [(round(x), round(y)) for x, y in clockwise(poly)]
        pen.moveTo(pts[0])
        for p in pts[1:]:
            pen.lineTo(p)
        pen.closePath()
    return pen.glyph()


def add_glyph(font, name, glyph, advance):
    order = font.getGlyphOrder()
    if name in order:
        raise SystemExit(f"glyph {name} already exists")
    order.append(name)
    font.setGlyphOrder(order)
    glyf = font["glyf"]
    glyf.glyphOrder = order
    glyf.glyphs[name] = glyph
    glyph.recalcBounds(glyf)
    font["hmtx"].metrics[name] = (advance, getattr(glyph, "xMin", 0))


def glyph_names(font, text):
    cmap = font.getBestCmap()
    missing = [c for c in text if ord(c) not in cmap]
    if missing:
        raise SystemExit(f"font lacks glyphs for {missing!r}")
    return [cmap[ord(c)] for c in text]


def build_feature_code(font, specs):
    """specs: list of (source glyph names, ligature glyph name)."""
    first_cells = sorted({n for names, _ in specs for n in names[:-1]})
    lines = [
        "languagesystem DFLT dflt;",
        "languagesystem latn dflt;",
        "",
        f"lookup LIG_SPACER {{ sub [{' '.join(first_cells)}] by {SPACER}; }} LIG_SPACER;",
    ]
    for i, (names, lig) in enumerate(specs):
        lines.append(f"lookup LIG_{i} {{ sub {names[-1]} by {lig}; }} LIG_{i};")
    lines += ["", "feature calt {"]
    for i, (names, _) in enumerate(specs):
        parts = [f"{n}' lookup LIG_SPACER" for n in names[:-1]] + [f"{names[-1]}' lookup LIG_{i}"]
        lines.append("    sub " + " ".join(parts) + ";")
    lines += ["} calt;", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GSUB merge: keep Hack's existing lookups/features, add the new ones
# ---------------------------------------------------------------------------


def _shift_lookup_refs(obj, offset, seen=None):
    seen = seen if seen is not None else set()
    if id(obj) in seen:
        return
    seen.add(id(obj))
    if isinstance(obj, otTables.SubstLookupRecord):
        obj.LookupListIndex += offset
        return
    if isinstance(obj, list):
        for item in obj:
            _shift_lookup_refs(item, offset, seen)
    elif hasattr(obj, "__dict__"):
        for value in vars(obj).values():
            if isinstance(value, (list, otTables.BaseTable)):
                _shift_lookup_refs(value, offset, seen)


def merge_gsub(font, scratch):
    """Append the lookups/features of `scratch`'s GSUB to `font`'s GSUB."""
    new = scratch["GSUB"].table
    if "GSUB" not in font:
        font["GSUB"] = scratch["GSUB"]
        return
    old = font["GSUB"].table

    offset = len(old.LookupList.Lookup)
    for lookup in new.LookupList.Lookup:
        _shift_lookup_refs(lookup.SubTable, offset)
    old.LookupList.Lookup.extend(new.LookupList.Lookup)
    old.LookupList.LookupCount = len(old.LookupList.Lookup)

    # New features join every existing script/language system so that the CJK
    # (hani), latn and DFLT runs all receive them.
    records = list(old.FeatureList.FeatureRecord)
    added = []
    for rec in new.FeatureList.FeatureRecord:
        feature = otTables.Feature()
        feature.FeatureParams = None
        feature.LookupListIndex = [i + offset for i in rec.Feature.LookupListIndex]
        feature.LookupCount = len(feature.LookupListIndex)
        added_rec = otTables.FeatureRecord()
        added_rec.FeatureTag = rec.FeatureTag
        added_rec.Feature = feature
        added.append(added_rec)

    # FeatureList must stay sorted by tag; remap indices held by LangSys.
    combined = [(r.FeatureTag, 0, i, r) for i, r in enumerate(records)] + [
        (r.FeatureTag, 1, i, r) for i, r in enumerate(added)
    ]
    combined.sort(key=lambda t: (t[0], t[1], t[2]))
    index_of = {id(t[3]): n for n, t in enumerate(combined)}
    old_index = {i: index_of[id(r)] for i, r in enumerate(records)}
    new_indexes = [index_of[id(r)] for r in added]

    old.FeatureList.FeatureRecord = [t[3] for t in combined]
    old.FeatureList.FeatureCount = len(combined)

    langsyses = []
    for script in old.ScriptList.ScriptRecord:
        if script.Script.DefaultLangSys:
            langsyses.append(script.Script.DefaultLangSys)
        langsyses.extend(l.LangSys for l in script.Script.LangSysRecord)
    for ls in langsyses:
        ls.FeatureIndex = sorted(old_index[i] for i in ls.FeatureIndex) + new_indexes
        ls.FeatureIndex.sort()
        ls.FeatureCount = len(ls.FeatureIndex)
        if ls.ReqFeatureIndex != 0xFFFF:
            ls.ReqFeatureIndex = old_index[ls.ReqFeatureIndex]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="Hack TTF")
    ap.add_argument("output", help="TTF with calt ligatures")
    args = ap.parse_args()

    font = TTFont(args.input)
    geo = Geometry(font)
    width = geo.width

    add_glyph(font, SPACER, TTGlyphPen(None).glyph(), width)

    specs = []
    for text, builder in LIGATURES:
        names = glyph_names(font, text)
        lig_name = "_".join(names) + ".liga"
        add_glyph(font, lig_name, make_glyph(builder(geo)), width)
        specs.append((names, lig_name))

    scratch = TTFont()
    scratch.setGlyphOrder(font.getGlyphOrder())
    addOpenTypeFeaturesFromString(scratch, build_feature_code(font, specs), tables=["GSUB"])
    merge_gsub(font, scratch)

    font.save(args.output)
    print(f"added {len(LIGATURES)} ligatures ({', '.join(t for t, _ in LIGATURES)}) -> {args.output}")


if __name__ == "__main__":
    sys.exit(main())
