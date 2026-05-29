#!/usr/bin/env bash
set -euo pipefail

DEST="${1:-/Users/cc/.hermes}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"

if [[ "$(id -u)" == "0" ]]; then
  echo "Do not run as root." >&2
  exit 1
fi

mkdir -p "$DEST"

# Copy files individually so an existing docs/ or scripts/ directory is not moved wholesale.
while IFS= read -r -d '' src; do
  rel="${src#"$SRC_DIR/"}"

  # Do not copy generated archives if someone runs this script from an unpacked directory that also contains them.
  case "$rel" in
    *.zip|*.tar.gz|ops/*) continue ;;
  esac

  dst="$DEST/$rel"
  mkdir -p "$(dirname "$dst")"

  if [[ -e "$dst" ]]; then
    bak="$dst.backup-$STAMP"
    echo "Backing up existing file: $dst -> $bak"
    mv "$dst" "$bak"
  fi

  cp "$src" "$dst"
  echo "Installed $rel"
done < <(find "$SRC_DIR" -type f -print0)

mkdir -p "$DEST/ops" "/Users/cc/HermesArchive"

# Restore executable bit for scripts.
find "$DEST/scripts" -type f -name '*.sh' -exec chmod 0755 {} + 2>/dev/null || true

echo "Plan system installed to $DEST"
echo "No Hermes production config, .env, auth.json, launchd plist, or gateway service state was modified."
echo "Next: open $DEST in CodexDesktop and run CODEX_DESKTOP_GOAL_PROMPT.md"
