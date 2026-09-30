#!/usr/bin/env python3
"""Produce WOFF2 file(s) + @font-face CSS from the finished master font (OTF or TTF).

Every output is subset from the same master, so metrics and the calt feature
stay identical to the desktop font.

  build-web.py dist/JimMonoTC-Regular.otf --out-dir dist            # one WOFF2
  build-web.py dist/JimMonoTC-Regular.otf --out-dir dist --split    # sliced, unicode-range CSS

--split cuts the character set into slices that browsers fetch on demand
(unicode-range); all slices share one family name, so 2W alignment holds:

  latin        everything that is neither East Asian Wide/Fullwidth nor private use (Hack, ligatures)
  icons        Nerd Fonts icons (private use areas)
  cjk-common   Big5 common hanzi (5,401) + kana, bopomofo, CJK / fullwidth punctuation
  cjk-big5     Big5 less common hanzi
  cjk-N        the remaining wide code points (rare hanzi, Ext. A/B, ...), --slice-size each
"""

import argparse
import importlib.util
import sys
import unicodedata
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont


def _load_merge_cjk():
    spec = importlib.util.spec_from_file_location("merge_cjk", Path(__file__).with_name("merge-cjk.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_wide(cp):
    return unicodedata.east_asian_width(chr(cp)) in ("W", "F")


def is_private_use(cp):
    return 0xE000 <= cp <= 0xF8FF or cp >= 0xF0000


def split_groups(cmap, slice_size):
    """Ordered {name: code points}; every code point of the font lands in exactly one group."""
    mc = _load_merge_cjk()
    common = mc.big5_characters(mc.BIG5_LEADS["big5-common"])
    for lo, hi in mc.EXTRA_RANGES:
        common.update(range(lo, hi + 1))
    big5 = mc.big5_characters(mc.BIG5_LEADS["big5"])
    wide = {cp for cp in cmap if is_wide(cp)}
    groups = {
        "latin": {cp for cp in cmap if not is_wide(cp) and not is_private_use(cp)},
        "icons": {cp for cp in cmap if is_private_use(cp)},
        "cjk-common": wide & common,
        "cjk-big5": (wide & big5) - common,
    }
    rest = sorted(wide - common - big5)
    for i in range(0, len(rest), slice_size):
        groups[f"cjk-{i // slice_size + 1}"] = set(rest[i : i + slice_size])
    return {name: cps for name, cps in groups.items() if cps}


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


def make_subset(source, codepoints, out_path):
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]  # keep calt (ligatures) and friends
    options.name_IDs = ["*"]
    options.notdef_outline = True
    options.glyph_names = False
    options.drop_tables += ["PfEd"]
    font = TTFont(source)
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=codepoints)
    subsetter.subset(font)
    font.flavor = "woff2"
    font.save(out_path)
    return out_path.stat().st_size


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("font", type=Path, help="master OTF / TTF")
    ap.add_argument("--out-dir", type=Path, default=Path("dist"))
    ap.add_argument("--split", action="store_true", help="cut into unicode-range slices (see above)")
    ap.add_argument("--slice-size", type=int, default=2500, help="code points per rare-CJK slice (default 2500)")
    ap.add_argument("--url-prefix", default="/fonts/", help="URL prefix used in the generated CSS")
    args = ap.parse_args()

    master = TTFont(args.font)
    family = master["name"].getName(1, 3, 1, 0x409).toUnicode()
    weight = master["OS/2"].usWeightClass
    style = "italic" if master["OS/2"].fsSelection & 1 else "normal"
    cmap = master.getBestCmap()
    stem = args.font.stem
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.split:
        groups = split_groups(cmap, args.slice_size)
    else:
        groups = {None: set(cmap)}

    css = []
    for group, cps in groups.items():
        filename = f"{stem}.{group}.woff2" if group else f"{stem}.woff2"
        size = make_subset(args.font, cps, args.out_dir / filename)
        print(f"{filename}: {len(cps)} code points, {size / 1024:.0f} KiB")
        css.append(face_css(family, weight, style, args.url_prefix + filename, ranges(cps) if group else None))

    css_path = args.out_dir / f"{stem}.css"
    css_path.write_text("\n\n".join(css) + "\n", encoding="utf-8")
    print(f"wrote {css_path}")


if __name__ == "__main__":
    sys.exit(main())
