import random

from neura_set.generation.markov_generator import MarkovGenerator, degree_to_pitch
from neura_set.types import MusicalContext, NoteEvent


def test_degree_to_pitch_stays_in_midi_range():
    for root in range(12):
        for is_minor in (False, True):
            for octave in (-1, 0, 1, 2, 5):
                for degree in range(7):
                    pitch = degree_to_pitch(degree, octave, root, is_minor)
                    assert 0 <= pitch <= 127


def test_generate_returns_expected_note_count_and_timing():
    random.seed(0)
    gen = MarkovGenerator(order=2)
    context = MusicalContext(tempo_bpm=120, key_root_pc=0, key_is_minor=False)
    notes = gen.generate(context, length_beats=4.0, note_duration_beats=0.5)

    assert len(notes) == 8
    assert all(0 <= n.pitch <= 127 for n in notes)
    beats = [n.start_beat for n in notes]
    assert beats == sorted(beats)
    assert beats[0] == 0.0
    assert beats[-1] == 3.5


def test_generator_trains_without_error_on_short_input():
    gen = MarkovGenerator(order=2)
    context = MusicalContext(tempo_bpm=120, key_root_pc=0, key_is_minor=False)
    gen.train([], context)  # empty input shouldn't raise
    gen.train([NoteEvent(pitch=60, start_beat=0.0, duration_beats=0.5)], context)  # single note
    notes = [
        NoteEvent(pitch=60, start_beat=0.0, duration_beats=0.5),
        NoteEvent(pitch=64, start_beat=0.5, duration_beats=0.5),
        NoteEvent(pitch=67, start_beat=1.0, duration_beats=0.5),
    ]
    gen.train(notes, context)
    generated = gen.generate(context, length_beats=2.0, note_duration_beats=0.5)
    assert len(generated) == 4
    assert all(0 <= n.pitch <= 127 for n in generated)
