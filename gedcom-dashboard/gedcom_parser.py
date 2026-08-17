"""
Parseur GEDCOM (5.5.x) minimal mais robuste, orienté analyse généalogique.

Ne dépend que de la bibliothèque standard. Construit un arbre de lignes
(niveau, tag, valeur, pointeur) puis assemble les enregistrements INDI et
FAM en objets Python exploitables par le module d'analyse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


MONTHS_FR = {
    "JAN": 1, "FEV": 2, "FEB": 2, "MAR": 3, "AVR": 4, "APR": 4, "MAI": 5, "MAY": 5,
    "JUN": 6, "JUIN": 6, "JUL": 7, "JUIL": 7, "AOU": 8, "AUG": 8, "SEP": 9,
    "OCT": 10, "NOV": 11, "DEC": 12,
}

DATE_PREFIXES = {"ABT", "BEF", "AFT", "EST", "CAL", "BET", "FROM", "TO", "AND"}


@dataclass
class GedDate:
    """Date GEDCOM normalisée, en conservant l'incertitude d'origine."""
    raw: str
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    qualifier: Optional[str] = None  # ABT, BEF, AFT, EST, CAL, BET, FROM
    year2: Optional[int] = None      # borne haute pour BET..AND.. / FROM..TO..

    @property
    def known(self) -> bool:
        return self.year is not None

    @property
    def precise(self) -> bool:
        """Jour/mois/année complets et sans qualificatif d'incertitude."""
        return self.known and self.day is not None and self.month is not None and self.qualifier is None

    @property
    def sort_key(self) -> float:
        if self.year is None:
            return float("inf")
        m = self.month or 1
        d = self.day or 1
        return self.year * 372 + m * 31 + d

    @property
    def decade(self) -> Optional[int]:
        if self.year is None:
            return None
        return (self.year // 10) * 10

    @property
    def century(self) -> Optional[int]:
        if self.year is None:
            return None
        return (self.year - 1) // 100 + 1

    def to_display(self) -> str:
        if self.year is None:
            return self.raw or "?"
        parts = []
        if self.day and self.month:
            parts.append(f"{self.day:02d}/{self.month:02d}/{self.year}")
        elif self.month:
            parts.append(f"{self.month:02d}/{self.year}")
        else:
            parts.append(str(self.year))
        prefix = {
            "ABT": "vers ", "EST": "vers (est.) ", "CAL": "calculé ",
            "BEF": "avant ", "AFT": "après ", "BET": "entre ", "FROM": "de ",
        }.get(self.qualifier or "", "")
        txt = prefix + parts[0]
        if self.qualifier in ("BET", "FROM") and self.year2:
            txt += f" et {self.year2}"
        return txt


def parse_gedcom_date(raw: Optional[str]) -> Optional[GedDate]:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None

    tokens = raw.upper().replace(",", " ").split()
    qualifier = None
    if tokens and tokens[0] in ("ABT", "BEF", "AFT", "EST", "CAL", "FROM"):
        qualifier = tokens[0]
        tokens = tokens[1:]
    elif tokens and tokens[0] == "BET":
        qualifier = "BET"
        tokens = tokens[1:]

    year2 = None
    if qualifier in ("BET", "FROM") and "AND" in tokens:
        idx = tokens.index("AND")
        tail = tokens[idx + 1:]
        tokens = tokens[:idx]
        y2 = next((int(t) for t in tail if t.isdigit() and len(t) == 4), None)
        year2 = y2
    elif qualifier == "FROM" and "TO" in tokens:
        idx = tokens.index("TO")
        tail = tokens[idx + 1:]
        tokens = tokens[:idx]
        y2 = next((int(t) for t in tail if t.isdigit() and len(t) == 4), None)
        year2 = y2

    day = month = year = None
    for tok in tokens:
        if tok in MONTHS_FR:
            month = MONTHS_FR[tok]
        elif re.fullmatch(r"\d{3,4}", tok):
            year = int(tok)
        elif re.fullmatch(r"\d{1,2}", tok):
            day = int(tok)

    if year is None:
        return GedDate(raw=raw, qualifier=qualifier)

    return GedDate(raw=raw, year=year, month=month, day=day, qualifier=qualifier, year2=year2)


@dataclass
class Event:
    date: Optional[GedDate] = None
    place: Optional[str] = None
    cause: Optional[str] = None
    known: bool = False  # événement mentionné même sans date/lieu (ex: DEAT Y)
    # Lignes GEDCOM brutes non interprétées (SOUR, NOTE, TYPE…) rattachées à
    # cet événement, conservées telles quelles pour ne rien perdre à l'export.
    extra_lines: list = field(default_factory=list)


@dataclass
class Individual:
    xref: str
    given: str = ""
    surname: str = ""
    full_name: str = ""
    sex: str = "U"
    birth: Event = field(default_factory=Event)
    death: Event = field(default_factory=Event)
    occupation: Optional[str] = None
    fams: list = field(default_factory=list)   # familles où il/elle est conjoint
    famc: list = field(default_factory=list)   # familles où il/elle est enfant
    # Blocs GEDCOM bruts non interprétés (NOTE, SOUR, RIN, _UID…) rattachés à
    # cette fiche, conservés tels quels pour ne rien perdre à l'export.
    extra_lines: list = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.full_name or f"{self.given} {self.surname}".strip() or "(nom non renseigné)"

    @property
    def is_deceased(self) -> bool:
        return self.death.known


@dataclass
class Family:
    xref: str
    husb: Optional[str] = None
    wife: Optional[str] = None
    chil: list = field(default_factory=list)
    marriage: Event = field(default_factory=Event)
    divorced: bool = False
    extra_lines: list = field(default_factory=list)


@dataclass
class GedcomData:
    individuals: dict
    families: dict
    header_source: Optional[str] = None
    header_author: Optional[str] = None
    # Enregistrements de niveau 0 non gérés (SOUR, OBJE, REPO, SUBM…),
    # conservés verbatim (chaque élément est le bloc multi-lignes complet)
    # afin que les références (ex. "1 SOUR @S1@" sur un individu) restent
    # valides après un export.
    other_records: list = field(default_factory=list)


def _tokenize(text: str):
    """Retourne une liste de tuples (niveau, pointeur, tag, valeur, ligne_brute).

    La ligne brute est conservée telle quelle (hors retour à la ligne) pour
    permettre de repasser en revue les blocs non interprétés sans perte de
    fidélité (accents, ponctuation, espacement interne...)."""
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r\n")
        if not line.strip():
            continue
        m = re.match(r"^(\d+)\s+(@[^@]+@)?\s*([A-Za-z0-9_]+)\s?(.*)$", line)
        if not m:
            continue
        level = int(m.group(1))
        xref = m.group(2)
        tag = m.group(3)
        value = m.group(4)
        lines.append((level, xref, tag, value, line))
    return lines


def parse_gedcom(text: str) -> GedcomData:
    lines = _tokenize(text)

    individuals: dict[str, Individual] = {}
    families: dict[str, Family] = {}
    other_records: list = []
    header_source = None
    header_author = None

    i = 0
    n = len(lines)
    while i < n:
        level, xref, tag, value, _raw = lines[i]

        if level == 0 and tag == "INDI" and xref:
            ind = Individual(xref=xref)
            i += 1
            # Mode courant du bloc de niveau 1 en cours (BIRT/DEAT ont un
            # objet Event associé ; UNHANDLED capture tout bloc non géré
            # verbatim, y compris ses descendants, pour ne rien perdre.
            top_mode = None
            event_obj = None
            event_sub_unhandled = False
            while i < n and lines[i][0] > 0:
                lv, lxref, ltag, lval, lraw = lines[i]
                if lv == 1:
                    event_sub_unhandled = False
                    if ltag == "NAME":
                        ind.full_name = lval.replace("/", "").strip()
                        m = re.match(r"^(.*?)/(.*)/", lval)
                        if m:
                            ind.given = m.group(1).strip()
                            ind.surname = m.group(2).strip()
                        else:
                            ind.given = lval.strip()
                        top_mode = "NAME"
                    elif ltag == "SEX":
                        ind.sex = lval.strip()[:1] or "U"
                        top_mode = "SEX"
                    elif ltag == "BIRT":
                        ind.birth.known = True
                        top_mode, event_obj = "BIRT", ind.birth
                    elif ltag == "DEAT":
                        ind.death.known = True
                        top_mode, event_obj = "DEAT", ind.death
                    elif ltag == "OCCU":
                        ind.occupation = lval.strip()
                        top_mode = "OCCU"
                    elif ltag == "FAMS":
                        ind.fams.append(lval.strip())
                        top_mode = "FAMS"
                    elif ltag == "FAMC":
                        ind.famc.append(lval.strip())
                        top_mode = "FAMC"
                    else:
                        top_mode = "UNHANDLED"
                        ind.extra_lines.append(lraw)
                elif lv == 2:
                    if top_mode in ("BIRT", "DEAT") and event_obj is not None:
                        if ltag == "DATE":
                            event_obj.date = parse_gedcom_date(lval)
                        elif ltag == "PLAC":
                            event_obj.place = lval.strip() or None
                        elif ltag == "CAUS":
                            event_obj.cause = lval.strip() or None
                        else:
                            event_obj.extra_lines.append(lraw)
                            event_sub_unhandled = True
                    elif top_mode == "UNHANDLED":
                        ind.extra_lines.append(lraw)
                else:  # lv >= 3
                    if top_mode in ("BIRT", "DEAT") and event_sub_unhandled and event_obj is not None:
                        event_obj.extra_lines.append(lraw)
                    elif top_mode == "UNHANDLED":
                        ind.extra_lines.append(lraw)
                i += 1
            individuals[xref] = ind
            continue

        if level == 0 and tag == "FAM" and xref:
            fam = Family(xref=xref)
            i += 1
            top_mode = None
            event_sub_unhandled = False
            while i < n and lines[i][0] > 0:
                lv, lxref, ltag, lval, lraw = lines[i]
                if lv == 1:
                    event_sub_unhandled = False
                    if ltag == "HUSB":
                        fam.husb = lval.strip()
                        top_mode = "HUSB"
                    elif ltag == "WIFE":
                        fam.wife = lval.strip()
                        top_mode = "WIFE"
                    elif ltag == "CHIL":
                        fam.chil.append(lval.strip())
                        top_mode = "CHIL"
                    elif ltag == "MARR":
                        fam.marriage.known = True
                        top_mode = "MARR"
                    elif ltag == "DIV":
                        fam.divorced = True
                        top_mode = "DIV"
                    else:
                        top_mode = "UNHANDLED"
                        fam.extra_lines.append(lraw)
                elif lv == 2:
                    if top_mode == "MARR":
                        if ltag == "DATE":
                            fam.marriage.date = parse_gedcom_date(lval)
                        elif ltag == "PLAC":
                            fam.marriage.place = lval.strip() or None
                        else:
                            fam.marriage.extra_lines.append(lraw)
                            event_sub_unhandled = True
                    elif top_mode == "UNHANDLED":
                        fam.extra_lines.append(lraw)
                else:  # lv >= 3
                    if top_mode == "MARR" and event_sub_unhandled:
                        fam.marriage.extra_lines.append(lraw)
                    elif top_mode == "UNHANDLED":
                        fam.extra_lines.append(lraw)
                i += 1
            families[xref] = fam
            continue

        if level == 0 and tag not in ("HEAD", "TRLR"):
            # Enregistrement de niveau 0 non géré (SOUR, OBJE, REPO, SUBM…) :
            # conservé verbatim pour que les références depuis les fiches
            # (ex. "1 SOUR @S1@") restent valides après un export.
            start = i
            i += 1
            while i < n and lines[i][0] > 0:
                lv, lxref, ltag, lval, lraw = lines[i]
                if tag == "SOUR":
                    if lv == 2 and ltag == "NAME" and header_source is None:
                        header_source = lval.strip()
                    if lv == 1 and ltag == "AUTH" and header_author is None:
                        header_author = lval.strip()
                i += 1
            other_records.append("\n".join(l[4] for l in lines[start:i]))
            continue

        i += 1

    return GedcomData(
        individuals=individuals, families=families,
        header_source=header_source, header_author=header_author,
        other_records=other_records,
    )


def load_gedcom_file(path: str) -> GedcomData:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        text = f.read()
    return parse_gedcom(text)


def _date_to_dict(d: Optional[GedDate]) -> Optional[dict]:
    if d is None:
        return None
    return {"raw": d.raw, "year": d.year, "month": d.month, "day": d.day, "qualifier": d.qualifier, "year2": d.year2}


def to_raw_json(data: GedcomData) -> dict:
    """Sérialise l'état parsé (non analysé) dans la forme attendue par le
    moteur JavaScript côté navigateur (gedcom_engine.js), qui recalcule
    ensuite toutes les statistiques et gère les éditions en direct."""
    individuals = {}
    for xref, ind in data.individuals.items():
        individuals[xref] = {
            "given": ind.given, "surname": ind.surname, "full_name": ind.full_name, "sex": ind.sex,
            "birth": {"date": _date_to_dict(ind.birth.date), "place": ind.birth.place, "known": ind.birth.known,
                      "extra_lines": ind.birth.extra_lines},
            "death": {"date": _date_to_dict(ind.death.date), "place": ind.death.place,
                      "cause": ind.death.cause, "known": ind.death.known, "extra_lines": ind.death.extra_lines},
            "occupation": ind.occupation, "fams": ind.fams, "famc": ind.famc,
            "extra_lines": ind.extra_lines,
        }
    families = {}
    for xref, fam in data.families.items():
        families[xref] = {
            "husb": fam.husb, "wife": fam.wife, "chil": fam.chil,
            "marriage": {"date": _date_to_dict(fam.marriage.date), "place": fam.marriage.place,
                         "known": fam.marriage.known, "extra_lines": fam.marriage.extra_lines},
            "divorced": fam.divorced,
            "extra_lines": fam.extra_lines,
        }
    return {
        "individuals": individuals, "families": families,
        "header_source": data.header_source, "header_author": data.header_author,
        "other_records": data.other_records,
    }
