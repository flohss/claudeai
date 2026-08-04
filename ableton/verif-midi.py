# -*- coding: utf-8 -*-
"""Relit Eclipse.mid sans rien supposer de la façon dont il a été écrit."""
import io, struct
d = io.open("Eclipse.mid", "rb").read()
assert d[:4] == b"MThd", "en-tête absent"
lg, fmt, npistes, tpq = struct.unpack(">IHHH", d[4:14])
print("format %d, %d pistes, %d tics par noire, %d octets" % (fmt, npistes, tpq, len(d)))

pos = 8 + lg
NOMS_NOTES = ["Do","Do#","Ré","Ré#","Mi","Fa","Fa#","Sol","Sol#","La","La#","Si"]
def nom(n): return "%s%d" % (NOMS_NOTES[n % 12], n // 12 - 1)

res, souci, reperes, fin = [], [], [], 0
for p in range(npistes):
    assert d[pos:pos+4] == b"MTrk", "piste %d mal formée" % p
    taille = struct.unpack(">I", d[pos+4:pos+8])[0]
    corps, pos = d[pos+8:pos+8+taille], pos+8+taille
    i, t, titre, notes, ouvertes, tempo = 0, 0, "", [], {}, None
    statut, prog, canaux = None, None, set()
    while i < len(corps):
        dt = 0
        while True:
            b = corps[i]; i += 1
            dt = (dt << 7) | (b & 0x7F)
            if not (b & 0x80): break
        t += dt
        st = corps[i]
        if st < 0x80: st = statut          # statut courant
        else: i += 1; statut = st
        if st == 0xFF:
            typ = corps[i]; i += 1
            n = 0
            while True:
                b = corps[i]; i += 1
                n = (n << 7) | (b & 0x7F)
                if not (b & 0x80): break
            val = corps[i:i+n]; i += n
            if typ == 0x03: titre = val.decode("ascii")
            if typ == 0x06: reperes.append((t, val.decode("ascii")))
            if typ == 0x51: tempo = int.from_bytes(val, "big")
        elif (st & 0xF0) in (0x90, 0x80):
            note, velo = corps[i], corps[i+1]; i += 2
            canaux.add(st & 0x0F)
            if (st & 0xF0) == 0x90 and velo > 0: ouvertes[note] = (t, velo)
            else:
                if note in ouvertes:
                    t0, v = ouvertes.pop(note)
                    notes.append((t0, note, v, t - t0))
        elif (st & 0xF0) in (0xC0, 0xD0):   # ces deux-là n'ont qu'un seul octet
            if (st & 0xF0) == 0xC0: prog = corps[i]
            i += 1
        else:
            i += 2
    if tempo: print("tempo : %.1f bpm" % (60_000_000 / tempo))
    if ouvertes: souci.append("%s : %d note(s) jamais relâchée(s)" % (titre, len(ouvertes)))
    if notes:
        notes.sort()
        fin = max(fin, max(t0 + dur for t0, _, _, dur in notes))
        plus_longue = max(notes, key=lambda x: x[3])
        res.append("%-22s %2d notes, canal %s, prog %-4s de %s à %s, la plus longue %.2f temps"
                   % (titre, len(notes), "+".join(str(c + 1) for c in sorted(canaux)),
                      prog if prog is not None else "-",
                      nom(min(n[1] for n in notes)), nom(max(n[1] for n in notes)),
                      plus_longue[3] / tpq))
        # aucune note ne doit en recouvrir une autre de même hauteur
        par_note = {}
        for t0, n, v, dur in notes: par_note.setdefault(n, []).append((t0, dur))
        for n, lst in par_note.items():
            lst.sort()
            for (a0, ad), (b0, _) in zip(lst, lst[1:]):
                if a0 + ad > b0: souci.append("%s : %s se recouvre à %d" % (titre, nom(n), b0))
        if titre.startswith("Nappe"):
            deb = {}
            for t0, n, v, dur in notes: deb.setdefault(t0, []).append(nom(n))
            print("   accords de la nappe :")
            for t0 in sorted(deb):
                print("     mesure %5.2f : %-14s (%d notes)"
                      % (t0 / tpq / 4 + 1, " ".join(deb[t0]), len(deb[t0])))
print()
print("\n".join(res))
print("\nrepères : " + ", ".join("mesure %.0f %s" % (t / tpq / 4 + 1, n) for t, n in reperes))
print("longueur : %.2f mesures" % (fin / tpq / 4))
print("\nPROBLÈMES : " + ("\n".join(souci) if souci else "aucun"))
