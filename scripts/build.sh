#!/usr/bin/env bash
# Build Jim Mono TC (Regular) from pinned upstream sources.
#
#   Hack ─► add-ligatures ─► Nerd Fonts patcher (--mono) ─► merge-cjk ─► finalize ─► verify
#                                                                            └─► WOFF2 (build-web)
#
# Default output is an OpenType/CFF font (.otf) with every East Asian wide code point
# Noto Sans CJK TC has (about 43k, 54.7k glyphs in total, under the 65,535 limit).
#
# Requirements: python3 with fonttools[woff] + uharfbuzz (requirements.txt),
# FontForge (for Nerd Fonts' font-patcher), curl, unzip, git; hb-shape optional.
#
# Usage: scripts/build.sh [--format otf|ttf] [--charset all|big5-common|big5|FILE]
#                         [--cjk-scale N] [--split-web]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
CACHE="${CACHE_DIR:-$ROOT/.cache}"
BUILD="$ROOT/build"
DIST="$ROOT/dist"
# shellcheck source=../sources/versions.env
source "$ROOT/sources/versions.env"

FAMILY="Jim Mono TC"
STEM="JimMonoTC-Regular"
FORMAT="otf"
FONT_VERSION="${FONT_VERSION:-0.1.0}"
CHARSET="all"
CJK_SCALE="1.0"
SPLIT_WEB=()

while (($#)); do
  case "$1" in
    --format) FORMAT="$2"; shift 2 ;;
    --charset) CHARSET="$2"; shift 2 ;;
    --cjk-scale) CJK_SCALE="$2"; shift 2 ;;
    --split-web) SPLIT_WEB=(--split); shift ;;
    -h|--help) sed -n '2,16p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

for tool in fontforge curl unzip "$PYTHON"; do
  command -v "$tool" >/dev/null || { echo "missing required tool: $tool" >&2; exit 1; }
done
"$PYTHON" -c 'import fontTools, brotli, uharfbuzz' 2>/dev/null \
  || { echo "install python deps first: $PYTHON -m pip install -r requirements.txt" >&2; exit 1; }

step() { printf '\n==> %s\n' "$*"; }

step "fetch pinned sources"
"$ROOT/scripts/fetch-sources.sh"

HACK="$CACHE/hack/Hack-Regular.ttf"
NOTO="$CACHE/downloads/$NOTO_CJK_FILE"

rm -rf "$BUILD" "$DIST"
mkdir -p "$BUILD/patched" "$DIST"

step "add programming ligatures to Hack"
"$PYTHON" "$ROOT/scripts/add-ligatures.py" "$HACK" "$BUILD/hack-lig.ttf"

step "Nerd Fonts font-patcher (--complete --mono)"
(cd "$CACHE/nerd-fonts" && fontforge -quiet -script font-patcher --complete --mono --quiet \
   -out "$BUILD/patched" "$BUILD/hack-lig.ttf" >"$BUILD/patcher.log" 2>&1) \
  || { tail -20 "$BUILD/patcher.log" >&2; exit 1; }
PATCHED="$(ls "$BUILD"/patched/*.ttf | head -n1)"
case "$FORMAT" in otf|ttf) ;; *) echo "--format must be otf or ttf" >&2; exit 2 ;; esac

step "merge Noto Sans CJK TC (charset: $CHARSET)"
"$PYTHON" "$ROOT/scripts/merge-cjk.py" "$PATCHED" "$NOTO" "$BUILD/merged.$FORMAT" \
  --reference "$HACK" --charset "$CHARSET" --cjk-scale "$CJK_SCALE" --format "$FORMAT"

step "finalize names and metrics"
"$PYTHON" "$ROOT/scripts/finalize.py" "$BUILD/merged.$FORMAT" "$DIST/$STEM.$FORMAT" \
  --family "$FAMILY" --style Regular --version "$FONT_VERSION" \
  --sources "Hack $HACK_VERSION; Noto Sans CJK 2.004; Nerd Fonts $NERD_FONTS_VERSION"

step "WOFF2 for the web"
"$PYTHON" "$ROOT/scripts/build-web.py" "$DIST/$STEM.$FORMAT" --out-dir "$DIST" ${SPLIT_WEB[@]+"${SPLIT_WEB[@]}"}

step "licences"
mkdir -p "$DIST/licenses/nerd-fonts"
cp "$ROOT/LICENSE-OFL.txt" "$ROOT/LICENSE-HACK.txt" "$ROOT/NOTICE.md" "$DIST/licenses/"
for f in "$CACHE"/nerd-fonts/src/glyphs/*/LICEN[CS]E*; do
  cp "$f" "$DIST/licenses/nerd-fonts/$(basename "$(dirname "$f")")-$(basename "$f")"
done

step "verify"
"$PYTHON" "$ROOT/scripts/verify.py" "$DIST/$STEM.$FORMAT"
if ((${#SPLIT_WEB[@]})); then
  "$PYTHON" "$ROOT/scripts/verify.py" --partial "$DIST"/"$STEM".*.woff2
else
  "$PYTHON" "$ROOT/scripts/verify.py" "$DIST/$STEM.woff2"
fi

printf '\nDone:\n'
ls -lh "$DIST"/*."$FORMAT" "$DIST"/*.woff2 "$DIST"/*.css
