"""Tests de l'interface en ligne de commande."""

from culture_generale.cli import ask_question, choose_theme
from culture_generale.quiz import Quiz

QUESTION = {
    "question": "2 + 2 ?",
    "choices": ["3", "4", "5", "6"],
    "answer": 1,
}


def test_ask_question_correct_answer(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "B")

    assert ask_question(QUESTION) is True
    assert "Bonne réponse" in capsys.readouterr().out


def test_ask_question_wrong_answer_reveals_correct_choice(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "A")

    assert ask_question(QUESTION) is False
    out = capsys.readouterr().out
    assert "Mauvaise réponse" in out
    assert "4" in out


def test_ask_question_accepts_lowercase(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "b")

    assert ask_question(QUESTION) is True


def test_ask_question_reprompts_on_invalid_input(monkeypatch, capsys):
    responses = iter(["Z", "9", "B"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    assert ask_question(QUESTION) is True
    assert "Répondez avec une lettre" in capsys.readouterr().out


def test_choose_theme_zero_quits(monkeypatch):
    quiz = Quiz({"Histoire": {}, "Sport": {}})
    monkeypatch.setattr("builtins.input", lambda _: "0")

    assert choose_theme(quiz) is None


def test_choose_theme_valid_choice(monkeypatch):
    quiz = Quiz({"Histoire": {}, "Sport": {}})
    monkeypatch.setattr("builtins.input", lambda _: "2")

    assert choose_theme(quiz) == "Sport"


def test_choose_theme_reprompts_on_invalid_choice(monkeypatch):
    quiz = Quiz({"Histoire": {}})
    responses = iter(["abc", "9", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    assert choose_theme(quiz) == "Histoire"
