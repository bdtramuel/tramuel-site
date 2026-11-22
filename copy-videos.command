#!/bin/bash
# Saves the videos and audio files from the old Squarespace site, which its
# export leaves out, before the Squarespace plan ends.
#   Videos -> tools/video-raw/   (Claude turns these into the posts' video files)
#   Audio  -> tools/audio-archive/ (kept on your Mac, not published)
# Neither folder goes to GitHub. Safe to run more than once.

cd "$(dirname "$0")" || exit 1
set -f    # web addresses contain ? and *, which the shell must leave alone
CDN="https://video.squarespace-cdn.com/content/v1/51f40a7be4b0339265c57592"
RAW="tools/video-raw"
AUDIO="tools/audio-archive"
LOG="tools/video-download-results.txt"
mkdir -p "$RAW" "$AUDIO"
: > "$LOG"

# Replace every copy of $1 with $2 in the text on stdin (plain text, no patterns).
swap() {
  awk -v o="$1" -v n="$2" '{ s = ""; while ((i = index($0, o)) > 0) { s = s substr($0, 1, i - 1) n; $0 = substr($0, i + length(o)) } print s $0 }'
}

# Save one HLS track ($1 = playlist URL) into folder $2 as $3.m3u8, with its
# key and media files beside it, so ffmpeg can read it with no network.
save_track() {
  local list url n
  list=$(curl -fsSL "$1") || return 1
  n=0
  for url in $(printf '%s\n' "$list" | sed -n 's/.*URI="\([^"]*\)".*/\1/p' | sort -u); do
    n=$((n + 1))
    curl -fsSL -o "$2/$3-key$n.key" "$url" || return 1
    list=$(printf '%s\n' "$list" | swap "$url" "$3-key$n.key")
  done
  n=0
  for url in $(printf '%s\n' "$list" | grep -v '^#' | grep -v '\.key$' | grep . | sort -u); do
    n=$((n + 1))
    curl -fsSL --retry 3 -o "$2/$3-$n.ts" "$url" || return 1
    list=$(printf '%s\n' "$list" | swap "$url" "$3-$n.ts")
  done
  printf '%s\n' "$list" > "$2/$3.m3u8"
}

total=$(grep -c . tools/video-list.txt)
count=0
while IFS=$'\t' read -r id post; do
  [ -z "$id" ] && continue
  count=$((count + 1))
  dir="$RAW/$id"
  if [ -s "$dir/video.m3u8" ]; then
    echo "ok $id already saved" >> "$LOG"; continue
  fi
  mkdir -p "$dir"
  echo "Video $count of $total  ($post)"
  master=$(curl -fsSL "$CDN/$id/playlist.m3u8")
  if [ -z "$master" ]; then echo "failed $id no-playlist $post" >> "$LOG"; continue; fi
  # The sharpest version of the picture, and the sound if it is separate.
  video=$(printf '%s\n' "$master" | awk '/^#EXT-X-STREAM-INF/ { match($0, /BANDWIDTH=[0-9]+/); bw = substr($0, RSTART + 10, RLENGTH - 10) + 0; getline u; if (bw > best) { best = bw; url = u } } END { print url }')
  audio=$(printf '%s\n' "$master" | grep '^#EXT-X-MEDIA:TYPE=AUDIO' | head -1 | sed -n 's/.*URI="\([^"]*\)".*/\1/p')
  if ! save_track "$video" "$dir" video; then echo "failed $id video $post" >> "$LOG"; rm -f "$dir/video.m3u8"; continue; fi
  if [ -n "$audio" ] && ! save_track "$audio" "$dir" audio; then echo "failed $id audio $post" >> "$LOG"; rm -f "$dir/video.m3u8"; continue; fi
  echo "ok $id $post" >> "$LOG"
done < tools/video-list.txt

echo "Saving the audio files..."
while IFS=$'\t' read -r url name; do
  [ -z "$url" ] && continue
  if [ -s "$AUDIO/$name" ] || curl -fsSL --retry 3 -o "$AUDIO/$name" "$url"; then
    echo "ok audio $name" >> "$LOG"
  else
    echo "failed audio $name" >> "$LOG"
  fi
done < tools/audio-list.txt

ok=$(grep -c '^ok' "$LOG"); bad=$(grep -c '^failed' "$LOG")
echo
echo "Done: $ok saved, $bad failed. Details in $LOG"
echo "You can close this window and tell Claude it's finished."
