"""Variable-order Markov chain generator over scale degrees.

This is the working, dependency-free generator NEURA-SET uses out of the
box: it listens to what's being played (`train`), builds a transition
table of scale-degree steps, and samples continuations from it — falling
back to a chord-tone/passing-tone voice-leading rule when a state hasn't
been seen yet. It is intentionally simple (no GPU, no checkpoint) so the
system is usable end-to-end before a heavier model (see
transformer_generator.py) is plugged in.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Sequence

from neura_set.generation.base import Generator
from neura_set.types import MusicalContext, NoteEvent

MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11]
NATURAL_MINOR_STEPS = [0, 2, 3, 5, 7, 8, 10]


def scale_intervals(is_minor: bool) -> list[int]:
    return NATURAL_MINOR_STEPS if is_minor else MAJOR_STEPS


def pitch_to_degree(pitch: int, root_pc: int, is_minor: bool) -> tuple[int, int]:
    """Return (scale_degree_index 0-6, octave), snapping to the nearest
    scale tone if the pitch isn't diatonic."""
    intervals = scale_intervals(is_minor)
    pc = (pitch - root_pc) % 12
    octave = (pitch - root_pc) // 12
    if pc in intervals:
        return intervals.index(pc), octave
    nearest = min(intervals, key=lambda i: abs(i - pc))
    return intervals.index(nearest), octave


def degree_to_pitch(degree: int, octave: int, root_pc: int, is_minor: bool) -> int:
    intervals = scale_intervals(is_minor)
    degree = degree % len(intervals)
    pitch = root_pc + intervals[degree] + 12 * octave
    return max(0, min(127, pitch))


def _weighted_choice(counter: Counter) -> int:
    items = list(counter.items())
    total = sum(w for _, w in items)
    r = random.uniform(0, total)
    upto = 0.0
    for item, w in items:
        upto += w
        if upto >= r:
            return item
    return items[-1][0]


class MarkovGenerator(Generator):
    name = "markov"

    def __init__(self, order: int = 2) -> None:
        self.order = order
        self._chain: dict[tuple[int, ...], Counter] = defaultdict(Counter)
        self._starts: Counter = Counter()

    def train(self, notes: Sequence[NoteEvent], context: MusicalContext) -> None:
        if len(notes) < 2:
            return
        ordered = sorted(notes, key=lambda n: n.start_beat)
        degrees = [
            pitch_to_degree(n.pitch, context.key_root_pc, context.key_is_minor)[0]
            for n in ordered
        ]
        self._starts[degrees[0]] += 1
        for i in range(len(degrees) - self.order):
            state = tuple(degrees[i : i + self.order])
            self._chain[state][degrees[i + self.order]] += 1

    def generate(
        self,
        context: MusicalContext,
        length_beats: float = 4.0,
        note_duration_beats: float = 0.5,
        register: int = 60,
    ) -> list[NoteEvent]:
        is_minor = (
            context.chord_is_minor
            if context.chord_is_minor is not None
            else context.key_is_minor
        )
        octave = (register - context.key_root_pc) // 12

        state_degrees = [self._weighted_choice(self._starts) if self._starts else 0]
        while len(state_degrees) < self.order:
            state_degrees.append(random.choice(range(7)))

        n_notes = max(1, int(length_beats / note_duration_beats))
        events: list[NoteEvent] = []
        beat = 0.0
        for _ in range(n_notes):
            state = tuple(state_degrees[-self.order :])
            if state in self._chain:
                next_degree = self._weighted_choice(self._chain[state])
            else:
                next_degree = self._fallback_degree(state_degrees[-1], beat)
            state_degrees.append(next_degree)

            pitch = degree_to_pitch(next_degree, octave, context.key_root_pc, is_minor)
            is_strong_beat = beat % 1.0 == 0
            velocity = 104 if is_strong_beat else 82
            events.append(
                NoteEvent(
                    pitch=pitch,
                    start_beat=beat,
                    duration_beats=note_duration_beats,
                    velocity=velocity,
                )
            )
            beat += note_duration_beats
        return events

    @staticmethod
    def _fallback_degree(last_degree: int, beat: float) -> int:
        """Rule-based voice leading: strong beats favor chord tones
        (scale degrees 0/2/4 = root/third/fifth), weak beats move by step."""
        if beat % 1.0 == 0:
            return random.choice([0, 2, 4])
        return (last_degree + random.choice([-1, 1])) % 7

    @staticmethod
    def _weighted_choice(counter: Counter) -> int:
        return _weighted_choice(counter)
