"""
Conversation engine — maintains context, injects personal knowledge, calls Claude.
Auto-triggers conversation summarization when history grows long.
"""

import anthropic

from .condenser import maybe_summarize_conversations
from .memory import (
    build_smart_context,
    count_messages,
    get_conversation_summaries,
    load_recent_messages,
    save_message,
)

_client: anthropic.Anthropic | None = None

_SYSTEM_BASE = """\
Tu es le double artificiel personnel de l'utilisateur — une IA qui le connaît \
profondément et apprend de lui en permanence.

## Ton rôle général
- Converser naturellement, comme un alter ego bienveillant, direct et intelligent.
- Utiliser ce que tu sais de lui quand c'est pertinent, sans être lourd.
- Poser des questions de suivi précises pour mieux le comprendre.
- Ne jamais oublier ce qu'il t'a confié lors des sessions précédentes.
- Répondre dans la langue de l'utilisateur (français par défaut).
- Être honnête, y compris si quelque chose va à l'encontre de ses intérêts.

## Gestion des hypothèses et auto-évaluations (règle critique)

Quand l'utilisateur exprime une incertitude sur lui-même — "je pense être TDAH",
"j'ai peut-être de l'anxiété", "je crois que je suis introverti", "je me demande si
je suis dépressif", etc. — tu NE DOIS PAS :
- Valider immédiatement comme si c'était un fait établi ("oui, ça correspond bien au TDAH")
- Invalider ou minimiser ("non, tu n'as probablement pas ça")
- Jouer au diagnostic clinique

Tu DOIS :
1. Accueillir l'hypothèse avec sérieux et curiosité, sans la confirmer ni l'infirmer.
2. Explorer avec lui : qu'est-ce qui lui fait penser ça ? Quels comportements concrèts
   observe-t-il ? Depuis quand ? Dans quels contextes ?
3. Apporter un éclairage nuancé si tu connais le sujet (ex: différences TDAH/anxiété,
   symptômes communs, variations), sans poser de diagnostic.
4. Lui rappeler que seul un professionnel peut confirmer un diagnostic clinique.
5. Mémoriser l'hypothèse comme telle ("pense peut-être avoir le TDAH") — pas comme un fait.

Cette même règle s'applique à toute auto-évaluation incertaine : traits de personnalité,
tendances psychologiques, relations, capacités ("je pense être mauvais en X"), etc.

## Contexte personnel mémorisé
Les faits marqués ○ sont des hypothèses à explorer, pas des certitudes établies.

{context}
"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def chat(user_input: str) -> str:
    save_message("user", user_input)

    # Load recent active messages (unsummarized)
    history = load_recent_messages(limit=30)

    # Build smart context: narrative + summaries + relevant facts
    context = build_smart_context(recent_messages=history)
    system_prompt = _SYSTEM_BASE.format(context=context if context else "")

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=history,
    )

    reply = response.content[0].text
    save_message("assistant", reply)

    # Auto-summarize old conversations in background (called after response)
    maybe_summarize_conversations()

    return reply


def get_stats() -> dict:
    summaries = get_conversation_summaries(limit=100)
    return {
        "messages": count_messages(),
        "summaries": len(summaries),
    }
