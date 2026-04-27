#!/usr/bin/env python3
"""
Moi.AI — double personnel artificiel.
Lancement : python main.py
"""

import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from moiai.chat import chat, get_stats
from moiai.condenser import condense_narrative, summarize_old_conversations
from moiai.extractor import extract_and_store, extract_from_messages
from moiai.importer import load_file
from moiai.memory import (
    CERTAINTY_BADGE,
    delete_fact,
    delete_profile_key,
    get_all_facts,
    get_latest_narrative,
    get_profile,
    init_db,
    search_facts,
)

console = Console()

COMMANDS = {
    "/profil":           "Afficher le profil mémorisé",
    "/faits":            "Lister tous les faits mémorisés",
    "/cherche <terme>":  "Rechercher dans la mémoire",
    "/oublie <terme>":   "Supprimer des faits ou entrées profil",
    "/condenser":        "Fusionner la mémoire en narration personnelle",
    "/rapport":          "Exporter un rapport complet de ton profil",
    "/import <fichier>": "Importer un fichier (WhatsApp, Instagram, Telegram, txt)",
    "/stats":            "Statistiques de mémoire",
    "/aide":             "Afficher cette aide",
    "/quitter":          "Quitter",
}


def _header() -> None:
    console.print(Panel(
        "[bold cyan]Moi.AI[/bold cyan]  —  ton double personnel artificiel\n"
        "[dim]Tape [bold]/aide[/bold] pour les commandes disponibles[/dim]",
        border_style="cyan",
        expand=False,
    ))


def _show_help() -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan", no_wrap=True)
    table.add_column()
    for cmd, desc in COMMANDS.items():
        table.add_row(cmd, desc)
    console.print(Panel(table, title="[bold]Commandes[/bold]", border_style="dim"))
    console.print()


def _show_profile() -> None:
    profile = get_profile()
    narrative = get_latest_narrative()

    if narrative:
        console.print(Panel(Markdown(narrative), title="[bold]Narration personnelle[/bold]", border_style="cyan"))

    if profile:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan bold", no_wrap=True)
        table.add_column()
        for k, v in profile.items():
            table.add_row(k, v)
        console.print(Panel(table, title="[bold]Profil[/bold]", border_style="blue"))
    elif not narrative:
        console.print("[dim]Aucun profil enregistré pour l'instant.[/dim]")
    console.print()


_CERTAINTY_COLOR = {
    "certain":   "white",
    "probable":  "yellow",
    "hypothèse": "dim",
    "réfuté":    "red",
}


def _show_facts() -> None:
    facts = get_all_facts()
    if not facts:
        console.print("[dim]Aucun fait mémorisé pour l'instant.[/dim]\n")
        return

    by_cat: dict[str, list[dict]] = {}
    for f in facts:
        by_cat.setdefault(f["category"], []).append(f)

    console.print(
        "[dim]● certain  ◐ probable  ○ hypothèse  ✕ réfuté[/dim]\n"
    )
    for cat, items in by_cat.items():
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("ID", style="dim", width=5)
        table.add_column(" ", width=2, no_wrap=True)
        table.add_column("Fait")
        table.add_column("✓", style="dim", width=4, justify="right")
        for f in items:
            certainty = f.get("certainty", "certain")
            badge = CERTAINTY_BADGE.get(certainty, "●")
            color = _CERTAINTY_COLOR.get(certainty, "white")
            table.add_row(
                str(f["id"]),
                f"[{color}]{badge}[/{color}]",
                f"[{color}]{f['fact']}[/{color}]",
                str(f["confirmed"]),
            )
        console.print(Panel(table, title=f"[bold cyan]{cat}[/bold cyan]", border_style="dim"))

    console.print(f"[dim]{len(facts)} faits au total[/dim]\n")


def _show_stats() -> None:
    stats = get_stats()
    facts = get_all_facts()
    profile = get_profile()
    narrative = get_latest_narrative()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold cyan")
    table.add_row("Messages totaux", str(stats["messages"]))
    table.add_row("Résumés de conversation", str(stats["summaries"]))
    table.add_row("Faits mémorisés", str(len(facts)))
    table.add_row("Entrées profil", str(len(profile)))
    table.add_row("Narration condensée", "oui" if narrative else "non")
    console.print(Panel(table, title="[bold]Statistiques[/bold]", border_style="dim"))
    console.print()


def _handle_search(query: str) -> None:
    if not query.strip():
        console.print("[yellow]Usage :[/yellow] /cherche <terme>\n")
        return

    results = search_facts(query.strip())
    facts = results["facts"]
    profile = results["profile"]

    if not facts and not profile:
        console.print(f"[dim]Aucun résultat pour « {query.strip()} ».[/dim]\n")
        return

    if profile:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan bold")
        table.add_column()
        for k, v in profile.items():
            table.add_row(k, v)
        console.print(Panel(table, title="[bold]Profil[/bold]", border_style="blue"))

    if facts:
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("ID", style="dim", width=5)
        table.add_column(" ", width=2, no_wrap=True)
        table.add_column("Catégorie", style="cyan", width=16)
        table.add_column("Fait")
        for f in facts:
            certainty = f.get("certainty", "certain")
            badge = CERTAINTY_BADGE.get(certainty, "●")
            color = _CERTAINTY_COLOR.get(certainty, "white")
            table.add_row(
                str(f["id"]),
                f"[{color}]{badge}[/{color}]",
                f["category"],
                f"[{color}]{f['fact']}[/{color}]",
            )
        console.print(Panel(table, title=f"[bold]{len(facts)} fait(s) trouvé(s)[/bold]", border_style="dim"))

    console.print()


def _handle_forget(query: str) -> None:
    query = query.strip()
    if not query:
        console.print("[yellow]Usage :[/yellow] /oublie <terme ou ID>\n")
        return

    # Try numeric ID first
    if query.isdigit():
        fact_id = int(query)
        facts = get_all_facts()
        target = next((f for f in facts if f["id"] == fact_id), None)
        if not target:
            console.print(f"[red]Aucun fait avec l'ID {fact_id}.[/red]\n")
            return
        console.print(f"Fait : [cyan]{target['fact']}[/cyan]")
        if Confirm.ask("Supprimer ce fait ?", default=False):
            delete_fact(fact_id)
            console.print("[green]✓ Supprimé.[/green]\n")
        else:
            console.print("[dim]Annulé.[/dim]\n")
        return

    # Otherwise search and let user pick
    results = search_facts(query)
    facts = results["facts"]
    profile = results["profile"]

    deleted_any = False

    if profile:
        for k, v in profile.items():
            console.print(f"Profil : [cyan]{k}[/cyan] = {v}")
            if Confirm.ask(f"Supprimer l'entrée profil « {k} » ?", default=False):
                delete_profile_key(k)
                console.print(f"[green]✓ Entrée « {k} » supprimée.[/green]")
                deleted_any = True

    if facts:
        for f in facts:
            console.print(f"[dim]ID {f['id']}[/dim] [{f['category']}] {f['fact']}")
            if Confirm.ask("Supprimer ce fait ?", default=False):
                delete_fact(f["id"])
                console.print("[green]✓ Supprimé.[/green]")
                deleted_any = True

    if not facts and not profile:
        console.print(f"[dim]Aucun résultat pour « {query} ».[/dim]")

    console.print()


def _handle_condense() -> None:
    console.print("[dim]Condensation de la mémoire en cours...[/dim]")
    with console.status("[dim]Claude synthétise ton profil...[/dim]", spinner="dots"):
        try:
            narrative = condense_narrative()
        except Exception as e:
            console.print(f"[red]Erreur :[/red] {e}\n")
            return

    console.print(Panel(
        Markdown(narrative),
        title="[bold]Narration personnelle condensée[/bold]",
        border_style="cyan",
    ))
    console.print("[green]✓ Narration sauvegardée en mémoire.[/green]\n")


def _handle_rapport() -> None:
    profile = get_profile()
    facts = get_all_facts()
    narrative = get_latest_narrative()
    stats = get_stats()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [f"# Rapport Moi.AI — {now}\n"]

    if narrative:
        lines.append("## Narration personnelle\n")
        lines.append(narrative)
        lines.append("")

    if profile:
        lines.append("## Profil\n")
        for k, v in profile.items():
            lines.append(f"- **{k}** : {v}")
        lines.append("")

    if facts:
        by_cat: dict[str, list[str]] = {}
        for f in facts:
            by_cat.setdefault(f["category"], []).append(f["fact"])
        lines.append("## Faits mémorisés\n")
        for cat, items in sorted(by_cat.items()):
            lines.append(f"### {cat}")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")

    lines.append("## Statistiques\n")
    lines.append(f"- Messages totaux : {stats['messages']}")
    lines.append(f"- Faits mémorisés : {len(facts)}")
    lines.append(f"- Entrées profil : {len(profile)}")
    lines.append(f"- Résumés de conversation : {stats['summaries']}")

    report_text = "\n".join(lines)

    # Save to file
    report_path = Path("rapport_moiai.md")
    report_path.write_text(report_text, encoding="utf-8")

    console.print(Panel(
        Markdown(report_text[:2000] + ("\n\n[…]" if len(report_text) > 2000 else "")),
        title="[bold]Rapport[/bold]",
        border_style="cyan",
    ))
    console.print(f"[green]✓ Rapport complet sauvegardé dans[/green] [bold]{report_path}[/bold]\n")


def _handle_import(args: str) -> None:
    filepath = args.strip().strip('"').strip("'")
    if not filepath:
        console.print("[yellow]Usage :[/yellow] /import <chemin/vers/fichier>\n")
        return

    path = Path(filepath).expanduser().resolve()
    if not path.exists():
        console.print(f"[red]Fichier introuvable :[/red] {path}\n")
        return

    from moiai.importer import detect_format
    fmt = detect_format(path)
    console.print(f"[dim]Format détecté : [bold]{fmt}[/bold][/dim]")

    user_name: str | None = None
    if fmt in ("whatsapp", "instagram", "instagram_zip", "instagram_multi", "telegram", "telegram_zip"):
        try:
            _, senders, _ = load_file(path, user_name=None)
            if senders:
                console.print("Participants : " + ", ".join(f"[cyan]{s}[/cyan]" for s in senders[:8]))
        except Exception:
            pass
        inp = Prompt.ask(
            "[bold]Ton nom dans ce fichier[/bold] (laisser vide = tous les messages)",
            default="",
        ).strip()
        user_name = inp if inp else None

    try:
        messages, _, _ = load_file(path, user_name=user_name)
    except Exception as e:
        console.print(f"[red]Erreur de lecture :[/red] {e}\n")
        return

    if not messages:
        console.print("[yellow]Aucun message trouvé dans ce fichier.[/yellow]\n")
        return

    console.print(f"[dim]{len(messages)} messages chargés — extraction en cours...[/dim]")

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
            console.print(f"[red]Erreur extraction :[/red] {e}\n")
            return

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

        lower = user_input.lower()

        if lower in ("/quitter", "/exit", "/quit", "exit", "quit"):
            console.print("[dim]À bientôt.[/dim]")
            break
        elif lower == "/aide":
            _show_help()
        elif lower == "/profil":
            _show_profile()
        elif lower == "/faits":
            _show_facts()
        elif lower == "/stats":
            _show_stats()
        elif lower == "/condenser":
            _handle_condense()
        elif lower == "/rapport":
            _handle_rapport()
        elif lower.startswith("/cherche"):
            _handle_search(user_input[8:])
        elif lower.startswith("/oublie"):
            _handle_forget(user_input[7:])
        elif lower.startswith("/import"):
            _handle_import(user_input[7:])
        else:
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
