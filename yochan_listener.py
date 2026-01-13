#!/usr/bin/env python3

import os
import sys
import time
import json

import pvporcupine
from pvrecorder import PvRecorder
from vosk import Model, KaldiRecognizer
import sounddevice as sd

from handlers import notify
from ai_core import handle_voice_input

from config import (
    MODEL_PATH,
    LISTEN_DURATION,
    ACCESS_KEY,
    WAKE_WORD_PATH,
    VOSK_SAMPLE_RATE,
    ASSISTANT_DISPLAY_NAME,
)

# -------------------------------------------------
# Validation
# -------------------------------------------------

if not os.path.isdir(MODEL_PATH):
    print(f"Vosk model not found: {MODEL_PATH}", file=sys.stderr)
    sys.exit(1)

# -------------------------------------------------
# Load Vosk model
# -------------------------------------------------

VOSK_MODEL = Model(MODEL_PATH)

# -------------------------------------------------
# Resolve wake word(s)
# -------------------------------------------------

def resolve_keywords(path: str):
    if os.path.isfile(path):
        return [path]
    if os.path.isdir(path):
        return [
            os.path.join(path, f)
            for f in os.listdir(path)
            if f.lower().endswith(".ppn")
        ]
    raise RuntimeError("Invalid WAKE_WORD_PATH")

KEYWORD_PATHS = resolve_keywords(WAKE_WORD_PATH)

# -------------------------------------------------
# Speech capture (FREE FORM, STREAMING)
# -------------------------------------------------

def listen_for_command() -> str:
    notify("STT", "Recording command...")

    rec = KaldiRecognizer(VOSK_MODEL, VOSK_SAMPLE_RATE)
    rec.SetWords(True)

    try:
        def callback(indata, frames, time_info, status):
            if status:
                print(status, file=sys.stderr)
            rec.AcceptWaveform(bytes(indata))

        with sd.RawInputStream(
            samplerate=VOSK_SAMPLE_RATE,
            blocksize=16000,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            time.sleep(LISTEN_DURATION)

        result = json.loads(rec.FinalResult())
        text = result.get("text", "").strip()

        if text:
            notify("STT", f"Heard: '{text}'")
        else:
            notify("STT", "Empty STT result", critical=True)

        return text

    except Exception as e:
        notify("ERROR", f"STT failure: {e}", critical=True)
        return ""

# -------------------------------------------------
# Main loop
# -------------------------------------------------

def run_assistant_listener():
    notify("SYSTEM", "Starting YoChan")

    porcupine = pvporcupine.create(
        access_key=ACCESS_KEY,
        keyword_paths=KEYWORD_PATHS,
        sensitivities=[0.9] * len(KEYWORD_PATHS),
    )

    recorder = PvRecorder(
        device_index=-1,
        frame_length=porcupine.frame_length,
    )
    recorder.start()

    notify("SYSTEM", "Wake-word listener active", critical=True)

    try:
        while True:
            pcm = recorder.read()
            if porcupine.process(pcm) >= 0:
                notify("WAKE", "Wake word detected", critical=True)

                try:
                    recorder.stop()
                except Exception:
                    pass

                text = listen_for_command()
                if text:
                    result = handle_voice_input(text)
                    notify("RESULT", result)
                else:
                    notify("ERROR", "No command detected")

                time.sleep(0.4)

                try:
                    recorder.start()
                except Exception:
                    pass

    except KeyboardInterrupt:
        pass
    finally:
        recorder.delete()
        porcupine.delete()
        sys.exit(0)

if __name__ == "__main__":
    run_assistant_listener()
