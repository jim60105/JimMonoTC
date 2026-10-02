#!/usr/bin/env python3
"""Check an assembled JimMonoTC-<version>-web.zip against the web slice contract.

  tests/check-web-zip.py out/JimMonoTC-0.2.0-web.zip [--masters dist]

Asserts (see docs/BUILDING.md, "Web slices"):
  * layout       JimMonoTC-<version>-web/{JimMonoTC-<Style>.<group>.woff2, JimMonoTC.css, licenses/**}
  * groups       latin latin-ext greek-cyrillic arabic-hebrew box symbols icons-N cjk-N cjk-xN, nothing else
  * bound        every .woff2 is at most 65,536 bytes
  * coverage     per style the groups are disjoint and their union is the master's cmap minus
                 U+0000 / U+000D / U+FEFF (needs --masters, the directory holding the .otf / .ttf masters)
  * cjk-N        the same code point sets for Regular / Bold and for Italic / BoldItalic
  * calt         the latin group has GSUB calt and the ligature sources
  * css          one @font-face per file with family, weight, style, font-display: swap, src url
                 and a unicode-range that equals the file's own cmap
  * licences     LICENSE, NOTICE.md, CascadiaCode-LICENSE.txt, nerd-fonts/*, third-party/*
"""

import argparse
import re
import sys
import tempfile
import zipfile
from pathlib import Path

from fontTools.ttLib import TTFont

MAX_BYTES = 65_536
DROPPED = {0x0000, 0x000D, 0xFEFF}
STYLES = {"Regular": (400, "normal"), "Bold": (700, "normal"), "Italic": (400, "italic"), "BoldItalic": (700, "italic")}
FIXED = ("latin", "latin-ext", "greek-cyrillic", "arabic-hebrew", "box", "symbols")
FILE_RE = re.compile(r"JimMonoTC-(Regular|Bold|Italic|BoldItalic)\.(latin|latin-ext|greek-cyrillic|arabic-hebrew|box|symbols|icons-[1-9]\d*|cjk-\d+|cjk-x[1-9]\d*)\.woff2")

failures = []


def check(ok, message):
    if not ok:
        failures.append(message)
        print(f"  FAIL  {message}")


def parse_ranges(spec):
    cps = set()
    for part in spec.split(","):
        lo, _, hi = part.strip().removeprefix("U+").partition("-")
        cps.update(range(int(lo, 16), int(hi or lo, 16) + 1))
    return cps


def cmap_of(path):
    return set(TTFont(path, lazy=True).getBestCmap())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip", type=Path)
    ap.add_argument("--masters", type=Path, help="directory with JimMonoTC-<Style>.otf|ttf, for the coverage check")
    args = ap.parse_args()

    m = re.fullmatch(r"(JimMonoTC-(.+)-web)\.zip", args.zip.name)
    if not m:
        raise SystemExit(f"{args.zip.name}: expected JimMonoTC-<version>-web.zip")
    top = m.group(1)
    tmp = tempfile.TemporaryDirectory()
    with zipfile.ZipFile(args.zip) as z:
        z.extractall(tmp.name)
    root = Path(tmp.name) / top
    check(root.is_dir(), f"{top}/ missing from the archive")

    print("- layout, bound")
    woff2 = sorted(root.glob("*.woff2"))
    strays = sorted(p.name for p in root.iterdir() if p.is_file() and p.suffix != ".woff2" and p.name != "JimMonoTC.css")
    check(not strays, f"unexpected files next to the slices: {strays}")
    by_style = {}
    for p in woff2:
        fm = FILE_RE.fullmatch(p.name)
        check(bool(fm), f"{p.name}: not a JimMonoTC-<Style>.<group>.woff2 name")
        if fm:
            by_style.setdefault(fm.group(1), {})[fm.group(2)] = p
        check(p.stat().st_size <= MAX_BYTES, f"{p.name}: {p.stat().st_size} bytes > {MAX_BYTES}")
    check(set(by_style) == set(STYLES), f"styles found {sorted(by_style)}, expected {sorted(STYLES)}")
    print(f"  {len(woff2)} slices")

    print("- groups: disjoint, cover the master, calt")
    sets = {}
    for style, files in by_style.items():
        for g in FIXED:
            # Cascadia's italics have no Arabic / Hebrew, so that group exists for the upright styles only.
            if g == "arabic-hebrew" and "Italic" in style:
                continue
            check(g in files, f"{style}: group {g} missing")
        seen, sets[style] = set(), {}
        for group, p in files.items():
            cps = cmap_of(p)
            sets[style][group] = cps
            check(not cps & seen, f"{style}.{group}: shares code points with another group ({len(cps & seen)})")
            seen |= cps
        if args.masters:
            master = next(iter(args.masters.glob(f"JimMonoTC-{style}.[ot]tf")), None)
            check(master is not None, f"{style}: no master in {args.masters}")
            if master:
                want = cmap_of(master) - DROPPED
                check(seen == want, f"{style}: union differs from the master cmap (missing {len(want - seen)}, extra {len(seen - want)})")
        check(not seen & DROPPED, f"{style}: contains U+0000 / U+000D / U+FEFF")
        latin = TTFont(files["latin"], lazy=True)
        tags = {r.FeatureTag for r in latin["GSUB"].table.FeatureList.FeatureRecord} if "GSUB" in latin else set()
        check("calt" in tags, f"{style}.latin: no GSUB calt")
        check({ord("="), ord(">"), ord("-")} <= sets[style]["latin"], f"{style}.latin: ligature source characters missing")

    print("- cjk-N sets equal between paired styles")
    for a, b in (("Regular", "Bold"), ("Italic", "BoldItalic")):
        if a in sets and b in sets:
            ka = {g: c for g, c in sets[a].items() if re.fullmatch(r"cjk-\d+", g)}
            kb = {g: c for g, c in sets[b].items() if re.fullmatch(r"cjk-\d+", g)}
            check(ka == kb, f"cjk-N differ between {a} and {b}")

    print("- css")
    css = (root / "JimMonoTC.css").read_text(encoding="utf-8")
    faces = re.findall(r"@font-face \{(.*?)\}", css, re.S)
    check(len(faces) == len(woff2), f"{len(faces)} @font-face rules for {len(woff2)} files")
    described = set()
    for body in faces:
        src = re.search(r'src: url\("([^"]+)"\) format\("woff2"\);', body)
        name = src and src.group(1).rsplit("/", 1)[-1]
        fm = FILE_RE.fullmatch(name or "")
        if not fm:
            check(False, f"@font-face without a recognised src: {body.strip()[:80]!r}")
            continue
        style, group = fm.groups()
        weight, fstyle = STYLES[style]
        described.add(name)
        check('font-family: "Jim Mono TC";' in body, f"{name}: font-family")
        check(f"font-weight: {weight};" in body, f"{name}: font-weight {weight}")
        check(f"font-style: {fstyle};" in body, f"{name}: font-style {fstyle}")
        check("font-display: swap;" in body, f"{name}: font-display swap")
        rng = re.search(r"unicode-range: ([^;]+);", body)
        check(bool(rng) and parse_ranges(rng.group(1)) == sets.get(style, {}).get(group), f"{name}: unicode-range differs from the file's cmap")
    check(described == {p.name for p in woff2}, "CSS and files do not describe the same set")

    print("- licences")
    lic = root / "licenses"
    for rel in ("LICENSE", "NOTICE.md", "CascadiaCode-LICENSE.txt"):
        check((lic / rel).is_file(), f"licenses/{rel} missing")
    for sub in ("nerd-fonts", "third-party"):
        check(any((lic / sub).glob("*")), f"licenses/{sub}/ empty or missing")

    print(f"{'FAILED' if failures else 'OK'}: {len(failures)} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
