"""music_recommender.py - Builds a list of recommended songs.

For each of the user's top genres we ask Last.fm for that genre's top tracks,
then mix well-known songs (top of the list) with less-known ones (further down).
Songs the user already has are skipped, and no song appears twice.
"""
import random

import requests

from genre_detector import lastfm_request

TOP_GENRES = 4          # how many of the user's genres to use
TRACKS_PER_GENRE = 60   # how many tracks to fetch per genre
POPULAR_COUNT = 20      # the first 20 are treated as "popular"


def fetch_genre_tracks(genre):
    """Top tracks for a genre as a list of {"title", "artist", "genre"}."""
    try:
        data = lastfm_request("tag.gettoptracks", tag=genre.lower(), limit=TRACKS_PER_GENRE)
    except (RuntimeError, requests.RequestException):
        return []
    tracks = data.get("tracks", {}).get("track", [])
    if isinstance(tracks, dict):
        tracks = [tracks]
    result = []
    for t in tracks:
        artist = t.get("artist", {})
        artist = artist.get("name", "") if isinstance(artist, dict) else str(artist)
        if t.get("name") and artist:
            result.append({"title": t["name"], "artist": artist, "genre": genre})
    return result


def mixed_order(tracks):
    """Shuffle popular and less-known tracks, then alternate between them."""
    popular, others = tracks[:POPULAR_COUNT], tracks[POPULAR_COUNT:]
    random.shuffle(popular)
    random.shuffle(others)
    mixed = []
    for i in range(max(len(popular), len(others))):
        if i < len(popular):
            mixed.append(popular[i])
        if i < len(others):
            mixed.append(others[i])
    return mixed


def recommend_songs(genre_counts, known_songs, total=20):
    """Return (recommendations, message). genre_counts = [(genre, count), ...]."""
    if not genre_counts:
        return [], "No genres were detected, so no recommendations can be made."

    top = genre_counts[:TOP_GENRES]
    seen = {(s["title"].lower(), s["artist"].lower()) for s in known_songs}
    pools = {genre: mixed_order(fetch_genre_tracks(genre)) for genre, _ in top}
    sum_counts = sum(count for _, count in top)

    recs = []

    def take(genre, how_many):
        """Move up to how_many unseen tracks from a genre's pool into recs."""
        taken = 0
        while pools[genre] and taken < how_many and len(recs) < total:
            track = pools[genre].pop(0)
            key = (track["title"].lower(), track["artist"].lower())
            if key not in seen:
                seen.add(key)
                recs.append(track)
                taken += 1

    # Pass 1: give each genre a share based on how often the user plays it
    for genre, count in top:
        take(genre, max(1, round(total * count / sum_counts)))
    # Pass 2: fill any gap, favouring the most-played genres
    while len(recs) < total and any(pools.values()):
        for genre, _ in top:
            take(genre, 1)

    if len(recs) < total:
        return recs, "Only %d recommendations were found (fewer than %d). Nothing was made up." % (len(recs), total)
    return recs, ""