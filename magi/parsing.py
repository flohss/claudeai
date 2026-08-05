"""Extraction tolérante de JSON depuis une réponse de LLM.

Même avec une consigne stricte, un modèle encadre volontiers son objet JSON de
balises Markdown, d'une phrase d'introduction ou d'un commentaire final. Ce
module récupère l'objet exploitable sans imposer de re-génération.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)


class JSONExtractionError(ValueError):
    """Aucun objet JSON exploitable n'a pu être isolé dans la réponse."""


def extract_json(text: str) -> dict[str, Any]:
    """Retourne le premier objet JSON valide contenu dans `text`.

    Stratégie, du moins au plus intrusif :
      1. la chaîne entière est déjà du JSON ;
      2. un bloc ```json ... ``` est présent ;
      3. balayage des accolades équilibrées, en ignorant celles des chaînes.

    Lève JSONExtractionError si rien ne convient.
    """
    if not text or not text.strip():
        raise JSONExtractionError("réponse vide")

    candidates: list[str] = [text.strip()]
    candidates.extend(block.strip() for block in _FENCE_RE.findall(text))
    candidates.extend(_balanced_objects(text))

    for candidate in candidates:
        if not candidate.startswith("{"):
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            parsed = _load_lenient(candidate)
        if isinstance(parsed, dict):
            return parsed

    preview = text.strip().replace("\n", " ")[:160]
    raise JSONExtractionError(f"aucun objet JSON trouvé (début de réponse : {preview!r})")


def _balanced_objects(text: str) -> list[str]:
    """Isole les sous-chaînes `{...}` dont les accolades s'équilibrent."""
    objects: list[str] = []
    depth = 0
    start = -1
    in_string = False
    escaped = False

    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    objects.append(text[start : index + 1])

    # Un objet tronqué (réponse coupée par max_tokens) reste récupérable par la
    # passe indulgente ci-dessous.
    if depth > 0 and start >= 0:
        objects.append(text[start:] + "}" * depth)

    objects.sort(key=len, reverse=True)
    return objects


def _load_lenient(candidate: str) -> Any:
    """Deuxième chance : corrige les écarts de syntaxe les plus courants."""
    repaired = re.sub(r",(\s*[}\]])", r"\1", candidate)  # virgules traînantes
    repaired = repaired.replace("“", '"').replace("”", '"')  # guillemets typographiques
    repaired = re.sub(r"//[^\n\"]*", "", repaired)  # commentaires de style JS
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


def coerce_str_list(value: Any, limit: int = 8) -> list[str]:
    """Normalise un champ censé contenir une liste de chaînes."""
    if value is None:
        return []
    if isinstance(value, str):
        parts = [p.strip(" -•\t") for p in value.splitlines() if p.strip()]
        return parts[:limit] if len(parts) > 1 else ([value.strip()] if value.strip() else [])
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
            text = text.strip()
            if text:
                out.append(text)
        return out[:limit]
    return [str(value)]
