"""Récupération d'un article Wikipédia aléatoire lié à un sujet."""

import json
import random
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://fr.wikipedia.org/w/api.php"
SUMMARY_URL = "https://fr.wikipedia.org/api/rest_v1/page/summary/{}"
USER_AGENT = "culture-generale-app/1.0 (application pédagogique)"
TIMEOUT = 10


class WikipediaError(Exception):
    """Erreur lors de la récupération d'un article Wikipédia."""


class DisambiguationPage(WikipediaError):
    """Levée quand le titre correspond à une page d'homonymie sans contenu propre."""


def _get_json(url, params=None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise WikipediaError(
            "Impossible de contacter Wikipédia. Vérifiez votre connexion internet."
        ) from exc


def _search(search_expression, limit):
    data = _get_json(
        API_URL,
        {
            "action": "query",
            "list": "search",
            "srsearch": search_expression,
            "srnamespace": 0,
            "srlimit": limit,
            "format": "json",
        },
    )
    return [result["title"] for result in data.get("query", {}).get("search", [])]


def search_titles(query, limit=30):
    """Renvoie les titres d'articles Wikipédia liés à un sujet.

    Cherche d'abord la phrase exacte (plus précis, évite les faux amis dus à
    la racinisation, ex. « capitale » confondu avec « capital ») avant de se
    rabattre sur une recherche plein texte plus large si rien n'est trouvé.
    """
    titles = _search(f'"{query}"', limit) or _search(query, limit)
    if not titles:
        raise WikipediaError(f"Aucun article trouvé pour « {query} ».")
    return titles


def fetch_summary(title):
    """Renvoie le résumé d'un article Wikipédia (titre, extrait, url)."""
    encoded_title = urllib.parse.quote(title.replace(" ", "_"), safe="")
    data = _get_json(SUMMARY_URL.format(encoded_title))
    if data.get("type") == "disambiguation":
        raise DisambiguationPage(title)
    return {
        "title": data.get("title", title),
        "extract": data.get("extract") or "Pas de résumé disponible.",
        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
    }


def random_article(query, choose=random.choice):
    """Tire au hasard un article Wikipédia lié au sujet donné.

    Ignore les pages d'homonymie et retente avec un autre titre tiré au sort
    tant qu'il en reste.
    """
    candidates = list(search_titles(query))
    while candidates:
        title = choose(candidates)
        try:
            return fetch_summary(title)
        except DisambiguationPage:
            candidates.remove(title)
    raise WikipediaError(f"Seules des pages d'homonymie ont été trouvées pour « {query} ».")
