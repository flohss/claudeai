"""
Voice I/O via Termux:API.
- Speech input  : termux-speech-to-text
- Speech output : termux-tts-speak
"""

import json
import re
import shutil
import subprocess


# ── Speech input ───────────────────────────────────────────────────────────────

def is_available() -> bool:
    return shutil.which("termux-speech-to-text") is not None


def transcribe(timeout: int = 15) -> str | None:
    if not is_available():
        return None
    try:
        result = subprocess.run(
            ["termux-speech-to-text"],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        data = json.loads(result.stdout)
        content = data.get("content", [])
        if content and content[0]:
            text = content[0][0].strip()
            return text if text else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None
    return None


# ── Speech output ──────────────────────────────────────────────────────────────

_tts_process: subprocess.Popen | None = None


def is_tts_available() -> bool:
    return shutil.which("termux-tts-speak") is not None


def _strip_markdown(text: str) -> str:
    text = re.sub(r"#{1,6}\s+", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", " ", text)
    return text.strip()


def speak(text: str, lang: str = "fr") -> None:
    """Speak text using Android TTS. Runs synchronously — call in a thread."""
    global _tts_process
    stop_speaking()
    clean = _strip_markdown(text)
    if not clean or not is_tts_available():
        return
    try:
        _tts_process = subprocess.Popen(
            ["termux-tts-speak", "-l", lang, clean],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _tts_process.wait()
    except Exception:
        pass
    finally:
        _tts_process = None


def stop_speaking() -> None:
    """Interrupt any ongoing TTS immediately."""
    global _tts_process
    if _tts_process and _tts_process.poll() is None:
        _tts_process.terminate()
        try:
            _tts_process.wait(timeout=1)
        except Exception:
            _tts_process.kill()
    _tts_process = None
