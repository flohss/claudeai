import pytest

from neura_set.perception.analyzer import _EMA, _SectionDebouncer
from neura_set.types import SectionLabel


def test_ema_moves_toward_new_value_gradually():
    ema = _EMA(alpha=0.3)
    assert ema.update(100.0) == 100.0  # first sample seeds the average

    v = ema.update(140.0)
    assert 100.0 < v < 140.0  # moved toward the new value, not straight to it
    assert v == pytest.approx(100.0 + 0.3 * (140.0 - 100.0))


def test_ema_converges_to_a_steady_input():
    ema = _EMA(alpha=0.3)
    v = 0.0
    for _ in range(50):
        v = ema.update(128.0)
    assert v == pytest.approx(128.0, abs=0.01)


def test_section_debouncer_ignores_single_tick_flicker():
    deb = _SectionDebouncer(confirm_ticks=3)
    assert deb.update(SectionLabel.VERSE) == SectionLabel.UNKNOWN  # not confirmed yet
    assert deb.update(SectionLabel.DROP) == SectionLabel.UNKNOWN  # flicker, still unconfirmed
    assert deb.update(SectionLabel.VERSE) == SectionLabel.UNKNOWN  # still not 3 in a row


def test_section_debouncer_confirms_after_consecutive_agreement():
    deb = _SectionDebouncer(confirm_ticks=3)
    deb.update(SectionLabel.CHORUS)
    deb.update(SectionLabel.CHORUS)
    assert deb.update(SectionLabel.CHORUS) == SectionLabel.CHORUS


def test_section_debouncer_does_not_flip_on_a_single_differing_tick():
    deb = _SectionDebouncer(confirm_ticks=3)
    for _ in range(3):
        deb.update(SectionLabel.CHORUS)
    assert deb.active == SectionLabel.CHORUS

    assert deb.update(SectionLabel.VERSE) == SectionLabel.CHORUS  # one-off, stays confirmed
