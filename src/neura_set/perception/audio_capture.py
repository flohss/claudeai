"""Real-time audio capture from a loopback / internal Ableton routing.

Uses `sounddevice` (PortAudio) to pull audio from whichever input device
is fed by Ableton's internal routing (e.g. a virtual loopback such as
BlackHole/VB-Cable on the master or a cue bus). `sounddevice` is imported
lazily so the rest of the package — and its test suite — doesn't require
PortAudio to be installed.
"""

from __future__ import annotations

import threading
from collections import deque

import numpy as np

from neura_set.config import AudioConfig, DEFAULT_CONFIG


class RingBuffer:
    """Fixed-capacity mono float32 ring buffer, thread-safe for a single
    producer (audio callback) / single consumer (analysis loop)."""

    def __init__(self, capacity_samples: int) -> None:
        self._capacity = capacity_samples
        self._buffer: deque[float] = deque(maxlen=capacity_samples)
        self._lock = threading.Lock()

    def write(self, samples: np.ndarray) -> None:
        with self._lock:
            self._buffer.extend(samples.tolist())

    def read_latest(self, n_samples: int) -> np.ndarray:
        with self._lock:
            if not self._buffer:
                return np.zeros(n_samples, dtype=np.float32)
            data = list(self._buffer)[-n_samples:]
        if len(data) < n_samples:
            data = [0.0] * (n_samples - len(data)) + data
        return np.asarray(data, dtype=np.float32)


class AudioCapture:
    """Wraps a sounddevice InputStream feeding a RingBuffer.

    Example:
        capture = AudioCapture()
        capture.start()
        buf = capture.read_window()  # last `analysis_window_seconds` of audio
        capture.stop()
    """

    def __init__(self, config: AudioConfig = DEFAULT_CONFIG.audio) -> None:
        self.config = config
        window_samples = int(config.analysis_window_seconds * config.sample_rate)
        self.ring_buffer = RingBuffer(window_samples)
        self._stream = None

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        mono = indata.mean(axis=1) if indata.ndim > 1 else indata
        self.ring_buffer.write(mono.astype(np.float32))

    def start(self) -> None:
        import sounddevice as sd  # lazy import: requires PortAudio at runtime

        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            device=self.config.input_device,
            channels=1,
            blocksize=self.config.hop_length,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def read_window(self) -> np.ndarray:
        window_samples = int(self.config.analysis_window_seconds * self.config.sample_rate)
        return self.ring_buffer.read_latest(window_samples)

    def __enter__(self) -> "AudioCapture":
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
