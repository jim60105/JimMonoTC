"""The Nerd Fonts glyph-set table, read out of the pinned `font-patcher` script.

Shared by audit-licenses.py (licence audit) and prepare-base.py (fills the icons that
Cascadia Code NF lacks).  Each row maps a range of a glyph font in the patcher archive
(`src/glyphs/<file>`) to the code points it occupies in a patched font.
"""

import re

GLYPHS = "src/glyphs"  # inside the patcher archive

ROW = re.compile(
    r"\{'Enabled':\s*(?P<enabled>[^,]+?),\s*'Name':\s*\"(?P<name>[^\"]+)\",\s*'Filename':\s*\"(?P<file>[^\"]+)\","
    r"\s*'Exact':\s*(?P<exact>True|False),\s*'SymStart':\s*(?P<start>0[xX][0-9A-Fa-f]+),\s*'SymEnd':\s*(?P<end>0[xX][0-9A-Fa-f]+),"
    r"\s*'SrcStart':\s*(?P<dest>None|0[xX][0-9A-Fa-f]+)"
)


def patch_sets(patcher):
    """Rows of the table: enabled (raw expression), name, file, src (lo, hi) in the glyph font, dest lo / hi."""
    rows = []
    for m in ROW.finditer(patcher.read_text(encoding="utf-8")):
        start, end = int(m["start"], 16), int(m["end"], 16)
        dest = start if m["exact"] == "True" or m["dest"] == "None" else int(m["dest"], 16)
        rows.append({
            "enabled": m["enabled"].strip(), "name": m["name"], "file": m["file"],
            "src_lo": start, "src_hi": end,
            "lo": dest, "hi": dest + (end - start),
        })
    return rows
