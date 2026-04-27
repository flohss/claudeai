#!/usr/bin/env python3
"""
Moi.AI — double personnel artificiel.
Lancement : python main.py
"""

import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from moiai.chat import finish_turn, get_stats, start_session, stream_response
from moiai.condenser import condense_narrative
from moiai.extractor import extract_and_store, extract_from_messages
from moiai.importer import load_file
from moiai.memory import (
    CERTAINTY_BADGE,
    CERTAINTY_LEVELS,
    delete_fact,
    delete_profile_key,
    fact_age_badge,
    get_all_facts,
    get_conversation_summaries,
    get_fact_by_id,
    get_latest_narrative,
    get_profile,
    get_recent_mood,
    get_stale_facts,
    init_db,
    load_conversation_history,
    search_facts,
    update_fact,
)

console = Console()

_CERTAINTY_COLOR = {
    "certain":   "white",
    "probable":  "yellow",
    "hypothèse": "dim",
    "réfuté":    "red",
}

COMMANDS = {
    "/profil":              "Afficher profil + narration",
    "/faits [cat]":         "Lister les faits (filtrable par catégorie)",
    "/cherche <terme>":     "Recherche plein-texte dans la mémoire",
    "/oublie <ID|terme>":   "Supprimer un fait ou une entrée profil",
    "/edit <ID> <texte>":   "Corriger le texte d'un fait",
    "/historique [n]":      "Afficher les n derniers échanges (défaut 10)",
    "/import <fichier>":    "Importer un fichier (WhatsApp, Instagram, Telegram, txt)",
    "/condenser":           "Fusionner la mémoire en narration personnelle",
    "/rapport":             "Exporter le profil complet en Markdown",
    "/export":              "Exporter toute la mémoire en JSON",
    "/stats":               "Statistiques de mémoire",
    "/aide":                "Afficher cette aide",
    "/quitter":             "Quitter",
}


# ── Header ─────────────────────────────────────────────────────────────────────

def _header() -> None:
    console.print(Panel(
        "[bold cyan]Moi.AI[/bold cyan]  —  ton double personnel artificiel\n"
        "[dim]Tape [bold]/aide[/bold] pour les commandes  •  "
        "Les réponses s'affichent en temps réel[/dim]",
        border_style="cyan",
        expand=False,
    ))


# ── Help ───────────────────────────────────────────────────────────────────────

def _show_help() -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan", no_wrap=True)
    table.add_column()
    for cmd, desc in COMMANDS.items():
        table.add_row(cmd, desc)
    console.print(Panel(table, title="[bold]Commandes[/bold]", border_style="dim"))
    console.print()


# ── Profile ────────────────────────────────────────────────────────────────────

def _show_profile() -> None:
    narrative = get_latest_narrative()
    profile = get_profile()
    mood = get_recent_mood(limit=1)

    if narrative:
        console.print(Panel(
            Markdown(narrative),
            title="[bold]Narration personnelle[/bold]",
            border_style="cyan",
        ))

    if mood:
        m = mood[0]
        badge = {"positive": "🟢", "negative": "🔴", "mixed": "🟡", "neutral": "⚪"}.get(m["valence"], "⚪")
        console.print(f"[dim]Humeur récente : {badge} {m['state']}[/dim]")

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


# ── Facts ──────────────────────────────────────────────────────────────────────

def _show_facts(args: str = "") -> None:
    cat_filter = args.strip().lower() or None
    facts = get_all_facts()
    if cat_filter:
        facts = [f for f in facts if cat_filter in f["category"].lower()]

    if not facts:
        msg = f"Aucun fait dans la catégorie « {cat_filter} »." if cat_filter else "Aucun fait mémorisé."
        console.print(f"[dim]{msg}[/dim]\n")
        return

    console.print("[dim]● certain  ◐ probable  ○ hypothèse  ✕ réfuté  ⏳ >6 mois  ⌛ >1 an[/dim]\n")

    by_cat: dict[str, list[dict]] = {}
    for f in facts:
        by_cat.setdefault(f["category"], []).append(f)

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
            age = fact_age_badge(f.get("last_confirmed") or f["timestamp"])
            table.add_row(
                str(f["id"]),
                f"[{color}]{badge}[/{color}]",
                f"[{color}]{f['fact']}[/{color}]{age}",
                str(f["confirmed"]),
            )
        console.print(Panel(table, title=f"[bold cyan]{cat}[/bold cyan]", border_style="dim"))

    console.print(f"[dim]{len(facts)} fait(s)[/dim]\n")


# ── Stats ──────────────────────────────────────────────────────────────────────

def _show_stats() -> None:
    stats = get_stats()
    facts = get_all_facts()
    profile = get_profile()
    narrative = get_latest_narrative()
    summaries = get_conversation_summaries(limit=100)
    stale = get_stale_facts(days=180)

    by_cat: dict[str, int] = {}
    for f in facts:
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold cyan")
    table.add_row("Messages totaux", str(stats["messages"]))
    table.add_row("Résumés de conversation", str(len(summaries)))
    table.add_row("Faits mémorisés", str(len(facts)))
    table.add_row("Dont potentiellement périmés", f"[yellow]{len(stale)}[/yellow]" if stale else "0")
    table.add_row("Entrées profil", str(len(profile)))
    table.add_row("Narration condensée", "[green]oui[/green]" if narrative else "[dim]non[/dim]")

    if by_cat:
        table.add_row("", "")
        for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
            table.add_row(f"  {cat}", str(n))

    console.print(Panel(table, title="[bold]Statistiques[/bold]", border_style="dim"))
    console.print()


# ── Search ─────────────────────────────────────────────────────────────────────

def _handle_search(args: str) -> None:
    query = args.strip()
    if not query:
        console.print("[yellow]Usage :[/yellow] /cherche <terme>\n")
        return

    results = search_facts(query, limit=25)
    facts = results["facts"]
    profile = results["profile"]

    if not facts and not profile:
        console.print(f"[dim]Aucun résultat pour « {query} ».[/dim]\n")
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
        table.add_column("Catégorie", style="cyan", width=14)
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
        console.print(Panel(
            table,
            title=f"[bold]{len(facts)} fait(s) trouvé(s)[/bold]"
            + ("[dim] (25 max)[/dim]" if len(facts) == 25 else ""),
            border_style="dim",
        ))

    console.print()


# ── Forget ─────────────────────────────────────────────────────────────────────

def _handle_forget(args: str) -> None:
    query = args.strip()
    if not query:
        console.print("[yellow]Usage :[/yellow] /oublie <ID ou terme>\n")
        return

    if query.isdigit():
        f = get_fact_by_id(int(query))
        if not f:
            console.print(f"[red]Aucun fait avec l'ID {query}.[/red]\n")
            return
        certainty = f.get("certainty", "certain")
        color = _CERTAINTY_COLOR.get(certainty, "white")
        console.print(f"[dim]#{f['id']}[/dim] [{f['category']}] [{color}]{f['fact']}[/{color}]")
        if Confirm.ask("Supprimer ?", default=False):
            delete_fact(f["id"])
            console.print("[green]✓ Supprimé (soft-delete).[/green]\n")
        else:
            console.print("[dim]Annulé.[/dim]\n")
        return

    results = search_facts(query, limit=10)
    deleted_any = False

    for k, v in results["profile"].items():
        console.print(f"Profil : [cyan]{k}[/cyan] = {v}")
        if Confirm.ask(f"Supprimer « {k} » ?", default=False):
            delete_profile_key(k)
            console.print(f"[green]✓ Supprimé.[/green]")
            deleted_any = True

    for f in results["facts"]:
        color = _CERTAINTY_COLOR.get(f.get("certainty", "certain"), "white")
        console.print(f"[dim]#{f['id']}[/dim] [{f['category']}] [{color}]{f['fact']}[/{color}]")
        if Confirm.ask("Supprimer ?", default=False):
            delete_fact(f["id"])
            console.print("[green]✓ Supprimé.[/green]")
            deleted_any = True

    if not results["facts"] and not results["profile"]:
        console.print(f"[dim]Aucun résultat pour « {query} ».[/dim]")

    console.print()


# ── Edit ───────────────────────────────────────────────────────────────────────

def _handle_edit(args: str) -> None:
    parts = args.strip().split(None, 1)
    if len(parts) < 2 or not parts[0].isdigit():
        console.print("[yellow]Usage :[/yellow] /edit <ID> <nouveau texte>\n")
        console.print("[dim]Astuce : /edit 42 certain  — pour changer uniquement la certitude[/dim]\n")
        return

    fact_id = int(parts[0])
    new_text = parts[1].strip()
    f = get_fact_by_id(fact_id)
    if not f:
        console.print(f"[red]Aucun fait avec l'ID {fact_id}.[/red]\n")
        return

    console.print(f"[dim]Actuel :[/dim] {f['fact']}  [dim]({f.get('certainty','certain')})[/dim]")

    # Detect if the user is just changing the certainty
    if new_text.lower() in CERTAINTY_LEVELS:
        ok = update_fact(fact_id, new_certainty=new_text.lower())
        if ok:
            console.print(f"[green]✓ Certitude mise à jour → {new_text}.[/green]\n")
        else:
            console.print("[red]Mise à jour échouée.[/red]\n")
    else:
        ok = update_fact(fact_id, new_text=new_text)
        if ok:
            console.print(f"[green]✓ Fait mis à jour.[/green]\n")
        else:
            console.print("[red]Mise à jour échouée.[/red]\n")


# ── History ────────────────────────────────────────────────────────────────────

def _handle_history(args: str) -> None:
    n = 10
    if args.strip().isdigit():
        n = min(int(args.strip()), 100)

    history = load_conversation_history(limit=n)
    if not history:
        console.print("[dim]Aucun échange enregistré.[/dim]\n")
        return

    for msg in history:
        role = msg["role"]
        ts = msg["timestamp"][:16].replace("T", " ")
        if role == "user":
            console.print(Panel(
                msg["content"],
                title=f"[bold green]Toi[/bold green]  [dim]{ts}[/dim]",
                border_style="green",
            ))
        else:
            console.print(Panel(
                Markdown(msg["content"]),
                title=f"[bold blue]Moi.AI[/bold blue]  [dim]{ts}[/dim]",
                border_style="blue",
            ))
    console.print()


# ── Condense ───────────────────────────────────────────────────────────────────

def _handle_condense() -> None:
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
    console.print("[green]✓ Narration sauvegardée.[/green]\n")


# ── Rapport ────────────────────────────────────────────────────────────────────

def _handle_rapport() -> None:
    profile = get_profile()
    facts = get_all_facts()
    narrative = get_latest_narrative()
    stats = get_stats()
    mood = get_recent_mood(limit=5)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [f"# Rapport Moi.AI — {now}\n"]

    if narrative:
        lines += ["## Narration personnelle\n", narrative, ""]

    if mood:
        lines.append("## Humeur récente\n")
        for m in mood:
            lines.append(f"- {m['timestamp'][:10]} : {m['valence']} — {m['state']}")
        lines.append("")

    if profile:
        lines.append("## Profil\n")
        for k, v in profile.items():
            lines.append(f"- **{k}** : {v}")
        lines.append("")

    if facts:
        by_cat: dict[str, list[dict]] = {}
        for f in facts:
            by_cat.setdefault(f["category"], []).append(f)
        lines.append("## Faits mémorisés\n")
        for cat, items in sorted(by_cat.items()):
            lines.append(f"### {cat}")
            for f in items:
                badge = CERTAINTY_BADGE.get(f.get("certainty", "certain"), "●")
                lines.append(f"- {badge} {f['fact']}")
            lines.append("")

    lines += [
        "## Statistiques\n",
        f"- Messages totaux : {stats['messages']}",
        f"- Faits mémorisés : {len(facts)}",
        f"- Entrées profil : {len(profile)}",
    ]

    text = "\n".join(lines)
    path = Path("rapport_moiai.md")
    path.write_text(text, encoding="utf-8")

    console.print(Panel(
        Markdown(text[:2000] + ("\n\n[…]" if len(text) > 2000 else "")),
        title="[bold]Rapport[/bold]",
        border_style="cyan",
    ))
    console.print(f"[green]✓ Sauvegardé dans[/green] [bold]{path}[/bold]\n")


# ── Export JSON ────────────────────────────────────────────────────────────────

def _handle_export() -> None:
    data = {
        "exported_at": datetime.now().isoformat(),
        "profile": get_profile(),
        "facts": get_all_facts(),
        "narrative": get_latest_narrative(),
        "mood_log": get_recent_mood(limit=50),
        "conversation_summaries": get_conversation_summaries(limit=20),
    }
    path = Path("export_moiai.json")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]✓ Export JSON sauvegardé dans[/green] [bold]{path}[/bold]\n")


# ── Import ─────────────────────────────────────────────────────────────────────

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
        inp = Prompt.ask("[bold]Ton nom dans ce fichier[/bold] (vide = tous)", default="").strip()
        user_name = inp if inp else None

    try:
        messages, _, _ = load_file(path, user_name=user_name)
    except Exception as e:
        console.print(f"[red]Erreur de lecture :[/red] {e}\n")
        return

    if not messages:
        console.print("[yellow]Aucun message trouvé.[/yellow]\n")
        return

    console.print(f"[dim]{len(messages)} messages — extraction en cours...[/dim]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(), TaskProgressColumn(),
        console=console, transient=False,
    ) as progress:
        task = progress.add_task("Analyse...", total=None)

        def on_progress(current: int, total: int) -> None:
            progress.update(task, total=total, completed=current,
                            description=f"Bloc {current}/{total}")
        try:
            n = extract_from_messages(messages, progress_callback=on_progress)
        except Exception as e:
            console.print(f"[red]Erreur extraction :[/red] {e}\n")
            return

    console.print(
        f"[green]✓[/green] {n} fait(s) mémorisé(s) depuis [cyan]{path.name}[/cyan]\n"
    )


# ── Background extraction ──────────────────────────────────────────────────────

def _extract_async(user_msg: str, assistant_msg: str) -> None:
    try:
        n = extract_and_store(user_msg, assistant_msg)
        if n:
            console.print(f"[dim]  ✦ {n} nouveau(x) fait(s) mémorisé(s)[/dim]")
    except Exception:
        pass


# ── Main loop ──────────────────────────────────────────────────────────────────

def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Erreur :[/red] [bold]ANTHROPIC_API_KEY[/bold] non définie.\n"
            "Lance : [cyan]export ANTHROPIC_API_KEY=sk-...[/cyan]"
        )
        sys.exit(1)

    init_db()
    _header()
    start_session()  # warm curiosity cache in background

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
        elif lower.startswith("/faits"):
            _show_facts(user_input[6:])
        elif lower == "/stats":
            _show_stats()
        elif lower == "/condenser":
            _handle_condense()
        elif lower == "/rapport":
            _handle_rapport()
        elif lower == "/export":
            _handle_export()
        elif lower.startswith("/cherche"):
            _handle_search(user_input[8:])
        elif lower.startswith("/oublie"):
            _handle_forget(user_input[7:])
        elif lower.startswith("/edit"):
            _handle_edit(user_input[5:])
        elif lower.startswith("/historique"):
            _handle_history(user_input[11:])
        elif lower.startswith("/import"):
            _handle_import(user_input[7:])
        else:
            # ── Streaming chat response ────────────────────────────────────
            full_reply = ""
            try:
                stream = stream_response(user_input)
                with Live(
                    Panel("", title="[bold blue]Moi.AI[/bold blue]", border_style="blue"),
                    console=console,
                    refresh_per_second=15,
                    vertical_overflow="visible",
                ) as live:
                    for chunk in stream:
                        full_reply += chunk
                        live.update(Panel(
                            Markdown(full_reply),
                            title="[bold blue]Moi.AI[/bold blue]",
                            border_style="blue",
                        ))
            except Exception as e:
                error_type = type(e).__name__
                console.print(f"[red]Erreur {error_type} :[/red] {e}\n")
                continue

            finish_turn(full_reply)

            threading.Thread(
                target=_extract_async,
                args=(user_input, full_reply),
                daemon=True,
            ).start()


if __name__ == "__main__":
    main()
