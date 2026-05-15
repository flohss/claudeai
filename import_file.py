#!/usr/bin/env python3
"""
Import a file into Moi.AI memory without entering the chat.

Usage:
  python import_file.py <fichier> [--nom "Ton Nom"]

Formats supportés : WhatsApp (.txt), Instagram (.json/.zip),
                    Telegram (.json/.zip), texte brut (.txt)
"""

import argparse
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.prompt import Prompt

from moiai.extractor import extract_from_messages
from moiai.importer import detect_format, load_file
from moiai.memory import get_all_facts, get_profile, init_db

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Importer un fichier dans Moi.AI")
    parser.add_argument("fichier", help="Chemin vers le fichier à importer")
    parser.add_argument("--nom", default="", help="Ton nom dans ce fichier (WhatsApp/Instagram/Telegram)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Erreur :[/red] ANTHROPIC_API_KEY non définie.\n"
            "Lance : [cyan]export ANTHROPIC_API_KEY=sk-...[/cyan]"
        )
        sys.exit(1)

    init_db()

    path = Path(args.fichier).expanduser().resolve()
    if not path.exists():
        console.print(f"[red]Fichier introuvable :[/red] {path}")
        sys.exit(1)

    fmt = detect_format(path)
    console.print(f"\n[bold]Fichier :[/bold] {path.name}  |  [bold]Format :[/bold] [cyan]{fmt}[/cyan]")

    user_name: str | None = args.nom.strip() or None

    # If messaging format and no name given, offer a peek
    if fmt in ("whatsapp", "instagram", "instagram_zip", "instagram_multi", "telegram", "telegram_zip"):
        if not user_name:
            try:
                _, senders, _ = load_file(path, user_name=None)
                if senders:
                    console.print("Participants : " + ", ".join(f"[cyan]{s}[/cyan]" for s in senders[:10]))
            except Exception:
                pass
            user_name_input = Prompt.ask(
                "[bold]Ton nom dans ce fichier[/bold] (laisser vide = tous les messages)",
                default="",
            ).strip()
            user_name = user_name_input if user_name_input else None

    try:
        messages, _, _ = load_file(path, user_name=user_name)
    except Exception as e:
        console.print(f"[red]Erreur de lecture :[/red] {e}")
        sys.exit(1)

    if not messages:
        console.print("[yellow]Aucun message trouvé.[/yellow]")
        sys.exit(0)

    facts_before = len(get_all_facts())
    console.print(f"[dim]{len(messages)} messages chargés — extraction en cours...[/dim]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Analyse...", total=None)

        def on_progress(current: int, total: int) -> None:
            progress.update(task, total=total, completed=current,
                            description=f"Bloc {current}/{total}")

        total_facts = extract_from_messages(messages, progress_callback=on_progress)

    facts_after = len(get_all_facts())
    profile_size = len(get_profile())

    console.print(
        f"\n[green]✓ Import terminé[/green]\n"
        f"  Faits extraits   : [bold]{total_facts}[/bold]\n"
        f"  Total en mémoire : [bold]{facts_after}[/bold] faits  •  [bold]{profile_size}[/bold] entrées profil\n"
    )


if __name__ == "__main__":
    main()
