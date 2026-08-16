// Suit un entrainement en direct via un flux "Server-Sent Events" et
// dessine la courbe, le schema des boutons et le fil de pensee de l'IA.
// Aucune dependance externe (juste du JavaScript "vanilla"). Fonctionne
// pour un seul suivi (page suivi.html) ou pour deux cote a cote
// (page comparaison.html) : chaque conteneur ".suivi" trouve sur la
// page est initialise independamment.

const NS_SVG = "http://www.w3.org/2000/svg";
const COULEUR_CASE = {
    tete: "case-tete",
    corps: "case-corps",
    nourriture: "case-nourriture",
    vide: "case-vide",
};

function dessinerCourbe(canvas, points) {
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (points.length < 2) return;

    const marge = 34;
    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    const xMin = Math.min(...xs);
    const xMax = Math.max(...xs);
    const yMin = Math.min(0, ...ys);
    const yMax = Math.max(...ys) * 1.08 || 1;

    const px = (x) => marge + ((x - xMin) / ((xMax - xMin) || 1)) * (w - marge * 1.5);
    const py = (y) => h - marge - ((y - yMin) / ((yMax - yMin) || 1)) * (h - marge * 1.5);

    ctx.strokeStyle = "#94a3b8";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(marge, 10);
    ctx.lineTo(marge, h - marge);
    ctx.lineTo(w - 10, h - marge);
    ctx.stroke();

    ctx.fillStyle = "#64748b";
    ctx.font = "11px sans-serif";
    ctx.fillText(yMax.toFixed(2), 4, 14);
    ctx.fillText(yMin.toFixed(2), 4, h - marge);
    ctx.fillText(String(xMin), marge, h - 8);
    ctx.fillText(String(xMax), w - 34, h - 8);

    ctx.strokeStyle = "#3b82f6";
    ctx.lineWidth = 2;
    ctx.beginPath();
    points.forEach((p, i) => {
        const X = px(p.x);
        const Y = py(p.y);
        if (i === 0) ctx.moveTo(X, Y);
        else ctx.lineTo(X, Y);
    });
    ctx.stroke();
}

// Dessine un petit schema "entrees -> (couche cachee) -> sortie", avec
// une ligne par bouton : bleu = positif, rouge = negatif, plus la ligne
// est epaisse et opaque, plus le bouton pese lourd dans la decision.
function dessinerReseau(svg, poids1, poids2, biaisSortie, labelsEntrees, labelSortie) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    const largeur = 320;
    const hauteur = 200;
    svg.setAttribute("viewBox", `0 0 ${largeur} ${hauteur}`);

    const nbEntrees = poids1.length;
    const aCoucheCachee = poids2 !== null && poids2 !== undefined;
    const nbCaches = aCoucheCachee ? poids1[0].length : 0;

    const xEntrees = 30;
    const xCaches = aCoucheCachee ? largeur / 2 : null;
    const xSortie = largeur - 30;

    const positionsY = (n, h) => {
        if (n === 1) return [h / 2];
        const marge = 24;
        const pas = (h - marge * 2) / (n - 1);
        return Array.from({ length: n }, (_, i) => marge + i * pas);
    };

    const yEntrees = positionsY(nbEntrees, hauteur);
    const yCaches = aCoucheCachee ? positionsY(nbCaches, hauteur) : [];
    const ySortie = hauteur / 2;

    function styleBouton(valeur) {
        const v = Math.max(-3, Math.min(3, valeur));
        const intensite = Math.min(1, Math.abs(v) / 3);
        const couleur = v >= 0 ? "59,130,246" : "239,68,68";
        return { couleur: `rgba(${couleur},${0.25 + intensite * 0.75})`, epaisseur: 1 + intensite * 4 };
    }

    function ligne(x1, y1, x2, y2, valeur) {
        const style = styleBouton(valeur);
        const el = document.createElementNS(NS_SVG, "line");
        el.setAttribute("x1", x1);
        el.setAttribute("y1", y1);
        el.setAttribute("x2", x2);
        el.setAttribute("y2", y2);
        el.setAttribute("stroke", style.couleur);
        el.setAttribute("stroke-width", style.epaisseur);
        svg.appendChild(el);
    }

    function noeud(x, y, texte) {
        const cercle = document.createElementNS(NS_SVG, "circle");
        cercle.setAttribute("cx", x);
        cercle.setAttribute("cy", y);
        cercle.setAttribute("r", 5);
        cercle.setAttribute("class", "noeud");
        svg.appendChild(cercle);
        if (texte) {
            const t = document.createElementNS(NS_SVG, "text");
            t.setAttribute("x", x);
            t.setAttribute("y", y - 10);
            t.setAttribute("class", "noeud-texte");
            t.textContent = texte;
            svg.appendChild(t);
        }
    }

    if (aCoucheCachee) {
        // entrees -> couche cachee
        for (let i = 0; i < nbEntrees; i++) {
            for (let j = 0; j < nbCaches; j++) {
                ligne(xEntrees, yEntrees[i], xCaches, yCaches[j], poids1[i][j]);
            }
        }
        // couche cachee -> sortie
        for (let j = 0; j < nbCaches; j++) {
            ligne(xCaches, yCaches[j], xSortie, ySortie, poids2[j][0]);
        }
    } else {
        // entrees -> sortie directement
        for (let i = 0; i < nbEntrees; i++) {
            ligne(xEntrees, yEntrees[i], xSortie, ySortie, poids1[i][0]);
        }
    }

    if (biaisSortie !== null && biaisSortie !== undefined) {
        const yBiais = hauteur - 12;
        ligne(xSortie, yBiais, xSortie, ySortie, biaisSortie);
        noeud(xSortie, yBiais, "biais");
    }

    yEntrees.forEach((y, i) => noeud(xEntrees, y, labelsEntrees[i] || ""));
    if (aCoucheCachee) yCaches.forEach((y) => noeud(xCaches, y));
    noeud(xSortie, ySortie, labelSortie);
}

function dessinerGrille(container, grille) {
    container.innerHTML = "";
    const nbColonnes = grille[0].length;
    container.style.gridTemplateColumns = `repeat(${nbColonnes}, 1fr)`;
    grille.forEach((ligne) => {
        ligne.forEach((type) => {
            const cellule = document.createElement("div");
            cellule.className = "case " + (COULEUR_CASE[type] || "case-vide");
            container.appendChild(cellule);
        });
    });
}

function initialiserSuivi(conteneur, reseauConfig) {
    const sessionId = conteneur.dataset.sessionId;
    const numModule = parseInt(conteneur.dataset.num, 10);
    const estModule5 = numModule === 5;

    const canvas = conteneur.querySelector(".graphique");
    const zoneProgression = conteneur.querySelector(".progression");
    const zonePensees = conteneur.querySelector(".pensees");
    const zoneHistorique = conteneur.querySelector(".historique");
    const zoneStatut = conteneur.querySelector(".statut");
    const boutonArreter = conteneur.querySelector(".bouton-arreter");
    const svgReseau = conteneur.querySelector(".reseau");
    const sectionEntrainement = conteneur.querySelector(".section-entrainement");
    const sectionDemo = conteneur.querySelector(".section-demo");
    const zoneGrille = conteneur.querySelector(".grille");
    const zoneDemoInfo = conteneur.querySelector(".demo-info");

    if (sectionDemo) sectionDemo.hidden = true;

    let points = [];
    const MAX_POINTS = 300;

    function ajouterPoint(x, y) {
        points.push({ x, y });
        if (points.length > MAX_POINTS) points.shift();
        dessinerCourbe(canvas, points);
    }

    function afficherPensees(lignes, entete) {
        zonePensees.innerHTML = "";
        const titre = document.createElement("p");
        titre.className = "pensees-entete";
        titre.textContent = entete;
        zonePensees.appendChild(titre);
        lignes.forEach((ligne) => {
            const p = document.createElement("p");
            p.textContent = ligne;
            zonePensees.appendChild(p);
        });
    }

    function ajouterHistorique(texte) {
        const ligne = document.createElement("div");
        ligne.textContent = texte;
        zoneHistorique.prepend(ligne);
        while (zoneHistorique.children.length > 50) {
            zoneHistorique.removeChild(zoneHistorique.lastChild);
        }
    }

    function terminerAffichage(texte, classe) {
        zoneStatut.textContent = texte;
        zoneStatut.className = "statut " + classe;
        if (boutonArreter) boutonArreter.hidden = true;
    }

    const source = new EventSource(`/flux/${sessionId}`);

    if (boutonArreter) {
        boutonArreter.addEventListener("click", () => {
            boutonArreter.disabled = true;
            boutonArreter.textContent = "Arrêt en cours...";
            fetch(`/arreter/${sessionId}`, { method: "POST" });
        });
    }

    source.onmessage = (evenement) => {
        const donnees = JSON.parse(evenement.data);

        if (donnees.type === "essai") {
            const erreurInstable = donnees.erreur === null;
            if (!erreurInstable) ajouterPoint(donnees.essai, donnees.erreur);
            zoneProgression.textContent = erreurInstable
                ? `Essai ${donnees.essai} / ${donnees.nb_essais} — devenue instable (vitesse trop grande)`
                : `Essai ${donnees.essai} / ${donnees.nb_essais} — erreur : ${donnees.erreur.toFixed(4)}`;
            afficherPensees(donnees.pensees, `Essai ${donnees.essai} :`);
            ajouterHistorique(`Essai ${donnees.essai} — erreur : ${donnees.erreur.toFixed(4)}`);
            if (svgReseau && reseauConfig) {
                dessinerReseau(svgReseau, donnees.poids1, donnees.poids2, donnees.biais_sortie,
                    reseauConfig.entrees, reseauConfig.sortie);
            }
        } else if (donnees.type === "partie") {
            ajouterPoint(donnees.partie, donnees.score);
            zoneProgression.textContent = `Partie ${donnees.partie} / ${donnees.nb_parties} — score : ${donnees.score} — curiosité : ${donnees.curiosite.toFixed(2)}`;
            ajouterHistorique(`Partie ${donnees.partie} — score : ${donnees.score} — moyenne récente : ${donnees.moyenne_recente.toFixed(1)}`);
        } else if (donnees.type === "fin_entrainement") {
            zoneStatut.textContent = "Entraînement terminé, on regarde une partie jouée par l'IA...";
            if (sectionEntrainement) sectionEntrainement.hidden = true;
            if (sectionDemo) sectionDemo.hidden = false;
        } else if (donnees.type === "mouvement") {
            dessinerGrille(zoneGrille, donnees.grille);
            zoneDemoInfo.textContent = `Score : ${donnees.score} — ${donnees.message}`;
        } else if (donnees.type === "fin") {
            terminerAffichage("Terminé !", "statut-termine");
            source.close();
        } else if (donnees.type === "arrete") {
            terminerAffichage("Entraînement arrêté.", "statut-arrete");
            source.close();
        } else if (donnees.type === "erreur") {
            terminerAffichage("Erreur : " + donnees.message, "statut-erreur");
            source.close();
        }
    };

    source.onerror = () => {
        if (!zoneStatut.className.includes("statut-termine") && !zoneStatut.className.includes("statut-arrete")) {
            terminerAffichage("Connexion perdue avec le serveur.", "statut-erreur");
        }
    };
}

document.addEventListener("DOMContentLoaded", () => {
    const reseauConfig = window.RESEAU_CONFIG || null;
    document.querySelectorAll(".suivi").forEach((conteneur) => initialiserSuivi(conteneur, reseauConfig));
});
