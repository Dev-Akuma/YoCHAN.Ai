import os
import json
import sys

# --- MANUAL APPLICATION MAPPING (RELIABLE) ---
# Key = What the user is likely to say (or what Vosk transcribes)
# Value = The exact Linux executable command
APP_COMMANDS = {
    # --- BROWSERS & INTERNET ---
    'firefox': 'firefox', 
    'brave': 'brave-browser', 
    'browser': 'firefox',     
    'brave browser': 'brave-browser',
    'thunderbird': 'thunderbird',
    'mail reader': 'xfce4-mail-reader',

    # --- DEVELOPMENT & TOOLS ---
    'vscode': 'code',         
    'vs code': 'code', 
    'code': 'code',
    'visual studio code': 'code',
    'visual studio': 'code', # Alias for VS Code
    'sublime text': 'sublime_text',
    'sublime': 'sublime_text',
    'idle': 'idle-python3.12',
    'vim': 'vim',

    # --- DESIGN & CREATIVE ---
    'gimp': 'gimp',
    'inkscape': 'inkscape',
    'blender': 'blender',
    'photoshop': 'gimp',  # GIMP as alternative to Photoshop     
    'figma': 'flatpak run com.figma.Figma', 
    'sigma': 'flatpak run com.figma.Figma', # Common transcription error
    'drawing': 'com.github.maoschanz.drawing', # Executable for drawing.desktop
    'pix': 'pix', # Image viewer
    'xviewer': 'xviewer', # X Viewer

    # --- XFCE/SYSTEM UTILITIES ---
    'terminal': 'xfce4-terminal', 
    'terminal emulator': 'xfce4-terminal',
    'file explorer': 'thunar', 
    'explorer': 'thunar',
    'file manager': 'thunar',
    'settings': 'xfce4-settings-manager', 
    'settings manager': 'xfce4-settings-manager',
    'app finder': 'xfce4-appfinder',
    'task manager': 'xfce4-taskmanager',
    'manager' : 'taskmanager',
    'calculator': 'gnome-calculator',
    'calendar': 'gnome-calendar',
    'volume control': 'pavucontrol',
    'pavucontrol': 'pavucontrol',

    # --- MEDIA & COMMUNICATION ---
    'whatsapp': 'whatsapp-desktop', 
    "what's up": 'whatsapp-desktop',
    'camera': 'cheese', 
    'cheese': 'gnome-cheese', # Using the common executable name
    'hypnotix': 'hypnotix',
    'celluloid': 'io.github.celluloid_player.Celluloid',
    'rhythmbox': 'rhythmbox',
    'warpinator': 'warpinator',
    
    # --- SYSTEM TOOLS ---
    'gparted': 'gparted',
    'disks': 'gnome-disks', # gnome-disk-utility
    'disk utility': 'gnome-disks',
    'backup': 'mintbackup',
    'drivers': 'mintdrivers',
    'software manager': 'mintinstall',
    'update manager': 'mintupdate',
    'timeshift': 'timeshift-gtk',
    'printer': 'system-config-printer',
    'scan': 'simple-scan',
    'vpn': 'protonvpn', # Based on proton.vpn.app.gtk.desktop
    'vpn app': 'protonvpn',
    'firewall': 'gufw',
    'users': 'users', # User settings

    # --- ACCESSIBILITY ---
    'onboard': 'onboard', # On-screen keyboard
    'dict': 'xfce4-dict', # Dictionary

    # --- FILE HANDLING ---
    'file roller': 'file-roller',
    'archive manager': 'file-roller',
    'downloader': 'transmission-gtk',
    'transmission': 'transmission-gtk',

    # --- ALIASES (Simple/Common words) ---
    'manager': 'xfce4-settings-manager',
    'photos': 'pix',
    'sketch': 'com.github.maoschanz.drawing',
}

# ---------------------------------------
# NEW: USER OVERRIDE CONFIG LOADER
# ---------------------------------------

def _load_user_overrides():
    """
    Load yochan_apps.user.json from the same directory (if present)
    and merge into APP_COMMANDS.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_cfg_path = os.path.join(base_dir, "yochan_apps.user.json")

    if not os.path.exists(user_cfg_path):
        return  # nothing to do

    try:
        with open(user_cfg_path, "r", encoding="utf-8") as f:
            user_map = json.load(f)

        if not isinstance(user_map, dict):
            print("[Yo-Chan] Warning: yochan_apps.user.json is not a JSON object, ignoring.",
                  file=sys.stderr)
            return

        # merge: user overrides > defaults
        APP_COMMANDS.update(user_map)
        print(f"[Yo-Chan] Loaded {len(user_map)} user app mappings from yochan_apps.user.json.",
              file=sys.stderr)

    except json.JSONDecodeError as e:
        print(f"[Yo-Chan] Error: Invalid JSON in yochan_apps.user.json: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[Yo-Chan] Error reading yochan_apps.user.json: {e}", file=sys.stderr)


# Run at import time so yochan.py gets the merged dict automatically
_load_user_overrides()