# Music Genre Selector

A small Python (tkinter) app that finds your favorite genres from your recent songs
and recommends 20+ songs. Genres and recommendations come from **Last.fm**; Spotify
is used only to read your recently played songs and public playlists.

## 1. Install
Requires Python 3.9+ (tkinter is included with most Python installs).

    pip install -r requirements.txt

## 2. Get Spotify credentials
1. Go to https://developer.spotify.com/dashboard and log in.
2. Click **Create app**. Any name/description is fine.
3. Add this Redirect URI exactly: `http://127.0.0.1:8888/callback`
4. Tick **Web API**, save, then open **Settings** and copy the **Client ID** and **Client secret**.
5. Open **User Management** and add your own Spotify account's email. Apps in Spotify's
   development mode can only be used by accounts listed there.

## 3. Get a Last.fm API key (free)
Create one at https://www.last.fm/api/account/create and copy the **API key**.

## 4. Add your keys
Copy `.env.example` to `.env` and fill in the four values. `.env` is listed in
`.gitignore`, so it is never committed. (You may also set them as normal environment variables.)

## 5. Run

    python main.py

## How to use
- **Connect Spotify** – log in in your browser; your last 10 played songs are analyzed.
- **Paste Playlist** – paste lines like `Song Title - Artist Name` (numbered lines, `Title by Artist`
  and tab-separated rows also work). Tick the box if your lines are `Artist - Title`.
  Up to 30 songs are analyzed.
- **Search Spotify User** – enter a username or profile URL to see public profile info and
  playlists, then analyze a playlist. Spotify does **not** let apps read another person's
  listening history, and this app never tries to get around that.
- Results appear in **Music Preferences** and **Recommended Songs**.

## What each file does
| File | Job |
|---|---|
| `main.py` | The tkinter window, tabs and buttons. Runs the workflow. |
| `spotify_api.py` | Spotify login, recently played songs, user/playlist lookup. |
| `playlist_parser.py` | Turns pasted text into a list of title/artist pairs. |
| `genre_detector.py` | Looks up each song's genre on Last.fm, caches it, counts genres. |
| `music_recommender.py` | Picks 20+ unique songs from your top genres (popular + lesser-known mix). |

## Good to know
- **YouTube:** YouTube's API does not provide watch history, so YouTube playlists are supported
  by copy and paste only.
- **Genres** are crowd-sourced Last.fm tags, so they are approximate. Songs with no usable tag
  are shown as "Unknown" and are not counted.
- If fewer than 20 unique recommendations can be found, the app says so instead of inventing songs.
- Spotify changes its API access rules from time to time. If a playlist cannot be read, use the Paste tab.
- Lookups are cached in `genre_cache.json` (safe to delete).