# Yo-Chan! Voice Assistant (Low-Resource Linux)

Yo-Chan! is a simple, efficient, and completely local voice assistant for Linux desktop environments.  
It’s designed for low-spec machines (e.g. 4GB RAM, Intel i3), and stays almost idle when you’re not talking to it.

- **Wake word**: Picovoice Porcupine (e.g. “Yo-Chan!”)  
- **Speech-to-text**: Vosk, fully offline  
- **Desktop**: Optimized for XFCE / Cinnamon / Mint, but configurable for any DE

---

## 🚀 Features

- **Low resource usage**  
  Near-zero CPU usage while idle. Listener wakes only on the wake word.

- **Fully offline**  
  Once you download a Vosk model and a Porcupine `.ppn` wake word file, everything runs locally.

- **System control**  
  - Launch applications (e.g. “open firefox”, “start brave browser”)  
  - Close apps (e.g. “close firefox”)  
  - Adjust volume and brightness  
  - Power controls: shutdown, restart, sleep/suspend, logout

- **Config-driven**  
  - All core options (models, wake word, power commands) come from `.env` via `config.py`.  
  - Desktop/logout behaviour can be changed per-distro without touching code.

- **Smart command recognition**  
  - Vosk runs with a **limited command grammar** built from your app mappings and system verbs, instead of full free dictation.  
  - This improves recognition of short commands like “brave”, “firefox”, “file manager”.

- **Dynamic app mappings**  
  - Default app mappings live in `apps.py`.  
  - User overrides live in `yochan_apps.user.json`.  
  - A simple GUI (`yochan_configurator.py`) lets you edit mappings without touching code.

- **Clean exit command**  
  - You can tell Yo-Chan to stop entirely by saying:  
    **“Yo-Chan, die”** or **“Yo-Chan, stop listening”**.

---

## 🧱 Project Structure

Important files:

- `yochan_listener.py`  
  Main background listener. Handles wake word, recording audio, calling Vosk, and executing commands.

- `yochan.py`  
  Core command logic: power control, app launching/closing, volume, brightness, clipboard, etc.

- `apps.py`  
  Default app name → executable mapping (`APP_COMMANDS`). Loads user overrides from `yochan_apps.user.json`.

- `yochan_apps.user.json`  
  Optional user mapping file (JSON). Automatically loaded and merged into `APP_COMMANDS`.

- `config.py`  
  Central configuration module. Loads `.env`, auto-detects models when possible, and exposes power/logout commands.

- `config.template.env`  
  Template for your `.env` file.

- `yochan_configurator.py`  
  Tk-based GUI to manage:
  - app mappings (`yochan_apps.user.json`)  
  - core `.env` values (models, wake word, assistant name, power commands, fuzzy threshold, etc.)

- `yochan_update.py`  
  Git-aware updater:
  - checks for updates if this is a git clone  
  - can convert a ZIP/non-git folder into a proper git clone while preserving `.env` and `yochan_apps.user.json`.

- `setup.sh`  
  Installs dependencies, sets up virtualenv, downloads a default Vosk model.

- `run_listener.sh`  
  Helper script to activate venv and start `yochan_listener.py`.

- `yochan_startup.sh`  
  Script for starting Yo-Chan on login (via DE autostart or systemd user services).

---

## 📦 Dependencies

### Python packages

These are installed automatically by `setup.sh`, but if you prefer manual:

```bash
pip install pvporcupine pvrecorder vosk python-dotenv numpy sounddevice
