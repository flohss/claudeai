# claudeai

Made with Claude

## Personnalisation de personnage 3D

Ce projet Unity fournit un système générique et pilote par des données pour un
corps humain 3D entierement personnalisable (morphologie, visage, apparence)
avec des habits interchangeables.

### Important : ce qui est fourni et ce qui ne l'est pas

Le code gere toute la logique (blend shapes, teintes, equipement d'habits,
sauvegarde/chargement) mais **ne contient aucun asset 3D**. Il vous faut
importer :

- un **mesh humanoide rigue** avec des blend shapes nommees (ex: `Body_Weight`,
  `Body_Muscle`, `Face_JawWidth`, `Face_NoseSize`, ...) ;
- des **prefabs d'habits** rigues sur le meme squelette (memes noms d'os que
  le corps de base), un par slot d'equipement ;
- optionnellement des **prefabs de coiffure**.

Ces assets peuvent venir de Blender, Mixamo, Character Creator, de l'Asset
Store, etc. Le systeme est concu pour fonctionner avec n'importe quel mesh
tant que la convention de nommage ci-dessous est respectee.

### Architecture (`Assets/Scripts/CharacterCustomization`)

| Fichier | Role |
|---|---|
| `BlendShapeController.cs` | Acces aux blend shapes d'un `SkinnedMeshRenderer` par nom. |
| `MorphController.cs` | Pilote les sliders de morphologie et de visage a partir d'un `MorphProfile` (ScriptableObject). |
| `Data/MorphProfile.cs` | Definit la liste des sliders exposes (corps + visage), avec bornes et valeurs par defaut. |
| `AppearanceController.cs` | Teinte de peau et coiffure (style + couleur). |
| `EquipmentSlot.cs` | Enum des emplacements d'equipement (Tete, Torse, Jambes, Pieds, Mains, ...). |
| `Data/ClothingItem.cs` | ScriptableObject decrivant un habit : slot, prefab, teinte, parties du corps a masquer. |
| `EquipmentManager.cs` | Equipe/desequipe les habits en rebindant leurs os sur le squelette du personnage. |
| `CharacterCustomizationManager.cs` | Facade unique regroupant morphologie, apparence et equipement. |
| `Data/CharacterData.cs` + `CharacterSaveSystem.cs` | Modele serialisable et sauvegarde/chargement JSON d'un personnage. |
| `UI/CharacterCustomizationUI.cs` | Exemple de branchement UI (uGUI) generant les sliders depuis le `MorphProfile`. |

### Mise en place dans l'editeur

1. Importer votre mesh de corps humanoide (avec blend shapes) et son squelette
   dans la scene.
2. Creer un `MorphProfile` (clic droit > Create > Character Customization >
   Morph Profile) et lister vos sliders, en faisant correspondre
   `blendShapeName` aux noms exacts des blend shapes du mesh.
3. Ajouter un objet vide "Character" avec les composants
   `BlendShapeController`, `MorphController`, `AppearanceController`,
   `EquipmentManager` et `CharacterCustomizationManager`, et relier les
   references dans l'inspecteur.
4. Pour chaque habit, creer un `ClothingItem` (Create > Character
   Customization > Clothing Item) pointant vers un prefab rigue sur le meme
   squelette.
5. Brancher `CharacterCustomizationUI` sur une Canvas pour tester en jeu.

### Limite connue : masquage des parties du corps sous les vetements

`EquipmentManager.BodyPartsHidden` expose quelles parties du corps devraient
etre masquees quand un habit est equipe, mais l'implementation reelle
(desactivation de sous-maillages ou masque shader) depend de la facon dont
votre mesh de base est decoupe. A completer selon votre pipeline d'assets.
