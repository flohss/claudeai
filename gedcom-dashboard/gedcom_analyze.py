"""
Calcule toutes les statistiques généalogiques (démographie, chronologie,
géographie, structure familiale, patronymes, qualité des données) à partir
des objets produits par gedcom_parser, et prépare une structure JSON
sérialisable destinée au dashboard HTML.
"""

from __future__ import annotations

import datetime
import statistics
from collections import Counter, defaultdict

from gedcom_parser import GedcomData

CURRENT_YEAR = datetime.date.today().year


def _age_years(birth_year, birth_month, birth_day, end_year, end_month, end_day):
    if birth_year is None or end_year is None:
        return None
    age = end_year - birth_year
    bm, bd = birth_month or 1, birth_day or 1
    em, ed = end_month or 1, end_day or 1
    if (em, ed) < (bm, bd):
        age -= 1
    return age


def _place_parts(place: str):
    if not place:
        return []
    return [p.strip() for p in place.split(",") if p.strip()]


def _place_country(place: str):
    parts = _place_parts(place)
    return parts[-1] if parts else None


def _place_region(place: str):
    parts = _place_parts(place)
    if len(parts) >= 2:
        return parts[-2]
    return parts[-1] if parts else None


def _place_locality(place: str):
    parts = _place_parts(place)
    return parts[0] if parts else None


def find_proband(data: GedcomData):
    """Choisit un individu racine pour la numérotation des générations.

    Priorité : l'auteur/propriétaire de l'arbre s'il est identifiable dans
    l'en-tête GEDCOM (source avec AUTH) et présent parmi les individus ;
    sinon le premier individu disposant d'une famille parentale connue."""
    if data.header_author:
        target = set(data.header_author.upper().split())
        best, best_score = None, 0
        for xref, ind in data.individuals.items():
            tokens = set(f"{ind.given} {ind.surname}".upper().split())
            score = len(tokens & target)
            if score > best_score and score >= 2:
                best, best_score = xref, score
        if best:
            return best
    for xref, ind in data.individuals.items():
        if ind.famc:
            return xref
    return next(iter(data.individuals), None)


def compute_generations(data: GedcomData, root: str):
    generation = {}
    if root is None:
        return generation, []
    components = []
    visited_global = set()

    all_ids = list(data.individuals.keys())
    start_nodes = [root] + [x for x in all_ids if x != root]

    for start in start_nodes:
        if start in visited_global:
            continue
        comp_gen = {start: 0}
        queue = [start]
        head = 0
        while head < len(queue):
            cur = queue[head]
            head += 1
            gen = comp_gen[cur]
            ind = data.individuals.get(cur)
            if ind is None:
                continue
            for famc_id in ind.famc:
                fam = data.families.get(famc_id)
                if not fam:
                    continue
                for parent in (fam.husb, fam.wife):
                    if parent and parent not in comp_gen:
                        comp_gen[parent] = gen - 1
                        queue.append(parent)
            for fams_id in ind.fams:
                fam = data.families.get(fams_id)
                if not fam:
                    continue
                spouse = fam.wife if fam.husb == cur else fam.husb
                if spouse and spouse not in comp_gen:
                    comp_gen[spouse] = gen
                    queue.append(spouse)
                for child_id in fam.chil:
                    if child_id not in comp_gen:
                        comp_gen[child_id] = gen + 1
                        queue.append(child_id)
        visited_global |= set(comp_gen.keys())
        components.append(set(comp_gen.keys()))
        generation.update(comp_gen)

    return generation, components


def analyze(data: GedcomData) -> dict:
    individuals = data.individuals
    families = data.families

    root = find_proband(data)
    generation, components = compute_generations(data, root)

    # --- enrich individuals with computed relationships -------------------
    children_of = defaultdict(list)   # xref -> list of child xrefs (via any FAMS)
    parents_of = defaultdict(list)    # xref -> list of parent xrefs (via FAMC)
    spouses_of = defaultdict(list)    # xref -> list of spouse xrefs

    for fam in families.values():
        parents = [p for p in (fam.husb, fam.wife) if p]
        for p in parents:
            for c in fam.chil:
                children_of[p].append(c)
        for c in fam.chil:
            parents_of[c].extend(parents)
        if fam.husb and fam.wife:
            spouses_of[fam.husb].append(fam.wife)
            spouses_of[fam.wife].append(fam.husb)

    siblings_of = defaultdict(set)
    for fam in families.values():
        for c in fam.chil:
            for c2 in fam.chil:
                if c2 != c:
                    siblings_of[c].add(c2)

    ind_records = []
    ages_at_death = []
    alive_records = []
    deceased_count = 0

    for xref, ind in individuals.items():
        by, bm, bd = (ind.birth.date.year, ind.birth.date.month, ind.birth.date.day) if ind.birth.date else (None, None, None)
        dy, dm, dd = (ind.death.date.year, ind.death.date.month, ind.death.date.day) if ind.death.date else (None, None, None)

        age_at_death = None
        if ind.death.known:
            deceased_count += 1
            if by is not None and dy is not None:
                age_at_death = _age_years(by, bm, bd, dy, dm, dd)
                if age_at_death is not None and 0 <= age_at_death <= 115:
                    ages_at_death.append(age_at_death)
                else:
                    age_at_death = None

        is_alive = not ind.death.known and (by is None or (CURRENT_YEAR - by) < 100)
        current_age = None
        if is_alive and by is not None:
            current_age = CURRENT_YEAR - by
            alive_records.append((xref, current_age))

        rec = {
            "id": xref,
            "given": ind.given,
            "surname": ind.surname,
            "name": ind.display_name,
            "sex": ind.sex if ind.sex in ("M", "F") else "U",
            "birth": {
                "year": by, "month": bm, "day": bd,
                "display": ind.birth.date.to_display() if ind.birth.date else None,
                "place": ind.birth.place,
                "known": ind.birth.known,
            },
            "death": {
                "year": dy, "month": dm, "day": dd,
                "display": ind.death.date.to_display() if ind.death.date else None,
                "place": ind.death.place,
                "cause": ind.death.cause,
                "known": ind.death.known,
            },
            "age_at_death": age_at_death,
            "current_age": current_age,
            "alive": is_alive,
            "occupation": ind.occupation,
            "generation": generation.get(xref),
            "parents": sorted(set(parents_of.get(xref, []))),
            "children": sorted(set(children_of.get(xref, []))),
            "siblings": sorted(siblings_of.get(xref, [])),
            "spouses": sorted(set(spouses_of.get(xref, []))),
            "famc": ind.famc,
            "fams": ind.fams,
        }
        ind_records.append(rec)

    ind_by_id = {r["id"]: r for r in ind_records}

    fam_records = []
    remarriage_people = Counter()
    for xref, fam in families.items():
        husb = ind_by_id.get(fam.husb)
        wife = ind_by_id.get(fam.wife)
        m_year = fam.marriage.date.year if fam.marriage.date else None

        age_husb = None
        age_wife = None
        if m_year:
            if husb and husb["birth"]["year"]:
                age_husb = m_year - husb["birth"]["year"]
            if wife and wife["birth"]["year"]:
                age_wife = m_year - wife["birth"]["year"]

        age_gap = None
        if husb and wife and husb["birth"]["year"] and wife["birth"]["year"]:
            age_gap = husb["birth"]["year"] - wife["birth"]["year"]

        fam_records.append({
            "id": xref,
            "husb": fam.husb,
            "wife": fam.wife,
            "husb_name": husb["name"] if husb else None,
            "wife_name": wife["name"] if wife else None,
            "children": fam.chil,
            "n_children": len(fam.chil),
            "marriage": {
                "year": m_year,
                "display": fam.marriage.date.to_display() if fam.marriage.date else None,
                "place": fam.marriage.place,
                "known": fam.marriage.known,
            },
            "divorced": fam.divorced,
            "age_husb_at_marriage": age_husb,
            "age_wife_at_marriage": age_wife,
            "spouse_age_gap": age_gap,
        })
        if fam.husb:
            remarriage_people[fam.husb] += 1
        if fam.wife:
            remarriage_people[fam.wife] += 1

    # ------------------------------------------------------------------ #
    # 2. Démographie
    # ------------------------------------------------------------------ #
    total = len(ind_records)
    sex_counts = Counter(r["sex"] for r in ind_records)
    gen_counts = Counter(r["generation"] for r in ind_records if r["generation"] is not None)

    def century_bucket(age):
        return None

    age_periods = Counter()
    for r in ind_records:
        if r["age_at_death"] is not None and r["death"]["year"]:
            century = ((r["death"]["year"] - 1) // 100 + 1)
            age_periods[century] += 0  # placeholder, replaced below

    age_by_century = defaultdict(list)
    for r in ind_records:
        if r["age_at_death"] is not None and r["death"]["year"]:
            century = (r["death"]["year"] - 1) // 100 + 1
            age_by_century[century].append(r["age_at_death"])

    age_distribution_by_century = {
        str(c): {
            "count": len(v),
            "mean": round(statistics.mean(v), 1),
            "median": statistics.median(v),
        } for c, v in sorted(age_by_century.items())
    }

    pyramid_bins = list(range(0, 101, 10))
    pyramid = {b: {"M": 0, "F": 0} for b in pyramid_bins}
    for r in ind_records:
        age = r["age_at_death"] if r["age_at_death"] is not None else r["current_age"]
        if age is None or r["sex"] not in ("M", "F"):
            continue
        b = min((age // 10) * 10, 100)
        pyramid[b][r["sex"]] += 1
    age_pyramid = [{"band": f"{b}-{b+9}" if b < 100 else "100+", "M": v["M"], "F": v["F"]}
                   for b, v in sorted(pyramid.items())]

    oldest_living = max(alive_records, key=lambda t: t[1]) if alive_records else None
    oldest_death = max(
        (r for r in ind_records if r["age_at_death"] is not None),
        key=lambda r: r["age_at_death"], default=None,
    )
    youngest_death = min(
        (r for r in ind_records if r["age_at_death"] is not None),
        key=lambda r: r["age_at_death"], default=None,
    )

    demographics = {
        "total_individuals": total,
        "sex_counts": {"M": sex_counts.get("M", 0), "F": sex_counts.get("F", 0), "U": sex_counts.get("U", 0)},
        "generation_counts": {str(k): v for k, v in sorted(gen_counts.items())},
        "age_at_death": {
            "count": len(ages_at_death),
            "mean": round(statistics.mean(ages_at_death), 1) if ages_at_death else None,
            "median": statistics.median(ages_at_death) if ages_at_death else None,
            "min": min(ages_at_death) if ages_at_death else None,
            "max": max(ages_at_death) if ages_at_death else None,
            "distribution_by_century": age_distribution_by_century,
            "histogram": _histogram(ages_at_death, bin_size=10, max_val=110),
        },
        "alive_count": sum(1 for r in ind_records if r["alive"]),
        "deceased_count": deceased_count,
        "unknown_status_count": total - deceased_count - sum(1 for r in ind_records if r["alive"]),
        "age_pyramid": age_pyramid,
        "oldest_living": ({"id": oldest_living[0], "name": ind_by_id[oldest_living[0]]["name"], "age": oldest_living[1]}
                           if oldest_living else None),
        "oldest_at_death": ({"id": oldest_death["id"], "name": oldest_death["name"], "age": oldest_death["age_at_death"],
                              "date": oldest_death["death"]["display"]} if oldest_death else None),
        "youngest_at_death": ({"id": youngest_death["id"], "name": youngest_death["name"], "age": youngest_death["age_at_death"],
                                "date": youngest_death["death"]["display"]} if youngest_death else None),
    }

    # ------------------------------------------------------------------ #
    # 3. Chronologie
    # ------------------------------------------------------------------ #
    def decade_counter(years):
        c = Counter()
        for y in years:
            if y is not None:
                c[(y // 10) * 10] += 1
        return dict(sorted(c.items()))

    birth_years = [r["birth"]["year"] for r in ind_records if r["birth"]["year"]]
    death_years = [r["death"]["year"] for r in ind_records if r["death"]["year"]]
    marriage_years = [f["marriage"]["year"] for f in fam_records if f["marriage"]["year"]]

    gaps = []
    for r in ind_records:
        by = r["birth"]["year"]
        if not by:
            continue
        for pid in r["parents"]:
            p = ind_by_id.get(pid)
            if p and p["birth"]["year"]:
                gap = by - p["birth"]["year"]
                if 10 <= gap <= 70:
                    gaps.append(gap)

    known_gens = [g for g in generation.values() if g is not None]

    gen_year_range = defaultdict(list)
    for r in ind_records:
        if r["generation"] is not None and r["birth"]["year"]:
            gen_year_range[r["generation"]].append(r["birth"]["year"])
    generation_timeline = [
        {"generation": g, "min_year": min(v), "max_year": max(v), "count": len(v)}
        for g, v in sorted(gen_year_range.items())
    ]

    chronology = {
        "births_by_decade": decade_counter(birth_years),
        "marriages_by_decade": decade_counter(marriage_years),
        "deaths_by_decade": decade_counter(death_years),
        "earliest_birth_year": min(birth_years) if birth_years else None,
        "latest_birth_year": max(birth_years) if birth_years else None,
        "tree_depth_generations": (max(known_gens) - min(known_gens) + 1) if known_gens else 0,
        "oldest_generation": min(known_gens) if known_gens else None,
        "youngest_generation": max(known_gens) if known_gens else None,
        "avg_generational_gap": round(statistics.mean(gaps), 1) if gaps else None,
        "generational_gap_sample_size": len(gaps),
        "generation_timeline": generation_timeline,
    }

    # ------------------------------------------------------------------ #
    # 4. Géographie
    # ------------------------------------------------------------------ #
    birth_places = Counter(r["birth"]["place"] for r in ind_records if r["birth"]["place"])
    death_places = Counter(r["death"]["place"] for r in ind_records if r["death"]["place"])
    marriage_places = Counter(f["marriage"]["place"] for f in fam_records if f["marriage"]["place"])

    birth_regions = Counter(_place_region(r["birth"]["place"]) for r in ind_records if r["birth"]["place"])
    birth_countries = Counter(_place_country(r["birth"]["place"]) for r in ind_records if r["birth"]["place"])

    migrations = []
    migration_count = 0
    for r in ind_records:
        bp, dp = r["birth"]["place"], r["death"]["place"]
        if bp and dp:
            b_region, d_region = _place_region(bp), _place_region(dp)
            if b_region and d_region and b_region != d_region:
                migration_count += 1
                if len(migrations) < 60:
                    migrations.append({
                        "id": r["id"], "name": r["name"],
                        "from": bp, "to": dp,
                    })

    geography = {
        "birth_places_top": birth_places.most_common(20),
        "death_places_top": death_places.most_common(20),
        "marriage_places_top": marriage_places.most_common(20),
        "birth_regions_top": [ (k, v) for k, v in birth_regions.most_common(15) if k],
        "birth_countries_top": [ (k, v) for k, v in birth_countries.most_common(10) if k],
        "migrations_count": migration_count,
        "migrations_sample": migrations,
        "concentration_zones": [(k, v) for k, v in birth_regions.most_common(8) if k],
    }

    # ------------------------------------------------------------------ #
    # 5. Structure familiale
    # ------------------------------------------------------------------ #
    sibling_sizes = [f["n_children"] for f in fam_records if f["n_children"] > 0]
    large_families = [f for f in fam_records if f["n_children"] >= 5]

    ages_husb = [f["age_husb_at_marriage"] for f in fam_records if f["age_husb_at_marriage"] is not None and 10 <= f["age_husb_at_marriage"] <= 90]
    ages_wife = [f["age_wife_at_marriage"] for f in fam_records if f["age_wife_at_marriage"] is not None and 10 <= f["age_wife_at_marriage"] <= 90]
    all_marriage_ages = ages_husb + ages_wife
    age_gaps = [abs(f["spouse_age_gap"]) for f in fam_records if f["spouse_age_gap"] is not None and abs(f["spouse_age_gap"]) <= 40]

    remarried = [(pid, cnt) for pid, cnt in remarriage_people.items() if cnt > 1]
    remarried_details = [{"id": pid, "name": ind_by_id[pid]["name"], "n_unions": cnt}
                          for pid, cnt in remarried if pid in ind_by_id]

    family_structure = {
        "total_families": len(fam_records),
        "avg_children_per_family": round(statistics.mean(sibling_sizes), 2) if sibling_sizes else None,
        "median_children_per_family": statistics.median(sibling_sizes) if sibling_sizes else None,
        "large_families_count": len(large_families),
        "large_families_sample": [{"id": f["id"], "husb": f["husb_name"], "wife": f["wife_name"],
                                    "husb_id": f["husb"], "wife_id": f["wife"], "n_children": f["n_children"]}
                                   for f in sorted(large_families, key=lambda x: -x["n_children"])[:15]],
        "avg_age_at_marriage": round(statistics.mean(all_marriage_ages), 1) if all_marriage_ages else None,
        "avg_age_at_marriage_husb": round(statistics.mean(ages_husb), 1) if ages_husb else None,
        "avg_age_at_marriage_wife": round(statistics.mean(ages_wife), 1) if ages_wife else None,
        "avg_spouse_age_gap": round(statistics.mean(age_gaps), 1) if age_gaps else None,
        "remarriages_count": len(remarried_details),
        "remarriages_sample": sorted(remarried_details, key=lambda x: -x["n_unions"])[:20],
        "divorced_families": sum(1 for f in fam_records if f["divorced"]),
    }

    # ------------------------------------------------------------------ #
    # 6. Patronymes
    # ------------------------------------------------------------------ #
    # Les noms de famille peuvent apparaître avec une casse différente selon
    # les fiches (ex. "SCHAEFFER" / "Schaeffer") : on regroupe par forme
    # normalisée (majuscules) tout en affichant la graphie la plus fréquente.
    surname_casing = defaultdict(Counter)
    for r in ind_records:
        if r["surname"]:
            surname_casing[r["surname"].strip().upper()][r["surname"].strip()] += 1
    surname_canonical = {key: variants.most_common(1)[0][0] for key, variants in surname_casing.items()}

    surname_counts = Counter()
    for r in ind_records:
        if r["surname"]:
            key = r["surname"].strip().upper()
            surname_counts[surname_canonical[key]] += 1

    surname_by_period = defaultdict(Counter)
    for r in ind_records:
        if r["surname"] and r["birth"]["year"]:
            period = (r["birth"]["year"] // 50) * 50
            key = r["surname"].strip().upper()
            surname_by_period[period][surname_canonical[key]] += 1

    surname_evolution = {
        str(period): counter.most_common(5)
        for period, counter in sorted(surname_by_period.items())
    }

    surnames = {
        "total_distinct": len(surname_counts),
        "top_surnames": surname_counts.most_common(25),
        "evolution_by_period": surname_evolution,
    }

    # ------------------------------------------------------------------ #
    # 7. Qualité des données
    # ------------------------------------------------------------------ #
    anomalies = []
    for r in ind_records:
        by, dy = r["birth"]["year"], r["death"]["year"]
        if by and not r["death"]["known"] and (CURRENT_YEAR - by) >= 100:
            anomalies.append({"type": "deces_manquant_probable", "id": r["id"], "name": r["name"],
                               "detail": f"Né(e) en {by} (aurait {CURRENT_YEAR - by} ans), aucun décès enregistré"})
        if by and dy and dy < by:
            anomalies.append({"type": "deces_avant_naissance", "id": r["id"], "name": r["name"],
                               "detail": f"Naissance {by}, décès {dy}"})
        if by and dy and (dy - by) > 115:
            anomalies.append({"type": "age_deces_invraisemblable", "id": r["id"], "name": r["name"],
                               "detail": f"Âge au décès: {dy - by} ans"})
        for pid in r["parents"]:
            p = ind_by_id.get(pid)
            if p and p["birth"]["year"] and by:
                gap = by - p["birth"]["year"]
                if gap < 0:
                    anomalies.append({"type": "enfant_avant_parent", "id": r["id"], "name": r["name"],
                                       "detail": f"Né(e) en {by}, avant la naissance de {p['name']} ({p['birth']['year']})"})
                elif gap < 10:
                    anomalies.append({"type": "parent_trop_jeune", "id": r["id"], "name": r["name"],
                                       "detail": f"{p['name']} n'avait que {gap} ans à sa naissance"})
                elif gap > 65:
                    anomalies.append({"type": "parent_trop_age", "id": r["id"], "name": r["name"],
                                       "detail": f"{p['name']} avait {gap} ans à sa naissance"})
    for f in fam_records:
        if f["marriage"]["year"]:
            for role, age in (("époux", f["age_husb_at_marriage"]), ("épouse", f["age_wife_at_marriage"])):
                if age is not None and age < 12:
                    anomalies.append({"type": "mariage_trop_jeune", "id": f["id"], "name": f"{f['husb_name']} × {f['wife_name']}",
                                       "detail": f"{role} âgé(e) de {age} ans au mariage"})

    completeness_fields = {
        "date_naissance": sum(1 for r in ind_records if r["birth"]["year"]) / total if total else 0,
        "lieu_naissance": sum(1 for r in ind_records if r["birth"]["place"]) / total if total else 0,
        "date_deces": sum(1 for r in ind_records if r["death"]["known"] and r["death"]["year"]) / deceased_count if deceased_count else 0,
        "lieu_deces": sum(1 for r in ind_records if r["death"]["known"] and r["death"]["place"]) / deceased_count if deceased_count else 0,
        "sexe_connu": sum(1 for r in ind_records if r["sex"] in ("M", "F")) / total if total else 0,
        "famille_parentale_connue": sum(1 for r in ind_records if r["parents"]) / total if total else 0,
    }

    # doublons potentiels : même nom complet + même année de naissance (ou proche)
    dup_map = defaultdict(list)
    for r in ind_records:
        key = (r["given"].strip().lower(), r["surname"].strip().lower(), r["birth"]["year"])
        if key[0] and key[1]:
            dup_map[key].append(r["id"])
    duplicates = [{"name": f"{k[0].title()} {k[1].title()}", "year": k[2], "ids": v}
                  for k, v in dup_map.items() if len(v) > 1]

    quality = {
        "anomalies_count": len(anomalies),
        "anomalies": anomalies[:200],
        "completeness": {k: round(v * 100, 1) for k, v in completeness_fields.items()},
        "duplicates_count": len(duplicates),
        "duplicates": duplicates[:50],
    }

    return {
        "meta": {
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "total_individuals": total,
            "total_families": len(fam_records),
            "source_label": data.header_source,
            "root_individual": root,
            "root_name": ind_by_id[root]["name"] if root in ind_by_id else None,
        },
        "individuals": ind_records,
        "families": fam_records,
        "stats": {
            "demographics": demographics,
            "chronology": chronology,
            "geography": geography,
            "family_structure": family_structure,
            "surnames": surnames,
            "quality": quality,
        },
    }


def _histogram(values, bin_size=10, max_val=110):
    bins = list(range(0, max_val + bin_size, bin_size))
    counts = [0] * (len(bins) - 1)
    for v in values:
        idx = min(v // bin_size, len(counts) - 1)
        counts[idx] += 1
    return [{"range": f"{bins[i]}-{bins[i+1]-1}", "count": counts[i]} for i in range(len(counts))]
