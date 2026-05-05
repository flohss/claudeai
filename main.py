#!/usr/bin/env python3
"""
Moi.AI — double personnel artificiel.
Lancement : python main.py
"""

import json
import os
import shutil
import sqlite3
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
from moiai.api import get_last_call_cost, get_session_cost
from moiai.api import get_debug_enabled, get_last_debug, set_debug as _set_debug
from moiai.memory import count_messages as _count_messages
from moiai.condenser import condense_narrative
from moiai.extractor import extract_and_store, extract_from_messages
from moiai.voice import is_available as _voice_available, transcribe as _voice_transcribe
from moiai.voice import is_tts_available as _tts_available, speak as _tts_speak, stop_speaking as _tts_stop
from moiai.goals import (
    GOAL_STATUSES,
    add_goal,
    delete_goal,
    get_all_goals,
    update_goal_status,
)
from moiai.importer import load_file
from moiai.memory import DB_PATH as _DB_PATH
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
    get_mood_by_day,
    get_recent_facts,
    get_recent_mood,
    get_stale_facts,
    init_db,

    search_facts,
    update_fact,
)
from moiai.people import delete_person, get_all_people, get_person_by_id
from moiai.questioner import (
    DEPTH_LEVELS,
    DEPTH_THRESHOLD,
    INTERVIEW_DOMAINS,
    generate_question,
    generate_session_narrative,
    get_coverage_report,
    get_last_session_info,
    get_total_questions_asked,
    find_domain_by_arg,
    is_sensitive_answer,
    log_question,
    stream_reaction_and_question,
)
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

    "/faits [cat]":         "Lister les faits (filtrable par catégorie)",
    "/cherche <terme>":     "Recherche plein-texte dans la mémoire",
    "/oublie <ID|terme>":   "Supprimer un fait ou une entrée profil",
    "/récent [n]":          "Faits mémorisés ces n dernières minutes (défaut 30) — supprimer ceux indésirables",
    "/supprimer <ID>":      "Supprimer un fait par ID",
    "/corriger <ID>":       "Corriger le texte d'un fait (interactif)",
    "/réfuter <ID>":        "Marquer un fait comme réfuté",
    "/fusionner":           "Détecter et fusionner les faits redondants (assisté par IA)",
    "/import <fichier>":    "Importer un fichier (WhatsApp, Instagram, Telegram, txt, pdf)",
    "/condenser":           "Fusionner la mémoire en narration personnelle",
    "/humeur":              "Graphique d'humeur sur les 30 derniers jours",
    "/analyser":            "Audit complet de la mémoire — cohérence, lacunes, patterns, qualité",
    "/reflect":             "Analyse psychologique de ton profil (pattern, angles morts)",    "/objectif <texte>":    "Ajouter un objectif",
    "/objectifs":           "Lister et gérer les objectifs",
    "/bilan":               "Bilan de vie — auto-évaluation par domaine (1-5)",
    "/personnes":           "Afficher les personnes de ton entourage",
    "/capsule <texte>":     "Créer une capsule temporelle (ex: dans 2 semaines)",
    "/capsules":            "Lister toutes les capsules",
    "/questions":           "Mode interview — questions sur ta vie pour construire ta mémoire",
    "/rapport":             "Exporter le profil complet en Markdown",
    "/export":              "Exporter toute la mémoire en JSON",
    "/stats":               "Statistiques de mémoire",
    "/aide":                "Afficher cette aide",
    "/backup":              "Sauvegarder toute la mémoire dans un fichier .db",
    "/restaurer":           "Restaurer un backup (liste les fichiers disponibles automatiquement)",
    "/voix":                "Activer / désactiver la saisie vocale (nécessite Termux:API)",
    "/tts":                 "Activer / désactiver la synthèse vocale des réponses (nécessite Termux:API)",
    "/debug":               "Activer / désactiver le mode débogage (affiche requêtes, tokens, coûts)",
    "/màj":                 "Vérifier et installer les mises à jour",
    "/restart":             "Redémarrer l'application",
    "/cle":                 "Configurer ou modifier la clé API Anthropic",
    "/reset":               "Effacer toute la mémoire et repartir de zéro",
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


# ── Debug display ─────────────────────────────────────────────────────────────

def _print_debug() -> None:
    d = get_last_debug()
    if not d:
        return

    # ── Token & cost table ─────────────────────────────────────────────────────
    u = d.get("usage", {})
    c = d.get("cost", {})
    total_cost = sum(c.values())
    cache_saved = u.get("cache_read_tokens", 0)

    tok_table = Table(show_header=True, box=None, padding=(0, 2))
    tok_table.add_column("Type", style="dim")
    tok_table.add_column("Tokens", justify="right")
    tok_table.add_column("Coût (USD)", justify="right", style="cyan")

    cache_write = u.get("cache_write_tokens", 0)
    rows = [
        ("Input",        u.get("input_tokens", 0),  c.get("input", 0),       "white"),
        ("Output",       u.get("output_tokens", 0), c.get("output", 0),      "white"),
        ("Cache write" + (" ⚠ contexte modifié" if cache_write and cache_saved == 0 else ""),
                         cache_write,                c.get("cache_write", 0), "yellow" if cache_write else "white"),
        ("Cache read ✓", cache_saved,                c.get("cache_read", 0), "green" if cache_saved else "dim"),
    ]
    for label, tok, cost, color in rows:
        tok_table.add_row(
            f"[{color}]{label}[/{color}]",
            f"[{color}]{tok:,}[/{color}]",
            f"[{color}]${cost:.6f}[/{color}]",
        )
    tok_table.add_row("[bold]TOTAL[/bold]", "", f"[bold cyan]${total_cost:.6f}[/bold cyan]")

    console.print(Panel(tok_table, title=f"[bold]Debug — {d.get('model','')}[/bold]",
                        border_style="dim yellow"))

    # ── System blocks ──────────────────────────────────────────────────────────
    for i, blk in enumerate(d.get("system_blocks", []), 1):
        text = blk.get("text", "") if isinstance(blk, dict) else str(blk)
        cached = "● cache" if isinstance(blk, dict) and "cache_control" in blk else ""
        preview = text[:600] + (" […]" if len(text) > 600 else "")
        console.print(Panel(
            preview,
            title=f"[dim]Système bloc {i}  {cached}  ({len(text)} car.)[/dim]",
            border_style="dim",
        ))

    # ── Messages sent ──────────────────────────────────────────────────────────
    msgs = d.get("messages", [])
    if msgs:
        lines = []
        for m in msgs[-6:]:
            role = m.get("role", "?")
            content = m.get("content", "")
            if isinstance(content, list):
                content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
            preview = content[:200].replace("\n", " ")
            color = "green" if role == "user" else "blue"
            lines.append(f"[{color}]{role}[/{color}] {preview}")
        console.print(Panel(
            "\n".join(lines),
            title=f"[dim]Messages envoyés ({len(msgs)} — 6 derniers affichés)[/dim]",
            border_style="dim",
        ))

    # ── Response ───────────────────────────────────────────────────────────────
    response = d.get("response", "")
    console.print(Panel(
        response[:400] + (" […]" if len(response) > 400 else ""),
        title="[dim]Réponse reçue[/dim]",
        border_style="dim",
    ))
    console.print()


# ── Cost display helper ────────────────────────────────────────────────────────

def _print_cost() -> None:
    last = get_last_call_cost()
    total = get_session_cost()
    if last > 0:
        console.print(f"[dim]  réponse : ${last:.4f}  ·  session : ${total:.4f}[/dim]")


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

# ── Récent ────────────────────────────────────────────────────────────────────

def _handle_recent(args: str) -> None:
    minutes = 30
    if args.strip().isdigit():
        minutes = max(1, min(1440, int(args.strip())))

    facts = get_recent_facts(minutes=minutes)
    if not facts:
        console.print(f"[dim]Aucun fait enregistré dans les {minutes} dernières minutes.[/dim]\n")
        return

    table = Table(show_header=True, box=None, padding=(0, 1))
    table.add_column("ID", style="dim", width=5)
    table.add_column(" ", width=2, no_wrap=True)
    table.add_column("Catégorie", style="cyan", width=14)
    table.add_column("Fait")
    table.add_column("Heure", style="dim", width=8)

    for f in facts:
        certainty = f.get("certainty", "certain")
        badge = CERTAINTY_BADGE.get(certainty, "●")
        color = _CERTAINTY_COLOR.get(certainty, "white")
        heure = f["timestamp"][11:16]
        table.add_row(
            str(f["id"]),
            f"[{color}]{badge}[/{color}]",
            f["category"],
            f"[{color}]{f['fact']}[/{color}]",
            heure,
        )

    console.print(Panel(
        table,
        title=f"[bold]{len(facts)} fait(s) mémorisé(s) — {minutes} dernières minutes[/bold]",
        border_style="cyan",
    ))

    raw = Prompt.ask(
        "[dim]IDs à supprimer (ex: [bold]12 34[/bold]) ou Entrée pour tout garder[/dim]",
        default="",
    ).strip()

    if not raw:
        console.print("[dim]Aucune suppression.[/dim]\n")
        return

    deleted = []
    for token in raw.split():
        if token.isdigit():
            fid = int(token)
            if delete_fact(fid):
                deleted.append(fid)

    if deleted:
        console.print(f"[green]✓ Supprimé :[/green] #{', #'.join(str(x) for x in deleted)}\n")
    else:
        console.print("[yellow]Aucun ID valide trouvé.[/yellow]\n")


# ── Supprimer / Corriger / Réfuter ────────────────────────────────────────────

def _handle_supprimer(args: str) -> None:
    query = args.strip()
    if not query or not query.isdigit():
        console.print("[yellow]Usage :[/yellow] /supprimer <ID>\n")
        return
    f = get_fact_by_id(int(query))
    if not f:
        console.print(f"[red]Aucun fait avec l'ID {query}.[/red]\n")
        return
    certainty = f.get("certainty", "certain")
    color = _CERTAINTY_COLOR.get(certainty, "white")
    badge = CERTAINTY_BADGE.get(certainty, "●")
    console.print(
        f"[dim]#{f['id']}[/dim]  [{color}]{badge}[/{color}]  "
        f"[{f['category']}]  [{color}]{f['fact']}[/{color}]"
    )
    if Confirm.ask("Supprimer ?", default=False):
        delete_fact(f["id"])
        console.print(f"[green]✓ Fait #{f['id']} supprimé.[/green]\n")
    else:
        console.print("[dim]Annulé.[/dim]\n")


def _handle_corriger(args: str) -> None:
    query = args.strip()
    if not query or not query.isdigit():
        console.print("[yellow]Usage :[/yellow] /corriger <ID>\n")
        return
    f = get_fact_by_id(int(query))
    if not f:
        console.print(f"[red]Aucun fait avec l'ID {query}.[/red]\n")
        return
    certainty = f.get("certainty", "certain")
    color = _CERTAINTY_COLOR.get(certainty, "white")
    badge = CERTAINTY_BADGE.get(certainty, "●")
    console.print(
        f"[dim]Actuel :[/dim]  [{color}]{badge}[/{color}]  [{color}]{f['fact']}[/{color}]  "
        f"[dim]({certainty})[/dim]"
    )
    new_text = Prompt.ask("[bold]Nouveau texte[/bold] (Entrée = annuler)", default="").strip()
    if not new_text:
        console.print("[dim]Annulé.[/dim]\n")
        return
    if update_fact(f["id"], new_text=new_text):
        console.print(f"[green]✓ Fait #{f['id']} corrigé.[/green]\n")
    else:
        console.print("[red]Mise à jour échouée.[/red]\n")


def _handle_fusionner() -> None:
    """AI-assisted fact merger: detects overlapping facts and proposes consolidations."""
    from moiai.merger import suggest_merges
    from datetime import datetime as _dt

    facts = get_all_facts()
    active = [f for f in facts if f.get("certainty") != "réfuté"]
    if len(active) < 2:
        console.print("[dim]Pas assez de faits pour détecter des fusions.[/dim]\n")
        return

    with console.status(
        f"[dim]Analyse de {len(active)} faits en recherche de redondances...[/dim]",
        spinner="dots",
    ):
        try:
            candidates = suggest_merges(facts)
        except Exception as e:
            console.print(f"[red]Erreur :[/red] {e}\n")
            return

    if not candidates:
        console.print("[green]✓ Aucune redondance détectée — ta mémoire est bien organisée.[/green]\n")
        _print_cost()
        return

    console.print(f"[yellow]{len(candidates)} fusion(s) suggérée(s) :[/yellow]\n")

    merged_count = 0
    id_to_fact = {f["id"]: f for f in facts}

    for i, cand in enumerate(candidates, 1):
        ids = cand["ids"]
        merged_text = cand["merged"]
        category = cand["category"]
        reason = cand.get("reason", "")

        # Build display of original facts
        originals = []
        for fid in ids:
            f = id_to_fact.get(fid)
            if f:
                badge = CERTAINTY_BADGE.get(f.get("certainty", "certain"), "●")
                color = _CERTAINTY_COLOR.get(f.get("certainty", "certain"), "white")
                originals.append(
                    f"  [dim]#{fid}[/dim] [{color}]{badge} {f['fact']}[/{color}]"
                )

        reason_line = f"[dim italic]{reason}[/dim italic]\n" if reason else ""
        panel_content = (
            reason_line
            + "\n".join(originals)
            + f"\n\n[bold]→ Fusion proposée :[/bold] [cyan]{merged_text}[/cyan]"
        )

        console.print(Panel(
            panel_content,
            title=f"[bold yellow]Fusion {i}/{len(candidates)}[/bold yellow]  [dim]{category}[/dim]",
            border_style="yellow",
        ))

        action = Prompt.ask(
            "  [bold]o[/bold]ui  [bold]e[/bold]diter  [bold]n[/bold]on",
            choices=["o", "e", "n"],
            default="n",
        ).strip().lower()

        if action == "n":
            console.print("[dim]Ignoré.[/dim]\n")
            continue

        if action == "e":
            new_text = Prompt.ask(
                "[bold]Texte fusionné[/bold]", default=merged_text
            ).strip()
            if not new_text:
                console.print("[dim]Ignoré.[/dim]\n")
                continue
            merged_text = new_text

        # Insert merged fact then soft-delete originals
        from moiai.memory import add_facts, soft_delete_fact
        add_facts([{"category": category, "fact": merged_text, "certainty": "certain"}])
        for fid in ids:
            soft_delete_fact(fid)

        console.print(
            f"[green]✓ Fait fusionné.[/green]  [dim]#{', #'.join(str(x) for x in ids)} supprimés.[/dim]\n"
        )
        merged_count += 1

    if merged_count:
        console.print(f"[green]✓ {merged_count} fusion(s) effectuée(s).[/green]")
    else:
        console.print("[dim]Aucune fusion effectuée.[/dim]")
    _print_cost()
    console.print()


def _handle_refuter(args: str) -> None:
    query = args.strip()
    if not query or not query.isdigit():
        console.print("[yellow]Usage :[/yellow] /réfuter <ID>\n")
        return
    f = get_fact_by_id(int(query))
    if not f:
        console.print(f"[red]Aucun fait avec l'ID {query}.[/red]\n")
        return
    if f.get("certainty") == "réfuté":
        console.print(f"[dim]Fait #{f['id']} est déjà marqué réfuté.[/dim]\n")
        return
    certainty = f.get("certainty", "certain")
    color = _CERTAINTY_COLOR.get(certainty, "white")
    console.print(f"[dim]#{f['id']}[/dim]  [{color}]{f['fact']}[/{color}]  [dim]({certainty})[/dim]")
    if Confirm.ask("Marquer comme réfuté ?", default=False):
        update_fact(f["id"], new_certainty="réfuté")
        console.print(f"[green]✓ Fait #{f['id']} marqué réfuté.[/green]\n")
    else:
        console.print("[dim]Annulé.[/dim]\n")



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
    console.print("[green]✓ Narration sauvegardée.[/green]")
    _print_cost()
    console.print()


# ── Download folder helper ─────────────────────────────────────────────────────

def _best_export_dir() -> Path:
    """Return the most accessible export directory (Android Download first, then home)."""
    candidates = [
        Path("/sdcard/Download"),
        Path("/storage/emulated/0/Download"),
        Path("/sdcard/Downloads"),
        Path("/storage/emulated/0/Downloads"),
        Path("/sdcard"),
        Path("/storage/emulated/0"),
        Path.home(),
        _DB_PATH.parent,
    ]
    return next((p for p in candidates if p.exists() and os.access(p, os.W_OK)), Path.home())


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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _best_export_dir() / f"moiai_rapport_{timestamp}.md"
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _best_export_dir() / f"moiai_export_{timestamp}.json"
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

    console.print(f"[green]✓[/green] {n} fait(s) mémorisé(s) depuis [cyan]{path.name}[/cyan]")
    _print_cost()
    console.print()


# ── Mood chart ────────────────────────────────────────────────────────────────

_BLOCKS = "▁▂▃▄▅▆▇█"
_MOOD_COLOR = {"positive": "green", "negative": "red", "mixed": "yellow", "neutral": "dim"}
_MOOD_LABEL = {"positive": "positive", "negative": "négative", "mixed": "mixte", "neutral": "neutre"}


def _mood_score(valence: str, intensity: int) -> float:
    i = max(1, min(5, intensity or 3))
    if valence == "positive":
        return 2.5 + i * 0.5   # 3.0 – 5.0
    if valence == "negative":
        return 3.5 - i * 0.5   # 1.0 – 3.0
    return 3.0                  # neutral / mixed


def _score_to_block(score: float) -> str:
    idx = min(7, max(0, round((score - 1) / 4 * 7)))
    return _BLOCKS[idx]


def _handle_mood_chart() -> None:
    from datetime import date, timedelta as td

    entries = get_mood_by_day(days=30)
    if not entries:
        console.print("[dim]Aucune humeur enregistrée — parle-moi un peu ![/dim]\n")
        return

    day_map = {e["day"]: e for e in entries}
    today = date.today()
    all_days = [(today - td(days=29 - i)).isoformat() for i in range(30)]

    # ── Sparkline ──────────────────────────────────────────────────────────────
    spark = ""
    for d in all_days:
        if d in day_map:
            e = day_map[d]
            s = _mood_score(e["valence"], e["intensity"])
            color = _MOOD_COLOR.get(e["valence"], "white")
            spark += f"[{color}]{_score_to_block(s)}[/{color}]"
        else:
            spark += "[dim]·[/dim]"

    label_l = (today - td(days=29)).strftime("%-d %b")
    label_r = today.strftime("%-d %b")
    padding = 30 - len(label_l) - len(label_r)

    # ── Stats ──────────────────────────────────────────────────────────────────
    scores = [_mood_score(e["valence"], e["intensity"]) for e in entries]
    avg = sum(scores) / len(scores)
    avg_color = "green" if avg >= 3.5 else ("red" if avg < 2.5 else "yellow")

    valence_counts: dict[str, int] = {}
    for e in entries:
        valence_counts[e["valence"]] = valence_counts.get(e["valence"], 0) + 1
    dominant = max(valence_counts, key=valence_counts.get)

    # ── Recent entries table ───────────────────────────────────────────────────
    recent = get_recent_mood(limit=8)
    table = Table(show_header=True, box=None, padding=(0, 1))
    table.add_column("Date", style="dim", width=11)
    table.add_column("Valence", width=11)
    table.add_column("État")
    table.add_column("Intensité", width=13)

    for m in recent:
        color = _MOOD_COLOR.get(m["valence"], "white")
        intensity_bar = "●" * m["intensity"] + "○" * (5 - m["intensity"])
        table.add_row(
            m["timestamp"][:10],
            f"[{color}]{_MOOD_LABEL.get(m['valence'], m['valence'])}[/{color}]",
            m["state"],
            f"[{color}]{intensity_bar}[/{color}]",
        )

    content = (
        f"{spark}\n"
        f"[dim]{label_l}{' ' * padding}{label_r}[/dim]\n\n"
        f"Moyenne : [{avg_color}]{_score_to_block(avg)} {avg:.1f}/5[/{avg_color}]  •  "
        f"Tendance : [{_MOOD_COLOR.get(dominant, 'white')}]{_MOOD_LABEL.get(dominant, dominant)}"
        f"[/{_MOOD_COLOR.get(dominant, 'white')}]  •  "
        f"[dim]{len(entries)} jour(s) sur 30[/dim]"
    )

    console.print(Panel(content, title="[bold]Humeur — 30 derniers jours[/bold]", border_style="cyan"))
    console.print(Panel(table, title="[bold]Entrées récentes[/bold]", border_style="dim"))
    console.print()


# ── Questions / Life interview ─────────────────────────────────────────────────

def _handle_questions(domain_arg: str = "") -> None:
    """Structured life interview — asks targeted questions to build personal memory."""
    report = get_coverage_report()
    facts = get_all_facts()
    profile = get_profile()
    session_id = datetime.now().strftime("%Y%m%dT%H%M%S")

    console.print()
    total_q = get_total_questions_asked()
    last_session = get_last_session_info()

    # Pre-session briefing
    briefing_lines = (
        "Je vais te poser des questions sur ta vie pour construire ta mémoire.\n"
        "Réponds librement — comme tu parlerais à un ami. Aucune bonne ou mauvaise réponse.\n"
    )
    if last_session:
        domains_str = " · ".join(last_session["domains"][:3])
        briefing_lines += (
            f"[dim]Dernière session : {last_session['started']}  •  "
            f"{last_session['count']} question(s)  •  {domains_str}[/dim]\n"
        )
    briefing_lines += (
        "[dim][bold]suivant[/bold] = changer de domaine  •  "
        "[bold]stop[/bold] = terminer  •  "
        "[bold]/questions <domaine>[/bold] = cibler un domaine[/dim]"
    )
    console.print(Panel(briefing_lines, border_style="dim"))
    console.print()

    # ── Resolve starting domain ────────────────────────────────────────────────
    start_domain = find_domain_by_arg(domain_arg) if domain_arg else None
    if start_domain:
        # Put the requested domain first in report order
        domain_idx = next(
            (i for i, d in enumerate(report) if d["key"] == start_domain["key"]), 0
        )
        console.print(f"[dim]Domaine sélectionné : [bold]{start_domain['label']}[/bold][/dim]\n")
    else:
        domain_idx = 0

    # ── Session state ──────────────────────────────────────────────────────────
    depth = 0          # 0=factuel, 1=émotionnel, 2=identitaire
    depth_count = 0    # questions answered at current depth
    facts_before = len(facts)
    session_count = 0
    session_transcript: list[dict] = []  # {domain, q, a} — full session history

    # Generate and display first question
    domain = report[domain_idx]
    depth_info = DEPTH_LEVELS[depth]
    with console.status("[dim]Préparation de la première question...[/dim]", spinner="dots"):
        question = generate_question(domain, profile, facts, session_transcript, depth)

    console.print(f"[dim][{domain['label']}  {depth_info['display']}][/dim]")
    console.print(f"[bold cyan]{question}[/bold cyan]")
    console.print()

    while True:
        try:
            answer = Prompt.ask("[bold green]Toi[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not answer or answer.lower() in ("stop", "fin", "exit", "quitter", "q"):
            break

        # "suivant" — move to next domain, reset depth
        if answer.lower() in ("suivant", "next", "autre", "changer"):
            domain_idx = (domain_idx + 1) % len(report)
            depth = 0
            depth_count = 0
            domain = report[domain_idx]
            depth_info = DEPTH_LEVELS[depth]
            console.print(f"\n[dim]── {domain['label']} ──[/dim]")
            with console.status("[dim]Changement de domaine...[/dim]", spinner="dots"):
                question = generate_question(domain, profile, facts, session_transcript, depth)
            console.print(f"[dim][{domain['label']}  {depth_info['display']}][/dim]")
            console.print(f"[bold cyan]{question}[/bold cyan]")
            console.print()
            continue

        # Detect sensitive topic
        sensitive = is_sensitive_answer(answer)

        # Log question + extract facts
        log_question(domain["key"], question, session_id=session_id, depth=depth)
        session_count += 1

        try:
            n = extract_and_store(answer, "")
            if n:
                console.print(f"[dim]  ✦ {n} souvenir(s) mémorisé(s)[/dim]")
        except Exception:
            pass

        # Add to session transcript
        session_transcript.append({"domain": domain["label"], "q": question, "a": answer})

        # Refresh facts
        facts = get_all_facts()

        # Depth escalation
        depth_count += 1
        if depth_count >= DEPTH_THRESHOLD and depth < 2:
            depth += 1
            depth_count = 0

        depth_info = DEPTH_LEVELS[depth]

        # Generate next question (with full session context + new depth)
        with console.status("[dim]Réflexion...[/dim]", spinner="dots"):
            next_question = generate_question(domain, profile, facts, session_transcript, depth)

        prev_question = question
        question = next_question

        # Stream: warm reaction + next question (with session context)
        console.print()
        full_reply = ""
        try:
            stream = stream_reaction_and_question(
                domain_label=domain["label"],
                prev_question=prev_question,
                answer=answer,
                next_question=question,
                session_transcript=session_transcript[:-1],  # exclude current exchange
                sensitive=sensitive,
            )
            with Live(
                Panel(
                    "",
                    title=f"[bold blue]Moi.AI[/bold blue]  [dim]{depth_info['display']}[/dim]",
                    border_style="blue",
                ),
                console=console,
                refresh_per_second=15,
                vertical_overflow="visible",
            ) as live:
                for chunk in stream:
                    full_reply += chunk
                    live.update(Panel(
                        Markdown(full_reply),
                        title=f"[bold blue]Moi.AI[/bold blue]  [dim]{depth_info['display']}[/dim]",
                        border_style="blue",
                    ))
        except Exception:
            console.print(f"[dim][{domain['label']}  {depth_info['display']}][/dim]")
            console.print(f"[bold cyan]{question}[/bold cyan]")

        _print_cost()
        console.print()

    # ── End-of-session ─────────────────────────────────────────────────────────
    facts_added = len(get_all_facts()) - facts_before

    console.print(Panel(
        f"[bold]Session terminée[/bold] — {session_count} question(s)  •  "
        f"[bold cyan]{facts_added}[/bold cyan] souvenir(s) mémorisé(s).\n"
        "[dim]Reviens avec [bold]/questions[/bold] pour continuer à construire ta mémoire.[/dim]",
        border_style="cyan",
    ))
    console.print()

    # Generate session narrative if there's enough material
    if len(session_transcript) >= 3:
        console.print("[dim]Génération du récit de session...[/dim]")
        try:
            narrative = generate_session_narrative(session_transcript)
            if narrative:
                console.print()
                console.print(Panel(
                    Markdown(narrative),
                    title="[bold]Ce que tu m'as partagé aujourd'hui[/bold]",
                    border_style="magenta",
                ))
                _print_cost()
                console.print()
        except Exception:
            pass


# ── Analyser ───────────────────────────────────────────────────────────────────

def _extract_contradiction_pairs(report: str) -> list[tuple[int, int]]:
    """Extract pairs of fact IDs from the Incohérences section of the report."""
    import re
    section = re.search(r"## Incohérences.*?(?=\n##|\Z)", report, re.DOTALL | re.IGNORECASE)
    if not section:
        return []
    pairs: list[tuple[int, int]] = []
    for line in section.group(0).splitlines():
        ids = re.findall(r"#(\d+)", line)
        if len(ids) >= 2:
            try:
                pairs.append((int(ids[0]), int(ids[1])))
            except ValueError:
                pass
    return pairs


def _handle_analyser() -> None:
    """A posteriori audit of all stored facts, with interactive contradiction resolution."""
    from moiai.analyser import analyse_facts
    facts_count = len(get_all_facts())
    if facts_count == 0:
        console.print("[dim]Aucun fait mémorisé. Commence à parler pour construire ta mémoire.[/dim]\n")
        return
    with console.status(
        f"[dim]Analyse de {facts_count} fait(s) en cours...[/dim]", spinner="dots"
    ):
        try:
            report = analyse_facts()
        except Exception as e:
            console.print(f"[red]Erreur :[/red] {e}\n")
            return
    console.print(Panel(
        Markdown(report),
        title="[bold]Audit de mémoire — analyse a posteriori[/bold]",
        border_style="cyan",
    ))
    _print_cost()
    console.print()

    # ── Interactive contradiction resolution ───────────────────────────────────
    pairs = _extract_contradiction_pairs(report)
    if not pairs:
        return

    console.print(f"[yellow]{len(pairs)} contradiction(s) à résoudre :[/yellow]\n")
    for id1, id2 in pairs:
        f1 = get_fact_by_id(id1)
        f2 = get_fact_by_id(id2)
        if not f1 or not f2:
            continue

        console.print(Panel(
            f"[bold cyan]1.[/bold cyan] #{id1} · {f1['category']} · {f1['fact']}\n"
            f"[bold cyan]2.[/bold cyan] #{id2} · {f2['category']} · {f2['fact']}",
            title="[yellow]Contradiction[/yellow]",
            border_style="yellow",
        ))
        choice = Prompt.ask(
            "  Supprimer",
            choices=["1", "2", "ignorer"],
            default="ignorer",
        )
        if choice == "1":
            delete_fact(id1)
            console.print(f"[green]✓[/green] Fait #{id1} supprimé.\n")
        elif choice == "2":
            delete_fact(id2)
            console.print(f"[green]✓[/green] Fait #{id2} supprimé.\n")
        else:
            console.print("[dim]Ignoré.[/dim]\n")


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
    _print_cost()
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


# ── Auto-backup (silent) ───────────────────────────────────────────────────────

_AUTO_BACKUP_EVERY = 20   # messages between periodic auto-backups
_AUTO_BACKUP_KEEP  = 5    # number of auto-backup files to keep


def _auto_backup(silent: bool = True) -> None:
    """Create a silent auto-backup in the Download folder. Keeps last N files."""
    if not _DB_PATH.exists():
        return
    dest_dir = _best_export_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"moiai_auto_{timestamp}.db"
    try:
        src_conn = sqlite3.connect(_DB_PATH)
        dst_conn = sqlite3.connect(dest)
        src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()
    except Exception:
        return

    # Rotate: delete oldest auto-backups beyond the keep limit
    try:
        auto_files = sorted(dest_dir.glob("moiai_auto_*.db"))
        for old in auto_files[:-_AUTO_BACKUP_KEEP]:
            old.unlink(missing_ok=True)
    except Exception:
        pass

    if not silent:
        console.print(f"[dim]  💾 Auto-backup → {dest.name}[/dim]")


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


# ── Backup & restore ───────────────────────────────────────────────────────────

def _handle_update() -> None:
    """Check for updates on the remote branch and apply them."""
    import subprocess as _sp

    def _run(cmd: list[str]) -> tuple[int, str]:
        r = _sp.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        return r.returncode, (r.stdout + r.stderr).strip()

    # Detect current branch
    _, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if not branch:
        console.print("[red]Impossible de détecter la branche git.[/red]\n")
        return

    console.print(f"[dim]Branche : [bold]{branch}[/bold] — vérification des mises à jour...[/dim]")

    # Fetch remote quietly
    code, out = _run(["git", "fetch", "origin", branch])
    if code != 0:
        console.print(f"[red]Erreur réseau :[/red] {out}\n")
        return

    # Compare local vs remote
    _, local_sha  = _run(["git", "rev-parse", "HEAD"])
    _, remote_sha = _run(["git", "rev-parse", f"origin/{branch}"])

    if local_sha == remote_sha:
        console.print("[green]✓ Application déjà à jour.[/green]\n")
        return

    # Show what changed
    _, log = _run([
        "git", "log", "--oneline", "--no-decorate",
        f"HEAD..origin/{branch}",
    ])
    if log:
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="dim", width=8)
        table.add_column()
        for line in log.splitlines():
            parts = line.split(" ", 1)
            table.add_row(parts[0], parts[1] if len(parts) > 1 else "")
        console.print(Panel(table, title="[bold]Mises à jour disponibles[/bold]", border_style="cyan"))

    code, out = _run(["git", "pull", "origin", branch])
    if code != 0:
        console.print(f"[red]Erreur lors du pull :[/red] {out}\n")
        return

    console.print("[green]✓ Mises à jour installées. Redémarrage...[/green]")
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _handle_backup() -> None:
    if not _DB_PATH.exists():
        console.print("[yellow]Aucune mémoire à sauvegarder.[/yellow]\n")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"moiai_backup_{timestamp}.db"

    # Try accessible locations in order: /sdcard, ~/Documents, home, then fallback to DB dir
    candidates = [
        Path("/sdcard/Download"),
        Path("/storage/emulated/0/Download"),
        Path("/sdcard/Downloads"),
        Path("/storage/emulated/0/Downloads"),
        Path("/sdcard"),
        Path("/storage/emulated/0"),
        Path.home(),
        _DB_PATH.parent,
    ]
    dest_dir = next((p for p in candidates if p.exists() and os.access(p, os.W_OK)), _DB_PATH.parent)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    try:
        src_conn = sqlite3.connect(_DB_PATH)
        dst_conn = sqlite3.connect(dest)
        src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()
    except Exception as e:
        console.print(f"[red]Erreur backup :[/red] {e}\n")
        return

    size_kb = dest.stat().st_size // 1024
    console.print(
        f"[green]✓ Sauvegarde créée[/green]\n"
        f"[bold]{dest}[/bold]\n"
        f"[dim]{size_kb} Ko — visible dans le gestionnaire de fichiers Android.[/dim]\n"
    )


def _find_backups() -> list[Path]:
    """Scan Download folders and DB dir for moiai backup files, most recent first."""
    search_dirs = [
        Path("/sdcard/Download"),
        Path("/storage/emulated/0/Download"),
        Path("/sdcard/Downloads"),
        Path("/storage/emulated/0/Downloads"),
        Path("/sdcard"),
        Path("/storage/emulated/0"),
        Path.home(),
        _DB_PATH.parent,
    ]
    seen: set[Path] = set()
    found: list[Path] = []
    for d in search_dirs:
        if not d.exists():
            continue
        for f in d.glob("moiai_*.db"):
            resolved = f.resolve()
            if resolved not in seen:
                seen.add(resolved)
                found.append(f)
    return sorted(found, key=lambda f: f.stat().st_mtime, reverse=True)


def _handle_restore(args: str) -> None:
    filepath = args.strip().strip('"').strip("'")

    if not filepath:
        # Interactive mode: list available backups
        backups = _find_backups()
        if not backups:
            console.print("[yellow]Aucun fichier de backup trouvé dans le dossier Download.[/yellow]\n")
            console.print("[dim]Usage manuel :[/dim] /restaurer <chemin/vers/backup.db>\n")
            return

        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("#", style="dim", width=4)
        table.add_column("Fichier", style="cyan")
        table.add_column("Taille", width=8, style="dim")
        table.add_column("Date", width=17, style="dim")

        for i, f in enumerate(backups, 1):
            size_kb = f.stat().st_size // 1024
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
            table.add_row(str(i), f.name, f"{size_kb} Ko", mtime)

        console.print(Panel(table, title="[bold]Backups disponibles[/bold]", border_style="cyan"))

        choice = Prompt.ask(
            f"[dim]Numéro à restaurer (1-{len(backups)}) ou Entrée pour annuler[/dim]",
            default="",
        ).strip()

        if not choice:
            console.print("[dim]Annulé.[/dim]\n")
            return
        if not choice.isdigit() or not (1 <= int(choice) <= len(backups)):
            console.print("[yellow]Numéro invalide.[/yellow]\n")
            return

        src = backups[int(choice) - 1]
    else:
        src = Path(filepath).expanduser().resolve()
        if not src.exists():
            console.print(f"[red]Fichier introuvable :[/red] {src}\n")
            return
    # Validate it's a SQLite DB
    try:
        conn = sqlite3.connect(src)
        conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        conn.close()
    except Exception:
        console.print("[red]Fichier invalide — ce n'est pas une base SQLite.[/red]\n")
        return

    console.print(Panel(
        f"[bold yellow]Attention[/bold yellow] — cette opération va remplacer toute ta mémoire actuelle\n"
        f"par le contenu de [bold]{src.name}[/bold].\n"
        f"[dim]La mémoire actuelle sera perdue (sauf si tu as fait un /backup avant).[/dim]",
        border_style="yellow",
    ))
    if not Confirm.ask("[bold]Confirmer la restauration ?[/bold]", default=False):
        console.print("[dim]Annulé.[/dim]\n")
        return

    # Safety backup of current DB before overwriting
    if _DB_PATH.exists():
        safety = _DB_PATH.parent / f"backup_avant_restauration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        try:
            shutil.copy2(_DB_PATH, safety)
            console.print(f"[dim]Sauvegarde de sécurité créée : {safety.name}[/dim]")
        except Exception:
            pass

    try:
        src_conn = sqlite3.connect(src)
        dst_conn = sqlite3.connect(_DB_PATH)
        src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()
    except Exception as e:
        console.print(f"[red]Erreur restauration :[/red] {e}\n")
        return

    console.print("[green]✓ Mémoire restaurée.[/green] Relance l'application pour que les changements prennent effet.\n")


# ── API key management ─────────────────────────────────────────────────────────

def _handle_api_key() -> None:
    current = os.environ.get("ANTHROPIC_API_KEY", "")
    if current:
        masked = current[:12] + "..." + current[-4:]
        console.print(f"Clé actuelle : [dim]{masked}[/dim]")
    else:
        console.print("[yellow]Aucune clé configurée.[/yellow]")

    key = Prompt.ask(
        "[bold]Nouvelle clé API[/bold] (Entrée pour annuler)", default=""
    ).strip()
    if not key:
        console.print("[dim]Annulé.\n[/dim]")
        return
    if not (key.startswith("sk-ant-") and len(key) >= 60):
        console.print("[red]Clé invalide (doit commencer par sk-ant- et faire 60+ caractères).[/red]\n")
        return
    os.environ["ANTHROPIC_API_KEY"] = key
    env_path = Path(__file__).parent / ".env"
    env_path.write_text(f"ANTHROPIC_API_KEY={key}\n", encoding="utf-8")
    console.print("[green]✓ Clé mise à jour et sauvegardée dans .env[/green]\n")


# ── Reset ─────────────────────────────────────────────────────────────────────

def _handle_reset() -> None:
    from moiai.memory import DB_PATH
    console.print(
        "[bold red]ATTENTION[/bold red] — Cette action supprime définitivement :\n"
        "  • Toutes les conversations\n"
        "  • Tous les faits mémorisés\n"
        "  • Le profil, la narration, les humeurs\n"
        "  • Les objectifs, personnes et capsules\n"
    )
    if not Confirm.ask("[bold red]Confirmer la suppression totale ?[/bold red]", default=False):
        console.print("[dim]Annulé.\n[/dim]")
        return
    if not Confirm.ask("[bold red]Vraiment ? C'est irréversible.[/bold red]", default=False):
        console.print("[dim]Annulé.\n[/dim]")
        return
    try:
        DB_PATH.unlink(missing_ok=True)
        console.print("[green]✓ Mémoire effacée. Redémarre l'application pour repartir de zéro.[/green]\n")
    except Exception as e:
        console.print(f"[red]Erreur :[/red] {e}\n")


# ── Welcome screen (first session) ────────────────────────────────────────────

def _show_welcome() -> None:
    console.print(Panel(
        "[bold cyan]Bienvenue sur Moi.AI[/bold cyan] — ton assistant personnel local.\n\n"
        "Moi.AI est un outil qui apprend à te connaître au fil de tes conversations.\n"
        "Il mémorise des faits sur toi, tes proches, tes objectifs, ton humeur —\n"
        "et s'en souvient à chaque session pour être vraiment utile.\n\n"
        "[bold]🔒 100 % local et privé[/bold]\n"
        "Toutes tes données sont stockées sur ton appareil uniquement,\n"
        "dans une base SQLite ([dim]moiai/data/memory.db[/dim]).\n"
        "Rien n'est envoyé à l'extérieur — sauf tes messages à l'API Anthropic\n"
        "pour générer les réponses (comme n'importe quel chat IA).\n"
        "Anthropic ne conserve pas tes données de conversation.\n\n"
        "[bold]Pour démarrer :[/bold]\n"
        "  [cyan]/import <fichier>[/cyan]    Importer WhatsApp, Instagram, Telegram, PDF…\n"
        "  [cyan]/objectif <texte>[/cyan]    Déclarer un objectif\n"
        "  [cyan]/bilan[/cyan]               Faire ton bilan de vie (note 1-5 par domaine)\n"
        "  [cyan]/cle[/cyan]                 Configurer ou modifier ta clé API\n"
        "  [cyan]/aide[/cyan]                Voir toutes les commandes disponibles\n\n"
        "[dim]Ou commence simplement à parler — je vais apprendre à te connaître.[/dim]",
        title="[bold]Première session[/bold]",
        border_style="cyan",
    ))
    console.print()



def _extract_async(user_msg: str, assistant_msg: str, sensitive: bool = False) -> None:
    try:
        n = extract_and_store(user_msg, assistant_msg)
        if n:
            console.print(f"[dim]  ✦ {n} souvenir(s) mémorisé(s)[/dim]")
    except Exception:
        pass


# ── Main loop ──────────────────────────────────────────────────────────────────

def _is_valid_key(key: str) -> bool:
    """A real Anthropic key starts with sk-ant- and is at least 60 chars long."""
    return bool(key) and key.startswith("sk-ant-") and len(key) >= 60


def _ensure_api_key() -> None:
    """Load API key from .env, env var, or ask the user. Offer to save it."""
    if _is_valid_key(os.environ.get("ANTHROPIC_API_KEY", "")):
        return

    # Try .env in script directory or cwd
    for env_path in (Path(__file__).parent / ".env", Path(".env")):
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if _is_valid_key(key):
                        os.environ["ANTHROPIC_API_KEY"] = key
                        return
            break

    console.print(
        "[yellow]Aucune clé API valide trouvée.[/yellow]\n"
        "[dim]Obtiens ta clé sur [bold]console.anthropic.com[/bold][/dim]\n"
    )
    key = Prompt.ask("[bold]Clé API Anthropic[/bold] (sk-ant-...)").strip()
    if not _is_valid_key(key):
        console.print("[red]Clé invalide (doit commencer par sk-ant- et faire 60+ caractères).[/red]")
        sys.exit(1)

    os.environ["ANTHROPIC_API_KEY"] = key

    if Confirm.ask("Sauvegarder dans [bold].env[/bold] pour ne plus la redemander ?", default=True):
        env_path = Path(__file__).parent / ".env"
        env_path.write_text(f"ANTHROPIC_API_KEY={key}\n", encoding="utf-8")
        console.print(f"[green]✓ Clé sauvegardée dans[/green] [bold]{env_path}[/bold]\n")


def _check_updates_bg() -> tuple[int, str]:
    """Return (n_commits_behind, branch). Runs in background thread."""
    import subprocess as _sp
    def _run(cmd):
        r = _sp.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        return (r.stdout + r.stderr).strip()
    try:
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        _run(["git", "fetch", "origin", branch, "--quiet"])
        local  = _run(["git", "rev-parse", "HEAD"])
        remote = _run(["git", "rev-parse", f"origin/{branch}"])
        if local == remote:
            return 0, branch
        count = _run(["git", "rev-list", "--count", f"HEAD..origin/{branch}"])
        return int(count or 0), branch
    except Exception:
        return 0, ""



def main() -> None:
    _ensure_api_key()

    init_db()
    _header()

    # Check for updates in background — result shown after startup
    _update_result: list = [None]
    def _bg_update():
        _update_result[0] = _check_updates_bg()
    update_thread = threading.Thread(target=_bg_update, daemon=True)
    update_thread.start()

    if _count_messages() == 0:
        _show_welcome()
    else:
        _show_due_capsules()
        start_session()
        briefing = get_startup_briefing(timeout=6.0)
        if briefing:
            console.print(Panel(
                briefing,
                title="[bold blue]Moi.AI[/bold blue]",
                border_style="blue",
            ))
            _print_cost()
            console.print()

    # Show update notification if ready (wait max 3s)
    update_thread.join(timeout=3.0)
    if _update_result[0] and _update_result[0][0] > 0:
        n, branch = _update_result[0]
        console.print(
            f"[cyan]  ↑ {n} mise(s) à jour disponible(s)[/cyan]  "
            f"[dim]→ tape [bold]/màj[/bold] pour installer[/dim]\n"
        )

    session_msg_count = 0
    voice_mode = False
    tts_mode = False

    while True:
        try:
            if voice_mode:
                console.print("[bold green]Toi[/bold green] [dim cyan]🎤 Entrée = parler  •  texte = taper[/dim cyan]")
                raw = input().strip()
                if not raw:
                    # Trigger voice capture
                    console.print("[dim cyan]Écoute...[/dim cyan]", end="\r")
                    transcribed = _voice_transcribe()
                    if transcribed:
                        console.print(f"[bold green]Toi (voix)[/bold green] {transcribed}")
                        user_input = transcribed
                    else:
                        console.print("[yellow]Rien capturé — réessaie ou tape ton message.[/yellow]")
                        continue
                else:
                    user_input = raw
            else:
                user_input = Prompt.ask("[bold green]Toi[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]À bientôt.[/dim]")
            _auto_backup()
            break

        if tts_mode:
            _tts_stop()

        if not user_input:
            continue

        lower = user_input.lower()

        if lower in ("/quitter", "/exit", "/quit", "exit", "quit"):
            console.print("[dim]À bientôt.[/dim]")
            _auto_backup()
            break
        elif lower == "/aide":
            _show_help()
        elif lower == "/debug":
            _set_debug(not get_debug_enabled())
            state = "[yellow]activé[/yellow]" if get_debug_enabled() else "[dim]désactivé[/dim]"
            console.print(f"Mode débogage {state}.\n")
        elif lower == "/tts":
            if not _tts_available():
                console.print(
                    "[yellow]Synthèse vocale non disponible.[/yellow]\n"
                    "[dim]Il faut [bold]Termux:API[/bold] depuis F-Droid "
                    "et [bold]pkg install termux-api[/bold][/dim]\n"
                )
            else:
                tts_mode = not tts_mode
                if tts_mode:
                    console.print("[cyan]🔊 Synthèse vocale activée[/cyan] — les réponses seront lues à voix haute.\n"
                                  "[dim]Tape n'importe quoi et appuie sur Entrée pour interrompre.[/dim]\n")
                else:
                    _tts_stop()
                    console.print("[dim]Synthèse vocale désactivée.[/dim]\n")
        elif lower == "/voix":
            if not _voice_available():
                console.print(
                    "[yellow]Saisie vocale non disponible.[/yellow]\n"
                    "[dim]Il faut installer [bold]Termux:API[/bold] depuis F-Droid "
                    "puis lancer : [bold]pkg install termux-api[/bold][/dim]\n"
                )
            else:
                voice_mode = not voice_mode
                if voice_mode:
                    console.print("[cyan]🎤 Mode vocal activé[/cyan] — appuie sur Entrée pour parler, tape pour écrire.\n")
                else:
                    console.print("[dim]Mode vocal désactivé.[/dim]\n")
        elif lower == "/backup":
            _handle_backup()
        elif lower in ("/màj", "/maj"):
            _handle_update()
        elif lower == "/restart":
            console.print("[dim]Redémarrage...[/dim]")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        elif lower.startswith("/restaurer"):
            _handle_restore(user_input[10:])
        elif lower in ("/cle", "/clé"):
            _handle_api_key()
        elif lower == "/reset":
            _handle_reset()
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
        elif lower.startswith("/récent") or lower.startswith("/recent"):
            _handle_recent(user_input.split(None, 1)[1] if " " in user_input else "")
        elif lower.startswith("/supprimer"):
            _handle_supprimer(user_input[10:])
        elif lower.startswith("/corriger"):
            _handle_corriger(user_input[9:])
        elif lower.startswith("/réfuter") or lower.startswith("/refuter"):
            _handle_refuter(user_input.split(None, 1)[1] if " " in user_input else "")
        elif lower == "/fusionner":
            _handle_fusionner()
        elif lower.startswith("/import"):
            _handle_import(user_input[7:])
        elif lower == "/humeur":
            _handle_mood_chart()
        elif lower.startswith("/questions"):
            _handle_questions(user_input[10:].strip())
        elif lower == "/analyser":
            _handle_analyser()
        elif lower == "/reflect":
            _handle_reflect()
        elif lower.startswith("/objectif") and not lower.startswith("/objectifs"):
            _handle_add_goal(user_input[9:])
        elif lower == "/objectifs":
            _handle_goals()
        elif lower in ("/bilan", "/bilan de vie"):
            _handle_bilan()
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

            last = get_last_call_cost()
            total = get_session_cost()
            console.print(
                f"[dim]  réponse : ${last:.4f}  ·  session : ${total:.4f}[/dim]"
            )

            if get_debug_enabled():
                _print_debug()

            if tts_mode:
                threading.Thread(target=_tts_speak, args=(full_reply,), daemon=True).start()

            sensitive = is_sensitive_answer(user_input)
            threading.Thread(
                target=_extract_async,
                args=(user_input, full_reply, sensitive),
                daemon=True,
            ).start()

            session_msg_count += 1
            if session_msg_count % _AUTO_BACKUP_EVERY == 0:
                threading.Thread(target=_auto_backup, daemon=True).start()


if __name__ == "__main__":
    main()
