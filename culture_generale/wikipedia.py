"""Récupération d'un article Wikipédia aléatoire lié à une thématique."""

import json
import random
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://fr.wikipedia.org/w/api.php"
SUMMARY_URL = "https://fr.wikipedia.org/api/rest_v1/page/summary/{}"
USER_AGENT = "culture-generale-app/1.0 (application pédagogique)"
TIMEOUT = 10

THEME_QUERIES = {
    "Histoire": "histoire",
    "Géographie": "géographie",
    "Sciences": "science",
    "Littérature & Arts": "littérature art peinture",
    "Sport": "sport",
}


class WikipediaError(Exception):
    """Erreur lors de la récupération d'un article Wikipédia."""


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


def search_titles(theme, limit=30):
    """Renvoie les titres d'articles Wikipédia liés à une thématique."""
    query = THEME_QUERIES.get(theme, theme)
    data = _get_json(
        API_URL,
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": 0,
            "srlimit": limit,
            "format": "json",
        },
    )
    results = data.get("query", {}).get("search", [])
    if not results:
        raise WikipediaError(f"Aucun article trouvé pour la thématique « {theme} ».")
    return [result["title"] for result in results]


def fetch_summary(title):
    """Renvoie le résumé d'un article Wikipédia (titre, extrait, url)."""
    encoded_title = urllib.parse.quote(title.replace(" ", "_"), safe="")
    data = _get_json(SUMMARY_URL.format(encoded_title))
    return {
        "title": data.get("title", title),
        "extract": data.get("extract") or "Pas de résumé disponible.",
        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
    }


def random_article(theme, choose=random.choice):
    """Tire au hasard un article Wikipédia lié à la thématique donnée."""
    titles = search_titles(theme)
    return fetch_summary(choose(titles))
