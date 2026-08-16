// Formulaire du module 10 (SPECIAL) : bascule entre les deux types de
// leçon (catégories / nombre) et gère l'ajout/suppression de lignes
// d'exemples tapées par vous, plus le pré-remplissage si le formulaire
// est réaffiché après une erreur de validation.

document.addEventListener("DOMContentLoaded", () => {
    const selectType = document.getElementById("type-lecon");
    const blocCategories = document.getElementById("bloc-categories");
    const blocNombre = document.getElementById("bloc-nombre");
    const tableCategoriesBody = document.querySelector("#table-categories tbody");
    const tableNombreBody = document.querySelector("#table-nombre tbody");
    const inputCategorieA = document.querySelector('input[name="categorie_a"]');
    const inputCategorieB = document.querySelector('input[name="categorie_b"]');
    const inputNomCar1 = document.querySelector('input[name="nom_car1"]');
    const inputNomCar2 = document.querySelector('input[name="nom_car2"]');
    const inputNomCar = document.querySelector('input[name="nom_car"]');
    const inputNomSortie = document.querySelector('input[name="nom_sortie"]');
    const enteteCar1 = document.querySelector(".entete-car1");
    const enteteCar2 = document.querySelector(".entete-car2");
    const enteteCar = document.querySelector(".entete-car");
    const enteteSortie = document.querySelector(".entete-sortie");

    function basculerBloc() {
        const estCategories = selectType.value === "categories";
        blocCategories.hidden = !estCategories;
        blocNombre.hidden = estCategories;
        blocCategories.disabled = !estCategories;
        blocNombre.disabled = estCategories;
    }
    selectType.addEventListener("change", basculerBloc);
    basculerBloc();

    function rafraichirEntetes() {
        if (enteteCar1) enteteCar1.textContent = inputNomCar1.value || "caractéristique 1";
        if (enteteCar2) enteteCar2.textContent = inputNomCar2.value || "caractéristique 2";
        if (enteteCar) enteteCar.textContent = inputNomCar.value || "caractéristique";
        if (enteteSortie) enteteSortie.textContent = inputNomSortie.value || "à deviner";
    }
    [inputNomCar1, inputNomCar2, inputNomCar, inputNomSortie].forEach((input) => {
        if (input) input.addEventListener("input", rafraichirEntetes);
    });
    rafraichirEntetes();

    function rafraichirSelectsCategorie() {
        const nomA = inputCategorieA.value || "catégorie A";
        const nomB = inputCategorieB.value || "catégorie B";
        tableCategoriesBody.querySelectorAll("select.select-categorie").forEach((select) => {
            const valeurActuelle = select.value;
            select.innerHTML = `<option value="${nomA}">${nomA}</option><option value="${nomB}">${nomB}</option>`;
            if ([nomA, nomB].includes(valeurActuelle)) select.value = valeurActuelle;
        });
    }
    [inputCategorieA, inputCategorieB].forEach((input) => {
        if (input) input.addEventListener("input", rafraichirSelectsCategorie);
    });

    function ajouterLigneCategories(v1 = "", v2 = "", categorie = "") {
        const nomA = inputCategorieA.value || "catégorie A";
        const nomB = inputCategorieB.value || "catégorie B";
        const ligne = document.createElement("tr");
        ligne.innerHTML = `
          <td><input type="number" step="any" name="v1[]" value="${v1}" required></td>
          <td><input type="number" step="any" name="v2[]" value="${v2}" required></td>
          <td><select class="select-categorie" name="categorie[]">
                <option value="${nomA}">${nomA}</option>
                <option value="${nomB}">${nomB}</option>
              </select></td>
          <td><button type="button" class="bouton-supprimer" aria-label="Supprimer cette ligne">&times;</button></td>`;
        const select = ligne.querySelector("select.select-categorie");
        if (categorie) select.value = categorie;
        ligne.querySelector(".bouton-supprimer").addEventListener("click", () => ligne.remove());
        tableCategoriesBody.appendChild(ligne);
    }

    function ajouterLigneNombre(v = "", cible = "") {
        const ligne = document.createElement("tr");
        ligne.innerHTML = `
          <td><input type="number" step="any" name="v[]" value="${v}" required></td>
          <td><input type="number" step="any" name="cible[]" value="${cible}" required></td>
          <td><button type="button" class="bouton-supprimer" aria-label="Supprimer cette ligne">&times;</button></td>`;
        ligne.querySelector(".bouton-supprimer").addEventListener("click", () => ligne.remove());
        tableNombreBody.appendChild(ligne);
    }

    document.getElementById("ajouter-ligne-categories").addEventListener("click", () => ajouterLigneCategories());
    document.getElementById("ajouter-ligne-nombre").addEventListener("click", () => ajouterLigneNombre());

    const preremplis = window.EXEMPLES_PREREMPLIS || { categories: { v1: [], v2: [], categorie: [] }, nombre: { v: [], cible: [] } };
    if (preremplis.categories.v1.length) {
        preremplis.categories.v1.forEach((v1, i) => {
            ajouterLigneCategories(v1, preremplis.categories.v2[i] || "", preremplis.categories.categorie[i] || "");
        });
    } else {
        for (let i = 0; i < 4; i++) ajouterLigneCategories();
    }
    if (preremplis.nombre.v.length) {
        preremplis.nombre.v.forEach((v, i) => ajouterLigneNombre(v, preremplis.nombre.cible[i] || ""));
    } else {
        for (let i = 0; i < 4; i++) ajouterLigneNombre();
    }
});
