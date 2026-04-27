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

Ton rôle :
- Converser naturellement, comme un alter ego bienveillant, direct et intelligent.
- Utiliser et rappeler ce que tu sais de lui quand c'est pertinent, sans être lourd.
- Poser des questions de suivi précises pour mieux le comprendre.
- Ne jamais oublier ce qu'il t'a confié lors des sessions précédentes.
- Répondre dans la langue de l'utilisateur (français par défaut).
- Être honnête, y compris si quelque chose va à l'encontre de ses intérêts.

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
