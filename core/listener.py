# core/listener.py
from __future__ import annotations
import json
import queue
import struct
from typing import Callable, Optional

import sounddevice as sd
from vosk import Model, KaldiRecognizer

import config as _cfg
from utils.logger import get_logger

log = get_logger(__name__)

VOSK_MODEL_PATH = getattr(_cfg, "VOSK_MODEL_PATH", "vosk-model-small-en-us-0.15")
SAMPLE_RATE = int(getattr(_cfg, "SAMPLE_RATE", 16000))
CHANNELS = int(getattr(_cfg, "CHANNELS", 1))
WAKE_KEYWORDS = [w.strip().lower() for w in getattr(_cfg, "WAKE_KEYWORDS", "yochan").split(",") if w.strip()]
USE_PORCUPINE = bool(getattr(_cfg, "USE_PORCUPINE", False))


class Listener:
    """
    Core audio loop:
    - optional Porcupine wake-word
    - Vosk STT
    - calls on_text(transcript) when a command has been recognized
    """

    def __init__(self, on_text: Callable[[str], None], model_path: Optional[str] = None):
        self.on_text = on_text
        model_dir = model_path or VOSK_MODEL_PATH
        log.info("Loading Vosk model from %s", model_dir)
        self.model = Model(model_dir)
        self.rec = KaldiRecognizer(self.model, SAMPLE_RATE)
        self._q: "queue.Queue[bytes]" = queue.Queue()

        self.use_porcupine = USE_PORCUPINE
        self.porcupine = None
        if self.use_porcupine:
            try:
                import pvporcupine

                self.porcupine = pvporcupine.create()
                log.info("Porcupine initialized for wake-word.")
            except Exception as e:
                log.exception("Failed to init Porcupine, disabling wake-word: %s", e)
                self.use_porcupine = False

    def _audio_callback(self, indata, frames, time, status):
        if status:
            log.warning("Input status: %s", status)
        self._q.put(bytes(indata))

    def run(self):
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=8000,
            dtype="int16",
            channels=CHANNELS,
            callback=self._audio_callback,
        ):
            log.info("Listener started. Say the wake-word (%s)...", ", ".join(WAKE_KEYWORDS))
            while True:
                data = self._q.get()

                # Optional wake-word stage
                if self.use_porcupine and self.porcupine is not None:
                    try:
                        pcm = struct.unpack_from("h" * (len(data) // 2), data)
                        idx = self.porcupine.process(pcm)
                        if idx < 0:
                            # no wake yet; ignore this chunk
                            continue
                        else:
                            log.info("Wake word detected by Porcupine.")
                            # After wake: we keep processing with Vosk, but no keyword filter.
                    except Exception as e:
                        log.exception("Porcupine error: %s", e)
                        self.use_porcupine = False

                if self.rec.AcceptWaveform(data):
                    res = json.loads(self.rec.Result())
                    text = (res.get("text") or "").strip()
                    if not text:
                        continue
                    log.info("STT: %s", text)
                    lowered = text.lower()

                    if not self.use_porcupine and WAKE_KEYWORDS:
                        if not any(w in lowered for w in WAKE_KEYWORDS):
                            # ignore if wake keyword not spoken
                            continue
                        for w in WAKE_KEYWORDS:
                            lowered = lowered.replace(w, "").strip()
                        if not lowered:
                            continue

                    self.on_text(lowered)
