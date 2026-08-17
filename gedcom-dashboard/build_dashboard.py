#!/usr/bin/env python3
"""
Génère un dashboard HTML autonome (aucune dépendance externe) à partir
d'un fichier GEDCOM (.ged).

Le fichier généré embarque l'état GEDCOM brut (pas les statistiques
précalculées) : le moteur JavaScript (templates/gedcom_engine.js) recalcule
tout au chargement, ce qui permet aussi de charger un autre fichier .ged,
d'éditer l'arbre (ajout/modification/suppression) et de le réexporter en
GEDCOM, directement dans le navigateur.

Usage:
    python3 build_dashboard.py chemin/vers/arbre.ged [-o sortie.html]
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

from gedcom_parser import load_gedcom_file, to_raw_json
from gedcom_analyze import find_proband

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(HERE, "templates")


def build(ged_path: str, output_path: str) -> dict:
    data = load_gedcom_file(ged_path)
    raw = to_raw_json(data)

    root = find_proband(data)
    root_name = data.individuals[root].display_name if root in data.individuals else None
    total_individuals = len(data.individuals)
    total_families = len(data.families)

    with open(os.path.join(TEMPLATE_DIR, "dashboard.html.tpl"), "r", encoding="utf-8") as f:
        html = f.read()
    with open(os.path.join(TEMPLATE_DIR, "gedcom_engine.js"), "r", encoding="utf-8") as f:
        engine_js = f.read()
    with open(os.path.join(TEMPLATE_DIR, "app.js"), "r", encoding="utf-8") as f:
        app_js = f.read()

    title_root = root_name or "Arbre généalogique"
    title = f"Registre généalogique — {title_root}"
    subtitle = (
        f"{total_individuals} individus &middot; {total_families} familles &middot; "
        f"analyse générée à partir d'un export GEDCOM"
    )
    source_label = data.header_source or "MyHeritage Family Tree Builder"

    json_str = json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
    json_str = json_str.replace("</", "<\\/")  # évite toute fermeture accidentelle de balise <script>

    generated_at = datetime.datetime.now().isoformat(timespec="seconds")

    html = html.replace("__TITLE__", title)
    html = html.replace("__ROOT_NAME__", title_root)
    html = html.replace("__SUBTITLE__", subtitle)
    html = html.replace("__GENERATED_AT__", generated_at)
    html = html.replace("__SOURCE_LABEL__", f"Source : {source_label}")
    html = html.replace("__RAW_GEDCOM_JSON__", json_str)
    html = html.replace(
        '<script src="app.js"></script>',
        f"<script>\n{engine_js}\n</script>\n<script>\n{app_js}\n</script>",
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return {
        "total_individuals": total_individuals,
        "total_families": total_families,
        "root_name": root_name,
    }


def main():
    parser = argparse.ArgumentParser(description="Génère un dashboard HTML d'analyse généalogique à partir d'un fichier GEDCOM.")
    parser.add_argument("ged_file", help="Chemin du fichier .ged à analyser")
    parser.add_argument("-o", "--output", default="dashboard.html", help="Fichier HTML de sortie (défaut: dashboard.html)")
    args = parser.parse_args()

    if not os.path.isfile(args.ged_file):
        print(f"Fichier introuvable : {args.ged_file}", file=sys.stderr)
        sys.exit(1)

    meta = build(args.ged_file, args.output)
    print(f"OK — {args.output}")
    print(f"  {meta['total_individuals']} individus, {meta['total_families']} familles")
    print(f"  Racine de l'arbre : {meta.get('root_name')}")


if __name__ == "__main__":
    main()
