"""High-level bridge between Proposals and a dedicated Ableton MIDI track.

Every proposal is staged into a free clip slot on the "NEURA-SET
Proposals" track (never written directly into the arrangement), matching
the brief's "interface de validation" requirement: accepting fires the
clip, rejecting stops/removes it, and nothing reaches the mix without a
human choosing it.
"""

from __future__ import annotations

import itertools

from neura_set.action.midi_writer import notes_to_osc_tuples
from neura_set.action.osc_client import AbletonOSCClient
from neura_set.config import OSCConfig, DEFAULT_CONFIG
from neura_set.types import Proposal


class AbletonController:
    def __init__(
        self,
        osc_client: AbletonOSCClient,
        track_id: int,
        config: OSCConfig = DEFAULT_CONFIG.osc,
    ) -> None:
        """`track_id` must be the index of an existing MIDI track (create
        one named `config.proposal_track_name` beforehand, either by hand
        or via `osc_client.create_midi_track()`) — AbletonOSC's
        track-listing addresses vary enough across versions that
        auto-detecting it by name isn't reliable here.
        """
        self.osc = osc_client
        self.track_id = track_id
        self.config = config
        self._clip_id_counter = itertools.count()

    def stage_proposal(self, proposal: Proposal) -> int:
        """Write `proposal`'s notes into a new clip slot without firing
        it. Returns the clip_id so the caller can accept/reject later."""
        clip_id = next(self._clip_id_counter)
        length = max((n.start_beat + n.duration_beats for n in proposal.notes), default=4.0)
        self.osc.create_clip(self.track_id, clip_id, length)
        self.osc.add_notes(self.track_id, clip_id, notes_to_osc_tuples(proposal.notes))
        return clip_id

    def accept(self, clip_id: int) -> None:
        self.osc.fire_clip(self.track_id, clip_id)

    def reject(self, clip_id: int) -> None:
        self.osc.stop_clip(self.track_id, clip_id)
        self.osc.remove_notes(self.track_id, clip_id)
