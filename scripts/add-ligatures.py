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
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.pens.transformPen import TransformPen
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


def slice_x(poly, y):
    """Sorted x of the polygon edges crossing height y."""
    xs = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 - y) * (y1 - y) < 0:
            xs.append(x0 + (y - y0) / (y1 - y0) * (x1 - x0))
    return sorted(xs)


def stretch_y(poly, old0, old1, new0, new1):
    k = (new1 - new0) / (old1 - old0)
    return [(x, new0 + (y - old0) * k) for x, y in poly]


class Outline:
    """A copy of one of Hack's own glyph outlines (curves included), moved `dx` sideways
    (measured from the glyph's own origin, i.e. including its cell's offset)."""

    def __init__(self, codepoint, dx):
        self.codepoint, self.dx = codepoint, dx


class Geometry:
    """Measurements taken from Hack's `=`, `>`, so the ligatures match each weight.

    Hack Italic keeps these symbols upright, so the same geometry serves Italic.
    """

    HEAD_CUT = 300  # arrow head starts this far right of the chevron's open end

    def __init__(self, font):
        cmap = font.getBestCmap()
        self.cmap = cmap
        self.glyph_set = font.getGlyphSet()
        self._ink = {}
        self.width = font["hmtx"][cmap[ord("=")]][0]

        bars = sorted(polygons(font, ord("=")), key=lambda p: min(y for _, y in p))
        self.bar_lo = (min(y for _, y in bars[0]), max(y for _, y in bars[0]))
        self.bar_hi = (min(y for _, y in bars[1]), max(y for _, y in bars[1]))
        self.xmin = min(x for p in bars for x, _ in p)
        self.xmax = max(x for p in bars for x, _ in p)
        self.mid_y = (self.bar_lo[0] + self.bar_hi[1]) / 2
        self.stroke = self.bar_lo[1] - self.bar_lo[0]  # bar thickness: 170 Regular, 235 Bold
        self.span = self.bar_hi[1] - self.bar_lo[0]

        (chevron,) = polygons(font, ord(">"))
        self.chevron = clockwise(chevron)
        self.chev_y = (min(y for _, y in chevron), max(y for _, y in chevron))
        tip = sorted(y for x, y in chevron if x == self.xmax)
        self.tip_y = (tip[0], tip[-1])  # flat end of the chevron tip
        self.head = clockwise(clip_left(chevron, self.xmin + self.HEAD_CUT))
        self.axis = (self.xmin + self.xmax) / 2
        self.head_left = clockwise(mirror_x(self.head, self.axis))

        # x where a `=` bar end is fully inside the chevron's arm (see =>).
        lefts, rights = [], []
        for y0, y1 in (self.bar_lo, self.bar_hi):
            for y in (y0, y1):
                xs = slice_x(chevron, y)
                seg = [(a, b) for a, b in zip(xs[0::2], xs[1::2]) if a <= self.xmax]
                a, b = min(seg, key=lambda ab: abs((ab[0] + ab[1]) / 2 - self.xmax / 2))
                lefts.append(a)
                rights.append(b)
        self.bar_join_x = (max(lefts) + min(rights)) / 2
        self.bar_join_left = 2 * self.axis - self.bar_join_x

    def ink(self, codepoint):
        """(xmin, xmax) of a glyph's outline."""
        if codepoint not in self._ink:
            pen = BoundsPen(self.glyph_set)
            self.glyph_set[self.cmap[codepoint]].draw(pen)
            self._ink[codepoint] = (pen.bounds[0], pen.bounds[2])
        return self._ink[codepoint]

    def left(self, n):
        """x of the leftmost ink for an n-cell ligature (last-cell frame)."""
        return self.xmin - (n - 1) * self.width

    def bars(self, n, y_ranges=None, x0=None, x1=None):
        y_ranges = y_ranges or [self.bar_lo, self.bar_hi]
        return [rect(self.left(n) if x0 is None else x0, y0, x1 or self.xmax, y1) for y0, y1 in y_ranges]

    def three_bars(self, n):
        t, span = self.stroke * 140 / 170, self.span * 682 / 578
        centre = self.mid_y
        lo, hi = centre - span / 2, centre + span / 2
        mid = centre - t / 2
        return self.bars(n, [(lo, lo + t), (mid, mid + t), (hi - t, hi)])

    def slash(self, n):
        """A '/' crossing the bars, centred on the whole ligature."""
        cx = (self.left(n) + self.xmax) / 2
        y0, y1, dx, w = 150, 1130, 170, self.stroke
        return [(cx - dx - w / 2, y0), (cx + dx - w / 2, y1), (cx + dx + w / 2, y1), (cx - dx + w / 2, y0)]

    def head_at(self, cell, left=False):
        """Arrow head in the cell `cell` cells before the last one."""
        return shift(self.head_left if left else self.head, -cell * self.width)


def build_eq2(g):
    return g.bars(2)


def build_eq3(g):
    return g.three_bars(3)


def build_ne2(g):
    return g.bars(2) + [g.slash(2)]


def build_ne3(g):
    return g.three_bars(3) + [g.slash(3)]


def shaft(g, n):
    return rect(g.left(n), g.tip_y[0], g.xmax, g.tip_y[1])


def arrow_right(n):
    return lambda g: [g.head, shaft(g, n)]


def arrow_left(n):
    return lambda g: [g.head_at(n - 1, left=True), shaft(g, n)]


def fat_right(n):
    return lambda g: [g.head] + g.bars(n, x1=g.bar_join_x)


def fat_left(n):
    return lambda g: [g.head_at(n - 1, left=True)] + g.bars(n, x0=g.bar_join_left - (n - 1) * g.width)


def _sign(g, mirrored):
    """>= / <=  a wide chevron over a bar spanning both cells, like the mathematical sign."""
    bar_top = g.chev_y[0] + g.stroke
    chevron = g.chevron
    if mirrored:
        chevron = clockwise(mirror_x(chevron, g.axis))
    chevron = stretch_y(chevron, *g.chev_y, bar_top + 0.45 * g.stroke, g.chev_y[1])
    k = (g.xmax - g.left(2)) / (g.xmax - g.xmin)  # stretch the chevron across both cells
    chevron = [(g.left(2) + (x - g.xmin) * k, y) for x, y in chevron]
    return [chevron, rect(g.left(2), g.chev_y[0], g.xmax, bar_top)]


def build_ge(g):
    return _sign(g, False)


def build_le(g):
    return _sign(g, True)


def spaced(text, factor):
    """Same glyphs as the plain text, drawn closer: every gap between ink becomes `factor` * its natural size."""

    def build(g):
        n = len(text)
        origin = [-(n - 1 - i) * g.width for i in range(n)]  # cell i in the last-cell frame
        inks = [g.ink(ord(c)) for c in text]
        lefts = [o + a for o, (a, _) in zip(origin, inks)]
        rights = [o + b for o, (_, b) in zip(origin, inks)]
        gaps = [factor * (lefts[i + 1] - rights[i]) for i in range(n - 1)]
        total = sum(b - a for a, b in inks) + sum(gaps)
        x = (lefts[0] + rights[-1]) / 2 - total / 2  # keep the group centred where it was
        out = []
        for i, c in enumerate(text):
            a, b = inks[i]
            out.append(Outline(ord(c), round(x - a)))  # the outline is copied from cell origin 0
            x += (b - a) + (gaps[i] if i < n - 1 else 0)
        return out

    return build


def nested(text, step=0.55):
    """>> << >>> <<<  chevrons overlapping by `step` * cell instead of standing a cell apart."""

    def build(g):
        n = len(text)
        a, b = g.ink(ord(text[0]))
        origin = [-(n - 1 - i) * g.width for i in range(n)]
        pitch = step * g.width
        total = (n - 1) * pitch + (b - a)
        first = (origin[0] + a + origin[-1] + b) / 2 - total / 2
        return [Outline(ord(c), round(first + i * pitch - a)) for i, c in enumerate(text)]

    return build


def pipe_chevron(text, gap=0.7):
    """|> and <|  a bar and a chevron with its open end towards the bar."""

    def build(g):
        n = len(text)
        origin = [-(n - 1 - i) * g.width for i in range(n)]
        inks = [g.ink(ord(c)) for c in text]
        gap_units = gap * g.stroke
        total = sum(b - a for a, b in inks) + gap_units
        x = (origin[0] + inks[0][0] + origin[-1] + inks[-1][1]) / 2 - total / 2
        out = []
        for i, c in enumerate(text):
            a, b = inks[i]
            out.append(Outline(ord(c), round(x - a)))
            x += (b - a) + gap_units
        return out

    return build


def arrow_both(n):
    return lambda g: [g.head, g.head_at(n - 1, left=True), shaft(g, n)]


def fat_both(n):
    def build(g):
        x0 = g.bar_join_left - (n - 1) * g.width
        return [g.head, g.head_at(n - 1, left=True)] + g.bars(n, x0=x0, x1=g.bar_join_x)

    return build


def build_ne_slash(g):
    """=/=  two bars with a slash."""
    return g.bars(3) + [g.slash(3)]


# (source text, outline builder).  Longer sequences first: first match wins.
LIGATURES = [
    ("===", build_eq3),
    ("!==", build_ne3),
    ("<==>", fat_both(4)),
    ("<=>", fat_both(3)),
    ("<->", arrow_both(3)),
    ("==>", fat_right(3)),
    ("<==", fat_left(3)),
    ("-->", arrow_right(3)),
    ("<--", arrow_left(3)),
    ("=/=", build_ne_slash),
    (">>>", nested(">>>")),
    ("<<<", nested("<<<")),
    ("==", build_eq2),
    ("!=", build_ne2),
    ("->", arrow_right(2)),
    ("<-", arrow_left(2)),
    ("=>", fat_right(2)),
    (">=", build_ge),
    ("<=", build_le),
    (">>", nested(">>")),
    ("<<", nested("<<")),
    ("|>", pipe_chevron("|>")),
    ("<|", pipe_chevron("<|")),
    ("::", spaced("::", 0.35)),
    ("//", spaced("//", 0.4)),
    ("||", spaced("||", 0.5)),
    ("??", spaced("??", 0.4)),
    ("/*", spaced("/*", 0.45)),
    ("*/", spaced("*/", 0.45)),
]

# ---------------------------------------------------------------------------
# glyph + feature construction
# ---------------------------------------------------------------------------


def make_glyph(shapes, geo):
    """shapes: polygons (lists of points) and/or Outline copies of Hack glyphs."""
    pen = TTGlyphPen(None)
    for shape in shapes:
        if isinstance(shape, Outline):
            flat = DecomposingRecordingPen(geo.glyph_set)
            geo.glyph_set[geo.cmap[shape.codepoint]].draw(flat)
            flat.replay(TransformPen(pen, (1, 0, 0, 1, shape.dx, 0)))
            continue
        pts = [(round(x), round(y)) for x, y in clockwise(shape)]
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
    for text, builder in sorted(LIGATURES, key=lambda item: -len(item[0])):  # longest match first
        names = glyph_names(font, text)
        lig_name = "_".join(names) + ".liga"
        add_glyph(font, lig_name, make_glyph(builder(geo), geo), width)
        specs.append((names, lig_name))

    scratch = TTFont()
    scratch.setGlyphOrder(font.getGlyphOrder())
    addOpenTypeFeaturesFromString(scratch, build_feature_code(font, specs), tables=["GSUB"])
    merge_gsub(font, scratch)

    font.save(args.output)
    print(f"added {len(LIGATURES)} ligatures ({', '.join(t for t, _ in LIGATURES)}) -> {args.output}")


if __name__ == "__main__":
    sys.exit(main())
