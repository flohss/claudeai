#!/usr/bin/env python3
"""
Moi.AI — double personnel artificiel.
Lancement : python main.py
"""

import os
import sys
import threading
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.prompt import Prompt

from moiai.chat import chat, get_stats
from moiai.extractor import extract_and_store, extract_from_messages
from moiai.importer import load_file
from moiai.memory import init_db, get_all_facts, get_profile

console = Console()

COMMANDS = {
    "/profil":          "Afficher ce que je sais de toi",
    "/faits":           "Lister tous les faits mémorisés",
    "/stats":           "Statistiques de la session",
    "/import <fichier>":"Importer un fichier (WhatsApp, Instagram, Telegram, txt)",
    "/aide":            "Afficher cette aide",
    "/quitter":         "Quitter",
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
        lines.append(f"  [cyan]{cmd:<25}[/cyan] {desc}")
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


def _handle_import(args: str) -> None:
    filepath = args.strip().strip('"').strip("'")
    if not filepath:
        console.print("[yellow]Usage :[/yellow] /import <chemin/vers/fichier>\n")
        return

    path = Path(filepath).expanduser().resolve()
    if not path.exists():
        console.print(f"[red]Fichier introuvable :[/red] {path}\n")
        return

    # Detect format first
    from moiai.importer import detect_format
    fmt = detect_format(path)
    console.print(f"[dim]Format détecté : [bold]{fmt}[/bold][/dim]")

    # For WhatsApp/Instagram/Telegram ask for username
    user_name: str | None = None
    if fmt in ("whatsapp", "instagram", "instagram_zip", "instagram_multi", "telegram", "telegram_zip"):
        senders_hint = ""
        # Quick peek at senders
        try:
            _, senders, _ = load_file(path, user_name=None)
            if senders:
                senders_hint = "  Participants trouvés : " + ", ".join(f"[cyan]{s}[/cyan]" for s in senders[:8])
                if len(senders) > 8:
                    senders_hint += f" et {len(senders)-8} autres"
        except Exception:
            pass
        if senders_hint:
            console.print(senders_hint)
        user_name_input = Prompt.ask(
            "[bold]Ton nom dans ce fichier[/bold] (laisser vide = tous les messages)",
            default="",
        ).strip()
        user_name = user_name_input if user_name_input else None

    # Load messages
    try:
        messages, _, _ = load_file(path, user_name=user_name)
    except Exception as e:
        console.print(f"[red]Erreur de lecture :[/red] {e}\n")
        return

    if not messages:
        console.print("[yellow]Aucun message trouvé dans ce fichier.[/yellow]\n")
        return

    console.print(f"[dim]{len(messages)} messages chargés — extraction en cours...[/dim]")

    total_facts = 0
    errors = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Analyse...", total=None)

        def on_progress(current: int, total: int) -> None:
            progress.update(task, total=total, completed=current,
                            description=f"Bloc {current}/{total}")

        try:
            total_facts = extract_from_messages(messages, progress_callback=on_progress)
        except Exception as e:
            errors += 1
            console.print(f"[red]Erreur extraction :[/red] {e}\n")

    if not errors:
        console.print(
            f"[green]✓[/green] Import terminé — "
            f"[bold]{total_facts}[/bold] fait(s) mémorisé(s) depuis [cyan]{path.name}[/cyan]\n"
        )


def _extract_async(user_msg: str, assistant_msg: str) -> None:
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

        cmd_lower = user_input.lower()

        if cmd_lower in ("/quitter", "/exit", "/quit", "exit", "quit"):
            console.print("[dim]À bientôt.[/dim]")
            break
        elif cmd_lower == "/aide":
            _show_help()
            continue
        elif cmd_lower == "/profil":
            _show_profile()
            continue
        elif cmd_lower == "/faits":
            _show_facts()
            continue
        elif cmd_lower == "/stats":
            _show_stats()
            continue
        elif user_input.lower().startswith("/import"):
            _handle_import(user_input[7:])
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

        threading.Thread(
            target=_extract_async,
            args=(user_input, reply),
            daemon=True,
        ).start()


if __name__ == "__main__":
    main()
