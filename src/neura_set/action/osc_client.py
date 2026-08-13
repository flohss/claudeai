"""Thin wrapper around AbletonOSC's UDP address space.

AbletonOSC (https://github.com/ideoforms/AbletonOSC) is a Max-for-Live-free
Remote Script that exposes Ableton Live's Live Object Model over OSC. The
addresses below match its documented address space as of this writing —
verify against the AbletonOSC version you have installed before relying
on them, since the project has renamed a few addresses across releases.
"""

from __future__ import annotations

import queue
import threading
from typing import Any

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from neura_set.config import OSCConfig, DEFAULT_CONFIG


class AbletonOSCClient:
    def __init__(self, config: OSCConfig = DEFAULT_CONFIG.osc) -> None:
        self.config = config
        self._client = SimpleUDPClient(config.ableton_host, config.ableton_send_port)
        self._reply_queues: dict[str, queue.Queue] = {}

        self._dispatcher = Dispatcher()
        self._dispatcher.set_default_handler(self._on_message)
        self._server = ThreadingOSCUDPServer(
            (config.ableton_host, config.ableton_receive_port), self._dispatcher
        )
        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> None:
        """Start listening for AbletonOSC replies (track counts, etc)."""
        self._server_thread.start()

    def stop(self) -> None:
        self._server.shutdown()

    def _on_message(self, address: str, *args: Any) -> None:
        q = self._reply_queues.get(address)
        if q is not None:
            q.put(args)

    def send(self, address: str, *args: Any) -> None:
        self._client.send_message(address, list(args))

    def query(self, address: str, *args: Any, timeout: float = 2.0) -> tuple:
        """Send `address` and block for its reply on the same address
        (AbletonOSC echoes get/ addresses back with the queried value)."""
        q = self._reply_queues.setdefault(address, queue.Queue())
        self.send(address, *args)
        try:
            return q.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError(f"No reply from Ableton on {address}") from exc

    # --- convenience wrappers over the address space ---

    def create_midi_track(self, index: int = -1) -> None:
        self.send("/live/song/create_midi_track", index)

    def create_clip(self, track_id: int, clip_id: int, length_beats: float) -> None:
        self.send("/live/clip_slot/create_clip", track_id, clip_id, length_beats)

    def add_notes(self, track_id: int, clip_id: int, notes: list[tuple]) -> None:
        """`notes` is a list of (pitch, start_time, duration, velocity, mute) tuples."""
        flat: list[Any] = [track_id, clip_id]
        for note in notes:
            flat.extend(note)
        self.send("/live/clip/add/notes", *flat)

    def remove_notes(self, track_id: int, clip_id: int) -> None:
        self.send("/live/clip/remove/notes", track_id, clip_id)

    def fire_clip(self, track_id: int, clip_id: int) -> None:
        self.send("/live/clip/fire", track_id, clip_id)

    def stop_clip(self, track_id: int, clip_id: int) -> None:
        self.send("/live/clip/stop", track_id, clip_id)

    def get_num_tracks(self, timeout: float = 2.0) -> int:
        reply = self.query("/live/song/get/num_tracks", timeout=timeout)
        return int(reply[0])

    def __enter__(self) -> "AbletonOSCClient":
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
