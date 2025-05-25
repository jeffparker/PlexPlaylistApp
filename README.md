# Plex Playlist Exporter/Importer

A simple Python GUI app to export, import, and modify playlists on a Plex Media Server.

## Features

- **Export** playlists to JSON format
- **Import** playlists from JSON (with rename and conflict handling)
- **Modify** existing playlists: sort by year (and alphabetically for same-year items)
- Feedback indicators and non-blocking UI using threads

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/jeffparker/PlexPlaylistApp.git
   cd PlexPlaylistApp
   ```
2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the GUI application:
```bash
python PlexPlaylistApp.py
```

1. Click **Connect to Plex** and wait for connection status.
2. Use the **Export** tab to select one or more playlists and export them to JSON.
3. Use the **Import** tab to load a JSON file, optionally rename playlists, and import them back to Plex.
4. Use the **Modify** tab to pick a playlist, sort its items by year (and title), and update the playlist on the server.

## Configuration

**No configuration is required for most users!**

By default, the app uses Plex's secure PIN login flow. When you run the app, a browser window opens for you to log in with your Plex account, and the app automatically connects to your server. This is the recommended and easiest method for most users—just run the app and follow the prompts.

**Advanced/Automated Use:**
- If you want to bypass the PIN login (for automation, scripts, or running on a headless server), you can supply your Plex server URL and authentication token either:
  - As environment variables (`PLEX_URL` and `PLEX_TOKEN`), or
  - By editing `plex_utils.py` to hardcode your credentials.

Most users should not need to do this. These options are only for special circumstances, such as automated workflows or servers without a browser. If you are unsure, just use the default PIN login.

## Dependencies

- [plexapi](https://github.com/pkkid/python-plexapi)
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter)
- [CTkMessagebox](https://github.com/TomSchimansky/CustomTkinter)
- [requests](https://requests.readthedocs.io/)

## Acknowledgements

This project is built on top of [PlexPlaylistMaker by primetime43](https://github.com/primetime43/PlexPlaylistMaker), and retains the original MIT License for derived portions.

## License

This project is released under the terms of the MIT License. The full license text is included in the [LICENSE](./LICENSE) file at the root of this repository.
