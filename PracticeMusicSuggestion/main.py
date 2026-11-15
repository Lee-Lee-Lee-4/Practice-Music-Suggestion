"""main.py - Simple Music Genre Selector & Song Recommender (tkinter window).

Run with:  python main.py
"""
import os
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import playlist_parser
import spotify_api
from genre_detector import analyze_songs, count_genres
from music_recommender import recommend_songs

MAX_SPOTIFY_SONGS = 10    # spotify "recently played" size
MAX_PLAYLIST_SONGS = 30   # limit for pasted/public playlists (keeps lookups quick)
TAB_PREFERENCES, TAB_RECOMMENDED = 4, 5

state = {"playlists": []}  # playlists found by the user search


def load_env_file():
    """Load KEY=VALUE lines from a local .env file into environment variables."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"'))


load_env_file()
os.environ.setdefault("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

root = tk.Tk()
root.title("Music Genre Selector")
root.geometry("840x620")


# ---------- helpers ----------
def set_status(text):
    status.set(text)
    root.update()


def write_box(box, text):
    """Replace the text of a read-only text box."""
    box.config(state="normal")
    box.delete("1.0", "end")
    box.insert("1.0", text)
    box.config(state="disabled")


def show_preferences(songs, genres):
    lines = ["Recently Played Songs:"]
    for i, s in enumerate(songs, start=1):
        lines.append("%d. %s - %s (%s)" % (i, s["title"], s["artist"], s["genre"]))

    lines.append("")
    lines.append("Detected Music Preferences:")
    total = sum(count for _, count in genres)
    for genre, count in genres:
        percent = count / total * 100
        lines.append("- %s: %d song%s (%.0f%%) %s" % (genre, count, "" if count == 1 else "s", percent, "#" * int(percent // 5)))

    unknown = sum(1 for s in songs if s["genre"] == "Unknown")
    if unknown:
        lines.append("(%d song%s had no genre information and were not counted.)" % (unknown, "" if unknown == 1 else "s"))
    lines.append("")
    lines.append("Most Preferred Genre: " + (genres[0][0] if genres else "Unknown"))
    write_box(prefs_box, "\n".join(lines))


def show_recommendations(recs, message):
    lines = ["Recommended Songs:", ""]
    for i, r in enumerate(recs, start=1):
        lines.append("%d. %s - %s (%s)" % (i, r["title"], r["artist"], r["genre"]))
    if message:
        lines += ["", message]
    write_box(recs_box, "\n".join(lines))


def process_songs(songs):
    """Steps 3-7: detect genres, count them, recommend, and show the results."""
    if not songs:
        messagebox.showinfo("No songs", "No songs were found to analyze.")
        return
    try:
        set_status("Looking up genres...")
        analyze_songs(songs, progress=lambda i, n: set_status("Looking up genres... %d/%d" % (i, n)))
        genres = count_genres(songs)
        show_preferences(songs, genres)
        set_status("Finding recommendations...")
        recs, message = recommend_songs(genres, songs)
        show_recommendations(recs, message)
        notebook.select(TAB_PREFERENCES)
        set_status("Done. Analyzed %d songs." % len(songs))
    except Exception as error:  # basic error handling for the whole workflow
        set_status("Something went wrong.")
        messagebox.showerror("Error", str(error))


def need_spotify_keys():
    if spotify_api.credentials_set():
        return False
    messagebox.showwarning("Spotify keys missing", "Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET first (see README.md).")
    return True


# ---------- button actions ----------
def on_connect_spotify():
    if need_spotify_keys():
        return
    try:
        set_status("Waiting for Spotify login in your browser...")
        songs = spotify_api.get_recent_songs(MAX_SPOTIFY_SONGS)
    except Exception as error:
        set_status("Spotify connection failed.")
        messagebox.showerror("Spotify error", str(error))
        return
    process_songs(songs)


def on_analyze_paste():
    text = paste_box.get("1.0", "end").strip()
    if not text:
        messagebox.showinfo("Empty", "Please paste some songs first.")
        return
    songs, skipped = playlist_parser.parse_playlist(text, artist_first.get())
    if skipped:
        messagebox.showinfo("Some lines skipped", "%d line(s) could not be read, for example:\n%s" % (len(skipped), skipped[0]))
    process_songs(songs[:MAX_PLAYLIST_SONGS])


def on_search_user():
    if need_spotify_keys():
        return
    text = search_entry.get().strip()
    if not text:
        messagebox.showinfo("Empty", "Enter a Spotify username or profile URL.")
        return
    try:
        set_status("Searching Spotify...")
        info, playlists = spotify_api.search_user(text)
    except Exception as error:
        set_status("Search failed.")
        messagebox.showerror("Search error", str(error))
        return
    state["playlists"] = playlists
    followers = info["followers"] if info["followers"] is not None else "not shown"
    profile_label.config(text="Name: %s\nFollowers: %s\nPublic playlists found: %d" % (info["name"], followers, len(playlists)))
    playlist_list.delete(0, "end")
    for p in playlists:
        playlist_list.insert("end", p["name"])
    set_status("Search finished.")
    if not playlists:
        messagebox.showinfo("No playlists", "No public playlists found. Paste a playlist on the 'Paste Playlist' tab instead.")


def on_analyze_playlist():
    chosen = playlist_list.curselection()
    if not chosen:
        messagebox.showinfo("Choose one", "Select a playlist from the list first.")
        return
    playlist = state["playlists"][chosen[0]]
    try:
        set_status("Reading playlist...")
        songs = spotify_api.get_playlist_songs(playlist["id"], MAX_PLAYLIST_SONGS)
    except Exception as error:
        set_status("Could not read playlist.")
        messagebox.showerror("Playlist error", str(error))
        return
    process_songs(songs)


# ---------- window layout ----------
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=8, pady=8)


def make_tab(name):
    tab = ttk.Frame(notebook, padding=12)
    notebook.add(tab, text=name)
    return tab


# tab 0: Home
home = make_tab("Home")
ttk.Label(home, text="Music Genre Selector", font=("Arial", 20, "bold")).pack(pady=(20, 5))
ttk.Label(home, text="Find your favorite genres from your recent songs\nand get 20+ song recommendations.", justify="center").pack(pady=10)
ttk.Button(home, text="1. Connect Spotify", width=30, command=lambda: notebook.select(1)).pack(pady=5)
ttk.Button(home, text="2. Paste Playlist", width=30, command=lambda: notebook.select(2)).pack(pady=5)
ttk.Button(home, text="3. Search Spotify User", width=30, command=lambda: notebook.select(3)).pack(pady=5)

# tab 1: Connect Spotify
connect = make_tab("Connect Spotify")
ttk.Label(connect, text="Log in with Spotify to analyze YOUR last 10 played songs.\nA browser window will open so you can approve access.", justify="left").pack(anchor="w", pady=10)
ttk.Button(connect, text="Connect Spotify", command=on_connect_spotify).pack(anchor="w")

# tab 2: Paste Playlist
paste = make_tab("Paste Playlist")
ttk.Label(paste, text="Paste songs from Spotify or YouTube, one per line (Song Title - Artist Name):").pack(anchor="w")
paste_box = ScrolledText(paste, height=18)
paste_box.pack(fill="both", expand=True, pady=6)
artist_first = tk.BooleanVar(value=False)
ttk.Checkbutton(paste, text="My lines are written as 'Artist - Song Title'", variable=artist_first).pack(anchor="w")
ttk.Button(paste, text="Analyze Playlist", command=on_analyze_paste).pack(anchor="w", pady=6)

# tab 3: Search Spotify User
search = make_tab("Search Spotify User")
ttk.Label(search, text="Spotify username or profile URL:").pack(anchor="w")
search_entry = ttk.Entry(search, width=60)
search_entry.pack(anchor="w", pady=4)
ttk.Button(search, text="Search", command=on_search_user).pack(anchor="w")
ttk.Label(
    search,
    text="Note: Spotify does not share another person's listening history.\nWe can only show public playlists. You can also paste a playlist instead.",
    foreground="gray30", justify="left",
).pack(anchor="w", pady=8)
profile_label = ttk.Label(search, text="", justify="left")
profile_label.pack(anchor="w", pady=4)
playlist_list = tk.Listbox(search, height=10)
playlist_list.pack(fill="x", pady=4)
ttk.Button(search, text="Analyze Selected Playlist", command=on_analyze_playlist).pack(anchor="w", pady=4)

# tab 4: Music Preferences
prefs = make_tab("Music Preferences")
prefs_box = ScrolledText(prefs, state="disabled")
prefs_box.pack(fill="both", expand=True)

# tab 5: Recommended Songs
recs_tab = make_tab("Recommended Songs")
recs_box = ScrolledText(recs_tab, state="disabled")
recs_box.pack(fill="both", expand=True)

status = tk.StringVar(value="Ready")
ttk.Label(root, textvariable=status).pack(anchor="w", padx=10, pady=(0, 6))

root.mainloop()