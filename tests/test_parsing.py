"""Extraction du JSON produit par les modèles.

Les cas testés ici sont ceux réellement rencontrés en production : balises
Markdown, phrase d'introduction, virgule traînante, réponse tronquée.
"""

from __future__ import annotations

import pytest

from magi.parsing import JSONExtractionError, coerce_str_list, extract_json


class TestExtractJson:
    def test_plain_object(self):
        assert extract_json('{"vote": "APPROVED"}') == {"vote": "APPROVED"}

    def test_surrounding_whitespace(self):
        assert extract_json('\n\n  {"a": 1}  \n') == {"a": 1}

    def test_markdown_fence(self):
        raw = 'Voici mon analyse :\n```json\n{"vote": "REJECTED", "confidence_score": 0.4}\n```'
        assert extract_json(raw)["vote"] == "REJECTED"

    def test_unlabelled_fence(self):
        assert extract_json('```\n{"vote": "APPROVED"}\n```')["vote"] == "APPROVED"

    def test_leading_prose(self):
        raw = 'Après examen, je conclus ceci.\n{"vote": "CONDITIONAL", "confidence_score": 0.6}'
        assert extract_json(raw)["confidence_score"] == 0.6

    def test_trailing_prose(self):
        raw = '{"vote": "APPROVED"}\n\nJ\'espère que cette analyse convient.'
        assert extract_json(raw) == {"vote": "APPROVED"}

    def test_nested_objects_and_braces_in_strings(self):
        raw = '{"detailed_analysis": "le motif {a:b} est cité", "meta": {"n": 2}}'
        parsed = extract_json(raw)
        assert parsed["meta"] == {"n": 2}
        assert "{a:b}" in parsed["detailed_analysis"]

    def test_escaped_quotes_inside_string(self):
        raw = '{"detailed_analysis": "il a dit \\"non\\" clairement", "vote": "REJECTED"}'
        assert extract_json(raw)["vote"] == "REJECTED"

    def test_trailing_comma_is_repaired(self):
        assert extract_json('{"vote": "APPROVED", "key_arguments": ["a", "b",],}')["vote"] == "APPROVED"

    def test_typographic_quotes_are_repaired(self):
        assert extract_json('{“vote”: “APPROVED”}')["vote"] == "APPROVED"

    def test_truncated_object_is_recovered(self):
        # Réponse coupée par max_tokens : les accolades manquantes sont ajoutées.
        raw = '{"vote": "APPROVED", "key_arguments": ["premier argument"]'
        assert extract_json(raw)["vote"] == "APPROVED"

    def test_picks_the_largest_object_when_several_are_present(self):
        raw = 'exemple {"x": 1} puis le vrai {"vote": "APPROVED", "confidence_score": 0.9}'
        assert extract_json(raw).get("vote") == "APPROVED"

    @pytest.mark.parametrize("raw", ["", "   ", "aucun json ici", "[1, 2, 3]", None])
    def test_unparseable_raises(self, raw):
        with pytest.raises(JSONExtractionError):
            extract_json(raw)

    def test_error_message_quotes_the_response(self):
        with pytest.raises(JSONExtractionError, match="désolé"):
            extract_json("désolé, je ne peux pas répondre")


class TestCoerceStrList:
    def test_list_of_strings_passes_through(self):
        assert coerce_str_list(["a", "b"]) == ["a", "b"]

    def test_none_gives_empty_list(self):
        assert coerce_str_list(None) == []

    def test_single_string_becomes_one_item(self):
        assert coerce_str_list("un seul argument") == ["un seul argument"]

    def test_multiline_string_is_split(self):
        assert coerce_str_list("- premier\n- second") == ["premier", "second"]

    def test_dict_values_are_used(self):
        assert coerce_str_list({"a": "premier", "b": "second"}) == ["premier", "second"]

    def test_nested_structures_are_serialised(self):
        assert coerce_str_list([{"point": "x"}]) == ['{"point": "x"}']

    def test_limit_is_enforced(self):
        assert len(coerce_str_list([f"arg{i}" for i in range(20)], limit=3)) == 3

    def test_blank_entries_dropped(self):
        assert coerce_str_list(["a", "  ", ""]) == ["a"]
