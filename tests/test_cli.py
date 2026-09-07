"""Tests de l'interface en ligne de commande."""

from culture_generale import cli
from culture_generale.cli import ask_question, choose_mode, choose_theme, display_article, run_wikipedia_mode
from culture_generale.quiz import Quiz
from culture_generale.wikipedia import WikipediaError

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


def test_choose_mode_quit(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "0")

    assert choose_mode() is None


def test_choose_mode_quiz(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "1")

    assert choose_mode() == "quiz"


def test_choose_mode_wikipedia(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "2")

    assert choose_mode() == "wikipedia"


def test_choose_mode_reprompts_on_invalid_choice(monkeypatch):
    responses = iter(["xyz", "5", "2"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    assert choose_mode() == "wikipedia"


def test_display_article_prints_title_extract_and_url(capsys):
    article = {"title": "Napoléon Ier", "extract": "Empereur des Français.", "url": "https://fr.wikipedia.org/wiki/Napoléon_Ier"}

    display_article(article)

    out = capsys.readouterr().out
    assert "Napoléon Ier" in out
    assert "Empereur des Français." in out
    assert "https://fr.wikipedia.org/wiki/Napoléon_Ier" in out


def test_display_article_without_url(capsys):
    article = {"title": "X", "extract": "Extrait.", "url": ""}

    display_article(article)

    assert "🔗" not in capsys.readouterr().out


def test_run_wikipedia_mode_displays_article_then_stops(monkeypatch):
    quiz = Quiz({"Histoire": {}})
    responses = iter(["1", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    monkeypatch.setattr(cli, "random_article", lambda theme: {"title": "T", "extract": "E", "url": "U"})

    run_wikipedia_mode(quiz)


def test_run_wikipedia_mode_handles_error_gracefully(monkeypatch, capsys):
    quiz = Quiz({"Histoire": {}})
    responses = iter(["1", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    def raise_error(theme):
        raise WikipediaError("pas de connexion")

    monkeypatch.setattr(cli, "random_article", raise_error)

    run_wikipedia_mode(quiz)

    assert "pas de connexion" in capsys.readouterr().out
