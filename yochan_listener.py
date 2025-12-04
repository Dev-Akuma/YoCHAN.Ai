#!/usr/bin/env python3
import pvporcupine
from pvrecorder import PvRecorder
import time
import os
import subprocess
import sys
import numpy as np 
from dotenv import load_dotenv 
import signal # Required for clean exit

# --- STT IMPORTS ---
from vosk import Model, KaldiRecognizer
import sounddevice as sd 
import json
from yochan import execute_command, show_notification 
# -------------------

# =========================================================
# === LOAD CONFIGURATION FROM .env FILE ===
# =========================================================
load_dotenv() 

MODEL_PATH = os.getenv("MODEL_PATH")
LISTEN_DURATION = int(os.getenv("LISTEN_DURATION", 5))
VOSK_SAMPLE_RATE = 16000 

ACCESS_KEY = os.getenv("ACCESS_KEY")
WAKE_WORD_PATH = os.getenv("WAKE_WORD_PATH")
# ---------------------------------------------------

# =========================================================
# === INITIALIZE MODELS (Run only once) ===
# =========================================================

if not all([MODEL_PATH, ACCESS_KEY, WAKE_WORD_PATH]):
    print("\nFATAL ERROR: One or more critical variables are missing from the .env file.", file=sys.stderr)
    sys.exit(1)

# NEW: Sanity Check 1: Verify Vosk Model Path Exists
if not os.path.isdir(MODEL_PATH):
    print(f"\nFATAL ERROR: Vosk Model directory not found at: {MODEL_PATH}", file=sys.stderr)
    sys.exit(1)

# NEW: Sanity Check 2: Verify Porcupine Model File Exists
if not os.path.isfile(WAKE_WORD_PATH):
    print(f"\nFATAL ERROR: Porcupine Wake Word file not found at: {WAKE_WORD_PATH}", file=sys.stderr)
    sys.exit(1)


try:
    VOSK_MODEL = Model(MODEL_PATH)
except Exception as e:
    print(f"\nFATAL ERROR: Could not load Vosk Model from {MODEL_PATH}. Details: {e}", file=sys.stderr)
    sys.exit(1)


def listen_for_command():
    rec = KaldiRecognizer(VOSK_MODEL, VOSK_SAMPLE_RATE)
    
    try:
        audio_data = sd.rec(
            int(VOSK_SAMPLE_RATE * LISTEN_DURATION), 
            samplerate=VOSK_SAMPLE_RATE, 
            channels=1, 
            dtype='int16'
        )
        sd.wait()

        rec.AcceptWaveform(audio_data.tobytes())
        result = json.loads(rec.FinalResult())
        
        command = result.get('text', '').strip()
        
        return command

    except Exception:
        return ""


def run_yo_chan_listener():
    porcupine = None
    recorder = None
    
    # 1. Initialize Porcupine (Wake Word Engine)
    try:
        porcupine = pvporcupine.create(
            access_key=ACCESS_KEY,
            keyword_paths=[WAKE_WORD_PATH],
            sensitivities=[0.9] 
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
        show_notification("Yo-Chan! Assistant", "Background listener is active.", icon="audio-volume-high")

    except Exception as e:
        print(f"\nFATAL ERROR: Could not start recorder. Check microphone access. Details: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        while True:
            pcm = recorder.read()
            keyword_index = porcupine.process(pcm)
            
            # --- WAKE WORD DETECTED ---
            if keyword_index >= 0:
                show_notification("Yo-Chan! Listening...", "Speak your command now.")
                
                recorder.stop() 
                user_command = listen_for_command()

                if user_command:
                    response = execute_command(user_command)
                    
                    if response == "QUIT_LISTENER":
                        break 

                else:
                    show_notification("Yo-Chan! Error", "Command not detected. Try again.")

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