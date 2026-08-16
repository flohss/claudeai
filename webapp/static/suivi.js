// Suit l'entrainement en direct via un flux "Server-Sent Events" et
// dessine la courbe + le fil de pensee de l'IA, sans aucune dependance
// externe (juste du JavaScript "vanilla").

const corps = document.body;
const sessionId = corps.dataset.sessionId;
const numModule = parseInt(corps.dataset.num, 10);
const estModule5 = numModule === 5;

const canvas = document.getElementById("graphique");
const ctxGraphique = canvas.getContext("2d");
const zoneProgression = document.getElementById("progression");
const zonePensees = document.getElementById("pensees");
const zoneHistorique = document.getElementById("historique");
const zoneStatut = document.getElementById("statut");
const titreGraphique = document.getElementById("titre-graphique");

const sectionEntrainement = document.getElementById("section-entrainement");
const sectionDemo = document.getElementById("section-demo");
const zoneGrille = document.getElementById("grille");
const zoneDemoInfo = document.getElementById("demo-info");

if (estModule5) {
    titreGraphique.textContent = "Score par partie";
}

let points = [];
const MAX_POINTS = 300;

function dessinerCourbe() {
    const w = canvas.width;
    const h = canvas.height;
    ctxGraphique.clearRect(0, 0, w, h);
    if (points.length < 2) return;

    const marge = 36;
    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    const xMin = Math.min(...xs);
    const xMax = Math.max(...xs);
    const yMin = Math.min(0, ...ys);
    const yMax = Math.max(...ys) * 1.08 || 1;

    const px = (x) => marge + ((x - xMin) / ((xMax - xMin) || 1)) * (w - marge * 1.5);
    const py = (y) => h - marge - ((y - yMin) / ((yMax - yMin) || 1)) * (h - marge * 1.5);

    ctxGraphique.strokeStyle = "#94a3b8";
    ctxGraphique.lineWidth = 1;
    ctxGraphique.beginPath();
    ctxGraphique.moveTo(marge, 10);
    ctxGraphique.lineTo(marge, h - marge);
    ctxGraphique.lineTo(w - 10, h - marge);
    ctxGraphique.stroke();

    ctxGraphique.fillStyle = "#64748b";
    ctxGraphique.font = "12px sans-serif";
    ctxGraphique.fillText(yMax.toFixed(2), 4, 16);
    ctxGraphique.fillText(yMin.toFixed(2), 4, h - marge);
    ctxGraphique.fillText(String(xMin), marge, h - 10);
    ctxGraphique.fillText(String(xMax), w - 40, h - 10);

    ctxGraphique.strokeStyle = "#3b82f6";
    ctxGraphique.lineWidth = 2;
    ctxGraphique.beginPath();
    points.forEach((p, i) => {
        const X = px(p.x);
        const Y = py(p.y);
        if (i === 0) ctxGraphique.moveTo(X, Y);
        else ctxGraphique.lineTo(X, Y);
    });
    ctxGraphique.stroke();
}

function ajouterPoint(x, y) {
    points.push({ x, y });
    if (points.length > MAX_POINTS) points.shift();
    dessinerCourbe();
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

const COULEUR_CASE = {
    tete: "case-tete",
    corps: "case-corps",
    nourriture: "case-nourriture",
    vide: "case-vide",
};

function dessinerGrille(grille) {
    zoneGrille.innerHTML = "";
    const nbColonnes = grille[0].length;
    zoneGrille.style.gridTemplateColumns = `repeat(${nbColonnes}, 1fr)`;
    grille.forEach((ligne) => {
        ligne.forEach((type) => {
            const cellule = document.createElement("div");
            cellule.className = "case " + (COULEUR_CASE[type] || "case-vide");
            zoneGrille.appendChild(cellule);
        });
    });
}

const source = new EventSource(`/flux/${sessionId}`);

source.onmessage = (evenement) => {
    const donnees = JSON.parse(evenement.data);

    if (donnees.type === "essai") {
        ajouterPoint(donnees.essai, donnees.erreur);
        zoneProgression.textContent = `Essai ${donnees.essai} / ${donnees.nb_essais} — erreur : ${donnees.erreur.toFixed(4)}`;
        afficherPensees(donnees.pensees, `Essai ${donnees.essai} :`);
        ajouterHistorique(`Essai ${donnees.essai} — erreur : ${donnees.erreur.toFixed(4)}`);
    } else if (donnees.type === "partie") {
        ajouterPoint(donnees.partie, donnees.score);
        zoneProgression.textContent = `Partie ${donnees.partie} / ${donnees.nb_parties} — score : ${donnees.score} — curiosité : ${donnees.curiosite.toFixed(2)}`;
        ajouterHistorique(`Partie ${donnees.partie} — score : ${donnees.score} — moyenne récente : ${donnees.moyenne_recente.toFixed(1)}`);
    } else if (donnees.type === "fin_entrainement") {
        zoneStatut.textContent = "Entraînement terminé, on regarde une partie jouée par l'IA...";
        sectionEntrainement.hidden = true;
        sectionDemo.hidden = false;
    } else if (donnees.type === "mouvement") {
        dessinerGrille(donnees.grille);
        zoneDemoInfo.textContent = `Score : ${donnees.score} — ${donnees.message}`;
    } else if (donnees.type === "fin") {
        zoneStatut.textContent = "Terminé !";
        zoneStatut.className = "statut statut-termine";
        source.close();
    } else if (donnees.type === "erreur") {
        zoneStatut.textContent = "Erreur : " + donnees.message;
        zoneStatut.className = "statut statut-erreur";
        source.close();
    }
};

source.onerror = () => {
    if (zoneStatut.className !== "statut statut-termine") {
        zoneStatut.textContent = "Connexion perdue avec le serveur.";
        zoneStatut.className = "statut statut-erreur";
    }
};

if (estModule5) {
    sectionDemo.hidden = true;
}
