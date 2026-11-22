"""Turns what copy-videos.command saved into each post's video file.

For every video in tools/video-raw/<id>/: unlocks the stream (Squarespace sends
it in AES-128 pieces, with the key alongside), joins picture and sound, and
writes content/<post>/video.mp4 (720p, H.264) plus video.jpg as its poster.
Records each finished one in tools/video-results.txt and skips those next time.

Usage (from the site folder): python3 tools/convert_videos.py [seconds]
Stops starting new videos after the given number of seconds (default 150).
"""
import json, os, re, subprocess, sys, time

site = '.'
budget = float(sys.argv[1]) if len(sys.argv) > 1 else 150
began = time.time()
raw_root = os.path.join(site, 'tools', 'video-raw')
results = os.path.join(site, 'tools', 'video-results.txt')
videos = json.load(open(os.path.join(site, 'tools', 'videos.json'), encoding='utf-8'))

done = set()
if os.path.exists(results):
    done = {l.split()[1] for l in open(results) if l.startswith('ok ')}

# File name for each video: video.mp4, then video-2.mp4 for a second one in the same post.
names, seen = {}, {}
for v in videos:
    seen[v['post']] = seen.get(v['post'], 0) + 1
    n = seen[v['post']]
    names[v['id']] = 'video.mp4' if n == 1 else f'video-{n}.mp4'


def unlock(folder, track):
    """Decrypt and join the pieces of one track into a single .ts file."""
    playlist = os.path.join(folder, track + '.m3u8')
    out_path = os.path.join(folder, track + '.plain.ts')
    key = iv = None
    seq = 0
    rng = None
    ends = {}
    with open(out_path, 'wb') as out:
        for line in open(playlist, encoding='utf-8'):
            line = line.strip()
            if line.startswith('#EXT-X-MEDIA-SEQUENCE:'):
                seq = int(line.split(':', 1)[1])
            elif line.startswith('#EXT-X-KEY:'):
                if 'METHOD=NONE' in line:
                    key = iv = None
                else:
                    uri = re.search(r'URI="([^"]+)"', line).group(1)
                    key = open(os.path.join(folder, uri), 'rb').read().hex()
                    m = re.search(r'IV=0[xX]([0-9a-fA-F]+)', line)
                    iv = m.group(1).rjust(32, '0') if m else None
            elif line.startswith('#EXT-X-BYTERANGE:'):
                rng = line.split(':', 1)[1]
            elif line and not line.startswith('#'):
                path = os.path.join(folder, line)
                with open(path, 'rb') as fh:
                    if rng:
                        length, _, start = rng.partition('@')
                        start = int(start) if start else ends.get(line, 0)
                        fh.seek(start)
                        piece = fh.read(int(length))
                        ends[line] = start + int(length)
                    else:
                        piece = fh.read()
                rng = None
                if key:
                    piece = subprocess.run(
                        ['openssl', 'enc', '-d', '-aes-128-cbc', '-K', key,
                         '-iv', iv or format(seq, '032x')],
                        input=piece, capture_output=True, check=True).stdout
                out.write(piece)
                seq += 1
    return out_path


made = failed = 0
for v in videos:
    vid = v['id']
    if vid in done:
        continue
    if time.time() - began > budget:
        break
    folder = os.path.join(raw_root, vid)
    if not os.path.exists(os.path.join(folder, 'video.m3u8')):
        continue
    post_dir = os.path.join(site, 'content', v['post'].strip('/'))
    name = names[vid]
    target = os.path.join(post_dir, name)
    poster = target[:-4] + '.jpg'
    try:
        picture = unlock(folder, 'video')
        sound = unlock(folder, 'audio') if os.path.exists(os.path.join(folder, 'audio.m3u8')) else None
        # Fit within 1280 on the long side; phone clips stay upright.
        scale = "scale='if(gte(iw,ih),min(1280,iw),-2)':'if(gte(iw,ih),-2,min(1280,ih))'"
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', picture]
        if sound:
            cmd += ['-i', sound]
        cmd += ['-map', '0:v:0']
        cmd += ['-map', '1:a:0?'] if sound else ['-map', '0:a:0?']
        cmd += ['-vf', scale, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28',
                '-profile:v', 'high', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '96k', '-ac', '2',
                '-movflags', '+faststart', target + '.part.mp4']
        subprocess.run(cmd, check=True, capture_output=True)
        os.replace(target + '.part.mp4', target)
        at = '1' if v['dur'] >= 3 else '0'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', at, '-i', target,
                        '-frames:v', '1', '-q:v', '4', poster],
                       check=True, capture_output=True)
        with open(results, 'a') as fh:
            fh.write(f'ok {vid} {name} {os.path.getsize(target)} {v["post"]}\n')
        made += 1
        print('made', v['post'], name, os.path.getsize(target) // 1024, 'KB')
    except Exception as err:                     # keep going; report at the end
        failed += 1
        detail = getattr(err, 'stderr', b'') or b''
        print('FAILED', v['post'], vid, str(err)[:120], detail[-300:].decode('utf-8', 'replace'))
    finally:
        for track in ('video', 'audio'):         # free the space the joined copies used
            tmp = os.path.join(folder, track + '.plain.ts')
            if os.path.exists(tmp):
                open(tmp, 'wb').close()

left = sum(1 for v in videos if v['id'] not in done) - made
print(f'{made} made, {failed} failed, {left} still to do')
