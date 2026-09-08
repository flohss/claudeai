"""Tests de la logique de tirage aléatoire et de déroulement du quiz."""

from culture_generale.data import THEMES
from culture_generale.quiz import Quiz


def test_theme_names_matches_data():
    quiz = Quiz(THEMES)
    assert quiz.theme_names() == list(THEMES)


def test_pick_subject_returns_a_subject_from_the_chosen_theme():
    quiz = Quiz(THEMES)
    for theme, subjects in THEMES.items():
        subject_name, questions = quiz.pick_subject(theme)
        assert subject_name in subjects
        assert questions == subjects[subject_name]


def test_pick_subject_can_return_different_subjects():
    quiz = Quiz({"Thème": {"A": [], "B": [], "C": []}})
    picks = {quiz.pick_subject("Thème")[0] for _ in range(50)}
    assert len(picks) > 1


def test_pick_subject_does_not_repeat_until_all_subjects_seen():
    quiz = Quiz({"Thème": {"A": [], "B": [], "C": []}})
    seen = set()
    for _ in range(3):
        subject_name, _ = quiz.pick_subject("Thème")
        assert subject_name not in seen
        seen.add(subject_name)
    assert seen == {"A", "B", "C"}


def test_pick_subject_resets_once_all_subjects_have_been_seen():
    quiz = Quiz({"Thème": {"A": [], "B": []}})
    first_round = {quiz.pick_subject("Thème")[0] for _ in range(2)}
    assert first_round == {"A", "B"}

    subject_name, _ = quiz.pick_subject("Thème")
    assert subject_name in {"A", "B"}


def test_pick_subject_tracks_repeats_independently_per_theme():
    quiz = Quiz({"X": {"Commun": []}, "Y": {"Commun": []}})
    quiz.pick_subject("X")

    subject_name, _ = quiz.pick_subject("Y")

    assert subject_name == "Commun"


def test_run_subject_counts_correct_answers():
    quiz = Quiz(THEMES)
    questions = [
        {"question": "q1", "choices": ["a", "b"], "answer": 0},
        {"question": "q2", "choices": ["a", "b"], "answer": 1},
        {"question": "q3", "choices": ["a", "b"], "answer": 0},
    ]
    answers = iter([True, False, True])

    score, total = quiz.run_subject("Sujet", questions, lambda q: next(answers))

    assert score == 2
    assert total == 3


def test_run_subject_asks_every_question_exactly_once():
    quiz = Quiz(THEMES)
    questions = [{"question": f"q{i}", "choices": ["a", "b"], "answer": 0} for i in range(10)]
    asked = []

    quiz.run_subject("Sujet", questions, lambda q: asked.append(q["question"]) or True)

    assert sorted(asked) == sorted(q["question"] for q in questions)


def test_run_subject_does_not_mutate_the_original_question_list():
    quiz = Quiz(THEMES)
    questions = [{"question": f"q{i}", "choices": ["a", "b"], "answer": 0} for i in range(5)]
    original_order = list(questions)

    quiz.run_subject("Sujet", questions, lambda q: True)

    assert questions == original_order
