# yt-transcripts

Pull transcripts off YouTube in bulk — from a playlist, a channel, a handful of
video links, or bare video IDs. Comes as a CLI and a small Flask webapp that
share the same engine.

## Install

```bash
pip install flask youtube-transcript-api yt-dlp
```

`yt-dlp` needs to be on your `PATH` — it's what expands a playlist or channel
link into individual videos.

## CLI

```bash
python yt_transcripts.py "https://www.youtube.com/playlist?list=PL..."
```

Transcripts land in `transcripts/` as one `.txt` per video, named
`Video_Title_<id>.txt`. Videos are fetched in parallel, and a failure on one
doesn't stop the rest — it prints a `FAIL` line and moves on.

Mix input types freely; anything that isn't a bare 11-character ID goes through
`yt-dlp`, so playlists, channels and single video links all work:

```bash
python yt_transcripts.py "https://youtu.be/VIDEO_ID" ANOTHER_ID -o out -j 10
```

| flag | what it does |
| --- | --- |
| `-o, --outdir` | where to write (default `transcripts/`) |
| `-j, --jobs` | parallel fetches (default 5) |
| `--json` | keep timestamps, write JSON instead of flat text |

## Webapp

```bash
python app.py
```

Then open <http://127.0.0.1:5001>. (Port 5001 because macOS hands 5000 to
AirPlay Receiver.)

Paste any mix of playlist links, video links and bare IDs — one per line — and
hit **get transcripts**. Results de-duplicate across sources, so a playlist plus
one of its own videos still gives you one copy.

Each result gets its own **copy** and **download** button. For the whole batch:

- **copy all** — everything to the clipboard in one go
- **one combined file** — a single file, sections delimited by video title
- **separate files** — one file per video
- **.zip** — the batch as a single archive

Pick `.txt` or `.md` with the format selector. Markdown gets a heading and the
video URL per transcript; combined Markdown separates videos with `---`.

Ticking **keep timestamps (JSON)** overrides the format selector and gives you
valid JSON — the combined download becomes a proper JSON array rather than
concatenated blobs.

## Notes

YouTube rate-limits transcript requests by IP, and pulling a lot in a short
window will get you temporarily blocked (`IpBlocked`). It clears on its own.
Lower `-j` if you hit it often.

Not every video has a transcript, and some have them disabled — those come back
as per-video errors rather than taking down the run.

## Layout

```
yt_transcripts.py    CLI — link expansion, parallel fetch, file writing
app.py               Flask routes; imports expand()/safe() from the CLI
templates/index.html the entire frontend, no build step, no dependencies
```
