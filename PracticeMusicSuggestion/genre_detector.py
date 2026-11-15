"""genre_detector.py - Finds each song's genre using the free Last.fm API.

Spotify no longer attaches genres to tracks, so we ask Last.fm for the
most popular "tags" of a song (or its artist) and use the first real genre.
Get a free key at https://www.last.fm/api/account/create
Results are saved in genre_cache.json so repeat lookups are instant.
"""
import json
import os
import re
from collections import Counter

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "genre_cache.json")
LASTFM_URL = "https://ws.audioscrobbler.com/2.0/"

# Last.fm tags that are not genres
IGNORED_TAGS = {
    "seen live", "favorites", "favourites", "favorite", "love", "loved", "awesome",
    "good", "beautiful", "best", "cool", "catchy", "male vocalists", "female vocalists",
    "american", "british", "english", "usa", "uk", "my music", "albums i own",
    "spotify", "all", "mix", "playlist", "under 2000 listeners", "singer-songwriter",
}


def lastfm_request(method, **params):
    """Call the Last.fm API and return the JSON answer."""
    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        raise RuntimeError("LASTFM_API_KEY is not set. See README.md (Step 3).")
    params.update({"method": method, "api_key": api_key, "format": "json"})
    response = requests.get(LASTFM_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError("Last.fm error: " + str(data.get("message", "unknown")))
    return data


def get_tags(method, **params):
    """Return a list of tag names for a track or artist ([] if none/failed)."""
    try:
        data = lastfm_request(method, autocorrect=1, **params)
    except (RuntimeError, requests.RequestException):
        return []
    tags = data.get("toptags", {}).get("tag", [])
    if isinstance(tags, dict):  # Last.fm returns a dict when there is one tag
        tags = [tags]
    return [t.get("name", "") for t in tags]


def pick_genre(tag_names):
    """Return the first tag that looks like a real genre, or None."""
    for name in tag_names:
        name = name.strip().lower()
        if not name or name in IGNORED_TAGS or len(name) > 25:
            continue
        if re.fullmatch(r"\d{2,4}s?", name):  # years/decades like "80s"
            continue
        return name.title()
    return None


def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except OSError:
        pass  # the cache is optional


def detect_genre(title, artist, cache):
    """Genre of one song. Tries the song's tags first, then the artist's."""
    key = (title + "|" + artist).lower()
    if key in cache:
        return cache[key]
    genre = pick_genre(get_tags("track.gettoptags", track=title, artist=artist))
    if genre is None:
        genre = pick_genre(get_tags("artist.gettoptags", artist=artist))
    if genre is None:
        return "Unknown"  # not cached, so we can retry later
    cache[key] = genre
    return genre


def analyze_songs(songs, progress=None):
    """Add a "genre" entry to every song. progress(i, total) is optional."""
    if not os.environ.get("LASTFM_API_KEY"):
        raise RuntimeError("LASTFM_API_KEY is not set. See README.md (Step 3).")
    cache = load_cache()
    for i, song in enumerate(songs, start=1):
        song["genre"] = detect_genre(song["title"], song["artist"], cache)
        if progress:
            progress(i, len(songs))
    save_cache(cache)
    return songs


def count_genres(songs):
    """Return [(genre, count), ...] most common first. 'Unknown' is left out."""
    counter = Counter(s["genre"] for s in songs if s.get("genre") != "Unknown")
    return counter.most_common()