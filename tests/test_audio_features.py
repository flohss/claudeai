import numpy as np

from neura_set.config import AudioConfig
from neura_set.perception import audio_features as feats
from neura_set.perception.chord_detection import detect_chord


def test_estimate_key_recovers_rotated_major_profile():
    rotated = np.roll(feats._MAJOR_PROFILE, 3)
    root, is_minor = feats.estimate_key(rotated)
    assert root == 3
    assert is_minor is False


def test_estimate_key_recovers_rotated_minor_profile():
    rotated = np.roll(feats._MINOR_PROFILE, 9)
    root, is_minor = feats.estimate_key(rotated)
    assert root == 9
    assert is_minor is True


def test_detect_chord_c_major_triad():
    chroma = np.zeros(12)
    chroma[[0, 4, 7]] = 1.0
    root, is_minor, confidence = detect_chord(chroma)
    assert root == 0
    assert is_minor is False
    assert confidence > 0.9


def test_detect_chord_a_minor_triad():
    chroma = np.zeros(12)
    chroma[[9, 0, 4]] = 1.0  # A, C, E
    root, is_minor, confidence = detect_chord(chroma)
    assert root == 9
    assert is_minor is True
    assert confidence > 0.9


def test_rms_energy_of_sine_wave():
    sr = 22050
    t = np.linspace(0, 1.0, sr, endpoint=False)
    y = (0.8 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    cfg = AudioConfig(sample_rate=sr)
    rms = feats.rms_energy(y, cfg)
    expected = 0.8 / np.sqrt(2)
    assert abs(rms - expected) < 0.05
