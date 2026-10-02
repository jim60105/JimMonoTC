#!/usr/bin/env python3
"""Audit the Nerd Fonts glyph sets in the font.

The icons come from Cascadia Code NF (Microsoft's own build of the Nerd Fonts glyph sets),
and prepare-base.py fills the icons Cascadia lacks from the same sets in the pinned
Nerd Fonts archive, so the font holds exactly the sets of `font-patcher --complete`.

Reads the glyph-set table out of the pinned `font-patcher`, and fails when

  * a glyph set is not in LICENSES below (a patcher update added a source whose
    licence nobody has looked at yet), or
  * a licence file that we claim to ship is missing.

With --font FONT it also counts, per set, how many code points of the built font
lie in the range that the set was written to (informational: Cascadia and Noto
own the rest).  --markdown prints the table used in NOTICE.md.

Licence information comes from the licence files in the FontPatcher archive, the
copyright strings in the glyph fonts, and Nerd Fonts' own licence audit
(https://github.com/ryanoasis/nerd-fonts/blob/master/license-audit.md).
"""

import argparse
import sys
from pathlib import Path

from nerd_sets import GLYPHS, patch_sets

ROOT = Path(__file__).resolve().parent.parent

# patcher file name -> (project, licence, copyright holder, licence file, where the file is)
# where: "archive" = FontPatcher archive (GLYPHS + file), "repo" = licenses/third-party, None = none available
LICENSES = {
    "original-source.otf": ("Seti-UI + Custom", "MIT", "Jesse Weed (Seti-UI); Nerd Fonts", "Seti-UI-MIT.txt", "repo"),
    "extraglyphs.sfd": ("Nerd Fonts extras (heavy angle brackets, box drawing, progress)", "MIT", "Nerd Fonts", None, None),
    "devicons/devicons.otf": ("Devicons", "MIT", "konpa", "Devicon-MIT.txt", "repo"),
    "powerline-symbols/PowerlineSymbols.otf": ("Powerline Symbols", "MIT", "Kim Silkebækken and contributors", "powerline-symbols/LICENSE.txt", "archive"),
    "powerline-extra/PowerlineExtraSymbols.otf": ("Powerline Extra Symbols", "MIT", "Ryan L McIntyre", "powerline-extra/LICENSE", "archive"),
    "pomicons/Pomicons.otf": ("Pomicons", "OFL-1.1 (RFN \"Pomicons\")", "Gabriele Lana", "pomicons/LICENSE", "archive"),
    "font-awesome/FontAwesome.otf": ("Font Awesome Free (icons)", "CC-BY-4.0", "Fonticons, Inc.", "font-awesome/LICENSE.txt", "archive"),
    "font-awesome-extension.ttf": ("Font Awesome Extension", "MIT (per Nerd Fonts audit)", "AndreLZGava", None, None),
    "Unicode_IEC_symbol_font.otf": ("IEC Power Symbols", "MIT (per Nerd Fonts audit)", "unicodepowersymbol.com", None, None),
    "materialdesign/MaterialDesignIconsDesktop.ttf": ("Material Design Icons", "Apache-2.0", "Pictogrammers", "Apache-2.0.txt", "repo"),
    "weather-icons/weathericons-regular-webfont.ttf": ("Weather Icons", "OFL-1.1", "Erik Flowers; Lukas Bischoff (v1 art)", "weather-icons/OFL.txt", "archive"),
    "font-logos.ttf": ("Font Logos", "Unlicense (public domain)", "Lukas W", "Font-Logos-Unlicense.txt", "repo"),
    "octicons/octicons.otf": ("Octicons", "MIT", "GitHub Inc.", "octicons/LICENSE", "archive"),
    "codicons/codicon.ttf": ("Codicons", "CC-BY-4.0", "Microsoft Corporation", "codicons/LICENSE.txt", "archive"),
}
DISABLED_OK = {"materialdesign/materialdesignicons-webfont.ttf"}  # 'Material legacy', hard-wired off in the patcher

def license_path(cache, third_party, where, name):
    if where == "archive":
        return cache / "nerd-fonts" / GLYPHS / name
    return third_party / name if where == "repo" else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=ROOT / ".cache")
    ap.add_argument("--font", type=Path, help="built font, to count code points per set")
    ap.add_argument("--markdown", action="store_true", help="print the NOTICE.md table")
    args = ap.parse_args()

    patcher = args.cache / "nerd-fonts" / "font-patcher"
    rows = patch_sets(patcher)
    if not rows:
        raise SystemExit(f"no glyph-set table found in {patcher}: did the patcher format change?")

    problems = []
    for r in rows:
        if r["file"] in DISABLED_OK and r["enabled"] == "False":
            continue
        if r["file"] not in LICENSES:
            problems.append(f"glyph set {r['name']!r} ({r['file']}) has no licence entry in scripts/audit-licenses.py")
    for fname, (_, _, _, lic, where) in LICENSES.items():
        path = license_path(args.cache, ROOT / "licenses" / "third-party", where, lic) if lic else None
        if lic and not path.is_file():
            problems.append(f"{fname}: licence file {path} is missing")
        if not any(r["file"] == fname for r in rows):
            problems.append(f"{fname} is in LICENSES but not in the patcher any more (remove it)")

    cmap = None
    if args.font:
        from fontTools.ttLib import TTFont

        cmap = TTFont(args.font, lazy=True).getBestCmap()

    def count(file):
        if cmap is None:
            return None
        ranges = [(r["lo"], r["hi"]) for r in rows if r["file"] == file]
        return sum(1 for cp in cmap if any(lo <= cp <= hi for lo, hi in ranges))

    seen = {}
    for r in rows:
        seen.setdefault(r["file"], []).append(f"U+{r['lo']:04X}" + (f"-{r['hi']:04X}" if r["hi"] != r["lo"] else ""))

    if args.markdown:
        print("| Glyph set | Licence | Copyright | Code points in this font | Licence text |")
        print("| --- | --- | --- | --- | --- |")
    for fname, (project, lic, holder, lic_file, where) in LICENSES.items():
        if fname not in seen:
            continue
        ranges = ", ".join(seen[fname])
        n = count(fname)
        shown = ranges + (f" ({n} present)" if n is not None else "")
        text = f"`licenses/{'third-party/' if where == 'repo' else 'nerd-fonts/'}…`" if lic_file else "none available"
        if args.markdown:
            print(f"| {project} | {lic} | {holder} | {shown} | {text} |")
        else:
            print(f"{project:62} {lic:30} {shown}")

    if problems:
        print("\nLICENCE AUDIT FAILED", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    if not args.markdown:
        print(f"\n{len(LICENSES)} glyph sets, all with a licence entry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
