"""
Conversation engine — maintains context, injects personal knowledge, calls Claude.
"""

import anthropic

from .memory import (
    build_knowledge_summary,
    count_messages,
    load_recent_messages,
    save_message,
)

_client: anthropic.Anthropic | None = None

_SYSTEM_BASE = """\
Tu es le double artificiel personnel de l'utilisateur — une IA qui le connaît \
profondément et apprend de lui en permanence.

Ton rôle :
- Converser naturellement, comme un alter ego bienveillant et intelligent.
- Utiliser et rappeler ce que tu sais de lui quand c'est pertinent.
- Poser des questions de suivi pour mieux le comprendre.
- Ne jamais oublier ce qu'il t'a confié lors des sessions précédentes.
- Répondre dans la langue de l'utilisateur.

{knowledge}
"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _build_system_prompt() -> str:
    knowledge = build_knowledge_summary()
    return _SYSTEM_BASE.format(knowledge=knowledge if knowledge else "")


def chat(user_input: str) -> str:
    save_message("user", user_input)

    history = load_recent_messages(limit=40)
    system_prompt = _build_system_prompt()

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=history,
    )

    reply = response.content[0].text
    save_message("assistant", reply)
    return reply


def get_stats() -> dict:
    return {
        "messages": count_messages(),
    }
