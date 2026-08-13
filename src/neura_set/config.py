"""Central configuration for NEURA-SET."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AudioConfig:
    sample_rate: int = 44100
    hop_length: int = 512
    frame_length: int = 2048
    analysis_window_seconds: float = 4.0
    input_device: str | None = None  # None = system default input


@dataclass
class OSCConfig:
    ableton_host: str = "127.0.0.1"
    ableton_send_port: int = 11000  # AbletonOSC listens here
    ableton_receive_port: int = 11001  # AbletonOSC replies here
    proposal_track_name: str = "NEURA-SET Proposals"


@dataclass
class InterfaceConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class DecisionConfig:
    min_seconds_between_proposals: float = 8.0
    novelty_similarity_threshold: float = 0.92
    max_pending_proposals: int = 3
    min_rms_energy: float = 0.02  # below this, treat the buffer as silence/no signal


@dataclass
class NeuraSetConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    osc: OSCConfig = field(default_factory=OSCConfig)
    interface: InterfaceConfig = field(default_factory=InterfaceConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)


DEFAULT_CONFIG = NeuraSetConfig()
