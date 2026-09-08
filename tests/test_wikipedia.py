"""Tests du client Wikipédia (sans accès réseau réel : _get_json est simulé)."""

import pytest

from culture_generale import wikipedia


def test_search_titles_returns_titles(monkeypatch):
    monkeypatch.setattr(
        wikipedia,
        "_get_json",
        lambda url, params=None: {
            "query": {"search": [{"title": "Napoléon Ier"}, {"title": "Révolution française"}]}
        },
    )

    titles = wikipedia.search_titles("Histoire")

    assert titles == ["Napoléon Ier", "Révolution française"]


def test_search_titles_raises_when_no_results(monkeypatch):
    monkeypatch.setattr(wikipedia, "_get_json", lambda url, params=None: {"query": {"search": []}})

    with pytest.raises(wikipedia.WikipediaError):
        wikipedia.search_titles("Histoire")


def test_search_titles_tries_exact_phrase_first(monkeypatch):
    captured_expressions = []

    def fake_search(search_expression, limit):
        captured_expressions.append(search_expression)
        return ["Les capitales du monde (liste)"]

    monkeypatch.setattr(wikipedia, "_search", fake_search)

    titles = wikipedia.search_titles("Les capitales du monde")

    assert titles == ["Les capitales du monde (liste)"]
    assert captured_expressions == ['"Les capitales du monde"']


def test_search_titles_falls_back_to_loose_search_when_title_is_related(monkeypatch):
    calls = []

    def fake_search(search_expression, limit):
        calls.append(search_expression)
        if search_expression.startswith('"'):
            return []
        return ["Un sujet historique obscur"]

    monkeypatch.setattr(wikipedia, "_search", fake_search)

    titles = wikipedia.search_titles("Un sujet obscur")

    assert titles == ["Un sujet historique obscur"]
    assert calls == ['"Un sujet obscur"', "Un sujet obscur"]


def test_search_titles_rejects_loose_results_unrelated_to_the_query(monkeypatch):
    def fake_search(search_expression, limit):
        if search_expression.startswith('"'):
            return []
        return ["Uchronie"]

    monkeypatch.setattr(wikipedia, "_search", fake_search)

    with pytest.raises(wikipedia.WikipediaError):
        wikipedia.search_titles("Le monde contemporain")


def test_search_titles_strips_trailing_parenthesis_before_searching(monkeypatch):
    captured = []

    def fake_search(search_expression, limit):
        captured.append(search_expression)
        return ["Résultat"]

    monkeypatch.setattr(wikipedia, "_search", fake_search)

    wikipedia.search_titles("Le monde contemporain (XIXe-XXe siècle)")

    assert captured[0] == '"Le monde contemporain"'


def test_fetch_summary_parses_response(monkeypatch):
    monkeypatch.setattr(
        wikipedia,
        "_get_json",
        lambda url: {
            "title": "Napoléon Ier",
            "extract": "Empereur des Français.",
            "content_urls": {"desktop": {"page": "https://fr.wikipedia.org/wiki/Napol%C3%A9on_Ier"}},
        },
    )

    summary = wikipedia.fetch_summary("Napoléon Ier")

    assert summary == {
        "title": "Napoléon Ier",
        "extract": "Empereur des Français.",
        "url": "https://fr.wikipedia.org/wiki/Napol%C3%A9on_Ier",
    }


def test_fetch_summary_encodes_slashes_in_title(monkeypatch):
    captured_urls = []

    def fake_get_json(url):
        captured_urls.append(url)
        return {"title": "AC/DC", "extract": "Groupe de rock australien.", "content_urls": {}}

    monkeypatch.setattr(wikipedia, "_get_json", fake_get_json)

    wikipedia.fetch_summary("AC/DC")

    assert captured_urls[0].endswith("AC%2FDC")


def test_fetch_summary_handles_missing_extract(monkeypatch):
    monkeypatch.setattr(wikipedia, "_get_json", lambda url: {"title": "X", "content_urls": {}})

    summary = wikipedia.fetch_summary("X")

    assert summary["extract"] == "Pas de résumé disponible."
    assert summary["url"] == ""


def test_fetch_summary_raises_on_disambiguation_page(monkeypatch):
    monkeypatch.setattr(
        wikipedia,
        "_get_json",
        lambda url: {"title": "Moyen Âge (homonymie)", "type": "disambiguation"},
    )

    with pytest.raises(wikipedia.DisambiguationPage):
        wikipedia.fetch_summary("Moyen Âge (homonymie)")


def test_random_article_uses_search_then_fetch(monkeypatch):
    monkeypatch.setattr(wikipedia, "search_titles", lambda theme: ["A", "B", "C"])
    monkeypatch.setattr(
        wikipedia, "fetch_summary", lambda title: {"title": title, "extract": "...", "url": "..."}
    )

    result = wikipedia.random_article("Histoire", choose=lambda titles: titles[1])

    assert result["title"] == "B"


def test_random_article_skips_disambiguation_pages(monkeypatch):
    monkeypatch.setattr(wikipedia, "search_titles", lambda query: ["Moyen Âge (homonymie)", "Charlemagne"])

    def fake_fetch_summary(title):
        if title == "Moyen Âge (homonymie)":
            raise wikipedia.DisambiguationPage(title)
        return {"title": title, "extract": "...", "url": "..."}

    monkeypatch.setattr(wikipedia, "fetch_summary", fake_fetch_summary)

    result = wikipedia.random_article("Moyen Âge", choose=lambda candidates: candidates[0])

    assert result["title"] == "Charlemagne"


def test_random_article_raises_when_only_disambiguation_pages_found(monkeypatch):
    def always_disambiguation(title):
        raise wikipedia.DisambiguationPage(title)

    monkeypatch.setattr(wikipedia, "search_titles", lambda query: ["Moyen Âge (homonymie)"])
    monkeypatch.setattr(wikipedia, "fetch_summary", always_disambiguation)

    with pytest.raises(wikipedia.WikipediaError):
        wikipedia.random_article("Moyen Âge", choose=lambda candidates: candidates[0])


def test_get_json_wraps_network_errors(monkeypatch):
    def raise_error(request, timeout=None):
        raise wikipedia.urllib.error.URLError("boom")

    monkeypatch.setattr(wikipedia.urllib.request, "urlopen", raise_error)

    with pytest.raises(wikipedia.WikipediaError):
        wikipedia._get_json("https://fr.wikipedia.org/w/api.php")
