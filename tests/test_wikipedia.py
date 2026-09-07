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


def test_random_article_uses_search_then_fetch(monkeypatch):
    monkeypatch.setattr(wikipedia, "search_titles", lambda theme: ["A", "B", "C"])
    monkeypatch.setattr(
        wikipedia, "fetch_summary", lambda title: {"title": title, "extract": "...", "url": "..."}
    )

    result = wikipedia.random_article("Histoire", choose=lambda titles: titles[1])

    assert result["title"] == "B"


def test_get_json_wraps_network_errors(monkeypatch):
    def raise_error(request, timeout=None):
        raise wikipedia.urllib.error.URLError("boom")

    monkeypatch.setattr(wikipedia.urllib.request, "urlopen", raise_error)

    with pytest.raises(wikipedia.WikipediaError):
        wikipedia._get_json("https://fr.wikipedia.org/w/api.php")
