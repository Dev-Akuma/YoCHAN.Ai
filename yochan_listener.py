#!/usr/bin/env python3

import os
import sys
import time
import signal
import json

import pvporcupine
from pvrecorder import PvRecorder
from vosk import Model, KaldiRecognizer
import sounddevice as sd

from yochan import execute_command, show_notification
from apps import APP_COMMANDS
from config import (
    MODEL_PATH,
    LISTEN_DURATION,
    ACCESS_KEY,
    WAKE_WORD_PATH,
    VOSK_SAMPLE_RATE,
    ASSISTANT_NAME,
    ASSISTANT_DISPLAY_NAME,
)


# =========================================================
# === BUILD GRAMMAR FOR VOSK (LIMIT VOCABULARY) ===========
# =========================================================

GRAMMAR_PHRASES = set()

# 1) add all app names (keys in APP_COMMANDS) – includes user JSON overrides
for phrase in APP_COMMANDS.keys():
    GRAMMAR_PHRASES.add(phrase)

# 2) add power/control words
GRAMMAR_PHRASES.update([
    "shutdown", "turn off", "restart", "reboot", "sleep", "suspend",
    "logout", "log out", "log off",
    "volume", "brightness",
    "clipboard", "show clipboard",
    "close all", "kill all",
])

# 3) common helper verbs + quit keyword
GRAMMAR_PHRASES.update([
    "open", "launch", "start", "run", "close", "quit", "exit", "die",
])

# =========================================================
# === INITIALIZE MODELS (Run only once) ===================
# =========================================================

if not all([MODEL_PATH, ACCESS_KEY, WAKE_WORD_PATH]):
    print(
        "\nFATAL ERROR: One or more critical variables are missing from the .env file.",
        file=sys.stderr,
    )
    sys.exit(1)

# Sanity Check 1: Verify Vosk Model Path Exists
if not os.path.isdir(MODEL_PATH):
    print(f"\nFATAL ERROR: Vosk Model directory not found at: {MODEL_PATH}", file=sys.stderr)
    sys.exit(1)

# Sanity Check 2: Verify Porcupine Model File Exists
if not os.path.isfile(WAKE_WORD_PATH):
    print(f"\nFATAL ERROR: Porcupine Wake Word file not found at: {WAKE_WORD_PATH}", file=sys.stderr)
    sys.exit(1)

try:
    VOSK_MODEL = Model(MODEL_PATH)
except Exception as e:
    print(
        f"\nFATAL ERROR: Could not load Vosk Model from {MODEL_PATH}. Details: {e}",
        file=sys.stderr,
    )
    sys.exit(1)


# =========================================================
# === SPEECH-TO-TEXT LISTENER =============================
# =========================================================

def listen_for_command():
    """
    Record LISTEN_DURATION seconds of audio and transcribe using Vosk,
    constrained by GRAMMAR_PHRASES for better accuracy.
    """
    rec = KaldiRecognizer(
        VOSK_MODEL,
        VOSK_SAMPLE_RATE,
        json.dumps(list(GRAMMAR_PHRASES)),
    )

    try:
        audio_data = sd.rec(
            int(VOSK_SAMPLE_RATE * LISTEN_DURATION),
            samplerate=VOSK_SAMPLE_RATE,
            channels=1,
            dtype="int16",
        )
        sd.wait()

        rec.AcceptWaveform(audio_data.tobytes())
        result = json.loads(rec.FinalResult())

        command = result.get("text", "").strip()
        return command

    except Exception as e:
        print(f"[{ASSISTANT_NAME}] STT Error: {e}", file=sys.stderr)
        return ""


# =========================================================
# === MAIN WAKE WORD LOOP =================================
# =========================================================

def run_yo_chan_listener():
    porcupine = None
    recorder = None

    # 1. Initialize Porcupine (Wake Word Engine)
    try:
        porcupine = pvporcupine.create(
            access_key=ACCESS_KEY,
            keyword_paths=[WAKE_WORD_PATH],
            sensitivities=[0.9],
        )
    except Exception as e:
        print(f"\nFATAL ERROR: Failed to initialize Porcupine. Details: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Initialize PvRecorder (Efficient Listener)
    try:
        recorder = PvRecorder(
            device_index=-1,
            frame_length=porcupine.frame_length,
        )
        recorder.start()
        show_notification(
            ASSISTANT_DISPLAY_NAME,
            "Background listener is active.",
            icon="audio-volume-high",
        )


    except Exception as e:
        print(
            "\nFATAL ERROR: Could not start recorder. Check microphone access. "
            f"Details: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        while True:
            pcm = recorder.read()
            keyword_index = porcupine.process(pcm)

            # --- WAKE WORD DETECTED ---
            if keyword_index >= 0:
                show_notification("{ASSISTANT_NAME}! Listening...", "Speak your command now.")

                recorder.stop()
                user_command = listen_for_command()

                if user_command:
                    response = execute_command(user_command)

                    if response == "QUIT_LISTENER":
                        break
                else:
                    show_notification("{ASSISTANT_NAME}! Error", "Command not detected. Try again.")

                time.sleep(0.5)
                recorder.start()

    except KeyboardInterrupt:
        pass
    finally:
        # Crucial cleanup step to release resources
        if recorder is not None:
            recorder.delete()
        if porcupine is not None:
            porcupine.delete()

        # FIX for Process Persistence: Send SIGTERM to the current process
        os.kill(os.getpid(), signal.SIGTERM)


if __name__ == "__main__":
    run_yo_chan_listener()
