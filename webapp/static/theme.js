// Bouton "mode sombre" partagé par toutes les pages. Le choix est
// mémorisé dans le navigateur (localStorage) : la page se rappelle de
// vous d'une visite à l'autre. Un petit script anti-clignotement dans
// le <head> de chaque page applique déjà le thème avant l'affichage ;
// ce fichier se contente d'ajouter le bouton et de gérer le clic.

function appliquerTheme(theme) {
    if (theme === "dark") {
        document.documentElement.setAttribute("data-theme", "dark");
    } else {
        document.documentElement.removeAttribute("data-theme");
    }
    localStorage.setItem("theme", theme);
    const bouton = document.querySelector(".bouton-theme");
    if (bouton) bouton.textContent = theme === "dark" ? "☀️ Mode clair" : "🌙 Mode sombre";
}

document.addEventListener("DOMContentLoaded", () => {
    const bouton = document.createElement("button");
    bouton.type = "button";
    bouton.className = "bouton-theme";
    const themeActuel = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "clair";
    bouton.textContent = themeActuel === "dark" ? "☀️ Mode clair" : "🌙 Mode sombre";
    bouton.addEventListener("click", () => {
        const nouveau = document.documentElement.getAttribute("data-theme") === "dark" ? "clair" : "dark";
        appliquerTheme(nouveau);
    });
    document.body.appendChild(bouton);
});
