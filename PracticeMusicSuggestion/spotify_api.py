"""spotify_api.py - Everything that talks to Spotify (official Web API via spotipy).

Credentials come from environment variables (see README.md):
    SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI
"""
import os
import re

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_CACHE = os.path.join(BASE_DIR, ".spotify_token_cache")


def credentials_set():
    """True if the Spotify client ID and secret are available."""
    return bool(os.environ.get("SPOTIPY_CLIENT_ID") and os.environ.get("SPOTIPY_CLIENT_SECRET"))


def track_to_song(track):
    """Convert a Spotify track object to our simple song dictionary."""
    return {"title": track["name"], "artist": track["artists"][0]["name"]}


def get_recent_songs(limit=10):
    """Log in (opens the browser) and return YOUR last played songs."""
    auth = SpotifyOAuth(
        scope="user-read-recently-played",
        redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
        cache_path=TOKEN_CACHE,
    )
    sp = spotipy.Spotify(auth_manager=auth)
    items = sp.current_user_recently_played(limit=limit)["items"]
    return [track_to_song(item["track"]) for item in items if item.get("track")]


def extract_user_id(text):
    """Accept a username, a profile URL or a spotify:user: URI."""
    text = text.strip()
    match = re.search(r"open\.spotify\.com/(?:intl-[a-z]+/)?user/([^/?\s]+)", text)
    if match:
        return match.group(1)
    if text.startswith("spotify:user:"):
        return text.split(":")[2]
    return text


def search_user(text):
    """Look up a PUBLIC profile. Returns (profile_info, playlists).

    Spotify does not allow reading another person's listening history,
    so we only return public profile info and public playlists.
    """
    user_id = extract_user_id(text)
    auth = SpotifyClientCredentials()  # reads the SPOTIPY_* variables
    sp = spotipy.Spotify(auth_manager=auth)
    try:
        profile = sp.user(user_id)
        playlist_items = sp.user_playlists(user_id, limit=50).get("items", [])
    except spotipy.SpotifyException:
        raise RuntimeError("Spotify user '%s' was not found (or the profile is not accessible)." % user_id)

    info = {
        "name": profile.get("display_name") or user_id,
        "followers": (profile.get("followers") or {}).get("total"),
    }
    playlists = [{"id": p["id"], "name": p["name"]} for p in playlist_items if p]
    return info, playlists


def get_playlist_songs(playlist_id, limit=30):
    """Return up to `limit` songs from a public playlist."""
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
    try:
        items = sp.playlist_items(playlist_id, limit=limit).get("items", [])
    except spotipy.SpotifyException:
        raise RuntimeError(
            "Spotify did not allow reading this playlist (it may be private or restricted).\n"
            "Copy its songs and use the 'Paste Playlist' tab instead."
        )
    songs = []
    for entry in items:
        track = entry.get("track") or entry.get("item")  # field name differs by API version
        if track and track.get("name") and track.get("artists"):
            songs.append(track_to_song(track))
    return songs