#!/usr/bin/env bash
# Download the pinned upstream inputs into .cache/ and verify their SHA-256.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE="${CACHE_DIR:-$ROOT/.cache}"
# shellcheck source=../sources/versions.env
source "$ROOT/sources/versions.env"
mkdir -p "$CACHE/downloads"

verify() { # verify <file>
  local name expected actual
  name="$(basename "$1")"
  expected="$(awk -v n="$name" '$2 == n { print $1 }' "$ROOT/sources/checksums.sha256")"
  [[ -n "$expected" ]] || { echo "no checksum recorded for $name" >&2; return 1; }
  actual="$(sha256sum "$1" | awk '{ print $1 }')"
  [[ "$expected" == "$actual" ]] || { echo "checksum mismatch for $name: $actual" >&2; return 1; }
}

download() { # download <url> <dest>
  if [[ -f "$2" ]] && verify "$2" 2>/dev/null; then return 0; fi
  echo "fetching $1"
  curl -fsSL --retry 3 -o "$2.part" "$1" || { rm -f "$2.part"; return 1; }
  mv "$2.part" "$2"
  verify "$2" || { rm -f "$2"; return 1; }
}

# Fallback for Noto: the file is ~16 MB inside a very large repository, so use a
# blobless sparse checkout of the pinned commit instead of a full clone.
fetch_noto_via_git() {
  local dir="$CACHE/noto-cjk-git"
  rm -rf "$dir"
  GIT_LFS_SKIP_SMUDGE=1 git clone --quiet --no-checkout --filter=blob:none "$NOTO_CJK_REPO" "$dir"
  git -C "$dir" fetch --quiet --depth 1 origin "$NOTO_CJK_COMMIT" 2>/dev/null || true
  git -C "$dir" checkout --quiet "$NOTO_CJK_COMMIT" -- "$NOTO_CJK_PATH" 2>/dev/null \
    || { git -C "$dir" fetch --quiet --unshallow origin 2>/dev/null || true
         git -C "$dir" checkout --quiet "$NOTO_CJK_COMMIT" -- "$NOTO_CJK_PATH"; }
  cp "$dir/$NOTO_CJK_PATH" "$CACHE/downloads/$NOTO_CJK_FILE"
  rm -rf "$dir"
  verify "$CACHE/downloads/$NOTO_CJK_FILE"
}

# --- Hack ---------------------------------------------------------------
download "$HACK_URL" "$CACHE/downloads/$HACK_ARCHIVE"
unzip -oqj "$CACHE/downloads/$HACK_ARCHIVE" "$HACK_MEMBER" -d "$CACHE/hack"

# --- Nerd Fonts font-patcher ---------------------------------------------
download "$NERD_FONTS_URL" "$CACHE/downloads/$NERD_FONTS_ARCHIVE"
rm -rf "$CACHE/nerd-fonts"
mkdir -p "$CACHE/nerd-fonts"
unzip -oq "$CACHE/downloads/$NERD_FONTS_ARCHIVE" -d "$CACHE/nerd-fonts"

# --- Noto Sans CJK TC ------------------------------------------------------
if ! download "${NOTO_CJK_REPO}/raw/${NOTO_CJK_COMMIT}/${NOTO_CJK_PATH}" "$CACHE/downloads/$NOTO_CJK_FILE"; then
  echo "direct download failed, falling back to sparse git checkout" >&2
  rm -f "$CACHE/downloads/$NOTO_CJK_FILE.part"
  fetch_noto_via_git
fi

echo "sources OK: $CACHE"
