"""Interface en ligne de commande du système MAGI.

Affiche la délibération en direct dans le terminal, aux couleurs du dispositif
d'origine : rouge, noir et bleu.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import replace
from pathlib import Path

from rich.align import Align
from rich.console import Console, Group
from rich.columns import Columns
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .config import MagiConfig, find_default_config, load_config, load_env_file
from .events import EventType, MagiEvent
from .models import AGENT_ORDER, BALTHASAR, CASPER, MELCHIOR, MagiDecision, SystemStatus, Vote
from .orchestrator import MagiSystem

# Palette MAGI : rouge (Melchior / refus), bleu (Balthasar / accord),
# orange (Casper / réserve), sur fond noir.
AGENT_COLORS = {
    MELCHIOR: "bright_red",
    BALTHASAR: "bright_cyan",
    CASPER: "orange1",
}

VOTE_COLORS = {
    Vote.APPROVED: "bright_green",
    Vote.CONDITIONAL: "orange1",
    Vote.REJECTED: "bright_red",
}

VOTE_LABELS = {
    Vote.APPROVED: "AGREEMENT",
    Vote.CONDITIONAL: "CONDITIONAL",
    Vote.REJECTED: "DENIAL",
}

STATUS_COLORS = {
    SystemStatus.UNANIMOUS_APPROVAL: "bright_green",
    SystemStatus.MAJORITY_APPROVAL: "bright_cyan",
    SystemStatus.CONDITIONAL_APPROVAL: "orange1",
    SystemStatus.REJECTED: "bright_red",
}

_BANNER = r"""
 ███╗   ███╗  █████╗   ██████╗  ██╗
 ████╗ ████║ ██╔══██╗ ██╔════╝  ██║
 ██╔████╔██║ ███████║ ██║  ███╗ ██║
 ██║╚██╔╝██║ ██╔══██║ ██║   ██║ ██║
 ██║ ╚═╝ ██║ ██║  ██║ ╚██████╔╝ ██║
 ╚═╝     ╚═╝ ╚═╝  ╚═╝  ╚═════╝  ╚═╝
"""


class LiveDisplay:
    """État d'affichage alimenté par les événements du noyau."""

    def __init__(self, console: Console, query: str) -> None:
        self.console = console
        self.query = query
        self.round = 0
        self.max_rounds = 0
        self.backend = ""
        self.status_line = "INITIALISATION DU CONSEIL"
        self.models: dict[str, str] = {}
        self.states: dict[str, str] = {name: "STANDBY" for name in AGENT_ORDER}
        self.verdicts: dict[str, dict] = {}
        self.decision: MagiDecision | None = None

    # -- réception des événements ------------------------------------------

    def __call__(self, event: MagiEvent) -> None:
        payload = event.payload

        if event.type is EventType.DELIBERATION_STARTED:
            self.max_rounds = payload.get("max_rounds", 0)
            self.backend = payload.get("backend", "")
            self.models = {a["name"]: a["model"] for a in payload.get("agents", [])}
            self.status_line = "TRANSMISSION DE LA PROPOSITION AUX TROIS MAGI"

        elif event.type is EventType.ROUND_STARTED:
            self.round = payload["round"]
            self.states = {name: "PROCESSING" for name in AGENT_ORDER}
            self.status_line = (
                "TOUR 1 — ANALYSE INDÉPENDANTE" if self.round == 0
                else f"TOUR {self.round + 1} — DÉBAT CONTRADICTOIRE"
            )

        elif event.type in (EventType.AGENT_VERDICT, EventType.AGENT_ERROR):
            verdict = payload["verdict"]
            self.verdicts[verdict["agent"]] = verdict
            self.states[verdict["agent"]] = "ERROR" if verdict["degraded"] else "COMPLETE"

        elif event.type is EventType.ROUND_COMPLETED:
            tally = payload.get("tally", {})
            self.status_line = (
                f"TOUR {payload['round'] + 1} CLOS — "
                + " / ".join(f"{k} {v}" for k, v in tally.items() if v)
                + (" — UNANIMITÉ" if payload.get("unanimous") else " — DÉSACCORD")
            )

        elif event.type is EventType.DEBATE_SKIPPED:
            self.status_line = f"DÉBAT INUTILE — {payload.get('reason', '').upper()}"

        elif event.type is EventType.CONVERGED:
            self.status_line = f"DÉBAT CLOS — {payload.get('reason', '').upper()}"

        elif event.type is EventType.SYNTHESIS_STARTED:
            self.status_line = "SYNTHÈSE EN COURS — ORCHESTRATEUR MAGI"
            self.states = {name: "COMPLETE" for name in AGENT_ORDER}

        elif event.type is EventType.DECISION:
            self.status_line = "DÉLIBÉRATION TERMINÉE"

    # -- rendu ---------------------------------------------------------------

    def render(self):
        return Group(
            self._header(),
            self._agent_panels(),
            self._footer(),
        )

    def _header(self) -> Panel:
        title = Text("MAGI SYSTEM // CONSEIL DE DÉLIBÉRATION", style="bold bright_red")
        proposal = Text.assemble(
            ("PROPOSAL  ", "bold orange1"),
            (self.query.strip()[:400], "white"),
        )
        meta = Text(
            f"BACKEND {self.backend or '—'}   ·   TOURS MAX {self.max_rounds}   ·   "
            f"ÉTAT : {self.status_line}",
            style="dim bright_cyan",
        )
        return Panel(Group(Align.center(title), Text(), proposal, meta),
                     border_style="bright_red", padding=(0, 2))

    def _agent_panels(self) -> Columns:
        panels = []
        for name in AGENT_ORDER:
            color = AGENT_COLORS[name]
            verdict = self.verdicts.get(name)
            state = self.states.get(name, "STANDBY")

            body = Text()
            body.append(f"{self.models.get(name, '—')}\n", style="dim white")

            if state == "PROCESSING":
                body.append("\n▮▮▮ ANALYSE EN COURS ▮▮▮\n", style=f"blink {color}")
            elif verdict is None:
                body.append("\nEN ATTENTE\n", style="dim")
            else:
                vote = Vote.coerce(verdict["vote"])
                body.append("\n")
                body.append(f"{VOTE_LABELS[vote]}\n", style=f"bold {VOTE_COLORS[vote]}")
                body.append(f"vote      {vote.value}\n", style=VOTE_COLORS[vote])
                body.append(f"confiance {verdict['confidence_score']:.2f}\n", style="white")
                body.append(f"latence   {verdict['latency_ms']} ms\n", style="dim")
                if verdict["degraded"]:
                    body.append("\n⚠ INSTANCE INDISPONIBLE\n", style="bold bright_red")
                body.append("\n")
                for argument in verdict["key_arguments"][:3]:
                    body.append(f"▸ {argument}\n", style="white")

            panels.append(
                Panel(body, title=f"[bold {color}]{name}[/]",
                      subtitle=f"[{color}]{state}[/]",
                      border_style=color, width=42, height=18)
            )
        return Columns(panels, equal=True, expand=True)

    def _footer(self) -> Panel:
        if self.decision is None:
            return Panel(Text("EN ATTENTE DE LA DÉCISION DU CONSEIL…", style="dim bright_cyan"),
                         border_style="bright_cyan", padding=(0, 2))
        return decision_panel(self.decision)


def decision_panel(decision: MagiDecision) -> Panel:
    """Panneau final : statut système, réponse, conditions, dissidence."""
    color = STATUS_COLORS[decision.status]
    parts: list = [
        Align.center(Text(decision.status.value, style=f"bold {color}")),
        Align.center(Text(
            f"consensus {decision.consensus_confidence:.0%}   ·   "
            f"{decision.rounds_used} tour(s)   ·   {decision.total_duration_ms} ms",
            style="dim",
        )),
        Rule(style=color),
        Text(decision.final_answer, style="white"),
    ]

    if decision.conditions:
        parts.append(Text("\nCONDITIONS", style="bold orange1"))
        for condition in decision.conditions:
            parts.append(Text(f"  ▸ {condition}", style="orange1"))

    if decision.dissent:
        parts.append(Text("\nDISSIDENCE", style="bold bright_red"))
        parts.append(Text(f"  {decision.dissent}", style="bright_red"))

    if decision.degraded:
        parts.append(Text("\n⚠ Décision rendue en mode dégradé : au moins une instance "
                          "n'a pas répondu.", style="bold bright_red"))

    return Panel(Group(*parts), title="[bold]DÉCISION FINALE DU SYSTÈME MAGI[/]",
                 border_style=color, padding=(1, 2))


def vote_table(decision: MagiDecision) -> Table:
    """Récapitulatif tour par tour."""
    table = Table(title="HISTORIQUE DES VOTES", border_style="bright_cyan",
                  header_style="bold bright_red", expand=False)
    table.add_column("TOUR", justify="center")
    for name in AGENT_ORDER:
        table.add_column(name, justify="center", style=AGENT_COLORS[name])
    table.add_column("ISSUE", justify="center")

    for debate_round in decision.rounds:
        votes = debate_round.vote_map()
        cells = []
        for name in AGENT_ORDER:
            vote = votes.get(name)
            cells.append(Text(vote.value if vote else "—",
                              style=VOTE_COLORS.get(vote, "dim")) if vote else Text("—"))
        table.add_row(
            str(debate_round.index + 1),
            *cells,
            Text("UNANIME" if debate_round.is_unanimous else "DÉSACCORD",
                 style="bright_green" if debate_round.is_unanimous else "orange1"),
        )
    return table


# --------------------------------------------------------------------------
# Commandes
# --------------------------------------------------------------------------


async def _run_ask(args: argparse.Namespace, config: MagiConfig) -> int:
    console = Console()
    system = MagiSystem(config)

    if args.json:  # sortie machine : aucun affichage décoratif
        decision = await system.deliberate(args.query, args.context)
        print(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2))
        return 0 if decision.status.is_approval else 1

    console.print(Text(_BANNER, style="bold bright_red"))
    display = LiveDisplay(console, args.query)

    with Live(display.render(), console=console, refresh_per_second=8,
              vertical_overflow="visible") as live:
        def sink(event: MagiEvent) -> None:
            display(event)
            live.update(display.render())

        decision = await system.deliberate(args.query, args.context, sink)
        display.decision = decision
        live.update(display.render())

    console.print()
    console.print(vote_table(decision))

    if args.verbose:
        console.print()
        for debate_round in decision.rounds:
            console.print(Rule(f"TOUR {debate_round.index + 1}", style="bright_red"))
            for verdict in debate_round.verdicts:
                console.print(Panel(
                    Text(verdict.detailed_analysis or "(aucune analyse)", style="white"),
                    title=f"[{AGENT_COLORS[verdict.agent]}]{verdict.agent} — "
                          f"{verdict.vote.value} ({verdict.confidence_score:.2f})[/]",
                    border_style=AGENT_COLORS[verdict.agent],
                ))

    if args.output:
        Path(args.output).write_text(
            json.dumps(decision.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        console.print(f"[dim]Délibération enregistrée dans {args.output}[/dim]")

    return 0 if decision.status.is_approval else 1


def _run_check(config: MagiConfig) -> int:
    console = Console()
    table = Table(title="CONFIGURATION MAGI", border_style="bright_red",
                  header_style="bold bright_cyan")
    table.add_column("AGENT")
    table.add_column("MODÈLE")
    table.add_column("TEMP.", justify="right")
    table.add_column("CLÉ REQUISE")
    table.add_column("ÉTAT")

    missing = config.missing_api_keys()
    for cfg in [*config.agents, config.orchestrator]:
        key = cfg.required_env_key or "—"
        if config.backend != "litellm":
            state = Text("SIMULÉ", style="orange1")
        elif cfg.name in missing:
            state = Text("CLÉ ABSENTE", style="bright_red")
        else:
            state = Text("PRÊT", style="bright_green")
        table.add_row(cfg.name, cfg.model, f"{cfg.temperature:.2f}", key, state)

    console.print(table)
    console.print(f"\nBackend       : [bold]{config.backend}[/bold]")
    console.print(f"Tours de débat: [bold]{config.max_debate_rounds}[/bold] maximum")

    if missing:
        console.print("\n[bright_red]Clés d'API manquantes :[/bright_red] "
                      + ", ".join(sorted(set(missing.values()))))
        console.print("[dim]Utilisez --backend simulated pour une démonstration hors ligne.[/dim]")
        return 1

    console.print("\n[bright_green]Le conseil est opérationnel.[/bright_green]")
    return 0


def _run_serve(args: argparse.Namespace, config: MagiConfig) -> int:
    try:
        import uvicorn
    except ImportError:
        print("uvicorn est requis pour l'interface web : pip install 'uvicorn[standard]' fastapi",
              file=sys.stderr)
        return 2

    from .server import create_app

    app = create_app(config)
    print(f"Interface MAGI disponible sur http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


# --------------------------------------------------------------------------
# Point d'entrée
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="magi",
        description="Système de délibération multi-agents MAGI (MELCHIOR-1 / BALTHASAR-2 / CASPER-3).",
        epilog="Exemple : magi \"Faut-il déployer en production un vendredi ?\" --backend simulated",
    )
    parser.add_argument("--version", action="store_true", help="affiche la version et quitte")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-c", "--config", help="fichier de configuration YAML")
    common.add_argument("-b", "--backend", choices=["litellm", "simulated"],
                        help="fournisseur de LLM (défaut : celui de la configuration)")
    common.add_argument("-r", "--rounds", type=int, help="nombre maximal de tours de débat")
    common.add_argument("-v", "--verbose", action="store_true", help="affiche les analyses complètes")

    subparsers = parser.add_subparsers(dest="command")

    ask = subparsers.add_parser("ask", parents=[common], help="soumettre une requête au conseil")
    ask.add_argument("query", help="la question soumise aux trois MAGI")
    ask.add_argument("--context", default="", help="contexte additionnel transmis aux agents")
    ask.add_argument("--json", action="store_true", help="sortie JSON brute, sans interface")
    ask.add_argument("-o", "--output", help="enregistre la délibération complète en JSON")

    subparsers.add_parser("check", parents=[common], help="vérifier la configuration et les clés d'API")

    serve = subparsers.add_parser("serve", parents=[common], help="lancer l'interface web")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Confort d'usage : `magi "une question"` équivaut à `magi ask "une question"`.
    known = {"ask", "check", "serve"}
    if argv and argv[0] not in known and not argv[0].startswith("-"):
        argv.insert(0, "ask")

    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "version", False):
        from . import __version__
        print(f"magi {__version__}")
        return 0

    if not args.command:
        parser.print_help()
        return 0

    logging.basicConfig(
        level=logging.INFO if getattr(args, "verbose", False) else logging.WARNING,
        format="%(levelname)s %(name)s — %(message)s",
        stream=sys.stderr,
    )

    # Les clés posées dans un .env doivent être visibles avant toute lecture de
    # configuration — c'est ce qui rend le fichier utilisable tel quel, sans
    # `export` manuel ni équivalent PowerShell.
    load_env_file()

    config_path = args.config or find_default_config()
    try:
        config = load_config(config_path)
    except Exception as exc:  # noqa: BLE001
        print(f"Configuration invalide : {exc}", file=sys.stderr)
        return 2

    if args.backend:
        config = config.with_backend(args.backend)
    if getattr(args, "rounds", None) is not None:
        config = replace(config, max_debate_rounds=max(0, args.rounds))

    if args.command == "check":
        return _run_check(config)
    if args.command == "serve":
        return _run_serve(args, config)

    missing = config.missing_api_keys()
    if missing:
        print(
            "Clés d'API manquantes : " + ", ".join(sorted(set(missing.values())))
            + "\nLancez `magi check` pour le détail, ou ajoutez --backend simulated "
              "pour une démonstration hors ligne.",
            file=sys.stderr,
        )
        return 2

    try:
        return asyncio.run(_run_ask(args, config))
    except KeyboardInterrupt:
        print("\nDélibération interrompue.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
