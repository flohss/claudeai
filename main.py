#!/usr/bin/env python3
"""
Moi.AI — double personnel artificiel.
Lancement : python main.py
"""

import os
import sys
import threading

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from moiai.chat import chat, get_stats
from moiai.extractor import extract_and_store
from moiai.memory import init_db, build_knowledge_summary, get_all_facts, get_profile

console = Console()

COMMANDS = {
    "/profil":   "Afficher ce que je sais de toi",
    "/faits":    "Lister tous les faits mémorisés",
    "/stats":    "Statistiques de la session",
    "/aide":     "Afficher cette aide",
    "/quitter":  "Quitter",
}


def _header() -> None:
    console.print(Panel(
        "[bold cyan]Moi.AI[/bold cyan]  —  ton double personnel artificiel\n"
        "[dim]Tape [bold]/aide[/bold] pour les commandes disponibles[/dim]",
        border_style="cyan",
        expand=False,
    ))


def _show_help() -> None:
    lines = ["[bold]Commandes disponibles :[/bold]\n"]
    for cmd, desc in COMMANDS.items():
        lines.append(f"  [cyan]{cmd:<12}[/cyan] {desc}")
    console.print("\n".join(lines) + "\n")


def _show_profile() -> None:
    profile = get_profile()
    if not profile:
        console.print("[dim]Aucun profil enregistré pour l'instant.[/dim]\n")
        return
    lines = ["[bold]Profil :[/bold]"]
    for k, v in profile.items():
        lines.append(f"  [cyan]{k}[/cyan] : {v}")
    console.print("\n".join(lines) + "\n")


def _show_facts() -> None:
    facts = get_all_facts()
    if not facts:
        console.print("[dim]Aucun fait mémorisé pour l'instant.[/dim]\n")
        return
    by_cat: dict[str, list[str]] = {}
    for f in facts:
        by_cat.setdefault(f["category"], []).append(f["fact"])
    lines = ["[bold]Faits mémorisés :[/bold]"]
    for cat, items in by_cat.items():
        lines.append(f"\n  [cyan]{cat}[/cyan]")
        seen: set[str] = set()
        for item in items:
            if item not in seen:
                lines.append(f"    • {item}")
                seen.add(item)
    console.print("\n".join(lines) + "\n")


def _show_stats() -> None:
    stats = get_stats()
    facts = get_all_facts()
    profile = get_profile()
    console.print(
        f"[bold]Stats :[/bold]  "
        f"[cyan]{stats['messages']}[/cyan] messages  •  "
        f"[cyan]{len(facts)}[/cyan] faits  •  "
        f"[cyan]{len(profile)}[/cyan] entrées profil\n"
    )


def _extract_async(user_msg: str, assistant_msg: str) -> None:
    """Run extraction in background so the CLI stays responsive."""
    try:
        n = extract_and_store(user_msg, assistant_msg)
        if n:
            console.print(f"[dim]  ✦ {n} nouveau(x) fait(s) mémorisé(s)[/dim]")
    except Exception:
        pass


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Erreur :[/red] La variable d'environnement "
            "[bold]ANTHROPIC_API_KEY[/bold] n'est pas définie.\n"
            "Lance : [cyan]export ANTHROPIC_API_KEY=sk-...[/cyan]"
        )
        sys.exit(1)

    init_db()
    _header()

    while True:
        try:
            user_input = Prompt.ask("[bold green]Toi[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]À bientôt.[/dim]")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("/quitter", "/exit", "/quit", "exit", "quit"):
            console.print("[dim]À bientôt.[/dim]")
            break
        elif cmd == "/aide":
            _show_help()
            continue
        elif cmd == "/profil":
            _show_profile()
            continue
        elif cmd == "/faits":
            _show_facts()
            continue
        elif cmd == "/stats":
            _show_stats()
            continue

        with console.status("[dim]Réflexion...[/dim]", spinner="dots"):
            try:
                reply = chat(user_input)
            except Exception as e:
                console.print(f"[red]Erreur API :[/red] {e}\n")
                continue

        console.print(Panel(
            Markdown(reply),
            title="[bold blue]Moi.AI[/bold blue]",
            border_style="blue",
        ))

        # Extract personal info in background
        threading.Thread(
            target=_extract_async,
            args=(user_input, reply),
            daemon=True,
        ).start()


if __name__ == "__main__":
    main()
