#!/bin/bash
# Copies every photo the old posts use from Squarespace into the post folders,
# so the site stops depending on Squarespace. Safe to run again: it skips
# photos it already has.

cd "$(dirname "$0")" || exit 1
LIST="tools/image-list.txt"
export RESULTS="tools/image-results.txt"
: > "$RESULTS"

fetch() {
  dest="$1"; url="$2"
  for ext in jpg png gif webp; do
    if [ -s "$dest.$ext" ]; then echo "ok $url $dest.$ext" >> "$RESULTS"; return; fi
  done
  tmp="$dest.part"
  type=$(curl -fsSL --retry 2 --max-time 90 -o "$tmp" -w '%{content_type}' "$url?format=1500w") \
    || { rm -f "$tmp"; echo "fail $url $dest" >> "$RESULTS"; return; }
  case "$type" in
    image/png*)  ext=png ;;
    image/gif*)  ext=gif ;;
    image/webp*) ext=webp ;;
    *)           ext=jpg ;;
  esac
  mv "$tmp" "$dest.$ext" && echo "ok $url $dest.$ext" >> "$RESULTS"
}
export -f fetch

total=$(grep -c . "$LIST")
echo "Copying $total photos from Squarespace, eight at a time."
echo "This takes roughly 10 to 20 minutes. Leave this window open."
xargs -n 2 -P 8 bash -c 'fetch "$1" "$2"' _ < "$LIST" &
pid=$!
while kill -0 "$pid" 2>/dev/null; do
  printf "\r%s of %s done" "$(grep -c . "$RESULTS")" "$total"
  sleep 3
done
echo
echo "Finished: $(grep -c '^ok ' "$RESULTS") copied, $(grep -c '^fail ' "$RESULTS") could not be reached."
echo "You can close this window and tell Claude it's done."
