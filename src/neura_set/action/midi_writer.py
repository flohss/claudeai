"""Converts NoteEvents to AbletonOSC clip data or a standalone .mid file."""

from __future__ import annotations

import mido

from neura_set.types import NoteEvent


def notes_to_osc_tuples(notes: list[NoteEvent]) -> list[tuple[int, float, float, int, int]]:
    """(pitch, start_time_beats, duration_beats, velocity, mute) per AbletonOSC's
    `/live/clip/add/notes` schema."""
    return [(n.pitch, n.start_beat, n.duration_beats, n.velocity, 0) for n in notes]


def notes_to_midi_file(
    notes: list[NoteEvent],
    path: str,
    tempo_bpm: float = 120.0,
    ticks_per_beat: int = 480,
) -> None:
    """Write `notes` to a standalone .mid file — handy for auditioning a
    proposal without Ableton/AbletonOSC running."""
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm), time=0))

    events: list[tuple[int, int, NoteEvent]] = []  # (tick, is_note_on, note)
    for note in notes:
        start_tick = round(note.start_beat * ticks_per_beat)
        end_tick = round((note.start_beat + note.duration_beats) * ticks_per_beat)
        events.append((start_tick, 1, note))
        events.append((max(end_tick, start_tick + 1), 0, note))

    events.sort(key=lambda e: (e[0], e[1]))  # note_off (0) before note_on (1) at same tick

    last_tick = 0
    for tick, is_on, note in events:
        delta = tick - last_tick
        last_tick = tick
        if is_on:
            track.append(mido.Message("note_on", note=note.pitch, velocity=note.velocity, time=delta))
        else:
            track.append(mido.Message("note_off", note=note.pitch, velocity=0, time=delta))

    mid.save(path)
