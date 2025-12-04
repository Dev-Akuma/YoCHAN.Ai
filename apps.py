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