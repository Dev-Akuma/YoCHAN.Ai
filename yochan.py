#!/usr/bin/env python3
from core.listener import Listener
from utils.logger import get_logger
from ai_core import handle_voice_input

log = get_logger(__name__)

def on_text(text: str):
    log.info("STT Heard: %s", text)

    # Route EVERYTHING through ai_core
    result = handle_voice_input(text)

    log.info("Result: %s", result)

def main():
    listener = Listener(on_text)
    listener.run()

if __name__ == "__main__":
    main()
