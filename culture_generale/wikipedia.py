"""Récupération d'un article Wikipédia aléatoire lié à un sujet."""

import json
import random
import re
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


def _strip_trailing_parenthesis(query):
    """Retire un qualificatif entre parenthèses en fin de chaîne (ex. « (Tome 2) »).

    Ces qualificatifs sont nos propres regroupements de sujets, pas des
    formulations qu'on retrouve telles quelles dans la prose de Wikipédia :
    les garder ne fait que bruiter la recherche.
    """
    return re.sub(r"\s*\([^)]*\)\s*$", "", query).strip() or query


_LEADING_ARTICLE_RE = re.compile(r"^(?:les|la|le)\s+|^l['’]", re.IGNORECASE)


def _strip_leading_article(text):
    """Retire un article défini initial (« Les », « La », « Le », « L' »).

    Les titres réels de Wikipédia commencent rarement par l'article défini
    de nos intitulés de sujets (ex. « Liste des rois de France » plutôt que
    « Les rois de France ») ; le retirer aide la recherche par titre.
    """
    return _LEADING_ARTICLE_RE.sub("", text, count=1).strip() or text


def _significant_words(text):
    """Mots de 4 lettres ou plus, en minuscules — ignore les mots-outils courts."""
    return {word for word in re.findall(r"\w{4,}", text.lower())}


def search_titles(query, limit=30):
    """Renvoie les titres d'articles Wikipédia liés à un sujet.

    Cherche d'abord des articles dont le TITRE contient la phrase du sujet
    (le plus fiable : le titre garantit que l'article traite bien de ce
    sujet). En dernier recours, une recherche plein texte est tentée, mais
    restreinte aux résultats dont le titre partage au moins un mot
    significatif avec la requête — une simple mention en passant dans le
    corps d'un article sans rapport (ex. « Grégoire IX », dont la biographie
    évoque une fois « les rois de France ») est trop souvent hors sujet.
    """
    cleaned = _strip_trailing_parenthesis(query)
    significant = _significant_words(cleaned)

    titles = _search(f'intitle:"{_strip_leading_article(cleaned)}"', limit)
    if not titles:
        loose = _search(f'"{cleaned}"', limit) or _search(cleaned, limit)
        titles = [title for title in loose if _significant_words(title) & significant]
    if not titles:
        raise WikipediaError(f"Aucun article suffisamment pertinent trouvé pour « {query} ».")
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
