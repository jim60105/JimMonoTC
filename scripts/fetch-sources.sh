#!/usr/bin/env bash
# Copyright (C) 2026 Jim Chen <Jim@ChenJ.im>, licensed under GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==================================================================
#
# Download the pinned upstream inputs into .cache/ and verify their SHA-256.
#
# Usage: scripts/fetch-sources.sh
#
# Environment:
#   CACHE_DIR   Cache directory (default: <repo root>/.cache)
#
# Inputs are pinned in sources/versions.env and checked against
# sources/checksums.sha256; already-cached files are not re-downloaded.
set -euo pipefail

# --- Configuration -----------------------------------------------------------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE="${CACHE_DIR:-$ROOT/.cache}"
# shellcheck source=../sources/versions.env
source "$ROOT/sources/versions.env"
mkdir -p "$CACHE/downloads"
# Never leave partial downloads or the transient Noto clone behind.
trap 'rm -rf "$CACHE/noto-cjk-git" "$CACHE"/downloads/*.part' EXIT INT TERM

# --- Utility functions -------------------------------------------------------
RED='\033[0;31m'; YELLOW='\033[1;33m'; GRAY='\033[0;90m'; RESET='\033[0m'

info()  { printf '%s%s%s\n' "$GRAY"    "$*" >&2; }
warn()  { printf '%sWARNING: %s%s\n' "$YELLOW" "$*" >&2; }
error() { printf '%sERROR: %s%s\n'    "$RED"    "$*" >&2; }
die()   { error "$*"; exit 1; }

# Fail fast: every dependency is needed before any file is touched.
for tool in curl unzip git sha256sum awk; do
  command -v "$tool" >/dev/null 2>&1 \
    || die "required tool not installed: $tool"
done

verify() { # verify <file>
  local name expected actual
  name="$(basename "$1")"
  [[ -f "$ROOT/sources/checksums.sha256" ]] \
    || die "checksum file missing: $ROOT/sources/checksums.sha256"
  expected="$(awk -v n="$name" '$2 == n { print $1 }' "$ROOT/sources/checksums.sha256")"
  [[ -n "$expected" ]] || { error "no checksum recorded for $name"; return 1; }
  actual="$(sha256sum "$1" | awk '{ print $1 }')"
  [[ "$expected" == "$actual" ]] \
    || { error "checksum mismatch for $name: $actual"; return 1; }
}

# --- Content processing functions --------------------------------------------
download() { # download <url> <dest>
  if [[ -f "$2" ]] && verify "$2" 2>/dev/null; then return 0; fi
  info "fetching $1"
  curl -fsSL --retry 3 -o "$2.part" "$1" || { rm -f "$2.part"; return 1; }
  mv "$2.part" "$2"  # atomic: readers never see a half-written file
  verify "$2" || { rm -f "$2"; return 1; }
}

noto_path() { echo "$NOTO_CJK_DIR/NotoSansCJKtc-$1.otf"; }
noto_file() { echo "NotoSansCJKtc-$1-2.004.otf"; }

# Fallback for Noto: each file is ~16 MB inside a very large repository, so use a
# blobless sparse checkout of the pinned commit instead of a full clone.
fetch_noto_via_git() { # fetch_noto_via_git <weight>...
  local dir="$CACHE/noto-cjk-git" w paths=()
  for w in "$@"; do paths+=("$(noto_path "$w")"); done
  rm -rf "$dir"
  GIT_LFS_SKIP_SMUDGE=1 git clone --quiet --no-checkout --filter=blob:none "$NOTO_CJK_REPO" "$dir"
  git -C "$dir" fetch --quiet --depth 1 origin "$NOTO_CJK_COMMIT" 2>/dev/null || true
  git -C "$dir" checkout --quiet "$NOTO_CJK_COMMIT" -- "${paths[@]}" 2>/dev/null \
    || { git -C "$dir" fetch --quiet --unshallow origin 2>/dev/null || true
         git -C "$dir" checkout --quiet "$NOTO_CJK_COMMIT" -- "${paths[@]}"; }
  for w in "$@"; do
    cp "$dir/$(noto_path "$w")" "$CACHE/downloads/$(noto_file "$w")"
    verify "$CACHE/downloads/$(noto_file "$w")"
  done
  rm -rf "$dir"
}

# --- Main execution ----------------------------------------------------------
# --- Cascadia Code NF ---------------------------------------------------------
download "$CASCADIA_URL" "$CACHE/downloads/$CASCADIA_ARCHIVE" || die "cannot fetch Cascadia Code NF"
for style in $CASCADIA_STYLES; do
  unzip -oqj "$CACHE/downloads/$CASCADIA_ARCHIVE" "ttf/static/CascadiaCodeNF-$style.ttf" -d "$CACHE/cascadia" \
    || die "Cascadia archive missing ttf/static/CascadiaCodeNF-$style.ttf"
done

# --- Nerd Fonts glyph sources ---------------------------------------------
download "$NERD_FONTS_URL" "$CACHE/downloads/$NERD_FONTS_ARCHIVE" || die "cannot fetch Nerd Fonts"
rm -rf "$CACHE/nerd-fonts"
mkdir -p "$CACHE/nerd-fonts"
unzip -oq "$CACHE/downloads/$NERD_FONTS_ARCHIVE" -d "$CACHE/nerd-fonts"

# --- Noto Sans CJK TC ------------------------------------------------------
missing=()
for w in $NOTO_CJK_WEIGHTS; do
  file="$CACHE/downloads/$(noto_file "$w")"
  if ! download "${NOTO_CJK_REPO}/raw/${NOTO_CJK_COMMIT}/$(noto_path "$w")" "$file"; then
    rm -f "$file.part"
    missing+=("$w")
  fi
done
if ((${#missing[@]})); then
  warn "direct download failed for: ${missing[*]}; falling back to sparse git checkout"
  fetch_noto_via_git "${missing[@]}" || die "cannot fetch Noto Sans CJK TC (${missing[*]})"
fi

info "sources OK: $CACHE"
