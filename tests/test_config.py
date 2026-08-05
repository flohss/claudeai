"""Chargement de la configuration : YAML, surcharges d'environnement, clés d'API."""

from __future__ import annotations

import pytest

from magi.config import config_from_dict, default_config, load_config, load_env_file
from magi.models import BALTHASAR, CASPER, MELCHIOR


class TestDefaults:
    def test_three_agents_with_three_distinct_providers(self):
        config = default_config()
        assert [a.name for a in config.agents] == [MELCHIOR, BALTHASAR, CASPER]
        providers = {a.model.split("/")[0] for a in config.agents}
        assert len(providers) == 3, "le triumvirat perd son intérêt avec un seul fournisseur"

    def test_temperatures_are_staggered(self):
        config = default_config()
        temps = {a.name: a.temperature for a in config.agents}
        # Melchior raisonne froid, Casper explore chaud.
        assert temps[MELCHIOR] < temps[BALTHASAR] < temps[CASPER]

    def test_every_agent_has_a_doctrine(self):
        config = default_config()
        for agent in [*config.agents, config.orchestrator]:
            assert len(agent.system_prompt) > 200
        assert "MELCHIOR-1" in config.agent(MELCHIOR).system_prompt


class TestFromDict:
    def test_model_override(self):
        config = config_from_dict({"agents": {MELCHIOR: {"model": "ollama/llama3"}}})
        assert config.agent(MELCHIOR).model == "ollama/llama3"
        # Les autres agents ne bougent pas.
        assert config.agent(CASPER).model == default_config().agent(CASPER).model

    def test_list_form_is_accepted(self):
        config = config_from_dict({"agents": [{"name": CASPER, "model": "groq/llama-3.3-70b"}]})
        assert config.agent(CASPER).model == "groq/llama-3.3-70b"

    def test_temperature_is_clamped(self):
        config = config_from_dict({"agents": {MELCHIOR: {"temperature": 9.5}}})
        assert config.agent(MELCHIOR).temperature == 2.0

    def test_prompt_append_extends_the_doctrine(self):
        config = config_from_dict(
            {"agents": {MELCHIOR: {"system_prompt_append": "Réponds toujours en anglais."}}}
        )
        prompt = config.agent(MELCHIOR).system_prompt
        assert "MELCHIOR-1" in prompt, "la doctrine d'origine doit être conservée"
        assert "Réponds toujours en anglais." in prompt

    def test_prompt_replacement(self):
        config = config_from_dict({"agents": {MELCHIOR: {"system_prompt": "Tu es un autre agent."}}})
        assert config.agent(MELCHIOR).system_prompt == "Tu es un autre agent."

    def test_env_interpolation(self, monkeypatch):
        monkeypatch.setenv("MY_MODEL", "openai/gpt-4o-mini")
        config = config_from_dict({"agents": {CASPER: {"model": "${MY_MODEL}"}}})
        assert config.agent(CASPER).model == "openai/gpt-4o-mini"

    def test_env_interpolation_default_value(self, monkeypatch):
        monkeypatch.delenv("ABSENT_MODEL", raising=False)
        config = config_from_dict({"agents": {CASPER: {"model": "${ABSENT_MODEL:-openai/gpt-4o}"}}})
        assert config.agent(CASPER).model == "openai/gpt-4o"

    def test_top_level_settings(self):
        config = config_from_dict({"backend": "simulated", "max_debate_rounds": 4})
        assert config.backend == "simulated"
        assert config.max_debate_rounds == 4

    def test_negative_rounds_are_floored(self):
        assert config_from_dict({"max_debate_rounds": -3}).max_debate_rounds == 0


class TestYamlLoading:
    def test_load_from_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MAGI_BACKEND", raising=False)
        path = tmp_path / "magi.yaml"
        path.write_text(
            "backend: simulated\nmax_debate_rounds: 1\n"
            "agents:\n  MELCHIOR-1:\n    model: mistral/mistral-large-latest\n",
            encoding="utf-8",
        )
        config = load_config(path)
        assert config.backend == "simulated"
        assert config.max_debate_rounds == 1
        assert config.agent(MELCHIOR).model == "mistral/mistral-large-latest"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "absent.yaml")

    def test_non_mapping_root_raises(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text("- juste une liste\n", encoding="utf-8")
        with pytest.raises(ValueError, match="mapping"):
            load_config(path)

    def test_environment_wins_over_the_file(self, tmp_path, monkeypatch):
        path = tmp_path / "magi.yaml"
        path.write_text("agents:\n  CASPER-3:\n    model: from/file\n", encoding="utf-8")
        monkeypatch.setenv("MAGI_CASPER_MODEL", "from/env")
        assert load_config(path).agent(CASPER).model == "from/env"

    def test_backend_env_override(self, monkeypatch):
        monkeypatch.setenv("MAGI_BACKEND", "simulated")
        assert load_config(None).backend == "simulated"


class TestEnvFile:
    def test_keys_are_loaded_into_the_environment(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        env = tmp_path / ".env"
        env.write_text("ANTHROPIC_API_KEY=sk-ant-test\n", encoding="utf-8")

        assert load_env_file(env) == {"ANTHROPIC_API_KEY": "sk-ant-test"}
        import os
        assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-test"

    def test_comments_blanks_and_export_prefix(self, tmp_path, monkeypatch):
        for key in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        env = tmp_path / ".env"
        env.write_text(
            "# un commentaire\n\n"
            "export OPENAI_API_KEY=sk-openai\n"
            'GEMINI_API_KEY="sk-gemini"\n',
            encoding="utf-8",
        )
        applied = load_env_file(env)
        assert applied["OPENAI_API_KEY"] == "sk-openai"
        assert applied["GEMINI_API_KEY"] == "sk-gemini", "les guillemets doivent être retirés"

    def test_empty_values_are_ignored(self, tmp_path, monkeypatch):
        # .env.example est livré avec des clés vides : les charger masquerait
        # le diagnostic « clé absente » derrière une chaîne vide.
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        env = tmp_path / ".env"
        env.write_text("OPENAI_API_KEY=\n", encoding="utf-8")

        assert load_env_file(env) == {}
        assert default_config().missing_api_keys()

    def test_existing_environment_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "déjà-exportée")
        env = tmp_path / ".env"
        env.write_text("OPENAI_API_KEY=depuis-le-fichier\n", encoding="utf-8")

        assert load_env_file(env) == {}
        import os
        assert os.environ["OPENAI_API_KEY"] == "déjà-exportée"

    def test_missing_file_is_not_an_error(self, tmp_path):
        assert load_env_file(tmp_path / "absent.env") == {}

    def test_bom_is_tolerated(self, tmp_path, monkeypatch):
        # Le Bloc-notes de Windows écrit volontiers un BOM en tête de fichier.
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        env = tmp_path / ".env"
        env.write_bytes("OPENAI_API_KEY=sk-windows\n".encode("utf-8-sig"))

        assert load_env_file(env) == {"OPENAI_API_KEY": "sk-windows"}

    def test_malformed_lines_are_skipped(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        env = tmp_path / ".env"
        env.write_text("ligne sans egal\nOPENAI_API_KEY=sk-ok\n", encoding="utf-8")

        assert load_env_file(env) == {"OPENAI_API_KEY": "sk-ok"}


class TestApiKeys:
    def test_missing_keys_are_reported_per_agent(self, monkeypatch):
        for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        missing = default_config().missing_api_keys()
        assert missing[MELCHIOR] == "ANTHROPIC_API_KEY"
        assert missing[BALTHASAR] == "OPENAI_API_KEY"
        assert missing[CASPER] == "GEMINI_API_KEY"

    def test_present_keys_are_not_reported(self, monkeypatch):
        for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
            monkeypatch.setenv(key, "clé-de-test")
        assert default_config().missing_api_keys() == {}

    def test_simulated_backend_needs_no_key(self, monkeypatch):
        for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        assert default_config().with_backend("simulated").missing_api_keys() == {}
