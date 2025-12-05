#!/usr/bin/env python3

import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog

# Optional: if this file is in repo root and apps.py is in same folder,
# we can derive the config path from apps.py location instead.
try:
    import apps  # your existing apps.py
    APPS_DIR = Path(apps.__file__).resolve().parent
except ImportError:
    # Fallback: use directory of this script
    APPS_DIR = Path(__file__).resolve().parent

CONFIG_PATH = APPS_DIR / "yochan_apps.user.json"


class AppMapperGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("YoChan App Mapper")

        # Data: dict[str, str] = { phrase: command }
        self.mappings = {}
        self.selected_key = None

        # --- UI Layout ---
        # Left: Listbox of phrases
        left_frame = tk.Frame(master)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(left_frame, text="Spoken Phrases").pack(anchor="w")

        self.listbox = tk.Listbox(left_frame, width=30)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Right: Details + buttons
        right_frame = tk.Frame(master)
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
        tk.Button(btn_frame, text="Save", command=self.save_to_disk).grid(row=0, column=2, padx=2)
        tk.Button(btn_frame, text="Reload", command=self.reload_from_disk).grid(row=0, column=3, padx=2)

        # Status label
        self.status_label = tk.Label(right_frame, text="", fg="grey")
        self.status_label.grid(row=5, column=0, sticky="w", pady=(10, 0))

        # make right_frame columns expand nicely
        right_frame.columnconfigure(0, weight=1)

        # Load initial data
        self.reload_from_disk(initial=True)

    # ------------------ helpers ------------------

    def set_status(self, text):
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
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.mappings, f, indent=4, ensure_ascii=False)
            self.set_status(f"Saved {len(self.mappings)} mappings to {CONFIG_PATH}")
        except Exception as e:
            messagebox.showerror("Save error", f"Could not save config:\n{e}")

    def reload_from_disk(self, initial=False):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, dict):
                    self.mappings = {str(k): str(v) for k, v in data.items()}
                else:
                    messagebox.showwarning("Invalid config",
                                           "Config file is not a JSON object. Starting with empty mappings.")
                    self.mappings = {}
            except json.JSONDecodeError as e:
                messagebox.showerror("Config error", f"Invalid JSON in config:\n{e}")
                self.mappings = {}
            except Exception as e:
                messagebox.showerror("Read error", f"Could not read config:\n{e}")
                self.mappings = {}
        else:
            # no config yet → start empty
            self.mappings = {}

        self.refresh_listbox()
        if not initial:
            self.set_status(f"Reloaded {len(self.mappings)} mappings from disk.")


def main():
    root = tk.Tk()
    gui = AppMapperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
