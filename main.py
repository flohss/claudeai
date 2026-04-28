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

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from moiai.capsule import (
    add_capsule,
    delete_capsule,
    get_all_capsules,
    get_due_capsules,
    mark_opened,
    parse_delay,
)
from moiai.chat import finish_turn, get_startup_briefing, get_stats, start_session, stream_response
from moiai.condenser import condense_narrative
from moiai.extractor import extract_and_store, extract_from_messages
from moiai.goals import (
    GOAL_STATUSES,
    add_goal,
    delete_goal,
    get_all_goals,
    update_goal_status,
)
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
from moiai.people import delete_person, get_all_people, get_person_by_id
from moiai.reflect import (
    LIFE_DOMAINS,
    find_contradictions,
    generate_reflection,
    get_latest_domain_scores,
    resolve_contradiction,
    save_domain_scores,
    store_contradiction,
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
    "/import <fichier>":    "Importer un fichier (WhatsApp, Instagram, Telegram, txt, pdf)",
    "/condenser":           "Fusionner la mémoire en narration personnelle",
    "/reflect":             "Analyse psychologique de ton profil (pattern, angles morts)",
    "/objectif <texte>":    "Ajouter un objectif",
    "/objectifs":           "Lister et gérer les objectifs",
    "/bilan":               "Bilan de vie — auto-évaluation par domaine (1-5)",
    "/révision":            "Détecter les contradictions dans ta mémoire",
    "/personnes":           "Afficher les personnes de ton entourage",
    "/capsule <texte>":     "Créer une capsule temporelle (ex: dans 2 semaines)",
    "/capsules":            "Lister toutes les capsules",
    "/rapport":             "Exporter le profil complet en Markdown",
    "/export":              "Exporter toute la mémoire en JSON",
    "/stats":               "Statistiques de mémoire",
    "/aide":                "Afficher cette aide",
    "/quitter":             "Quitter",
}

_GOAL_STATUS_COLOR = {
    "active":    "green",
    "achieved":  "cyan",
    "abandoned": "red",
    "paused":    "yellow",
}
_GOAL_STATUS_LABEL = {
    "active":    "actif",
    "achieved":  "atteint ✓",
    "abandoned": "abandonné",
    "paused":    "en pause",
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


# ── Reflect ────────────────────────────────────────────────────────────────────

def _handle_reflect() -> None:
    with console.status("[dim]Analyse psychologique en cours...[/dim]", spinner="dots"):
        try:
            text = generate_reflection()
        except Exception as e:
            console.print(f"[red]Erreur :[/red] {e}\n")
            return
    console.print(Panel(
        Markdown(text),
        title="[bold]Analyse — patterns & angles morts[/bold]",
        border_style="magenta",
    ))
    console.print()


# ── Goals ──────────────────────────────────────────────────────────────────────

def _handle_add_goal(args: str) -> None:
    text = args.strip()
    if not text:
        console.print("[yellow]Usage :[/yellow] /objectif <texte de l'objectif>\n")
        return
    deadline = None
    dl_inp = Prompt.ask("[dim]Échéance (optionnel, ex: 2025-06-01)[/dim]", default="").strip()
    if dl_inp:
        deadline = dl_inp
    gid = add_goal(text, deadline=deadline, source="user")
    console.print(f"[green]✓ Objectif #{gid} ajouté.[/green]\n")


def _handle_goals() -> None:
    goals = get_all_goals()
    if not goals:
        console.print("[dim]Aucun objectif enregistré.[/dim]\n")
        return

    table = Table(show_header=True, box=None, padding=(0, 1))
    table.add_column("ID", style="dim", width=5)
    table.add_column("Objectif")
    table.add_column("Statut", width=14)
    table.add_column("Échéance", width=12, style="dim")
    table.add_column("Source", width=10, style="dim")

    for g in goals:
        status = g.get("status", "active")
        color = _GOAL_STATUS_COLOR.get(status, "white")
        label = _GOAL_STATUS_LABEL.get(status, status)
        dl = g.get("deadline", "") or ""
        dl = dl[:10] if dl else "—"
        src = "extrait" if g.get("source") == "extracted" else "toi"
        table.add_row(
            str(g["id"]),
            g["text"],
            f"[{color}]{label}[/{color}]",
            dl,
            src,
        )

    console.print(Panel(table, title="[bold]Objectifs[/bold]", border_style="cyan"))

    action = Prompt.ask(
        "\n[dim]Action : [bold]a[/bold]tteint / [bold]p[/bold]ause / [bold]x[/bold] abandonner / "
        "[bold]s[/bold]upprimer / Entrée=rien[/dim]",
        default="",
    ).strip().lower()

    if not action:
        console.print()
        return

    gid_str = Prompt.ask("[dim]ID de l'objectif[/dim]").strip()
    if not gid_str.isdigit():
        console.print("[yellow]ID invalide.[/yellow]\n")
        return
    gid = int(gid_str)

    if action == "a":
        update_goal_status(gid, "achieved")
        console.print(f"[cyan]✓ Objectif #{gid} marqué atteint.[/cyan]\n")
    elif action == "p":
        update_goal_status(gid, "paused")
        console.print(f"[yellow]⏸ Objectif #{gid} mis en pause.[/yellow]\n")
    elif action == "x":
        update_goal_status(gid, "abandoned")
        console.print(f"[red]✗ Objectif #{gid} abandonné.[/red]\n")
    elif action == "s":
        if delete_goal(gid):
            console.print(f"[green]✓ Objectif #{gid} supprimé.[/green]\n")
        else:
            console.print(f"[red]Objectif #{gid} introuvable.[/red]\n")
    else:
        console.print("[dim]Action non reconnue.[/dim]\n")


# ── Bilan ──────────────────────────────────────────────────────────────────────

def _handle_bilan() -> None:
    console.print(Panel(
        "[bold]Bilan de vie — auto-évaluation[/bold]\n"
        "[dim]Note chaque domaine de 1 (très insatisfaisant) à 5 (excellent).[/dim]",
        border_style="magenta",
    ))

    last = get_latest_domain_scores()
    scores: dict[str, int] = {}

    for domain in LIFE_DOMAINS:
        prev = last.get(domain)
        hint = f"  [dim](précédent : {prev}/5)[/dim]" if prev is not None else ""
        console.print(f"  [cyan]{domain}[/cyan]{hint}")
        while True:
            raw = Prompt.ask("  → Note (1-5)", default=str(prev or 3)).strip()
            if raw.isdigit() and 1 <= int(raw) <= 5:
                scores[domain] = int(raw)
                break
            console.print("  [yellow]Entre un chiffre entre 1 et 5.[/yellow]")

    save_domain_scores(scores)

    lines = ["## Bilan de vie\n"]
    for domain, score in scores.items():
        bar = "█" * score + "░" * (5 - score)
        prev = last.get(domain)
        delta = ""
        if prev is not None:
            diff = score - prev
            if diff > 0:
                delta = f"  [green]+{diff}[/green]"
            elif diff < 0:
                delta = f"  [red]{diff}[/red]"
        lines.append(f"  {domain:<28} {bar} {score}/5{delta}")

    console.print(Panel(
        "\n".join(lines),
        title="[bold]Résultat[/bold]",
        border_style="magenta",
    ))
    console.print("[green]✓ Bilan sauvegardé.[/green]\n")


# ── Révision (contradictions) ──────────────────────────────────────────────────

def _handle_revision() -> None:
    with console.status("[dim]Analyse des contradictions...[/dim]", spinner="dots"):
        try:
            contras = find_contradictions()
        except Exception as e:
            console.print(f"[red]Erreur :[/red] {e}\n")
            return

    if not contras:
        console.print("[green]✓ Aucune contradiction détectée.[/green]\n")
        return

    console.print(f"[yellow]{len(contras)} contradiction(s) détectée(s) :[/yellow]\n")

    for i, c in enumerate(contras, 1):
        console.print(Panel(
            f"[bold]Fait 1 :[/bold] {c.get('fact1', '—')}\n"
            f"[bold]Fait 2 :[/bold] {c.get('fact2', '—')}\n\n"
            f"[dim]{c.get('explanation', '')}[/dim]",
            title=f"[yellow]Contradiction #{i}[/yellow]",
            border_style="yellow",
        ))
        store_contradiction(None, None, c.get("explanation", ""))

    console.print("[dim]Contradictions enregistrées. Utilise /faits pour corriger.[/dim]\n")


# ── Personnes ──────────────────────────────────────────────────────────────────

def _handle_people() -> None:
    people = get_all_people()
    if not people:
        console.print("[dim]Aucune personne mémorisée.[/dim]\n")
        return

    table = Table(show_header=True, box=None, padding=(0, 1))
    table.add_column("ID", style="dim", width=5)
    table.add_column("Nom", style="bold cyan", width=20)
    table.add_column("Relation", width=15)
    table.add_column("Notes")
    table.add_column("Vu", style="dim", width=12)

    for p in people:
        rel = p.get("relation") or "—"
        notes = (p.get("notes") or "")[:60]
        if len(p.get("notes") or "") > 60:
            notes += "…"
        last = (p.get("last_mentioned") or "")[:10]
        table.add_row(str(p["id"]), p["name"], rel, notes, last)

    console.print(Panel(table, title=f"[bold]Personnes ({len(people)})[/bold]", border_style="cyan"))

    action = Prompt.ask(
        "\n[dim][bold]s[/bold]upprimer un profil / Entrée=rien[/dim]",
        default="",
    ).strip().lower()

    if action == "s":
        pid_str = Prompt.ask("[dim]ID[/dim]").strip()
        if pid_str.isdigit():
            if delete_person(int(pid_str)):
                console.print(f"[green]✓ Supprimé.[/green]\n")
            else:
                console.print("[red]ID introuvable.[/red]\n")
    else:
        console.print()


# ── Capsules ───────────────────────────────────────────────────────────────────

def _handle_add_capsule(args: str) -> None:
    args = args.strip()
    if not args:
        console.print(
            "[yellow]Usage :[/yellow] /capsule <message> dans <n> jours|semaines|mois\n"
            "[dim]Exemples :[/dim]\n"
            "  /capsule mon entretien chez Google dans 3 jours\n"
            "  /capsule vérifier mon objectif sport dans 1 mois\n"
        )
        return

    open_at = parse_delay(args)
    if not open_at:
        # No delay in text — ask
        delay_str = Prompt.ask(
            "[dim]Dans combien de temps ? (ex: dans 2 semaines / 2025-06-01)[/dim]"
        ).strip()
        open_at = parse_delay(delay_str)
        if not open_at:
            console.print("[red]Délai non reconnu.[/red]\n")
            return
        content = args
    else:
        import re
        content = re.sub(
            r"\s+dans\s+\d+\s+(jour|jours|semaine|semaines|mois|an|ans).*$", "", args
        ).strip()
        if not content:
            content = args

    cid = add_capsule(content, open_at)
    date_str = open_at.strftime("%d/%m/%Y")
    console.print(
        f"[green]✓ Capsule #{cid} créée.[/green] "
        f"S'ouvrira le [bold]{date_str}[/bold]\n"
    )


def _handle_capsules() -> None:
    capsules = get_all_capsules()
    if not capsules:
        console.print("[dim]Aucune capsule créée.[/dim]\n")
        return

    table = Table(show_header=True, box=None, padding=(0, 1))
    table.add_column("ID", style="dim", width=5)
    table.add_column("Message")
    table.add_column("S'ouvre le", width=13)
    table.add_column("Statut", width=10)
    table.add_column("Source", style="dim", width=8)

    from datetime import datetime as _dt
    now = _dt.now().isoformat()

    for c in capsules:
        status = "[green]ouverte ✓[/green]" if c["opened"] else (
            "[yellow]en attente[/yellow]" if c["open_at"] > now else "[bold red]due ![/bold red]"
        )
        date_str = c["open_at"][:10]
        src = "auto" if c.get("source") == "auto" else "toi"
        table.add_row(str(c["id"]), c["content"][:60], date_str, status, src)

    console.print(Panel(
        table,
        title=f"[bold]Capsules temporelles ({len(capsules)})[/bold]",
        border_style="magenta",
    ))

    action = Prompt.ask(
        "\n[dim][bold]s[/bold]upprimer / Entrée=rien[/dim]", default=""
    ).strip().lower()
    if action == "s":
        cid_str = Prompt.ask("[dim]ID[/dim]").strip()
        if cid_str.isdigit():
            if delete_capsule(int(cid_str)):
                console.print("[green]✓ Supprimée.[/green]\n")
            else:
                console.print("[red]ID introuvable.[/red]\n")
    else:
        console.print()


def _show_due_capsules() -> None:
    """Show capsules that are due and mark them as opened."""
    due = get_due_capsules()
    if not due:
        return
    for c in due:
        note = f"\n[dim italic]{c['ai_note']}[/dim italic]" if c.get("ai_note") else ""
        src = " [dim](créée automatiquement)[/dim]" if c.get("source") == "auto" else ""
        console.print(Panel(
            f"[bold]{c['content']}[/bold]{note}",
            title=f"[bold magenta]📬 Capsule du {c['created_at'][:10]}[/bold magenta]{src}",
            border_style="magenta",
        ))
        mark_opened(c["id"])
    console.print()


# ── Background extraction ──────────────────────────────────────────────────────

def _extract_async(user_msg: str, assistant_msg: str) -> None:
    try:
        n = extract_and_store(user_msg, assistant_msg)
        if n:
            console.print(f"[dim]  ✦ {n} nouveau(x) fait(s) mémorisé(s)[/dim]")
    except Exception:
        pass


# ── Main loop ──────────────────────────────────────────────────────────────────

def _ensure_api_key() -> None:
    """Load API key from .env, env var, or ask the user. Offer to save it."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return

    # Try .env in script directory or cwd
    for env_path in (Path(__file__).parent / ".env", Path(".env")):
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key and not key.startswith("REMPLACE"):
                        os.environ["ANTHROPIC_API_KEY"] = key
                        return
            break

    console.print(
        "[yellow]Aucune clé API Anthropic trouvée.[/yellow]\n"
        "[dim]Obtiens ta clé sur [bold]console.anthropic.com[/bold][/dim]\n"
    )
    key = Prompt.ask("[bold]Clé API Anthropic[/bold] (sk-ant-...)").strip()
    if not key:
        console.print("[red]Clé vide — abandon.[/red]")
        sys.exit(1)

    os.environ["ANTHROPIC_API_KEY"] = key

    if Confirm.ask("Sauvegarder dans [bold].env[/bold] pour ne plus la redemander ?", default=True):
        env_path = Path(__file__).parent / ".env"
        env_path.write_text(f"ANTHROPIC_API_KEY={key}\n", encoding="utf-8")
        console.print(f"[green]✓ Clé sauvegardée dans[/green] [bold]{env_path}[/bold]\n")


def main() -> None:
    _ensure_api_key()

    init_db()
    _header()
    _show_due_capsules()
    start_session()

    briefing = get_startup_briefing(timeout=6.0)
    if briefing:
        console.print(Panel(
            briefing,
            title="[bold blue]Moi.AI[/bold blue]",
            border_style="blue",
        ))
        console.print()

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
        elif lower == "/reflect":
            _handle_reflect()
        elif lower.startswith("/objectif") and not lower.startswith("/objectifs"):
            _handle_add_goal(user_input[9:])
        elif lower == "/objectifs":
            _handle_goals()
        elif lower in ("/bilan", "/bilan de vie"):
            _handle_bilan()
        elif lower in ("/révision", "/revision"):
            _handle_revision()
        elif lower == "/personnes":
            _handle_people()
        elif lower.startswith("/capsule") and not lower.startswith("/capsules"):
            _handle_add_capsule(user_input[8:])
        elif lower == "/capsules":
            _handle_capsules()
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
