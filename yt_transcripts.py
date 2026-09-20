#!/usr/bin/env python3
"""
Batch-download YouTube transcripts.

Usage:
    python yt_transcripts.py <playlist-or-video-url> [more urls...] [-o OUTDIR] [-j N]

Examples:
    python yt_transcripts.py "https://www.youtube.com/playlist?list=PLxxxx"
    python yt_transcripts.py vid1 vid2 vid3 -o transcripts -j 5

Requires:
    pip install youtube-transcript-api yt-dlp
"""

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi

LANGS = ["en", "en-US", "en-GB"]


def expand(url):
    """Return [(video_id, title), ...] for a playlist, channel, or single video."""
    out = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--no-warnings",
         "--print", "%(id)s\t%(title)s", url],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    items = []
    for line in out.splitlines():
        vid, _, title = line.partition("\t")
        items.append((vid, title or vid))
    return items


def safe(name, limit=80):
    name = re.sub(r"[^\w\s.-]", "", name).strip()
    return re.sub(r"\s+", "_", name)[:limit] or "untitled"


def grab(item, outdir, as_json=False):
    vid, title = item
    try:
        fetched = YouTubeTranscriptApi().fetch(vid, languages=LANGS)
    except Exception as e:
        return f"FAIL {vid} ({title}): {type(e).__name__}: {e}"

    stem = outdir / f"{safe(title)}_{vid}"
    if as_json:
        path = stem.with_suffix(".json")
        path.write_text(json.dumps(fetched.to_raw_data(), indent=2), encoding="utf-8")
    else:
        path = stem.with_suffix(".txt")
        text = " ".join(s.text.strip() for s in fetched if s.text.strip())
        path.write_text(text, encoding="utf-8")
    return f"OK   {path.name}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("urls", nargs="+", help="playlist URLs, video URLs, or bare video IDs")
    p.add_argument("-o", "--outdir", default="transcripts")
    p.add_argument("-j", "--jobs", type=int, default=5)
    p.add_argument("--json", action="store_true", help="keep timestamps, write JSON")
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    items = []
    for u in args.urls:
        if re.fullmatch(r"[\w-]{11}", u):      # bare video ID
            items.append((u, u))
        else:
            items.extend(expand(u))

    # de-dupe, keep order
    seen, uniq = set(), []
    for vid, title in items:
        if vid not in seen:
            seen.add(vid)
            uniq.append((vid, title))

    print(f"{len(uniq)} video(s) -> {outdir}/", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for line in pool.map(lambda i: grab(i, outdir, args.json), uniq):
            print(line)


if __name__ == "__main__":
    main()
