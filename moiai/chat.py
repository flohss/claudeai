"""
Conversation engine — maintains context, injects personal knowledge, calls Claude.
Auto-triggers conversation summarization when history grows long.
Injects a curiosity block so the AI actively learns from the user.
"""

import anthropic

from .condenser import maybe_summarize_conversations
from .curiosity import build_curiosity_block
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
- Ne jamais oublier ce qu'il t'a confié lors des sessions précédentes.
- Répondre dans la langue de l'utilisateur (français par défaut).
- Être honnête, y compris si quelque chose va à l'encontre de ses intérêts.

## Curiosité et apprentissage actif
Tu cherches activement à mieux connaître l'utilisateur. À chaque échange :
- Pose UNE question naturelle, bien choisie — jamais plusieurs d'un coup.
- La question doit couler dans la conversation, pas tomber comme un formulaire.
- Priorise : (1) approfondir ce qu'il vient de dire, (2) suivre un fil ouvert
  de sessions précédentes, (3) explorer un angle que tu ne connais pas encore.
- Si la conversation est intense ou émotionnelle, lis l'émotion d'abord —
  la question attendra le moment opportun.
- Varie le ton : parfois directe, parfois anecdotique, parfois hypothétique.

## Suivi des fils ouverts
Si tu sais qu'il préparait quelque chose, attendait une réponse, traversait
une période difficile — rappelle-toi et demande comment ça s'est passé.
Ce suivi proactif est ce qui te différencie d'un chatbot ordinaire.

## Gestion des hypothèses et auto-évaluations (règle critique)
Quand l'utilisateur exprime une incertitude sur lui-même ("je pense être TDAH",
"j'ai peut-être de l'anxiété", "je crois que je suis introverti"), tu NE DOIS PAS :
- Valider immédiatement comme si c'était un fait établi
- Invalider ou minimiser
- Jouer au diagnostic clinique

Tu DOIS :
1. Accueillir l'hypothèse avec sérieux et curiosité, sans la confirmer ni l'infirmer.
2. Explorer : qu'est-ce qui lui fait penser ça ? Quels comportements concrets ? Depuis quand ?
3. Apporter un éclairage nuancé si tu connais le sujet, sans poser de diagnostic.
4. Rappeler que seul un professionnel peut confirmer un diagnostic clinique.
5. Mémoriser comme hypothèse, pas comme fait établi.

## Contexte personnel mémorisé
Les faits marqués ○ sont des hypothèses à explorer, pas des certitudes.

{context}
{curiosity}
"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def chat(user_input: str) -> str:
    save_message("user", user_input)

    total = count_messages()
    history = load_recent_messages(limit=30)

    context = build_smart_context(recent_messages=history)

    # Build curiosity block (may call Claude — cached per session turn)
    try:
        curiosity = build_curiosity_block(total_messages=total)
    except Exception:
        curiosity = ""

    system_prompt = _SYSTEM_BASE.format(
        context=context if context else "",
        curiosity=curiosity,
    )

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=history,
    )

    reply = response.content[0].text
    save_message("assistant", reply)

    maybe_summarize_conversations()

    return reply


def get_stats() -> dict:
    summaries = get_conversation_summaries(limit=100)
    return {
        "messages": count_messages(),
        "summaries": len(summaries),
    }
