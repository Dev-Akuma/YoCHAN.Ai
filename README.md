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

- `yochan_configurator.py`  
  Small Tk GUI to view/edit `yochan_apps.user.json` visually.

- `config.template.env`  
  Template for your `.env` file.

- `setup.sh`  
  Installs dependencies, sets up virtualenv, downloads a default Vosk model.

- `run_listener.sh`  
  Helper script to activate venv and start `yochan_listener.py`.

---

## 🛠️ Installation (Linux Mint / Ubuntu / similar)

### 1. Prerequisites

- Python 3.8+  
- `git`  
- A working microphone  
- Basic desktop with PulseAudio / PipeWire

### 2. Clone the repository

```bash
git clone <YOUR_GITHUB_URL> yochan-assistant
cd yochan-assistant
