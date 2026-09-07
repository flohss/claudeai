"""Vérifie l'intégrité de la banque de questions."""

from culture_generale.data import THEMES


def test_themes_not_empty():
    assert THEMES


def test_each_theme_has_subjects():
    for theme, subjects in THEMES.items():
        assert subjects, f"La thématique « {theme} » n'a aucun sujet"


def test_each_subject_has_questions():
    for theme, subjects in THEMES.items():
        for subject, questions in subjects.items():
            assert questions, f"Le sujet « {subject} » ({theme}) n'a aucune question"


def test_questions_are_well_formed():
    for theme, subjects in THEMES.items():
        for subject, questions in subjects.items():
            for question in questions:
                context = f"{theme} / {subject} / {question.get('question')!r}"

                assert isinstance(question["question"], str) and question["question"], context

                choices = question["choices"]
                assert isinstance(choices, list), context
                assert 2 <= len(choices) <= 4, context
                assert len(set(choices)) == len(choices), f"Choix en double : {context}"

                answer = question["answer"]
                assert isinstance(answer, int), context
                assert 0 <= answer < len(choices), context
