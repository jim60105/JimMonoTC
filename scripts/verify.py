#!/usr/bin/env python3
"""Verify cell widths, shaping and metadata of a built font (TTF or WOFF2).

Checks
  * every glyph advance is 0, W or 2W; East Asian Wide/Fullwidth code points are 2W,
    everything else W (zero only for combining marks / controls, as in Hack)
  * CJK outlines stay inside their 2W cell
  * tests/width-cases.txt : shaped total advance == cells * W, with and without calt
  * tests/shaping.txt     : expected glyph sequences (ligature substitution) and
                            identical total advance before / after substitution
  * calt is reachable from the DFLT and latn scripts
  * family name carries no upstream (Hack / Noto / Bitstream Vera / Nerd) names
  * cross-check of the width cases with the `hb-shape` CLI when it is installed

W is the advance of "A".  Text in the case files may use \\uXXXX / \\UXXXXXXXX escapes.
"""

import argparse
import io
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

import uharfbuzz as hb
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_NAME_PARTS = ("hack", "nerd", "noto", "bitstream", "vera", "source", "adobe")
ZERO_WIDTH_OK = ("Mn", "Me", "Cc", "Cf")


class Report:
    def __init__(self):
        self.failures = []
        self.passed = 0

    def check(self, ok, message):
        if ok:
            self.passed += 1
        else:
            self.failures.append(message)
            print(f"  FAIL  {message}")

    def section(self, title):
        print(f"- {title}")


def unescape(text):
    text = re.sub(r"\\U([0-9a-fA-F]{8})", lambda m: chr(int(m.group(1), 16)), text)
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)


def read_cases(path, columns):
    """Tab separated; '#' starts a comment (only at line start or after a tab)."""
    cases = []
    for lineno, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = re.sub(r"(^|\t)#.*$", "", raw)
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < columns:
            raise SystemExit(f"{path}:{lineno}: expected {columns} tab separated columns")
        cases.append((lineno, unescape(parts[0]), *parts[1:columns]))
    return cases


def font_bytes(font):
    buf = io.BytesIO()
    font.flavor = None
    font.save(buf)
    return buf.getvalue()


class Shaper:
    def __init__(self, data):
        self.font = hb.Font(hb.Face(hb.Blob(data)))

    def shape(self, text, calt=True):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.font, buf, {"calt": calt, "liga": calt, "kern": True})
        names = [self.font.glyph_to_string(i.codepoint) for i in buf.glyph_infos]
        return names, sum(p.x_advance for p in buf.glyph_positions)


def hb_shape_cli_total(path, text):
    """Total advance via the HarfBuzz command line tool, or None if unavailable."""
    exe = shutil.which("hb-shape")
    if not exe:
        return None
    unicodes = ",".join(f"U+{ord(c):04X}" for c in text)
    out = subprocess.run(
        [exe, "--output-format=json", f"--unicodes={unicodes}", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return sum(g["ax"] for g in json.loads(out))


def check_metrics(font, report, W):
    report.section("glyph metrics")
    cmap = font.getBestCmap()
    hmtx, glyf = font["hmtx"], font["glyf"]
    advances = {a for a, _ in hmtx.metrics.values()}
    report.check(advances <= {0, W, 2 * W}, f"glyph advances must be in {{0, {W}, {2 * W}}}, found {sorted(advances)}")

    bad_wide = bad_narrow = bad_outline = 0
    examples = []
    for cp, name in cmap.items():
        ch = chr(cp)
        adv = hmtx[name][0]
        wide = unicodedata.east_asian_width(ch) in ("W", "F")
        if wide:
            ok = adv == 2 * W
            bad_wide += not ok
            g = glyf[name]
            if g.numberOfContours:
                g.recalcBounds(glyf)
                if g.xMin < 0 or g.xMax > 2 * W:
                    bad_outline += 1
                    examples.append(f"U+{cp:04X} outline [{g.xMin}, {g.xMax}] leaves 0..{2 * W}")
        elif adv == 0:
            ok = unicodedata.category(ch) in ZERO_WIDTH_OK
            bad_narrow += not ok
        else:
            ok = adv == W
            bad_narrow += not ok
        if not ok and len(examples) < 5:
            examples.append(f"U+{cp:04X} {name} advance {adv}")
    report.check(not bad_wide, f"{bad_wide} wide/fullwidth code points are not 2W ({'; '.join(examples[:3])})")
    report.check(not bad_narrow, f"{bad_narrow} narrow code points are not W ({'; '.join(examples[:3])})")
    report.check(not bad_outline, f"{bad_outline} CJK outlines exceed their cell ({'; '.join(examples[:3])})")
    wide_count = sum(unicodedata.east_asian_width(chr(cp)) in ("W", "F") for cp in cmap)
    print(f"  {len(cmap)} code points checked ({wide_count} wide)")


def check_text_cases(font, shaper, path, report, W, args):
    report.section("width cases (tests/width-cases.txt)")
    cmap = font.getBestCmap()
    for lineno, text, cells in read_cases(args.width_cases, 2):
        if args.partial and any(ord(c) not in cmap for c in text):
            continue
        expected = int(cells) * W
        for calt in (True, False):
            _, total = shaper.shape(text, calt)
            report.check(total == expected, f"width-cases:{lineno} {text!r} calt={calt}: {total} != {cells} cells ({expected})")
        cli = hb_shape_cli_total(path, text) if args.cli_path else None
        if cli is not None:
            report.check(cli == expected, f"width-cases:{lineno} {text!r} hb-shape CLI: {cli} != {expected}")


def check_shaping_cases(font, shaper, report, W, args):
    report.section("ligature shaping (tests/shaping.txt)")
    cmap = font.getBestCmap()
    has_names = font["post"].formatType != 3.0
    for lineno, text, cells, glyphs in read_cases(args.shaping, 3):
        if args.partial and any(ord(c) not in cmap for c in text):
            continue
        names, total = shaper.shape(text, calt=True)
        plain_names, plain_total = shaper.shape(text, calt=False)
        expected = glyphs.split()
        if has_names:
            report.check(names == expected, f"shaping:{lineno} {text!r}: got {names}, expected {expected}")
        else:  # subset WOFF2 without glyph names: only "was anything substituted?" is observable
            wants_lig = any(".liga" in n for n in expected)
            report.check(
                (names != plain_names) == wants_lig and len(names) == len(expected),
                f"shaping:{lineno} {text!r}: substitution mismatch (ligature expected: {wants_lig})",
            )
        report.check(total == int(cells) * W, f"shaping:{lineno} {text!r}: total {total} != {cells} cells")
        report.check(total == plain_total, f"shaping:{lineno} {text!r}: calt changes total advance ({plain_total} -> {total})")
        if names != plain_names:
            report.check(len(names) == len(plain_names), f"shaping:{lineno} {text!r}: glyph count changed")


def check_layout(font, report, partial):
    report.section("OpenType layout")
    if partial and ord("=") not in font.getBestCmap():
        print("  subset without ligature sources: calt check skipped")
        return
    if "GSUB" not in font:
        report.check(False, "GSUB table missing")
        return
    gsub = font["GSUB"].table
    tags = [r.FeatureTag for r in gsub.FeatureList.FeatureRecord]
    report.check("calt" in tags, "GSUB has no calt feature")
    for script in gsub.ScriptList.ScriptRecord:
        if script.ScriptTag in ("DFLT", "latn") and script.Script.DefaultLangSys:
            indexes = script.Script.DefaultLangSys.FeatureIndex
            reachable = any(tags[i] == "calt" for i in indexes)
            report.check(reachable, f"calt not reachable from {script.ScriptTag}/dflt")


def check_names(font, report):
    report.section("names / metadata")
    for nid in (1, 4, 6, 16, 17):
        rec = font["name"].getName(nid, 3, 1, 0x409)
        if rec:
            text = rec.toUnicode().lower()
            hits = [p for p in FORBIDDEN_NAME_PARTS if p in text]
            report.check(not hits, f"name ID {nid} {rec.toUnicode()!r} contains upstream name(s) {hits}")
    report.check(font["OS/2"].fsType == 0, "OS/2.fsType should be 0 (installable)")
    report.check(font["post"].isFixedPitch == 1, "post.isFixedPitch should be 1")


def verify(path, args):
    print(f"== {path}")
    font = TTFont(path)
    report = Report()
    cmap = font.getBestCmap()
    # xAvgCharWidth carries W explicitly (finalize.py); it is the fallback for subsets lacking "A".
    W = font["hmtx"][cmap[ord("A")]][0] if ord("A") in cmap else font["OS/2"].xAvgCharWidth
    report.check(font["OS/2"].xAvgCharWidth == W, f"OS/2.xAvgCharWidth {font['OS/2'].xAvgCharWidth} != W {W}")
    print(f"  W = {W}, 2W = {2 * W}, UPM = {font['head'].unitsPerEm}")

    check_metrics(font, report, W)
    check_layout(font, report, args.partial)
    shaper = Shaper(font_bytes(TTFont(path)))
    args.cli_path = path if path.suffix == ".ttf" else None
    check_text_cases(font, shaper, path, report, W, args)
    check_shaping_cases(font, shaper, report, W, args)
    check_names(font, report)
    if not shutil.which("hb-shape"):
        print("  (hb-shape CLI not found: used the uharfbuzz bindings only)")
    print(f"  {report.passed} checks passed, {len(report.failures)} failed")
    return not report.failures


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument("--width-cases", default=ROOT / "tests" / "width-cases.txt")
    ap.add_argument("--shaping", default=ROOT / "tests" / "shaping.txt")
    ap.add_argument("--partial", action="store_true", help="font is a subset: skip cases using missing code points")
    args = ap.parse_args()
    results = [verify(p, args) for p in args.fonts]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
