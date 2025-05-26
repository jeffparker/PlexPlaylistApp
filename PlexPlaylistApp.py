import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import os
import tempfile, json

import plex_utils
import playlist_io

class PlexPlaylistExporterImporter(ctk.CTk):
    """
    Main GUI application for Plex Playlist Exporter/Importer.
    Handles export, import, and modification of Plex playlists with graceful shutdown of threads.
    """

    def __init__(self) -> None:
        """
        Initialize the PlexPlaylistExporterImporter GUI application.
        Sets up the main window, tabs, widgets, and graceful shutdown handler.
        """
        super().__init__()
        self.server = None
        self.server_var = tk.StringVar(self)
        self._threads: list[threading.Thread] = []
        self._shutting_down = False
        self.title("Plex Playlist App")
        # set fixed window size and center on screen
        win_w, win_h = 700, 600
        scr_w = self.winfo_screenwidth()
        scr_h = self.winfo_screenheight()
        x = (scr_w - win_w) // 2
        y = (scr_h - win_h) // 2
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.resizable(True, True)

        # allow main grid to expand
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Connect button, server dropdown & status label
        self.connect_btn = ctk.CTkButton(self, text="Connect to Plex", command=self.connect_to_plex)
        self.connect_btn.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.server_selector_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.server_label = ctk.CTkLabel(self.server_selector_frame, text="Select Plex Server:")
        self.server_label.pack(side="left", padx=(0, 5))
        self.server_menu = ctk.CTkOptionMenu(self.server_selector_frame, variable=self.server_var, values=[])
        self.server_menu.pack(side="left")
        self.server_selector_frame.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        # centered status message
        self.status_label = ctk.CTkLabel(self, text="", anchor="center", justify="center")
        self.status_label.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # Tabs for Export/Import
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=2, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")
        self.tabview.add("Export")
        self.tabview.add("Import")
        self.tabview.add("Modify")
        self.tabview.add("Delete")
        self.setup_export_tab()
        self.setup_import_tab()
        self.setup_modify_tab()
        self.setup_delete_tab()
        
        # Register graceful shutdown handler
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self) -> None:
        """
        Handler for window close event. Prevents new threads, waits for all background threads to finish, and closes the app.
        """
        self._shutting_down = True
        self.connect_btn.configure(state=ctk.DISABLED)
        self.status_label.configure(text="Shutting down, please wait...")
        # Wait for all threads to finish (with timeout)
        for t in self._threads:
            if t.is_alive():
                t.join(timeout=5)
        self.destroy()
        # Do not call any Tkinter methods after self.destroy() to avoid TclError
        return  # End of shutdown logic; all UI setup belongs in __init__

        # Tabs for Export/Import
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=2, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")
        self.tabview.add("Export")
        self.tabview.add("Import")
        self.tabview.add("Modify")
        self.setup_export_tab()
        self.setup_import_tab()
        self.setup_modify_tab()

    def connect_to_plex(self) -> None:
        """
        Initiate connection to Plex server using a background thread.
        Disables the connect button and updates status label during the process.
        """
        # disable connect button, then after 5s show waiting status
        self.connect_btn.configure(state=ctk.DISABLED)
        self.status_label.configure(text="")
        self.after(5000, lambda: self.status_label.configure(text="Awaiting access... please be patient, this can take up to one minute"))
        def task():
            try:
                server = plex_utils.login_to_plex()
                name = server.friendlyName
                # update UI on main thread
                self.after(0, lambda: self._on_connect_success(server, name))
            except Exception as e:
                self.after(0, lambda: self._on_connect_error(e))
        threading.Thread(target=task, daemon=True).start()

    def _on_connect_success(self, server: object, name: str) -> None:
        """
        Callback for successful Plex connection. Updates UI accordingly.

        Args:
            server (object): Connected Plex server instance.
            name (str): Server friendly name.
        """
        self.server = server
        self.server_var.set(name)
        self.server_menu.configure(values=[name])
        self.status_label.configure(text=f"Connected to Plex: {name}")
        self.connect_btn.configure(state=ctk.DISABLED)
        # Fetch all playlists and store in self.playlists
        try:
            self.export_refresh_btn.configure(state=ctk.DISABLED)
            self.modify_refresh_btn.configure(state=ctk.DISABLED)
            self.export_selected_btn.configure(state=ctk.DISABLED)
            self.import_selected_btn.configure(state=ctk.DISABLED)
            self.modify_selected_btn.configure(state=ctk.DISABLED)
            self.playlists = plex_utils.get_playlists(self.server)
        except Exception as e:
            self.playlists = []
        # Prepopulate Export and Modify tabs
        self.load_playlists()
        self.load_modify_playlists()
        self.load_delete_playlists()
        self.export_refresh_btn.configure(state=ctk.NORMAL)
        self.modify_refresh_btn.configure(state=ctk.NORMAL)
        self.export_selected_btn.configure(state=ctk.NORMAL)
        self.import_selected_btn.configure(state=ctk.NORMAL)
        self.modify_selected_btn.configure(state=ctk.NORMAL)
        self.delete_refresh_btn.configure(state=ctk.NORMAL)
        self.delete_selected_btn.configure(state=ctk.NORMAL)

    def _on_connect_error(self, error: Exception) -> None:
        """
        Callback for failed Plex connection. Updates UI and shows error message.

        Args:
            error (Exception): Exception encountered during connection.
        """
        self.status_label.configure(text=str(error))
        self.connect_btn.configure(state=ctk.DISABLED)
        CTkMessagebox(title="Error", message=str(error))

    def setup_export_tab(self) -> None:
        """
        Set up the Export tab UI elements and layout.
        """
        frame = self.tabview.tab("Export")
        # configure export tab grid
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_rowconfigure(1, weight=1)
        self.export_refresh_btn = ctk.CTkButton(frame, text="Refresh Playlists", command=self._refresh_export_playlists, state=ctk.DISABLED)
        self.export_refresh_btn.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.playlist_frame = ctk.CTkFrame(frame)
        self.playlist_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.playlist_vars = {}
        self.export_selected_btn = ctk.CTkButton(frame, text="Export Selected", command=self.export_playlists, state=ctk.DISABLED)
        self.export_selected_btn.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

    def _refresh_export_playlists(self):
        self.export_refresh_btn.configure(state=ctk.DISABLED)
        self.export_selected_btn.configure(state=ctk.DISABLED)
        self.import_selected_btn.configure(state=ctk.DISABLED)
        self.modify_selected_btn.configure(state=ctk.DISABLED)
        def task():
            try:
                self.playlists = plex_utils.get_playlists(self.server)
            except Exception:
                self.playlists = []
            self.after(0, self.load_playlists)
            self.after(0, lambda: self.export_refresh_btn.configure(state=ctk.NORMAL))
            self.after(0, lambda: self.export_selected_btn.configure(state=ctk.NORMAL))
            self.after(0, lambda: self.import_selected_btn.configure(state=ctk.NORMAL))
            self.after(0, lambda: self.modify_selected_btn.configure(state=ctk.NORMAL))
        threading.Thread(target=task, daemon=True).start()

    def _refresh_modify_playlists(self):
        self.modify_refresh_btn.configure(state=ctk.DISABLED)
        self.export_selected_btn.configure(state=ctk.DISABLED)
        self.import_selected_btn.configure(state=ctk.DISABLED)
        self.modify_selected_btn.configure(state=ctk.DISABLED)
        def task():
            try:
                self.playlists = plex_utils.get_playlists(self.server)
            except Exception:
                self.playlists = []
            self.after(0, self.load_modify_playlists)
            self.after(0, lambda: self.modify_refresh_btn.configure(state=ctk.NORMAL))
            self.after(0, lambda: self.export_selected_btn.configure(state=ctk.NORMAL))
            self.after(0, lambda: self.import_selected_btn.configure(state=ctk.NORMAL))
            self.after(0, lambda: self.modify_selected_btn.configure(state=ctk.NORMAL))
        threading.Thread(target=task, daemon=True).start()
    def load_playlists(self) -> None:
        """
        Load playlists from the connected Plex server and populate the export selection list.
        Shows error if not connected.
        """
        for w in self.playlist_frame.winfo_children():
            w.destroy()
        if not self.server:
            CTkMessagebox(title="Error", message="Not connected to Plex")
            return
        pls = getattr(self, 'playlists', None)
        if pls is None:
            pls = plex_utils.get_playlists(self.server)
            self.playlists = pls
        self.playlist_vars = {}
        for i, pl in enumerate(pls):
            var = tk.BooleanVar()
            ctk.CTkCheckBox(self.playlist_frame, text=pl.title, variable=var).grid(row=i, column=0, sticky="w")
            self.playlist_vars[pl.title] = (var, pl)




    def export_playlists(self) -> None:
        """
        Export selected playlists to a JSON file using a background thread.
        Shows error if no playlists are selected.
        """
        selected = [(name, pl) for name, (var, pl) in self.playlist_vars.items() if var.get()]
        if not selected:
            CTkMessagebox(title="Error", message="No playlists selected")
            return
        filetypes = [("JSON", "*.json")]
        default_name = selected[0][1].title if len(selected) == 1 else "Plex Playlists"
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=filetypes, initialfile=f"{default_name}.json")
        if not path:
            return
        def task():
            try:
                playlist_io.export_to_json(self.server, [pl for _, pl in selected], path)
                CTkMessagebox(title="Success", message="Export completed")
            except Exception as e:
                CTkMessagebox(title="Error", message=str(e))
        threading.Thread(target=task, daemon=True).start()

    def setup_import_tab(self) -> None:
        """
        Set up the Import tab UI elements and layout.
        """
        frame = self.tabview.tab("Import")
        # configure import tab grid
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=1)
        ctk.CTkButton(frame, text="Browse File", command=self.browse_file).grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.file_label = ctk.CTkLabel(frame, text="No file selected")
        self.file_label.grid(row=1, column=0, columnspan=2, padx=10, pady=2, sticky="w")
        self.import_frame = ctk.CTkFrame(frame)
        self.import_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.import_vars = {}
        self.file_path = None
        self.import_selected_btn = ctk.CTkButton(frame, text="Import Selected", command=self.import_playlists, state=ctk.DISABLED)
        self.import_selected_btn.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

    def browse_file(self) -> None:
        """
        Open a file dialog for the user to select a JSON/CSV file for import.
        Previews available playlists for import and allows renaming.
        """
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("CSV", "*.csv")])
        if not path:
            return
        self.file_path = path
        self.file_label.configure(text=os.path.basename(path))
        names = playlist_io.preview_import(path)
        for w in self.import_frame.winfo_children():
            w.destroy()
        self.import_vars.clear()
        if not names:
            return
        for i, name in enumerate(names):
            sel_var = tk.BooleanVar(value=True)
            ctk.CTkCheckBox(self.import_frame, text=name, variable=sel_var).grid(row=i, column=0, sticky="w")
            new_name_var = tk.StringVar(value=name)
            entry = ctk.CTkEntry(self.import_frame, textvariable=new_name_var, width=200)
            entry.grid(row=i, column=1, padx=10, pady=2, sticky="ew")
            self.import_vars[name] = (sel_var, new_name_var)
        # allow entry column to expand
        self.import_frame.grid_columnconfigure(1, weight=1)



    def import_playlists(self) -> None:
        """
        Import selected playlists from the chosen file into Plex.
        Handles playlist renaming and conflict resolution.
        Runs import in a background thread for UI responsiveness.
        """
        if not self.file_path:
            CTkMessagebox(title="Error", message="No file selected")
            return
        # build map of original -> target name for checked playlists
        rename_map = {}
        for original, (sel_var, new_name_var) in self.import_vars.items():
            if sel_var.get():
                rename_map[original] = new_name_var.get()
        if not rename_map:
            CTkMessagebox(title="Error", message="No playlists selected")
            return
        # resolve conflicts with existing playlists
        existing_titles = [pl.title for pl in self.server.playlists()]
        for original in list(rename_map.keys()):
            new_name = rename_map[original]
            if new_name in existing_titles:
                # ask user to delete existing or rename import
                delete = messagebox.askyesno(
                    "Playlist Exists",
                    f"Playlist '{new_name}' already exists. Delete existing and import under same name? (No = rename imported)"
                )
                if delete:
                    try:
                        existing = next(pl for pl in self.server.playlists() if pl.title == new_name)
                        existing.delete()
                    except Exception as e:
                        CTkMessagebox(title="Error", message=f"Failed to delete existing playlist: {e}")
                        return
                else:
                    # prompt for new name
                    new_name_prompt = simpledialog.askstring(
                        "Rename Playlist",
                        f"Enter new name for imported playlist (was '{new_name}'):",
                        initialvalue=new_name
                    )
                    if not new_name_prompt:
                        # skip this playlist
                        rename_map.pop(original)
                        continue
                    rename_map[original] = new_name_prompt
        if not rename_map:
            CTkMessagebox(title="Error", message="No playlists to import after resolving conflicts")
            return
        cancel_event = threading.Event()
        progress_dialog = ctk.CTkToplevel(self)
        progress_dialog.title("Importing Playlists")
        dialog_w, dialog_h = 400, 150
        scr_w = self.winfo_screenwidth()
        scr_h = self.winfo_screenheight()
        x = (scr_w - dialog_w) // 2
        y = (scr_h - dialog_h) // 2
        progress_dialog.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
        progress_dialog.grab_set()  # Modal
        progress_dialog.attributes('-topmost', True)
        self.attributes('-disabled', True)
        progress_label = ctk.CTkLabel(progress_dialog, text="Starting import...")
        progress_label.pack(pady=(20, 10))
        progress_bar = ctk.CTkProgressBar(progress_dialog, orientation="horizontal", width=300)
        progress_bar.pack(pady=10)
        progress_bar.set(0)
        cancel_btn = ctk.CTkButton(progress_dialog, text="Cancel Import", command=cancel_event.set)
        cancel_btn.pack(pady=10)
        def update_progress(current, total):
            percent = current / total if total else 0
            self.after(0, lambda: progress_bar.set(percent))
            self.after(0, lambda: progress_label.configure(text=f"Importing... {current} / {total}"))
        def run_import():
            try:
                res = playlist_io.import_from_file(self.server, self.file_path, rename_map, progress_callback=update_progress, cancel_event=cancel_event)
                # Check if Missing Movies.json was created and append explanation if so
                missing_path = os.path.join(os.getcwd(), "Missing Movies.json")
                extra_msg = ""
                if os.path.exists(missing_path):
                    try:
                        with open(missing_path, "r", encoding="utf-8") as f:
                            import json as _json
                            try:
                                missing_list = _json.load(f)
                            except Exception:
                                missing_list = []
                        if missing_list:
                            extra_msg = ("\n\nSome movies were not imported because they were not found on your Plex server. "
                                         "A list of missing movies has been saved as 'Missing Movies.json'.")
                        else:
                            os.remove(missing_path)
                    except Exception:
                        pass
                def show_results_and_focus():
                    CTkMessagebox(title="Import Results", message=res + extra_msg)
                    self.focus_force()
                self.after(0, show_results_and_focus)
                self.after(0, self._refresh_export_playlists)
                self.after(0, self._refresh_modify_playlists)
                self.after(0, self._refresh_delete_playlists)
            except Exception as e:
                self.after(0, lambda: CTkMessagebox(title="Error", message=str(e)))
            finally:
                self.after(0, lambda: progress_dialog.destroy())
                self.after(0, lambda: self.attributes('-disabled', False))
        threading.Thread(target=run_import, daemon=True).start()

    def setup_modify_tab(self):
        frame = self.tabview.tab("Modify")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(1, weight=1)  # Make row 1 (the playlist frame) expand
        self.modify_refresh_btn = ctk.CTkButton(frame, text="Refresh Playlists", command=self._refresh_modify_playlists, state=ctk.DISABLED)
        self.modify_refresh_btn.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.modify_frame = ctk.CTkFrame(frame)
        self.modify_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.modify_var = tk.StringVar()
        self.modify_selected_btn = ctk.CTkButton(frame, text="Modify Playlist to Sort by Year", command=self.modify_playlist, state=ctk.DISABLED)
        self.modify_selected_btn.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

    def load_modify_playlists(self):
        for w in self.modify_frame.winfo_children():
            w.destroy()
        if not self.server:
            CTkMessagebox(title="Error", message="Not connected to Plex")
            return
        pls = getattr(self, 'playlists', None)
        if pls is None:
            pls = plex_utils.get_playlists(self.server)
            self.playlists = pls
        for i, pl in enumerate(pls):
            ctk.CTkRadioButton(self.modify_frame, text=pl.title, variable=self.modify_var, value=pl.title).grid(row=i, column=0, sticky="w")

    def modify_playlist(self):
        selected = self.modify_var.get()
        if not selected:
            CTkMessagebox(title="Error", message="No playlist selected")
            return
        pls = plex_utils.get_playlists(self.server)
        pl = next((p for p in pls if p.title == selected), None)
        if not pl:
            CTkMessagebox(title="Error", message="Playlist not found")
            return
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tf.close()
        path = tf.name
        playlist_io.export_to_json(self.server, [pl], path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data["playlists"][0]["items"]
        items.sort(key=lambda x: ((x.get("year") or 0), x.get("title", "")))
        data["playlists"][0]["items"] = items
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        try:
            pl.delete()
        except Exception as e:
            CTkMessagebox(title="Error", message=f"Failed to delete original playlist: {e}")
            return
        res = playlist_io.import_from_file(self.server, path, {selected: selected})
        CTkMessagebox(title="Playlist Modified", message=f"Playlist '{selected}' sorted by year and updated on Plex server successfully.")
        try:
            os.remove(path)
        except OSError:
            pass

    def setup_delete_tab(self):
        frame = self.tabview.tab("Delete")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        self.delete_refresh_btn = ctk.CTkButton(frame, text="Refresh Playlists", command=self._refresh_delete_playlists, state=ctk.DISABLED)
        self.delete_refresh_btn.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.delete_frame = ctk.CTkFrame(frame)
        self.delete_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.delete_vars = {}
        self.delete_selected_btn = ctk.CTkButton(frame, text="Delete Selected Playlists from Plex Server", command=self.delete_selected_playlists, state=ctk.DISABLED)
        self.delete_selected_btn.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

    def _refresh_delete_playlists(self):
        self.delete_refresh_btn.configure(state=ctk.DISABLED)
        self.delete_selected_btn.configure(state=ctk.DISABLED)
        def task():
            try:
                self.playlists = plex_utils.get_playlists(self.server)
            except Exception:
                self.playlists = []
            self.after(0, self.load_delete_playlists)
            self.after(0, lambda: self.delete_refresh_btn.configure(state=ctk.NORMAL))
            self.after(0, lambda: self.delete_selected_btn.configure(state=ctk.NORMAL))
        threading.Thread(target=task, daemon=True).start()

    def load_delete_playlists(self):
        for w in self.delete_frame.winfo_children():
            w.destroy()
        if not self.server:
            CTkMessagebox(title="Error", message="Not connected to Plex")
            return
        pls = getattr(self, 'playlists', None)
        if pls is None:
            pls = plex_utils.get_playlists(self.server)
            self.playlists = pls
        self.delete_vars = {}
        for i, pl in enumerate(pls):
            var = tk.BooleanVar()
            ctk.CTkCheckBox(self.delete_frame, text=pl.title, variable=var).grid(row=i, column=0, sticky="w")
            self.delete_vars[pl.title] = (var, pl)

    def delete_selected_playlists(self):
        selected = [(name, pl) for name, (var, pl) in self.delete_vars.items() if var.get()]
        if not selected:
            CTkMessagebox(title="Error", message="No playlists selected")
            return
        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {len(selected)} playlist(s) from your Plex server?"):
            return
        def task():
            errors = []
            for name, pl in selected:
                try:
                    pl.delete()
                except Exception as e:
                    errors.append(f"{name}: {e}")
            if errors:
                self.after(0, lambda: CTkMessagebox(title="Delete Results", message="Some playlists could not be deleted:\n" + "\n".join(errors)))
            else:
                self.after(0, lambda: CTkMessagebox(title="Delete Results", message="Selected playlists deleted successfully."))
            self.after(0, self._refresh_export_playlists)
            self.after(0, self._refresh_modify_playlists)
            self.after(0, self._refresh_delete_playlists)
        threading.Thread(target=task, daemon=True).start()

def main():
    app = PlexPlaylistExporterImporter()
    app.mainloop()

if __name__ == "__main__":
    main()
