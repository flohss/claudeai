"""
Voice input via termux-speech-to-text (Termux:API).
Falls back gracefully if unavailable.
"""

import json
import shutil
import subprocess


def is_available() -> bool:
    """Check if termux-speech-to-text is installed and accessible."""
    return shutil.which("termux-speech-to-text") is not None


def transcribe(timeout: int = 15) -> str | None:
    """
    Open Android speech recognition, return transcribed text or None.
    Returns None on error, cancellation, or unavailability.
    """
    if not is_available():
        return None
    try:
        result = subprocess.run(
            ["termux-speech-to-text"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        data = json.loads(result.stdout)
        # {"type":"results","content":[["best match", "alternative", ...]]}
        content = data.get("content", [])
        if content and content[0]:
            text = content[0][0].strip()
            return text if text else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None
    return None
