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
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    orchestrator = Orchestrator(ableton_track_id=args.track_id, style=args.style)
    app = create_app(orchestrator)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
