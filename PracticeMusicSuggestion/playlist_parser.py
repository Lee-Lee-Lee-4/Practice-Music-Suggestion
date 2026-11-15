"""playlist_parser.py - Turns pasted playlist text into a list of songs.

Each song is a simple dictionary: {"title": "...", "artist": "..."}
Supported line styles (one song per line):
    Song Title - Artist Name
    1. Song Title - Artist Name
    Song Title by Artist Name
    Song Title <TAB> Artist Name      (copied from Spotify's web player)
"""
import re

# Things like "(Official Video)" or "[Lyrics]" that YouTube titles often contain
NOISE = re.compile(
    r"\s*[\(\[](official|lyrics?|lyric video|audio|video|music video|hd|hq|visualizer|remaster)[^\)\]]*[\)\]]",
    re.IGNORECASE,
)
SEPARATORS = [" - ", " – ", " — ", " | "]


def clean_text(text):
    """Remove list numbers, noise like '(Official Video)' and '- Topic'."""
    text = re.sub(r"^\s*\d+[\.\)]\s+", "", text)  # "1. " or "1) "
    text = NOISE.sub("", text)
    text = re.sub(r"\s*-\s*Topic\s*$", "", text, flags=re.IGNORECASE)
    return text.strip()


def split_line(line, artist_first):
    """Split one line into (title, artist). Returns None if it can't be split."""
    # Tab-separated rows (Spotify web player copy)
    if "\t" in line:
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if parts and parts[0].isdigit():
            parts = parts[1:]
        if len(parts) >= 2:
            return parts[0], parts[1]

    line = clean_text(line)
    for sep in SEPARATORS:
        if sep in line:
            first, second = line.split(sep, 1)
            return (second, first) if artist_first else (first, second)

    # "Title by Artist"
    parts = re.split(r"\s+by\s+", line, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        return parts[0], parts[1]
    return None


def parse_playlist(text, artist_first=False):
    """Return (songs, skipped_lines). Duplicate songs are removed."""
    songs, skipped, seen = [], [], set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("http"):
            continue
        result = split_line(line, artist_first)
        if result is None:
            skipped.append(line)
            continue
        title, artist = result[0].strip(), clean_text(result[1])
        if not title or not artist:
            skipped.append(line)
            continue
        key = (title.lower(), artist.lower())
        if key not in seen:
            seen.add(key)
            songs.append({"title": title, "artist": artist})
    return songs, skipped