#!/bin/bash
# Preview tramuel.com on this Mac.
# Double-click this file. The site opens at http://localhost:1313 and updates
# as files change. Close the Terminal window to stop it.

cd "$(dirname "$0")" || exit 1
HUGO_VERSION=0.161.1
HUGO="tools/bin/hugo"

if [ ! -x "$HUGO" ]; then
  echo "Getting Hugo $HUGO_VERSION (first time only)..."
  mkdir -p tools/bin
  TMP="$(mktemp -d)"
  curl -fL --progress-bar -o "$TMP/hugo.pkg" \
    "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_darwin-universal.pkg" \
    || { echo "Download failed."; exit 1; }
  # Unpack the installer instead of running it, so nothing needs an admin password.
  pkgutil --expand-full "$TMP/hugo.pkg" "$TMP/unpacked" >/dev/null || { echo "Could not unpack Hugo."; exit 1; }
  FOUND="$(find "$TMP/unpacked" -type f -name hugo | head -1)"
  [ -n "$FOUND" ] || { echo "Hugo was not in the download."; exit 1; }
  cp "$FOUND" "$HUGO" && chmod +x "$HUGO"
  rm -rf "$TMP"
fi

echo "Building the site. It opens in your browser in a few seconds."
(sleep 6; open "http://localhost:1313/") &
"$HUGO" server --disableFastRender 2>&1 | tee tools/preview.log
