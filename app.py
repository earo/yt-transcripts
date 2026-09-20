#!/usr/bin/env python3
"""
Light Flask front-end for yt_transcripts.py.

Paste playlist links, video links, or bare IDs (any mix, one per line),
then copy or download whatever comes back.

Run:
    python app.py          # http://127.0.0.1:5001

Requires:
    pip install flask youtube-transcript-api yt-dlp
"""

import io
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, jsonify, render_template, request, send_file
from youtube_transcript_api import YouTubeTranscriptApi

from yt_transcripts import LANGS, expand, safe

app = Flask(__name__)

BARE_ID = re.compile(r"[\w-]{11}")
MAX_WORKERS = 5


def parse_targets(raw):
    """Turn the textarea blob into [(video_id, title), ...], de-duped, order kept.

    Anything that isn't a bare 11-char ID goes through yt-dlp, so a single
    video link, a playlist and a channel are all handled the same way.
    """
    seen, out, errors = set(), [], []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items = [(line, line)] if BARE_ID.fullmatch(line) else expand(line)
        except FileNotFoundError:
            errors.append("yt-dlp not found on PATH - activate the venv that has it")
            continue
        except Exception as e:
            errors.append(f"{line}: couldn't expand ({type(e).__name__})")
            continue

        for vid, title in items:
            if vid and vid not in seen:
                seen.add(vid)
                out.append((vid, title or vid))

    return out, errors


def fetch_one(item, as_json=False):
    vid, title = item
    # a bare ID has no title, so don't stutter it into the filename
    stem = vid if title == vid else f"{safe(title)}_{vid}"
    row = {"id": vid, "title": title, "stem": stem}
    try:
        fetched = YouTubeTranscriptApi().fetch(vid, languages=LANGS)
    except Exception as e:
        row.update(ok=False, error=f"{type(e).__name__}: {e}", text="")
        return row

    if as_json:
        import json as _json
        row["text"] = _json.dumps(fetched.to_raw_data(), indent=2)
    else:
        row["text"] = " ".join(s.text.strip() for s in fetched if s.text.strip())
    row.update(ok=True, error=None)
    return row


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/transcripts")
def api_transcripts():
    data = request.get_json(silent=True) or {}
    raw = (data.get("input") or "").strip()
    as_json = bool(data.get("json"))

    if not raw:
        return jsonify(results=[], errors=["nothing pasted in"])

    targets, errors = parse_targets(raw)
    if not targets:
        return jsonify(results=[], errors=errors or ["no videos found"])

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(lambda t: fetch_one(t, as_json), targets))

    return jsonify(results=results, errors=errors)


@app.post("/api/zip")
def api_zip():
    """Bundle whatever the page currently holds into one download."""
    rows = (request.get_json(silent=True) or {}).get("results") or []
    rows = [r for r in rows if r.get("text")]
    if not rows:
        return jsonify(error="nothing to zip"), 400

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for r in rows:
            z.writestr(r["filename"], r["text"])
    buf.seek(0)
    return send_file(buf, mimetype="application/zip",
                     as_attachment=True, download_name="transcripts.zip")


if __name__ == "__main__":
    # 5000 is AirPlay Receiver on macOS, so 5001
    app.run(debug=True, port=5001)
