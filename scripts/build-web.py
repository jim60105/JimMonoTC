#!/usr/bin/env python3
"""Produce WOFF2 file(s) + @font-face CSS from the finished master font (OTF or TTF).

Every output is subset from the same master, so metrics and the calt feature
stay identical to the desktop font.

  build-web.py dist/JimMonoTC-Regular.otf --out-dir dist            # one WOFF2
  build-web.py dist/JimMonoTC-Regular.otf --out-dir dist --split    # sliced, unicode-range CSS

--split cuts the character set into slices that browsers fetch on demand
(unicode-range); all slices share one family name, so 2W alignment holds.  Every slice is
at most --max-bytes (default 65,536) and the build fails otherwise.  The groups are disjoint and
together cover the whole cmap except U+0000, U+000D and U+FEFF.  The group names are a public
interface (downstream projects pick slices by name); do not rename them.

  latin, latin-ext,       one-cell, non-private-use code points, claimed in this order by the
  greek-cyrillic, box,    WINDOWS below (latin carries the ligature sources).  A one-cell code
  symbols                 point outside every window fails the build.
  icons-N                 private use (U+E000-F8FF, planes 15-16), chunked by size, N from 1
  cjk-N                   two-cell (East Asian Wide / Fullwidth) code points inside Noto Sans TC's
                          Google Fonts frequency range N (sources/noto-sans-tc-web-ranges.txt);
                          N is the Google index, first claim in file order, empty ones omitted
  cjk-xN                  the remaining two-cell code points in code point order, chunked by
                          size, N from 1
"""

import argparse
import io
import statistics
import sys
import unicodedata
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont


def is_wide(cp):
    return unicodedata.east_asian_width(chr(cp)) in ("W", "F")


def is_private_use(cp):
    return 0xE000 <= cp <= 0xF8FF or cp >= 0xF0000


MAX_BYTES = 65_536
DROPPED = frozenset({0x0000, 0x000D, 0xFEFF})  # not needed in a web font; never in a slice
RANGES_FILE = Path(__file__).resolve().parent.parent / "sources" / "noto-sans-tc-web-ranges.txt"
# Initial code points per chunk; a chunk that still exceeds --max-bytes is halved until it fits.
ICONS_CHUNK = 300
CJK_X_CHUNK = 250

WINDOWS = (
    ("latin", (
        (0x0020, 0x007E), (0x00A0, 0x00FF), (0x2013, 0x2014), (0x2018, 0x201F),
        (0x2022, 0x2022), (0x2026, 0x2026), (0x2039, 0x203A), (0x20AC, 0x20AC),
        (0x2122, 0x2122), (0x2190, 0x2193), (0xFFFD, 0xFFFD),
    )),
    ("latin-ext", (
        (0x0100, 0x036F), (0x0E3F, 0x0E3F), (0x1E00, 0x1EFF), (0x2000, 0x218F),
        (0x2C60, 0x2C7F),
    )),
    ("greek-cyrillic", ((0x0370, 0x03FF), (0x0400, 0x058F), (0x10A0, 0x10FF), (0x1F00, 0x1FFF))),
    ("box", ((0x2500, 0x259F),)),
    ("symbols", ((0x2190, 0x23FF), (0x25A0, 0x2BFF), (0x2E00, 0x2E7F))),
)


def load_google_ranges(path=RANGES_FILE):
    """[(N, set of code points)] in file order, from the vendored Google Fonts unicode-range split."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        n, spec = line.split("\t")
        cps = set()
        for part in spec.split(","):
            lo, _, hi = part.strip().removeprefix("U+").partition("-")
            cps.update(range(int(lo, 16), int(hi or lo, 16) + 1))
        out.append((int(n), cps))
    return out


def split_groups(cmap):
    """(fixed groups, icons code points, cjk-x code points): ordered {name: code points} + two sorted lists.

    Every code point of the font except DROPPED lands in exactly one group.
    """
    remaining = set(cmap) - DROPPED
    groups = {}
    one_cell = {cp for cp in remaining if not is_wide(cp) and not is_private_use(cp)}
    for name, windows in WINDOWS:
        claimed = {cp for cp in one_cell if any(lo <= cp <= hi for lo, hi in windows)}
        one_cell -= claimed
        if claimed:
            groups[name] = claimed
    if one_cell:
        sample = ", ".join(f"U+{cp:04X}" for cp in sorted(one_cell)[:10])
        raise SystemExit(f"{len(one_cell)} one-cell code points fall outside every window ({sample}...); widen WINDOWS")
    wide = {cp for cp in remaining if is_wide(cp)}
    for n, cps in load_google_ranges():
        claimed = wide & cps
        wide -= claimed
        if claimed:
            groups[f"cjk-{n}"] = claimed
    icons = sorted(cp for cp in remaining if is_private_use(cp))
    return groups, icons, sorted(wide)


def ranges(codepoints):
    """Compress code points into 'U+0020-007E, U+00A0' style ranges."""
    out, start, prev = [], None, None
    for cp in sorted(codepoints):
        if start is None:
            start = prev = cp
        elif cp == prev + 1:
            prev = cp
        else:
            out.append((start, prev))
            start = prev = cp
    if start is not None:
        out.append((start, prev))
    return ", ".join(f"U+{a:04X}" if a == b else f"U+{a:04X}-{b:04X}" for a, b in out)


def subset_bytes(source, codepoints):
    """WOFF2 bytes of `source` (master file bytes) restricted to `codepoints`."""
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]  # keep calt (ligatures) and friends
    options.name_IDs = ["*"]
    options.notdef_outline = True
    options.glyph_names = False
    options.hinting = False  # hinted box drawing broke grid joins in headless Chromium (TrueType masters only)
    options.drop_tables += ["PfEd"]
    font = TTFont(io.BytesIO(source))
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=codepoints)
    subsetter.subset(font)
    # Glyph closure (e.g. vertical alternates) keeps cmap entries of neighbouring slices' code points
    # that share a retained glyph; drop them so the slices stay disjoint.
    wanted = set(codepoints)
    for table in font["cmap"].tables:
        if table.format != 14:
            table.cmap = {cp: name for cp, name in table.cmap.items() if cp in wanted}
    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def fit_chunks(source, codepoints, chunk, max_bytes):
    """Cut sorted `codepoints` into [(code points, woff2 bytes)], each within max_bytes (halving on overflow)."""
    out = []

    def fit(cps):
        data = subset_bytes(source, cps)
        if len(data) <= max_bytes:
            out.append((cps, data))
        elif len(cps) == 1:
            raise SystemExit(f"U+{cps[0]:04X} alone is {len(data)} bytes, over the {max_bytes} limit")
        else:
            mid = len(cps) // 2
            fit(cps[:mid])
            fit(cps[mid:])

    for i in range(0, len(codepoints), chunk):
        fit(codepoints[i : i + chunk])
    return out


def face_css(family, weight, style, url, unicode_range=None):
    lines = [
        "@font-face {",
        f'  font-family: "{family}";',
        f'  src: url("{url}") format("woff2");',
        f"  font-weight: {weight};",
        f"  font-style: {style};",
        "  font-display: swap;",
    ]
    if unicode_range:
        lines.append(f"  unicode-range: {unicode_range};")
    lines.append("}")
    return "\n".join(lines)


def summarize(label, sizes):
    print(f"  {label}: {len(sizes)} files, {min(sizes) / 1024:.1f} / {statistics.median(sizes) / 1024:.1f} / "
          f"{max(sizes) / 1024:.1f} KiB (min / median / max), {sum(sizes) / 1024:.0f} KiB total")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("font", type=Path, help="master OTF / TTF")
    ap.add_argument("--out-dir", type=Path, default=Path("dist"))
    ap.add_argument("--split", action="store_true", help="cut into unicode-range slices (see above)")
    ap.add_argument("--max-bytes", type=int, default=MAX_BYTES, help=f"size limit of every slice (default {MAX_BYTES})")
    ap.add_argument("--url-prefix", default="/fonts/", help="URL prefix used in the generated CSS")
    args = ap.parse_args()

    source = args.font.read_bytes()
    master = TTFont(io.BytesIO(source))
    family = master["name"].getName(1, 3, 1, 0x409).toUnicode()
    weight = master["OS/2"].usWeightClass
    style = "italic" if master["OS/2"].fsSelection & 1 else "normal"
    cmap = master.getBestCmap()
    stem = args.font.stem
    args.out_dir.mkdir(parents=True, exist_ok=True)

    files = []  # (filename, code points or None, woff2 bytes), in CSS order
    if args.split:
        groups, icons, cjk_x = split_groups(cmap)
        for name, cps in groups.items():
            files.append((f"{stem}.{name}.woff2", cps, subset_bytes(source, cps)))
        for prefix, cps, chunk in (("icons-", icons, ICONS_CHUNK), ("cjk-x", cjk_x, CJK_X_CHUNK)):
            for i, (part, data) in enumerate(fit_chunks(source, cps, chunk, args.max_bytes), 1):
                files.append((f"{stem}.{prefix}{i}.woff2", set(part), data))
        oversize = [f"{name} ({len(data)} bytes)" for name, _, data in files if len(data) > args.max_bytes]
        if oversize:
            raise SystemExit(f"slices over the {args.max_bytes} byte limit: {', '.join(oversize)}")
    else:
        files.append((f"{stem}.woff2", None, subset_bytes(source, set(cmap))))

    css = []
    for filename, cps, data in files:
        (args.out_dir / filename).write_bytes(data)
        css.append(face_css(family, weight, style, args.url_prefix + filename, ranges(cps) if cps else None))
    if args.split:
        families = {}
        for filename, _, data in files:
            group = filename.removeprefix(f"{stem}.").removesuffix(".woff2")
            key = "cjk-N" if group.startswith("cjk-") and not group.startswith("cjk-x") else group.rstrip("0123456789") + ("N" if group[-1].isdigit() else "")
            families.setdefault(key, []).append(len(data))
        print(f"{stem}: {len(files)} slices")
        for key, sizes in families.items():
            summarize(key, sizes)
    else:
        print(f"{files[0][0]}: {len(files[0][2]) / 1024:.0f} KiB")

    css_path = args.out_dir / f"{stem}.css"
    css_path.write_text("\n\n".join(css) + "\n", encoding="utf-8")
    print(f"wrote {css_path}")


if __name__ == "__main__":
    sys.exit(main())
