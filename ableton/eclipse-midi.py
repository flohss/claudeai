# -*- coding: utf-8 -*-
"""Éclipse -> fichier MIDI type 1, une piste par partie, prêt à glisser dans
Ableton Live (ou n'importe quel séquenceur).

Les motifs sont lus tels qu'ils sont écrits dans trance.html : « = » prolonge le
pas précédent, ce qui devient tout naturellement une note MIDI plus longue.

Tout est en ASCII dans les noms : la norme MIDI ne garantit pas l'UTF-8, et un
accent mal lu ferait une piste au nom illisible."""
import io, re, struct

SRC = io.open("/home/user/claudeai/trance.html", encoding="utf-8").read()
bloc = SRC[SRC.index('name: "Éclipse"'):]
bloc = bloc[:bloc.index("\n    },")]

BPM = int(re.search(r"bpm: (\d+)", bloc).group(1))
CHAINE = re.search(r'chain: "(\d+)"', bloc).group(1)
PISTES = []
for m in re.finditer(r'preset: "(\w+)", octave: (\d+), vol: ([\d.]+), pats: \[\s*((?:"[^"]*",?\s*)+)\]', bloc):
    pats = re.findall(r'"([^"]*)"', m.group(4))
    PISTES.append({"preset": m.group(1), "octave": int(m.group(2)),
                   "vol": float(m.group(3)), "pats": pats})
assert len(PISTES) == 5, len(PISTES)

STEPS = 32
TPQ = 480                      # tics par noire
TICK = TPQ // 4                # un pas = une double-croche
LOW = "0123456789abc"
ACC = "ABCDEFGHIJKLM"

def jetons(s):
    return re.findall(r'!?\([0-9a-c]+\)|.', s or "")

def lire(motif):
    """-> liste de 32 pas : None, ou (notes, accent) ; « = » prolonge"""
    out = []
    for j in jetons(motif):
        if len(out) >= STEPS: break
        if j == "-": out.append(None)
        elif j == "=": out.append("tenue")
        elif j.startswith("(") or j.startswith("!("):
            acc = j.startswith("!")
            corps = j[j.index("(") + 1:j.index(")")]
            out.append(([LOW.index(c) for c in corps], acc))
        else:
            k = LOW.find(j)
            if k >= 0: out.append(([k], False))
            else:
                k = ACC.find(j)
                out.append(([k], True) if k >= 0 else None)
    while len(out) < STEPS: out.append(None)
    return out

# batterie : vers les notes du Drum Rack d'Ableton (norme General MIDI)
PERCU = {0: 36, 1: 39, 2: 42, 3: 46, 4: 49}   # GC, clap, charley, charley ouvert, crash
# Nom de piste tel qu'il apparaîtra dans Live, avec l'instrument à y poser.
NOMS = ["Lead - Drift Unison", "Nappe - Drift Unison", "Basse - Drift mono",
        "Pluck - Drift Unison", "Batterie - Drum Rack"]
# Programme General MIDI, pour que le fichier s'écoute tel quel hors DAW.
# Live ignore ces messages à l'import : ils ne gênent rien.
PROG = [81, 89, 38, 98, None]                 # saw lead, pad chaud, basse, cristal

def evenements(piste, idx):
    """-> [(tic_debut, note, velo, duree_tics)] pour toute la chaîne"""
    base = 12 * (piste["octave"] + 1)
    ev = []
    for bloc_i, c in enumerate(CHAINE):
        pas = lire(piste["pats"][int(c)])
        depart = bloc_i * STEPS * TICK
        for s in range(STEPS):
            v = pas[s]
            if v is None or v == "tenue": continue
            notes, acc = v
            # longueur : ce pas plus la suite de pas tenus
            span = 1
            while s + span < STEPS and pas[s + span] == "tenue": span += 1
            duree = span * TICK - 12          # petit blanc pour que les notes se distinguent
            velo = 112 if acc else 88
            for n in notes:
                midi = PERCU.get(n, base + n) if idx == 4 else base + n
                ev.append((depart + s * TICK, midi, velo, max(24, duree if idx != 4 else TICK // 2)))
    return ev

def varlen(n):
    out = bytearray([n & 0x7F]); n >>= 7
    while n: out.insert(0, (n & 0x7F) | 0x80); n >>= 7
    return bytes(out)

def meta(code, charge):
    return b"\xFF" + bytes([code]) + varlen(len(charge)) + charge

def piste_midi(nom, ev, canal, prog):
    data = bytearray()
    data += b"\x00" + meta(0x03, nom.encode("ascii"))
    if prog is not None:
        data += b"\x00" + bytes([0xC0 | canal, prog])
    # on déplie en messages, puis on trie par tic
    msgs = []
    for t, n, v, d in ev:
        msgs.append((t, 1, 0x90 | canal, n, v))
        msgs.append((t + d, 0, 0x80 | canal, n, 0))
    msgs.sort(key=lambda m: (m[0], m[1]))
    prev = 0
    for t, _, st, n, v in msgs:
        data += varlen(t - prev) + bytes([st, n, v])
        prev = t
    data += b"\x00" + meta(0x2F, b"")
    return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)

# piste 0 : tempo, mesure et repères de structure
usec = int(60_000_000 / BPM)
tete = bytearray()
tete += b"\x00" + meta(0x03, b"Eclipse")
tete += b"\x00" + meta(0x51, usec.to_bytes(3, "big"))
tete += b"\x00" + meta(0x58, b"\x04\x02\x18\x08")            # 4/4
prev = 0
for bloc_i, c in enumerate(CHAINE):
    t = bloc_i * STEPS * TICK
    tete += varlen(t - prev) + meta(0x06, ("Motif " + chr(65 + int(c))).encode())
    prev = t
tete += b"\x00" + meta(0x2F, b"")
pistes = [b"MTrk" + struct.pack(">I", len(tete)) + bytes(tete)]

total = 0
for i, p in enumerate(PISTES):
    ev = evenements(p, i)
    total += len(ev)
    canal = 9 if i == 4 else i          # canal 10 (index 9) = percussions
    pistes.append(piste_midi(NOMS[i], ev, canal, PROG[i]))
    print("%-22s %3d notes  octave %d  volume %.2f" % (NOMS[i], len(ev), p["octave"], p["vol"]))

entete = b"MThd" + struct.pack(">IHHH", 6, 1, len(pistes), TPQ)
io.open("Eclipse.mid", "wb").write(entete + b"".join(pistes))
print("\n%d notes au total, %d mesures, %d bpm, structure %s -> Eclipse.mid" %
      (total, len(CHAINE) * 2, BPM, " ".join(chr(65 + int(c)) for c in CHAINE)))
