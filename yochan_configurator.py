#!/usr/bin/env python3
"""
Yo-Chan Configurator

A small GUI for:
1. Managing app mappings (yochan_apps.user.json)
2. Managing core config values in .env:
   - MODEL_PATH
   - WAKE_WORD_PATH
   - ACCESS_KEY
   - LISTEN_DURATION
   - SHUTDOWN_COMMAND / REBOOT_COMMAND / SUSPEND_COMMAND / LOGOUT_COMMAND
   - FUZZY_THRESHOLD
   - ASSISTANT_NAME
"""

import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import webbrowser
from yochan_update import check_for_updates, apply_updates

# Import project modules to discover paths
try:
    import apps
except ImportError:
    apps = None

try:
    import config
except ImportError:
    config = None


# ----------------- PATHS -----------------

if apps is not None:
    APPS_DIR = Path(apps.__file__).resolve().parent
else:
    APPS_DIR = Path(__file__).resolve().parent

CONFIG_PATH_JSON = APPS_DIR / "yochan_apps.user.json"

if config is not None and hasattr(config, "BASE_DIR"):
    BASE_DIR = Path(config.BASE_DIR)
else:
    BASE_DIR = Path(__file__).resolve().parent

ENV_PATH = BASE_DIR / ".env"


# ----------------- HELPER: .env LOAD/SAVE -----------------

ENV_KEYS = [
    "MODEL_PATH",
    "WAKE_WORD_PATH",
    "ACCESS_KEY",
    "LISTEN_DURATION",
    "SHUTDOWN_COMMAND",
    "REBOOT_COMMAND",
    "SUSPEND_COMMAND",
    "LOGOUT_COMMAND",
    "FUZZY_THRESHOLD",
    "ASSISTANT_NAME",
]


def read_env_file(path: Path) -> dict:
    """
    Very simple .env parser:
    - Lines like KEY=VALUE
    - Ignores blank lines and comments
    - Returns dict of key->value (strings)
    """
    env = {}
    if not path.exists():
        return env

    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                env[key.strip()] = value.strip()
    except Exception as e:
        print(f"[Configurator] Error reading .env: {e}")
    return env


def write_env_file(path: Path, updates: dict):
    """
    Update specific keys in .env while preserving other lines
    and comments as much as possible.
    """
    lines = []
    existing_env = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        # Build map of existing keys
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            existing_env[key.strip()] = value.strip()

    # Apply updates into existing_env
    for k, v in updates.items():
        existing_env[k] = v

    # Rebuild lines:
    new_lines = []
    handled_keys = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue

        key, _ = stripped.split("=", 1)
        key_stripped = key.strip()

        if key_stripped in updates:
            # Replace this line
            value = existing_env.get(key_stripped, "")
            new_lines.append(f"{key_stripped}={value}\n")
            handled_keys.add(key_stripped)
        else:
            new_lines.append(line)

    # Any new keys that were not in the file get appended
    for k in updates.keys():
        if k not in handled_keys:
            value = existing_env.get(k, "")
            new_lines.append(f"{k}={value}\n")

    # Write back
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        messagebox.showerror("Save error", f"Could not write .env:\n{e}")


# ----------------- APP MAPPER TAB -----------------

class AppMapperFrame(tk.Frame):
    """
    Manages yochan_apps.user.json:
    - spoken phrase -> command
    Also provides a scanner for installed desktop apps (with search).
    """

    def __init__(self, master):
        super().__init__(master)

        self.mappings = {}
        self.selected_key = None

        # For scanner
        self.scanned_apps = []           # full list: {name, exec, path}
        self._scanner_current_apps = []  # currently displayed subset
        self.scanner_window = None
        self.scanner_listbox = None
        self.scanner_search_var = tk.StringVar()

        # Left side: list of phrases
        left_frame = tk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(left_frame, text="Spoken Phrases").pack(anchor="w")

        self.listbox = tk.Listbox(left_frame, width=30)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Right side: details and buttons
        right_frame = tk.Frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        # Phrase field
        tk.Label(right_frame, text="Spoken phrase:").grid(row=0, column=0, sticky="w")
        self.phrase_entry = tk.Entry(right_frame, width=35)
        self.phrase_entry.grid(row=1, column=0, sticky="we", pady=(0, 10))

        # Command field
        tk.Label(right_frame, text="Command to execute:").grid(row=2, column=0, sticky="w")
        self.command_entry = tk.Entry(right_frame, width=35)
        self.command_entry.grid(row=3, column=0, sticky="we", pady=(0, 10))

        # Buttons
        btn_frame = tk.Frame(right_frame)
        btn_frame.grid(row=4, column=0, pady=10, sticky="we")

        tk.Button(btn_frame, text="Add / Update", command=self.add_or_update).grid(row=0, column=0, padx=2)
        tk.Button(btn_frame, text="Delete", command=self.delete_selected).grid(row=0, column=1, padx=2)
        tk.Button(btn_frame, text="Save JSON", command=self.save_to_disk).grid(row=0, column=2, padx=2)
        tk.Button(btn_frame, text="Reload", command=self.reload_from_disk).grid(row=0, column=3, padx=2)

        # Scanner button
        tk.Button(
            right_frame,
            text="Scan Installed Apps",
            command=self.open_app_scanner,
        ).grid(row=5, column=0, pady=(5, 0), sticky="w")

        # Status label
        self.status_label = tk.Label(right_frame, text="", fg="grey")
        self.status_label.grid(row=6, column=0, sticky="w", pady=(10, 0))

        right_frame.columnconfigure(0, weight=1)

        # Initial load
        self.reload_from_disk(initial=True)

    # ----- internal helpers -----

    def set_status(self, text: str):
        self.status_label.config(text=text)

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for key in sorted(self.mappings.keys()):
            self.listbox.insert(tk.END, key)

    def on_select(self, event):
        if not self.listbox.curselection():
            return
        index = self.listbox.curselection()[0]
        key = self.listbox.get(index)
        self.selected_key = key

        self.phrase_entry.delete(0, tk.END)
        self.phrase_entry.insert(0, key)

        cmd = self.mappings.get(key, "")
        self.command_entry.delete(0, tk.END)
        self.command_entry.insert(0, cmd)

    def add_or_update(self):
        phrase = self.phrase_entry.get().strip().lower()
        cmd = self.command_entry.get().strip()

        if not phrase:
            messagebox.showwarning("Missing phrase", "Please enter a spoken phrase.")
            return
        if not cmd:
            messagebox.showwarning("Missing command", "Please enter a command to execute.")
            return

        self.mappings[phrase] = cmd
        self.refresh_listbox()
        self.set_status(f"Mapping saved: '{phrase}' → {cmd}")

    def delete_selected(self):
        if not self.listbox.curselection():
            messagebox.showinfo("No selection", "Select a phrase to delete.")
            return

        index = self.listbox.curselection()[0]
        key = self.listbox.get(index)

        if messagebox.askyesno("Delete mapping", f"Delete mapping for '{key}'?"):
            self.mappings.pop(key, None)
            self.refresh_listbox()
            self.phrase_entry.delete(0, tk.END)
            self.command_entry.delete(0, tk.END)
            self.selected_key = None
            self.set_status(f"Deleted mapping for '{key}'")

    def save_to_disk(self):
        try:
            CONFIG_PATH_JSON.parent.mkdir(parents=True, exist_ok=True)
            with CONFIG_PATH_JSON.open("w", encoding="utf-8") as f:
                json.dump(self.mappings, f, indent=4, ensure_ascii=False)
            self.set_status(f"Saved {len(self.mappings)} mappings to {CONFIG_PATH_JSON}")
        except Exception as e:
            messagebox.showerror("Save error", f"Could not save config:\n{e}")

    def reload_from_disk(self, initial=False):
        if CONFIG_PATH_JSON.exists():
            try:
                with CONFIG_PATH_JSON.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.mappings = {str(k): str(v) for k, v in data.items()}
                else:
                    messagebox.showwarning(
                        "Invalid config",
                        "yochan_apps.user.json is not a JSON object. Starting with empty mappings.",
                    )
                    self.mappings = {}
            except json.JSONDecodeError as e:
                messagebox.showerror("Config error", f"Invalid JSON in yochan_apps.user.json:\n{e}")
                self.mappings = {}
            except Exception as e:
                messagebox.showerror("Read error", f"Could not read yochan_apps.user.json:\n{e}")
                self.mappings = {}
        else:
            self.mappings = {}

        self.refresh_listbox()
        if not initial:
            self.set_status(f"Reloaded {len(self.mappings)} mappings from disk.")

    # ----- APP SCANNER + SEARCH -----

    def open_app_scanner(self):
        """Open a popup that lists installed desktop apps (.desktop files)."""
        self.scanned_apps = self._scan_installed_apps()
        self._scanner_current_apps = list(self.scanned_apps)

        if not self.scanned_apps:
            messagebox.showinfo(
                "No apps found",
                "Could not find any .desktop files in standard locations.\n"
                "Checked /usr/share/applications and ~/.local/share/applications.",
            )
            return

        if self.scanner_window is not None and tk.Toplevel.winfo_exists(self.scanner_window):
            self.scanner_window.lift()
            return

        self.scanner_window = tk.Toplevel(self)
        self.scanner_window.title("Installed Applications")
        self.scanner_window.geometry("650x450")

        # Top: search box
        search_frame = tk.Frame(self.scanner_window)
        search_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        search_entry = tk.Entry(search_frame, textvariable=self.scanner_search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Filter list whenever user types
        self.scanner_search_var.trace_add("write", self._filter_scanner_list)

        # Main list
        list_frame = tk.Frame(self.scanner_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.scanner_listbox = tk.Listbox(list_frame)
        self.scanner_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.scanner_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scanner_listbox.config(yscrollcommand=scrollbar.set)

        # Populate listbox initially
        self._refresh_scanner_listbox()

        # Label hint
        tk.Label(
            self.scanner_window,
            text="Double-click an app or select it and press 'Use Selected'.",
        ).pack(anchor="w", padx=10, pady=(0, 5))

        # Bind double-click
        self.scanner_listbox.bind("<Double-Button-1>", self._use_selected_app_from_scanner)

        # Buttons
        btn_frame = tk.Frame(self.scanner_window)
        btn_frame.pack(pady=(0, 10))

        tk.Button(
            btn_frame,
            text="Use Selected",
            command=self._use_selected_app_from_scanner,
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            btn_frame,
            text="Close",
            command=self.scanner_window.destroy,
        ).grid(row=0, column=1, padx=5)

    def _scan_installed_apps(self):
        """
        Scan common .desktop directories and return a list of:
        { 'name': ..., 'exec': ..., 'path': ... }
        """
        results = []
        desktop_dirs = [
            Path("/usr/share/applications"),
            Path.home() / ".local/share/applications",
        ]

        for d in desktop_dirs:
            if not d.is_dir():
                continue
            for desktop_file in d.glob("*.desktop"):
                app_info = self._parse_desktop_file(desktop_file)
                if app_info:
                    results.append(app_info)

        results.sort(key=lambda a: a["name"].lower())
        return results

    def _parse_desktop_file(self, path: Path):
        """
        Parse a .desktop file to extract Name= and Exec=.
        Ignore NoDisplay=true entries.
        """
        name = None
        exec_cmd = None
        nodisplay = False

        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue

                    if stripped.startswith("Name=") and name is None:
                        name = stripped[len("Name="):].strip()

                    elif stripped.startswith("Exec=") and exec_cmd is None:
                        exec_cmd = stripped[len("Exec="):].strip()

                    elif stripped.startswith("NoDisplay="):
                        if "true" in stripped.split("=", 1)[1].strip().lower():
                            nodisplay = True

            if not name or not exec_cmd or nodisplay:
                return None

            # Clean Exec command: remove placeholders like %U, %F, etc.
            exec_parts = exec_cmd.split()
            clean_parts = [p for p in exec_parts if not p.startswith("%")]
            exec_clean = " ".join(clean_parts).strip()

            if not exec_clean:
                return None

            return {
                "name": name,
                "exec": exec_clean,
                "path": str(path),
            }

        except Exception:
            return None

    def _refresh_scanner_listbox(self):
        """Refresh the listbox using self._scanner_current_apps."""
        if self.scanner_listbox is None:
            return

        self.scanner_listbox.delete(0, tk.END)
        for app in self._scanner_current_apps:
            display = f"{app['name']}  —  {app['exec']}"
            self.scanner_listbox.insert(tk.END, display)

    def _filter_scanner_list(self, *args):
        """Filter scanned apps based on search box content."""
        query = self.scanner_search_var.get().strip().lower()
        if not query:
            self._scanner_current_apps = list(self.scanned_apps)
        else:
            self._scanner_current_apps = [
                app for app in self.scanned_apps
                if query in app["name"].lower() or query in app["exec"].lower()
            ]
        self._refresh_scanner_listbox()

    def _use_selected_app_from_scanner(self, event=None):
        """Use currently selected app from the scanner window to pre-fill phrase/command."""
        if self.scanner_window is None or not tk.Toplevel.winfo_exists(self.scanner_window):
            return
        if self.scanner_listbox is None:
            return

        selection = self.scanner_listbox.curselection()
        if not selection:
            messagebox.showinfo("No selection", "Please select an application from the list.")
            return

        index = selection[0]
        if index < 0 or index >= len(self._scanner_current_apps):
            return

        app = self._scanner_current_apps[index]

        phrase_suggestion = app["name"].lower()

        self.phrase_entry.delete(0, tk.END)
        self.phrase_entry.insert(0, phrase_suggestion)

        self.command_entry.delete(0, tk.END)
        self.command_entry.insert(0, app["exec"])

        self.set_status(f"Loaded from scanner: '{phrase_suggestion}' → {app['exec']}")
        # Optional: close scanner
        # self.scanner_window.destroy()


# ----------------- ENV / MODEL / SYSTEM TAB -----------------

class EnvConfigFrame(tk.Frame):
    """
    Manages .env keys.
    """

    def __init__(self, master):
        super().__init__(master)

        self.env_values = read_env_file(ENV_PATH)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.models_frame = tk.Frame(nb)
        self.system_frame = tk.Frame(nb)

        nb.add(self.models_frame, text="Models & Wake Word")
        nb.add(self.system_frame, text="System & Tuning")

        self._build_models_tab()
        self._build_system_tab()
    
    def check_updates_from_ui(self):
        """
        Check for YoChan updates using git and optionally apply them.

        - Does NOT overwrite local changes: if the working tree is dirty,
          it will refuse to auto-update and show a warning.
        """
        repo_dir = BASE_DIR

        has_updates, is_dirty, status = check_for_updates(repo_dir)

        if not has_updates:
            # No new commits, just show info (still mention dirty if any).
            messagebox.showinfo("YoChan Updates", status)
            return

        # There ARE updates
        if is_dirty:
            # Warn and abort auto-update
            messagebox.showwarning("YoChan Updates", status)
            return

        # Clean and remote is ahead: ask user for confirmation
        if not messagebox.askyesno(
            "YoChan Updates",
            status + "\n\nDo you want to update now?"
        ):
            return

        ok, msg = apply_updates(repo_dir)
        if ok:
            messagebox.showinfo("YoChan Updates", msg)
        else:
            messagebox.showerror("YoChan Updates", msg)


    # ---------- MODELS / WAKE WORD TAB ----------

    def _build_models_tab(self):
        f = self.models_frame

        row = 0

        # MODEL_PATH
        tk.Label(f, text="Vosk MODEL_PATH (folder):").grid(row=row, column=0, sticky="w")
        row += 1
        self.model_entry = tk.Entry(f, width=60)
        self.model_entry.grid(row=row, column=0, sticky="we", pady=(0, 5))
        tk.Button(f, text="Browse Folder", command=self.browse_model_dir).grid(row=row, column=1, padx=5)
        row += 1

        # WAKE_WORD_PATH
        tk.Label(f, text="Porcupine WAKE_WORD_PATH (.ppn file):").grid(row=row, column=0, sticky="w")
        row += 1
        self.wake_entry = tk.Entry(f, width=60)
        self.wake_entry.grid(row=row, column=0, sticky="we", pady=(0, 5))
        tk.Button(f, text="Browse File", command=self.browse_wake_file).grid(row=row, column=1, padx=5)
        row += 1

        # ACCESS_KEY
        tk.Label(f, text="Picovoice ACCESS_KEY:").grid(row=row, column=0, sticky="w")
        row += 1
        self.access_entry = tk.Entry(f, width=60, show="*")
        self.access_entry.grid(row=row, column=0, sticky="we", pady=(0, 5))
        row += 1

        # ASSISTANT_NAME (optional)
        tk.Label(
            f,
            text="Assistant name (optional, overrides name derived from wake word):"
        ).grid(row=row, column=0, sticky="w")
        row += 1
        self.assistant_name_entry = tk.Entry(f, width=60)
        self.assistant_name_entry.grid(row=row, column=0, sticky="we", pady=(0, 5))
        row += 1

        # Preview label (computed from assistant name / wake word)
        self.assistant_preview_label = tk.Label(
            f,
            text="",
            fg="grey",
        )
        self.assistant_preview_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 10))
        row += 1

        # Helpful links
        links_frame = tk.Frame(f)
        links_frame.grid(row=row, column=0, columnspan=2, pady=(5, 5), sticky="w")

        tk.Button(
            links_frame,
            text="Open Vosk model download page",
            command=self.open_vosk_models_page,
        ).grid(row=0, column=0, padx=2)

        tk.Button(
            links_frame,
            text="Open Picovoice Console",
            command=self.open_picovoice_console,
        ).grid(row=0, column=1, padx=2)

        row += 1

        # Save / Reload
        btn_frame = tk.Frame(f)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(10, 0), sticky="w")

        tk.Button(btn_frame, text="Save to .env", command=self.save_models_to_env).grid(row=0, column=0, padx=2)
        tk.Button(btn_frame, text="Reload from .env", command=self.reload_from_env).grid(row=0, column=1, padx=2)

        f.columnconfigure(0, weight=1)

        # Fill current values + preview
        self.reload_from_env()

    # --- MODEL BROWSER / LINKS HANDLERS ---

    def browse_model_dir(self):
        directory = filedialog.askdirectory(
            title="Select Vosk model directory",
            initialdir=self.env_values.get("MODEL_PATH", str(BASE_DIR)),
        )
        if directory:
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, directory)

    def browse_wake_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Porcupine .ppn file",
            filetypes=[("Porcupine model", "*.ppn"), ("All files", "*.*")],
            initialdir=self.env_values.get("WAKE_WORD_PATH", str(BASE_DIR)),
        )
        if file_path:
            self.wake_entry.delete(0, tk.END)
            self.wake_entry.insert(0, file_path)
        self.update_assistant_preview()

    def open_vosk_models_page(self):
        webbrowser.open("https://alphacephei.com/vosk/models")

    def open_picovoice_console(self):
        webbrowser.open("https://console.picovoice.ai/")

    def update_assistant_preview(self):
        """
        Compute a preview of the assistant display name based on:
        - ASSISTANT_NAME field if set
        - otherwise derive from WAKE_WORD_PATH filename
        - fallback to 'Assistant'
        """
        # 1) explicit assistant name, if any
        explicit = self.assistant_name_entry.get().strip() if hasattr(self, "assistant_name_entry") else ""

        if explicit:
            base = explicit
        else:
            # 2) derive from wake word path
            wake_path = self.wake_entry.get().strip() if hasattr(self, "wake_entry") else ""
            base = ""
            if wake_path:
                filename = os.path.basename(wake_path)
                name, _ext = os.path.splitext(filename)
                # clean up common filename patterns: underscores/dashes → spaces
                name = name.replace("_", " ").replace("-", " ").strip()
                # strip typical porcupine suffixes like "_linux"
                for suffix in (" linux", "mac", "windows"):
                    if name.lower().endswith(suffix):
                        name = name[: -len(suffix)].strip()
                base = name.title()

            if not base:
                base = "Assistant"

        base = base.strip() or "Assistant"

        if base.endswith("!"):
            display = f"{base} Assistant"
        else:
            display = f"{base}! Assistant"

        if hasattr(self, "assistant_preview_label"):
            self.assistant_preview_label.config(
                text=f"Current assistant display name will be:  {display}"
            )

    def reload_from_env(self):
        self.env_values = read_env_file(ENV_PATH)

        self.model_entry.delete(0, tk.END)
        self.model_entry.insert(0, self.env_values.get("MODEL_PATH", ""))

        self.wake_entry.delete(0, tk.END)
        self.wake_entry.insert(0, self.env_values.get("WAKE_WORD_PATH", ""))

        self.access_entry.delete(0, tk.END)
        self.access_entry.insert(0, self.env_values.get("ACCESS_KEY", ""))

        self.assistant_name_entry.delete(0, tk.END)
        self.assistant_name_entry.insert(0, self.env_values.get("ASSISTANT_NAME", ""))

        # update preview label
        self.update_assistant_preview()

    def save_models_to_env(self):
        updates = {
            "MODEL_PATH": self.model_entry.get().strip(),
            "WAKE_WORD_PATH": self.wake_entry.get().strip(),
            "ACCESS_KEY": self.access_entry.get().strip(),
            "ASSISTANT_NAME": self.assistant_name_entry.get().strip(),
        }

        write_env_file(ENV_PATH, updates)
        self.update_assistant_preview()
        messagebox.showinfo("Saved", "Model / wake word / assistant settings saved to .env.")

    # ---------- SYSTEM / TIMING TAB ----------

    def _build_system_tab(self):
        f = self.system_frame

        row = 0

        # LISTEN_DURATION
        tk.Label(f, text="LISTEN_DURATION (seconds to listen after wake word):").grid(row=row, column=0, sticky="w")
        row += 1
        self.listen_entry = tk.Entry(f, width=10)
        self.listen_entry.grid(row=row, column=0, sticky="w", pady=(0, 10))
        row += 1

        # FUZZY_THRESHOLD
        tk.Label(f, text="FUZZY_THRESHOLD (0.0 to 1.0, 1.0 = Exact Match):").grid(row=row, column=0, sticky="w")
        row += 1
        self.fuzzy_entry = tk.Entry(f, width=10)
        self.fuzzy_entry.grid(row=row, column=0, sticky="w", pady=(0, 10))
        row += 1

        # Power commands
        tk.Label(f, text="Power commands (optional overrides):").grid(row=row, column=0, sticky="w")
        row += 1

        tk.Label(f, text="SHUTDOWN_COMMAND (e.g., systemctl poweroff):").grid(row=row, column=0, sticky="w")
        row += 1
        self.shutdown_entry = tk.Entry(f, width=60)
        self.shutdown_entry.grid(row=row, column=0, sticky="we", pady=(0, 5))
        row += 1

        tk.Label(f, text="REBOOT_COMMAND:").grid(row=row, column=0, sticky="w")
        row += 1
        self.reboot_entry = tk.Entry(f, width=60)
        self.reboot_entry.grid(row=row, column=0, sticky="we", pady=(0, 5))
        row += 1

        tk.Label(f, text="SUSPEND_COMMAND:").grid(row=row, column=0, sticky="w")
        row += 1
        self.suspend_entry = tk.Entry(f, width=60)
        self.suspend_entry.grid(row=row, column=0, sticky="we", pady=(0, 5))
        row += 1

        tk.Label(f, text="LOGOUT_COMMAND:").grid(row=row, column=0, sticky="w")
        row += 1
        self.logout_entry = tk.Entry(f, width=60)
        self.logout_entry.grid(row=row, column=0, sticky="we", pady=(0, 5))
        row += 1

        updates_frame = tk.Frame(f)
        updates_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 0))

        tk.Button(
            updates_frame,
            text="Check for YoChan updates",
            command=self.check_updates_from_ui,
        ).grid(row=0, column=0, padx=(0, 8))
        
        row += 1

        # Buttons
        btn_frame = tk.Frame(f)
        btn_frame.grid(row=row, column=0, pady=(10, 0), sticky="w")
        tk.Button(btn_frame, text="Save to .env", command=self.save_system_to_env).grid(row=0, column=0, padx=2)
        tk.Button(btn_frame, text="Reload from .env", command=self.reload_system_from_env).grid(row=0, column=1, padx=2)

        f.columnconfigure(0, weight=1)

        # Fill current values
        self.reload_system_from_env()

    def reload_system_from_env(self):
        self.env_values = read_env_file(ENV_PATH)

        self.listen_entry.delete(0, tk.END)
        self.listen_entry.insert(0, self.env_values.get("LISTEN_DURATION", ""))

        self.fuzzy_entry.delete(0, tk.END)
        self.fuzzy_entry.insert(0, self.env_values.get("FUZZY_THRESHOLD", ""))

        self.shutdown_entry.delete(0, tk.END)
        self.shutdown_entry.insert(0, self.env_values.get("SHUTDOWN_COMMAND", ""))

        self.reboot_entry.delete(0, tk.END)
        self.reboot_entry.insert(0, self.env_values.get("REBOOT_COMMAND", ""))

        self.suspend_entry.delete(0, tk.END)
        self.suspend_entry.insert(0, self.env_values.get("SUSPEND_COMMAND", ""))

        self.logout_entry.delete(0, tk.END)
        self.logout_entry.insert(0, self.env_values.get("LOGOUT_COMMAND", ""))

    def save_system_to_env(self):
        # Validation for duration and threshold
        duration_str = self.listen_entry.get().strip()
        threshold_str = self.fuzzy_entry.get().strip()

        if duration_str:
            if not duration_str.isdigit() or int(duration_str) < 1:
                messagebox.showwarning("Validation Error", "LISTEN_DURATION must be a positive integer (seconds).")
                return

        if threshold_str:
            try:
                threshold = float(threshold_str)
                if not (0.0 <= threshold <= 1.0):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Validation Error", "FUZZY_THRESHOLD must be a number between 0.0 and 1.0.")
                return

        updates = {
            "LISTEN_DURATION": duration_str,
            "FUZZY_THRESHOLD": threshold_str,
            "SHUTDOWN_COMMAND": self.shutdown_entry.get().strip(),
            "REBOOT_COMMAND": self.reboot_entry.get().strip(),
            "SUSPEND_COMMAND": self.suspend_entry.get().strip(),
            "LOGOUT_COMMAND": self.logout_entry.get().strip(),
        }
        write_env_file(ENV_PATH, updates)
        messagebox.showinfo("Saved", "System / tuning settings saved to .env.")


# ----------------- ROOT APP -----------------

class YoChanConfiguratorApp:
    def __init__(self, root):
        self.root = root

        assistant_title = "Assistant"
        if config is not None and hasattr(config, "ASSISTANT_NAME"):
            if getattr(config, "ASSISTANT_NAME"):
                assistant_title = config.ASSISTANT_NAME

        self.root.title(f"{assistant_title} Configurator")

        # Optional: a bit of default window size
        self.root.geometry("800x500")

        nb = ttk.Notebook(root)
        nb.pack(fill=tk.BOTH, expand=True)

        self.apps_tab = AppMapperFrame(nb)
        self.env_tab = EnvConfigFrame(nb)

        nb.add(self.apps_tab, text="App Mappings")
        nb.add(self.env_tab, text="Models & System")


def main():
    root = tk.Tk()
    app = YoChanConfiguratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
