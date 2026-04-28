#!/usr/bin/env python3
"""
Moi.AI — version Android/Pydroid 3.
Sans streaming, sans Rich Live — compatible avec tous les terminaux simples.
Lancement : python main_android.py
"""

import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

# Ensure the directory containing this script is on the path
# (needed for Pydroid 3 and other environments where cwd != script dir)
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
    from rich.table import Table
    _RICH = True
except ImportError:
    _RICH = False

from moiai.chat import chat_complete, finish_turn, get_startup_briefing, get_stats, start_session
from moiai.capsule import (
    add_capsule,
    delete_capsule,
    get_all_capsules,
    get_due_capsules,
    mark_opened,
    parse_delay,
)
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
    get_mood_by_day,
    get_recent_mood,
    get_stale_facts,
    init_db,
    load_conversation_history,
    search_facts,
    update_fact,
)
from moiai.people import delete_person, get_all_people
from moiai.reflect import (
    LIFE_DOMAINS,
    find_contradictions,
    generate_reflection,
    get_latest_domain_scores,
    save_domain_scores,
    store_contradiction,
)

if _RICH:
    console = Console()


# ── Output helpers ─────────────────────────────────────────────────────────────

def _print(text: str = "") -> None:
    if _RICH:
        console.print(text)
    else:
        print(text)


def _input(prompt: str = "") -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise KeyboardInterrupt


def _confirm(question: str) -> bool:
    r = _input(f"{question} (o/n) : ").lower()
    return r in ("o", "oui", "y", "yes")


def _panel(content: str, title: str = "") -> None:
    if _RICH:
        console.print(Panel(Markdown(content), title=title, border_style="blue"))
    else:
        if title:
            print(f"\n=== {title} ===")
        print(content)
        print()


def _status(msg: str) -> None:
    _print(f"[dim]{msg}[/dim]" if _RICH else msg)


# ── Header ─────────────────────────────────────────────────────────────────────

COMMANDS_HELP = """
/profil       Afficher profil + narration
/faits [cat]  Lister les faits (filtrable par catégorie)
/cherche X    Recherche dans la mémoire
/oublie X     Supprimer un fait
/edit ID txt  Corriger un fait
/historique   Derniers échanges
/import fic   Importer un fichier
/condenser    Fusionner la mémoire
/humeur       Graphique d'humeur sur 30 jours
/reflect      Analyse psychologique
/objectif X   Ajouter un objectif
/objectifs    Lister les objectifs
/bilan        Auto-évaluation par domaine
/révision     Détecter les contradictions
/personnes    Personnes dans ta vie
/capsule X    Créer une capsule temporelle (ex: dans 2 semaines)
/capsules     Lister toutes les capsules
/rapport      Export Markdown
/export       Export JSON
/stats        Statistiques
/aide         Cette aide
/quitter      Quitter
"""


def _header() -> None:
    _print("=" * 50)
    _print("  Moi.AI — ton double personnel artificiel")
    _print("  /aide pour les commandes")
    _print("=" * 50)
    _print()


# ── Profile ────────────────────────────────────────────────────────────────────

def _show_profile() -> None:
    narrative = get_latest_narrative()
    profile = get_profile()
    mood = get_recent_mood(limit=1)

    if narrative:
        _panel(narrative, "Narration personnelle")

    if mood:
        m = mood[0]
        _print(f"Humeur récente : {m['valence']} — {m['state']}")

    if profile:
        _print("\n--- Profil ---")
        for k, v in profile.items():
            _print(f"  {k}: {v}")
    elif not narrative:
        _print("Aucun profil enregistré.")
    _print()


# ── Facts ──────────────────────────────────────────────────────────────────────

def _show_facts(args: str = "") -> None:
    cat_filter = args.strip().lower() or None
    facts = get_all_facts()
    if cat_filter:
        facts = [f for f in facts if cat_filter in f["category"].lower()]

    if not facts:
        _print(f"Aucun fait{'dans « ' + cat_filter + ' »' if cat_filter else ''}.")
        _print()
        return

    _print("● certain  ◐ probable  ○ hypothèse  ✕ réfuté\n")
    by_cat: dict[str, list[dict]] = {}
    for f in facts:
        by_cat.setdefault(f["category"], []).append(f)

    for cat, items in by_cat.items():
        _print(f"[ {cat.upper()} ]")
        for f in items:
            badge = CERTAINTY_BADGE.get(f.get("certainty", "certain"), "●")
            age = fact_age_badge(f.get("last_confirmed") or f["timestamp"])
            _print(f"  #{f['id']} {badge} {f['fact']}{age}")
        _print()

    _print(f"{len(facts)} fait(s)\n")


# ── Stats ──────────────────────────────────────────────────────────────────────

def _show_stats() -> None:
    stats = get_stats()
    facts = get_all_facts()
    profile = get_profile()
    narrative = get_latest_narrative()
    summaries = get_conversation_summaries(limit=100)
    stale = get_stale_facts(days=180)

    _print("--- Statistiques ---")
    _print(f"  Messages totaux       : {stats['messages']}")
    _print(f"  Résumés               : {len(summaries)}")
    _print(f"  Faits mémorisés       : {len(facts)}")
    _print(f"  Faits potent. périmés : {len(stale)}")
    _print(f"  Entrées profil        : {len(profile)}")
    _print(f"  Narration             : {'oui' if narrative else 'non'}")

    by_cat: dict[str, int] = {}
    for f in facts:
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
    if by_cat:
        _print()
        for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
            _print(f"    {cat}: {n}")
    _print()


# ── Search ─────────────────────────────────────────────────────────────────────

def _handle_search(args: str) -> None:
    query = args.strip()
    if not query:
        _print("Usage : /cherche <terme>")
        return
    results = search_facts(query, limit=25)
    if not results["facts"] and not results["profile"]:
        _print(f"Aucun résultat pour « {query} ».\n")
        return
    for k, v in results["profile"].items():
        _print(f"[Profil] {k}: {v}")
    for f in results["facts"]:
        badge = CERTAINTY_BADGE.get(f.get("certainty", "certain"), "●")
        _print(f"  #{f['id']} {badge} [{f['category']}] {f['fact']}")
    _print()


# ── Forget ─────────────────────────────────────────────────────────────────────

def _handle_forget(args: str) -> None:
    query = args.strip()
    if not query:
        _print("Usage : /oublie <ID ou terme>")
        return
    if query.isdigit():
        f = get_fact_by_id(int(query))
        if not f:
            _print(f"Aucun fait #{query}.")
            return
        _print(f"#{f['id']} [{f['category']}] {f['fact']}")
        if _confirm("Supprimer ?"):
            delete_fact(f["id"])
            _print("✓ Supprimé.\n")
        else:
            _print("Annulé.\n")
        return
    results = search_facts(query, limit=10)
    for k, v in results["profile"].items():
        _print(f"Profil : {k} = {v}")
        if _confirm(f"Supprimer « {k} » ?"):
            delete_profile_key(k)
            _print("✓ Supprimé.")
    for f in results["facts"]:
        _print(f"#{f['id']} [{f['category']}] {f['fact']}")
        if _confirm("Supprimer ?"):
            delete_fact(f["id"])
            _print("✓ Supprimé.")
    _print()


# ── Edit ───────────────────────────────────────────────────────────────────────

def _handle_edit(args: str) -> None:
    parts = args.strip().split(None, 1)
    if len(parts) < 2 or not parts[0].isdigit():
        _print("Usage : /edit <ID> <nouveau texte ou certitude>")
        return
    fact_id = int(parts[0])
    new_text = parts[1].strip()
    f = get_fact_by_id(fact_id)
    if not f:
        _print(f"Aucun fait #{fact_id}.")
        return
    _print(f"Actuel : {f['fact']}  ({f.get('certainty','certain')})")
    if new_text.lower() in CERTAINTY_LEVELS:
        update_fact(fact_id, new_certainty=new_text.lower())
        _print(f"✓ Certitude → {new_text}\n")
    else:
        update_fact(fact_id, new_text=new_text)
        _print("✓ Fait mis à jour.\n")


# ── History ────────────────────────────────────────────────────────────────────

def _handle_history(args: str) -> None:
    n = 10
    if args.strip().isdigit():
        n = min(int(args.strip()), 100)
    history = load_conversation_history(limit=n)
    if not history:
        _print("Aucun échange enregistré.\n")
        return
    for msg in history:
        role = "Toi" if msg["role"] == "user" else "Moi.AI"
        ts = msg["timestamp"][:16].replace("T", " ")
        _print(f"\n[{role}] {ts}")
        _print(msg["content"])
    _print()


# ── Condense ───────────────────────────────────────────────────────────────────

def _handle_condense() -> None:
    _status("Claude synthétise ton profil...")
    try:
        narrative = condense_narrative()
    except Exception as e:
        _print(f"Erreur : {e}\n")
        return
    _panel(narrative, "Narration personnelle")
    _print("✓ Narration sauvegardée.\n")


# ── Mood chart ────────────────────────────────────────────────────────────────

_BLOCKS = "▁▂▃▄▅▆▇█"
_MOOD_COLOR_LABEL = {
    "positive": "positive", "negative": "négative",
    "mixed": "mixte", "neutral": "neutre",
}


def _mood_score(valence: str, intensity: int) -> float:
    i = max(1, min(5, intensity or 3))
    if valence == "positive":
        return 2.5 + i * 0.5
    if valence == "negative":
        return 3.5 - i * 0.5
    return 3.0


def _handle_mood_chart() -> None:
    from datetime import date, timedelta as td

    entries = get_mood_by_day(days=30)
    if not entries:
        _print("Aucune humeur enregistrée — parle-moi un peu !\n")
        return

    day_map = {e["day"]: e for e in entries}
    today = date.today()
    all_days = [(today - td(days=29 - i)).isoformat() for i in range(30)]

    spark = ""
    for d in all_days:
        if d in day_map:
            e = day_map[d]
            s = _mood_score(e["valence"], e["intensity"])
            idx = min(7, max(0, round((s - 1) / 4 * 7)))
            spark += _BLOCKS[idx]
        else:
            spark += "·"

    scores = [_mood_score(e["valence"], e["intensity"]) for e in entries]
    avg = sum(scores) / len(scores)

    valence_counts: dict[str, int] = {}
    for e in entries:
        valence_counts[e["valence"]] = valence_counts.get(e["valence"], 0) + 1
    dominant = max(valence_counts, key=valence_counts.get)

    label_l = (today - td(days=29)).strftime("%d/%m")
    label_r = today.strftime("%d/%m")

    _print(f"\n--- Humeur — 30 derniers jours ---")
    _print(spark)
    _print(f"{label_l}{'':>22}{label_r}")
    _print(f"\nMoyenne : {avg:.1f}/5  •  Tendance : {_MOOD_COLOR_LABEL.get(dominant, dominant)}")
    _print(f"Jours enregistrés : {len(entries)}/30\n")

    _print("--- Entrées récentes ---")
    recent = get_recent_mood(limit=8)
    for m in recent:
        bar = "●" * m["intensity"] + "○" * (5 - m["intensity"])
        label = _MOOD_COLOR_LABEL.get(m["valence"], m["valence"])
        _print(f"  {m['timestamp'][:10]}  {label:<10}  {m['state']:<20}  {bar}")
    _print()


# ── Reflect ────────────────────────────────────────────────────────────────────

def _handle_reflect() -> None:
    _status("Analyse psychologique en cours...")
    try:
        text = generate_reflection()
    except Exception as e:
        _print(f"Erreur : {e}\n")
        return
    _panel(text, "Analyse — patterns & angles morts")


# ── Goals ──────────────────────────────────────────────────────────────────────

_GOAL_STATUS_LABEL = {
    "active": "actif", "achieved": "atteint ✓",
    "abandoned": "abandonné", "paused": "en pause",
}


def _handle_add_goal(args: str) -> None:
    text = args.strip()
    if not text:
        _print("Usage : /objectif <texte>")
        return
    dl = _input("Échéance (optionnel, ex: 2025-06-01) : ").strip() or None
    gid = add_goal(text, deadline=dl, source="user")
    _print(f"✓ Objectif #{gid} ajouté.\n")


def _handle_goals() -> None:
    goals = get_all_goals()
    if not goals:
        _print("Aucun objectif enregistré.\n")
        return
    _print("--- Objectifs ---")
    for g in goals:
        label = _GOAL_STATUS_LABEL.get(g.get("status", "active"), g.get("status", ""))
        dl = g.get("deadline", "") or ""
        dl_str = f"  [{dl[:10]}]" if dl else ""
        src = " (extrait)" if g.get("source") == "extracted" else ""
        _print(f"  #{g['id']} [{label}] {g['text']}{dl_str}{src}")
    _print()

    action = _input("Action : (a)tteint / (p)ause / (x)abandonner / (s)upprimer / Entrée=rien : ").lower()
    if not action:
        return
    gid_str = _input("ID : ")
    if not gid_str.isdigit():
        _print("ID invalide.\n")
        return
    gid = int(gid_str)
    if action == "a":
        update_goal_status(gid, "achieved"); _print(f"✓ Objectif #{gid} atteint.\n")
    elif action == "p":
        update_goal_status(gid, "paused"); _print(f"⏸ Objectif #{gid} en pause.\n")
    elif action == "x":
        update_goal_status(gid, "abandoned"); _print(f"✗ Objectif #{gid} abandonné.\n")
    elif action == "s":
        if delete_goal(gid):
            _print(f"✓ Objectif #{gid} supprimé.\n")
        else:
            _print(f"Objectif #{gid} introuvable.\n")


# ── Bilan ──────────────────────────────────────────────────────────────────────

def _handle_bilan() -> None:
    _print("=== Bilan de vie — notez chaque domaine de 1 à 5 ===\n")
    last = get_latest_domain_scores()
    scores: dict[str, int] = {}
    for domain in LIFE_DOMAINS:
        prev = last.get(domain)
        hint = f" (précédent: {prev}/5)" if prev is not None else ""
        while True:
            raw = _input(f"  {domain}{hint} → ").strip()
            if not raw and prev is not None:
                scores[domain] = prev; break
            if raw.isdigit() and 1 <= int(raw) <= 5:
                scores[domain] = int(raw); break
            _print("  Entre 1 et 5.")
    save_domain_scores(scores)
    _print("\n--- Résultat ---")
    for domain, score in scores.items():
        bar = "█" * score + "░" * (5 - score)
        prev = last.get(domain)
        delta = ""
        if prev is not None:
            diff = score - prev
            delta = f"  (+{diff})" if diff > 0 else (f"  ({diff})" if diff < 0 else "")
        _print(f"  {domain:<28} {bar} {score}/5{delta}")
    _print("\n✓ Bilan sauvegardé.\n")


# ── Révision ───────────────────────────────────────────────────────────────────

def _handle_revision() -> None:
    _status("Analyse des contradictions...")
    try:
        contras = find_contradictions()
    except Exception as e:
        _print(f"Erreur : {e}\n")
        return
    if not contras:
        _print("✓ Aucune contradiction détectée.\n")
        return
    _print(f"{len(contras)} contradiction(s) détectée(s) :\n")
    for i, c in enumerate(contras, 1):
        _print(f"--- Contradiction #{i} ---")
        _print(f"  Fait 1 : {c.get('fact1', '—')}")
        _print(f"  Fait 2 : {c.get('fact2', '—')}")
        _print(f"  Explication : {c.get('explanation', '')}")
        _print()
        store_contradiction(None, None, c.get("explanation", ""))
    _print("Contradictions enregistrées. Utilise /faits pour corriger.\n")


# ── Personnes ──────────────────────────────────────────────────────────────────

def _handle_people() -> None:
    people = get_all_people()
    if not people:
        _print("Aucune personne mémorisée.\n")
        return
    _print(f"--- Personnes ({len(people)}) ---")
    for p in people:
        rel = p.get("relation") or ""
        rel_str = f" ({rel})" if rel else ""
        notes = (p.get("notes") or "")[:60]
        last = (p.get("last_mentioned") or "")[:10]
        _print(f"  #{p['id']} {p['name']}{rel_str} — {notes}  [{last}]")
    _print()
    action = _input("(s)upprimer / Entrée=rien : ").lower()
    if action == "s":
        pid_str = _input("ID : ")
        if pid_str.isdigit():
            if delete_person(int(pid_str)):
                _print("✓ Supprimé.\n")
            else:
                _print("ID introuvable.\n")


# ── Capsules ───────────────────────────────────────────────────────────────────

def _handle_add_capsule(args: str) -> None:
    import re
    args = args.strip()
    if not args:
        _print("Usage : /capsule <message> dans <n> jours|semaines|mois")
        _print("Ex :    /capsule mon entretien Google dans 3 jours")
        return

    open_at = parse_delay(args)
    if not open_at:
        delay_str = _input("Dans combien de temps ? (ex: dans 2 semaines / 2025-06-01) : ")
        open_at = parse_delay(delay_str)
        if not open_at:
            _print("Délai non reconnu.\n")
            return
        content = args
    else:
        content = re.sub(
            r"\s+dans\s+\d+\s+(jour|jours|semaine|semaines|mois|an|ans).*$", "", args
        ).strip() or args

    cid = add_capsule(content, open_at)
    _print(f"✓ Capsule #{cid} créée. S'ouvrira le {open_at.strftime('%d/%m/%Y')}\n")


def _handle_capsules() -> None:
    capsules = get_all_capsules()
    if not capsules:
        _print("Aucune capsule créée.\n")
        return
    from datetime import datetime as _dt
    now = _dt.now().isoformat()
    _print(f"--- Capsules ({len(capsules)}) ---")
    for c in capsules:
        status = "ouverte ✓" if c["opened"] else ("EN ATTENTE" if c["open_at"] > now else "DUE !")
        src = " (auto)" if c.get("source") == "auto" else ""
        _print(f"  #{c['id']} [{status}] {c['open_at'][:10]} — {c['content'][:60]}{src}")
    _print()
    action = _input("(s)upprimer / Entrée=rien : ").lower()
    if action == "s":
        cid_str = _input("ID : ")
        if cid_str.isdigit():
            if delete_capsule(int(cid_str)):
                _print("✓ Supprimée.\n")
            else:
                _print("ID introuvable.\n")


def _show_due_capsules() -> None:
    due = get_due_capsules()
    if not due:
        return
    for c in due:
        _print("\n" + "=" * 50)
        _print(f"  📬 CAPSULE du {c['created_at'][:10]}")
        _print(f"  {c['content']}")
        if c.get("ai_note"):
            _print(f"  → {c['ai_note']}")
        _print("=" * 50)
        mark_opened(c["id"])
    _print()


# ── Rapport / Export ───────────────────────────────────────────────────────────

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
    _print(f"✓ Rapport sauvegardé dans {path}\n")


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
    _print(f"✓ Export JSON sauvegardé dans {path}\n")


# ── Import ─────────────────────────────────────────────────────────────────────

def _handle_import(args: str) -> None:
    filepath = args.strip().strip('"').strip("'")
    if not filepath:
        _print("Usage : /import <chemin/vers/fichier>")
        return
    path = Path(filepath).expanduser().resolve()
    if not path.exists():
        _print(f"Fichier introuvable : {path}")
        return

    from moiai.importer import detect_format
    fmt = detect_format(path)
    _print(f"Format détecté : {fmt}")

    user_name: str | None = None
    if fmt in ("whatsapp", "instagram", "instagram_zip", "instagram_multi", "telegram", "telegram_zip"):
        try:
            _, senders, _ = load_file(path, user_name=None)
            if senders:
                _print("Participants : " + ", ".join(senders[:8]))
        except Exception:
            pass
        inp = _input("Ton nom dans ce fichier (vide = tous) : ")
        user_name = inp if inp else None

    try:
        messages, _, _ = load_file(path, user_name=user_name)
    except Exception as e:
        _print(f"Erreur de lecture : {e}")
        return

    if not messages:
        _print("Aucun message trouvé.")
        return

    _print(f"{len(messages)} messages — extraction en cours...")
    _status_counter = [0]

    def on_progress(current: int, total: int) -> None:
        _status_counter[0] = current
        _print(f"  Bloc {current}/{total}...")

    try:
        n = extract_from_messages(messages, progress_callback=on_progress)
    except Exception as e:
        _print(f"Erreur extraction : {e}")
        return

    _print(f"✓ {n} fait(s) mémorisé(s) depuis {path.name}\n")


# ── Background extraction ──────────────────────────────────────────────────────

def _extract_async(user_msg: str, assistant_msg: str) -> None:
    try:
        n = extract_and_store(user_msg, assistant_msg)
        if n:
            _print(f"  ✦ {n} nouveau(x) fait(s) mémorisé(s)")
    except Exception:
        pass


# ── Main loop ──────────────────────────────────────────────────────────────────

def main() -> None:
    def _is_valid_key(k: str) -> bool:
        return bool(k) and k.startswith("sk-ant-") and len(k) >= 60

    for env_path in (Path(__file__).parent / ".env", Path(".env")):
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if _is_valid_key(key):
                        os.environ["ANTHROPIC_API_KEY"] = key
                    break
            break

    if not _is_valid_key(os.environ.get("ANTHROPIC_API_KEY", "")):
        _print("Aucune clé API valide trouvée.")
        _print("Obtiens ta clé sur console.anthropic.com")
        key = _input("Clé API (sk-ant-...) : ").strip()
        if not _is_valid_key(key):
            _print("Clé invalide — abandon.")
            sys.exit(1)
        os.environ["ANTHROPIC_API_KEY"] = key
        save = _input("Sauvegarder dans .env ? (o/n) : ").lower()
        if save in ("o", "oui", "y", "yes"):
            env_path = Path(__file__).parent / ".env"
            env_path.write_text(f"ANTHROPIC_API_KEY={key}\n", encoding="utf-8")
            _print(f"✓ Clé sauvegardée dans {env_path}")

    init_db()
    _header()
    _show_due_capsules()
    start_session()

    briefing = get_startup_briefing(timeout=8.0)
    if briefing:
        _panel(briefing, "Moi.AI")

    while True:
        try:
            user_input = _input("\nToi > ")
        except KeyboardInterrupt:
            _print("\nÀ bientôt.")
            break

        if not user_input:
            continue

        lower = user_input.lower()

        if lower in ("/quitter", "/exit", "/quit", "exit", "quit"):
            _print("À bientôt.")
            break
        elif lower == "/aide":
            _print(COMMANDS_HELP)
        elif lower == "/profil":
            _show_profile()
        elif lower.startswith("/faits"):
            _show_facts(user_input[6:])
        elif lower == "/stats":
            _show_stats()
        elif lower == "/condenser":
            _handle_condense()
        elif lower == "/reflect":
            _handle_reflect()
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
        elif lower == "/humeur":
            _handle_mood_chart()
        elif lower == "/reflect":
            _handle_reflect()
        elif lower.startswith("/capsule") and not lower.startswith("/capsules"):
            _handle_add_capsule(user_input[8:])
        elif lower == "/capsules":
            _handle_capsules()
        else:
            _status("...")
            try:
                reply = chat_complete(user_input)
            except Exception as e:
                _print(f"Erreur {type(e).__name__} : {e}\n")
                continue

            _print()
            _panel(reply, "Moi.AI")

            threading.Thread(
                target=_extract_async,
                args=(user_input, reply),
                daemon=True,
            ).start()


if __name__ == "__main__":
    main()
