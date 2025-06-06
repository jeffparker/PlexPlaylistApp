import json
import csv
import os
import datetime
from plexapi.exceptions import NotFound

def export_to_json(server: object, playlists: list, filepath: str) -> None:
    """
    Export selected Plex playlists to a JSON file.

    Args:
        server (object): The connected Plex server instance (plexapi.server.PlexServer).
        playlists (list): List of Plex playlist objects to export.
        filepath (str): Path to the output JSON file.
    """
    data = {
        "export_date": datetime.datetime.now().isoformat(),
        "plex_server": server.friendlyName,
        "playlists": []
    }
    for pl in playlists:
        items = []
        for item in pl.items():
            items.append({
                "title": item.title,
                "year": getattr(item, 'year', None),
                "type": item.type,
                "imdb_id": (item.guid.split('://')[-1] if getattr(item, 'guid', None) else None),
                "plex_rating_key": item.ratingKey
            })
        data["playlists"].append({
            "name": pl.title,
            "description": pl.summary or "",
            "items": items
        })
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def export_to_csv(playlist: object, filepath: str) -> None:
    """
    Export a single Plex playlist to a CSV file.

    Args:
        playlist (object): Plex playlist object to export.
        filepath (str): Path to the output CSV file.
    """
    fieldnames = ["title", "year", "type", "imdb_id", "plex_rating_key"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in playlist.items():
            writer.writerow({
                "title": item.title,
                "year": getattr(item, 'year', None),
                "type": item.type,
                "imdb_id": (item.guid.split('://')[-1] if getattr(item, 'guid', None) else None),
                "plex_rating_key": item.ratingKey
            })

def preview_import(file_path: str) -> list:
    """
    Preview playlist names from a JSON or CSV file before import.

    Args:
        file_path (str): Path to the JSON or CSV file.

    Returns:
        list: List of playlist names found in the file.
    """
    names = []
    if file_path.lower().endswith(".json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            names = [pl["name"] for pl in data.get("playlists", [])]
    elif file_path.lower().endswith(".csv"):
        # assume single playlist; name from filename
        names = [os.path.splitext(os.path.basename(file_path))[0]]
    return names

def import_from_file(server: object, file_path: str, rename_map: dict, progress_callback=None, cancel_event=None) -> str:
    """
    Import playlists from a JSON or CSV file into Plex, matching media items and handling renames.

    Args:
        server (object): The connected Plex server instance.
        file_path (str): Path to the import file (JSON or CSV).
        rename_map (dict): Mapping of original playlist names to new names for import.

    Returns:
        str: Summary of import results for each playlist.
    """
    results = []
    missing_movies = []
    if file_path.lower().endswith(".json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for pl in data.get("playlists", []):
            original = pl["name"]
            if original not in rename_map:
                continue
            new_name = rename_map[original]
            items = pl.get("items", [])
            matched = []
            total = len(items)
            for idx, item in enumerate(items):
                if cancel_event and cancel_event.is_set():
                    results.append(f"{new_name}: Import cancelled at {idx}/{total}")
                    break
                media = find_media_in_plex(server, item)
                if media:
                    matched.append(media)
                else:
                    missing_movies.append(item)
                if progress_callback:
                    progress_callback(idx + 1, total)
            else:
                try:
                    server.createPlaylist(new_name, items=matched)
                except Exception as e:
                    results.append(f"{new_name}: ERROR {e}")
                else:
                    results.append(f"{new_name}: added {len(matched)}/{len(items)}")
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            playlist_name = os.path.splitext(os.path.basename(file_path))[0]
            if playlist_name not in rename_map:
                return "; ".join(results)
            new_name = rename_map[playlist_name]
            items = list(reader)
            matched = []
            total = len(items)
            for idx, item in enumerate(items):
                if cancel_event and cancel_event.is_set():
                    results.append(f"{new_name}: Import cancelled at {idx}/{total}")
                    break
                media = find_media_in_plex(server, item)
                if media:
                    matched.append(media)
                else:
                    missing_movies.append(item)
                if progress_callback:
                    progress_callback(idx + 1, total)
            else:
                try:
                    server.createPlaylist(new_name, items=matched)
                except Exception as e:
                    results.append(f"{new_name}: ERROR {e}")
                else:
                    results.append(f"{new_name}: added {len(matched)}/{len(items)}")
    # Save missing movies to JSON if any
    if missing_movies:
        with open("Missing Movies.json", "w", encoding="utf-8") as f:
            json.dump(missing_movies, f, indent=2)
    return "\n".join(results)


def find_media_in_plex(server: object, item: dict) -> object | None:
    """
    Attempt to find a matching media item in Plex for a given item dict.
    Tries rating key, then IMDB ID, then title+year, then title only.

    Args:
        server (object): The connected Plex server instance.
        item (dict): Dictionary describing the media item (title, year, imdb_id, etc).

    Returns:
        object | None: The matched Plex media item, or None if not found.
    """
    # Try matching by plex rating key
    if item.get("plex_rating_key"):
        try:
            return server.fetchItem(item["plex_rating_key"])
        except Exception:
            pass
    # Use Movies section for searching
    try:
        movies_section = server.library.section('Movies')
    except Exception:
        return None
    # Try by external IDs (IMDB)
    if item.get("imdb_id"):
        imdb_id = item["imdb_id"]
        # Search by title and year if available, else by title
        if item.get("year"):
            results = movies_section.search(title=item["title"], year=item["year"])
        else:
            results = movies_section.search(title=item["title"])
        # Filter results by IMDB ID in guid
        for result in results:
            guid = getattr(result, 'guid', '')
            if imdb_id in guid:
                return result
    # Try by title and year
    if item.get("year"):
        results = movies_section.search(title=item["title"], year=item["year"])
        if results:
            return results[0]
    # Fallback to title only
    results = movies_section.search(title=item["title"])
    return results[0] if results else None
