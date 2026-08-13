"""Entry point: `python -m neura_set [--track-id N] [--style techno]`."""

from __future__ import annotations

import argparse
import logging

import uvicorn

from neura_set.config import DEFAULT_CONFIG
from neura_set.generation.style import STYLES
from neura_set.orchestrator import Orchestrator, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="NEURA-SET — AI co-producer for Ableton Live")
    parser.add_argument(
        "--track-id",
        type=int,
        default=None,
        help="MIDI track index for AbletonOSC proposals (omit to run UI-only, no Ableton)",
    )
    parser.add_argument("--style", default="default", choices=sorted(STYLES))
    parser.add_argument("--host", default=DEFAULT_CONFIG.interface.host)
    parser.add_argument("--port", type=int, default=DEFAULT_CONFIG.interface.port)
    parser.add_argument(
        "--input-device",
        default=None,
        help="Name or index of the audio input device to listen on (see --list-audio-devices). "
        "Defaults to the system's default input.",
    )
    parser.add_argument(
        "--list-audio-devices",
        action="store_true",
        help="Print available audio devices (to find your loopback/virtual cable) and exit.",
    )
    parser.add_argument(
        "--min-rms-energy",
        type=float,
        default=None,
        help="Override the silence threshold below which NEURA-SET never proposes "
        "(DecisionConfig.min_rms_energy, default 0.02). Lower it if audio is reaching "
        "the app (see --verbose) but proposals never trigger.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Log the measured audio level on every analysis tick — use this to check "
        "whether NEURA-SET is actually receiving sound and how it compares to the "
        "silence threshold.",
    )
    args = parser.parse_args()

    if args.list_audio_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return

    # Keep third-party libraries (numba's JIT compiler in particular, via
    # librosa) at INFO — only NEURA-SET's own logger goes to DEBUG. numba
    # alone dumps thousands of lines of bytecode/compilation trace per
    # analysis tick under a global DEBUG level, drowning out the one line
    # --verbose is meant to surface.
    logging.basicConfig(level=logging.INFO)
    if args.verbose:
        logging.getLogger("neura_set").setLevel(logging.DEBUG)

    if args.input_device is not None:
        device = int(args.input_device) if args.input_device.isdigit() else args.input_device
        DEFAULT_CONFIG.audio.input_device = device
    if args.min_rms_energy is not None:
        DEFAULT_CONFIG.decision.min_rms_energy = args.min_rms_energy

    orchestrator = Orchestrator(ableton_track_id=args.track_id, style=args.style)
    app = create_app(orchestrator)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
