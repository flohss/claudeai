"""Banque de questions, organisée par thématique puis par sujet."""

THEMES = {
    "Histoire": {
        "Révolution française": [
            {
                "question": "En quelle année la prise de la Bastille a-t-elle eu lieu ?",
                "choices": ["1789", "1799", "1804", "1776"],
                "answer": 0,
            },
            {
                "question": "Quel roi de France a été guillotiné en 1793 ?",
                "choices": ["Louis XIV", "Louis XV", "Louis XVI", "Charles X"],
                "answer": 2,
            },
            {
                "question": "Quel texte fondamental est adopté le 26 août 1789 ?",
                "choices": [
                    "Le Code civil",
                    "La Déclaration des droits de l'homme et du citoyen",
                    "La Constitution de l'an III",
                    "Le Concordat",
                ],
                "answer": 1,
            },
            {
                "question": "Comment appelle-t-on la période de répression menée par Robespierre ?",
                "choices": ["Le Directoire", "La Terreur", "Le Consulat", "La Fronde"],
                "answer": 1,
            },
            {
                "question": "Quel événement marque la fin de la Révolution française ?",
                "choices": [
                    "Le sacre de Napoléon",
                    "Le coup d'État du 18 Brumaire",
                    "La bataille de Valmy",
                    "L'exécution de Louis XVI",
                ],
                "answer": 1,
            },
        ],
        "Empire romain": [
            {
                "question": "Qui fut le premier empereur romain ?",
                "choices": ["Jules César", "Auguste", "Néron", "Trajan"],
                "answer": 1,
            },
            {
                "question": "En quelle année l'Empire romain d'Occident s'effondre-t-il ?",
                "choices": ["410", "476", "395", "527"],
                "answer": 1,
            },
            {
                "question": "Quel empereur a fait de Constantinople la capitale de l'Empire ?",
                "choices": ["Constantin", "Dioclétien", "Hadrien", "Marc Aurèle"],
                "answer": 0,
            },
            {
                "question": "Quel monument emblématique de Rome servait aux combats de gladiateurs ?",
                "choices": ["Le Panthéon", "Le Forum", "Le Colisée", "Le Circus Maximus"],
                "answer": 2,
            },
            {
                "question": "Quelle langue était la langue officielle de l'Empire romain ?",
                "choices": ["Le grec", "Le latin", "L'étrusque", "Le gaulois"],
                "answer": 1,
            },
        ],
        "Seconde Guerre mondiale": [
            {
                "question": "En quelle année la Seconde Guerre mondiale a-t-elle commencé ?",
                "choices": ["1937", "1939", "1941", "1940"],
                "answer": 1,
            },
            {
                "question": "Quel événement marque l'entrée en guerre des États-Unis ?",
                "choices": [
                    "Le débarquement de Normandie",
                    "L'attaque de Pearl Harbor",
                    "La bataille de Stalingrad",
                    "L'invasion de la Pologne",
                ],
                "answer": 1,
            },
            {
                "question": "Quelle opération désigne le débarquement allié en Normandie ?",
                "choices": ["Overlord", "Barbarossa", "Torch", "Market Garden"],
                "answer": 0,
            },
            {
                "question": "En quelle année la guerre se termine-t-elle en Europe ?",
                "choices": ["1943", "1944", "1945", "1946"],
                "answer": 2,
            },
            {
                "question": "Quelle conférence organise le partage de l'Allemagne après-guerre ?",
                "choices": ["Munich", "Versailles", "Yalta", "Berlin"],
                "answer": 2,
            },
        ],
    },
    "Géographie": {
        "Fleuves du monde": [
            {
                "question": "Quel est le plus long fleuve du monde ?",
                "choices": ["Le Nil", "L'Amazone", "Le Yangtsé", "Le Mississippi"],
                "answer": 0,
            },
            {
                "question": "Quel fleuve traverse Paris ?",
                "choices": ["La Loire", "La Garonne", "La Seine", "Le Rhône"],
                "answer": 2,
            },
            {
                "question": "Dans quel pays le fleuve Amazone prend-il principalement sa source ?",
                "choices": ["Brésil", "Pérou", "Colombie", "Équateur"],
                "answer": 1,
            },
            {
                "question": "Quel fleuve traverse l'Égypte ?",
                "choices": ["Le Niger", "Le Congo", "Le Nil", "Le Zambèze"],
                "answer": 2,
            },
            {
                "question": "Quel est le fleuve le plus long d'Europe ?",
                "choices": ["Le Danube", "Le Rhin", "La Volga", "Le Rhône"],
                "answer": 2,
            },
        ],
        "Capitales européennes": [
            {
                "question": "Quelle est la capitale du Portugal ?",
                "choices": ["Porto", "Madrid", "Lisbonne", "Séville"],
                "answer": 2,
            },
            {
                "question": "Quelle est la capitale de la Norvège ?",
                "choices": ["Stockholm", "Oslo", "Helsinki", "Copenhague"],
                "answer": 1,
            },
            {
                "question": "Quelle est la capitale de la Hongrie ?",
                "choices": ["Bucarest", "Varsovie", "Budapest", "Prague"],
                "answer": 2,
            },
            {
                "question": "Quelle est la capitale de la Grèce ?",
                "choices": ["Athènes", "Thessalonique", "Sparte", "Corinthe"],
                "answer": 0,
            },
            {
                "question": "Quelle est la capitale de la Suisse ?",
                "choices": ["Genève", "Zurich", "Berne", "Lausanne"],
                "answer": 2,
            },
        ],
        "Déserts": [
            {
                "question": "Quel est le plus grand désert chaud du monde ?",
                "choices": ["Le désert de Gobi", "Le Sahara", "Le désert de Sonora", "Le Kalahari"],
                "answer": 1,
            },
            {
                "question": "Sur quel continent se trouve le désert de Gobi ?",
                "choices": ["Afrique", "Amérique du Sud", "Asie", "Océanie"],
                "answer": 2,
            },
            {
                "question": "Quel désert est considéré comme le plus aride du monde ?",
                "choices": ["Le désert d'Atacama", "Le Sahara", "Le désert de Namib", "Le désert du Néguev"],
                "answer": 0,
            },
            {
                "question": "Dans quel pays se trouve principalement le désert du Kalahari ?",
                "choices": ["Égypte", "Botswana", "Maroc", "Kenya"],
                "answer": 1,
            },
            {
                "question": "Quel désert australien est le plus vaste ?",
                "choices": ["Simpson", "Grand désert de sable", "Gibson", "Tanami"],
                "answer": 1,
            },
        ],
    },
    "Sciences": {
        "Système solaire": [
            {
                "question": "Quelle est la planète la plus proche du Soleil ?",
                "choices": ["Vénus", "Mercure", "Mars", "Terre"],
                "answer": 1,
            },
            {
                "question": "Quelle planète est surnommée la « planète rouge » ?",
                "choices": ["Jupiter", "Vénus", "Mars", "Saturne"],
                "answer": 2,
            },
            {
                "question": "Combien de planètes compte le système solaire depuis 2006 ?",
                "choices": ["8", "9", "7", "10"],
                "answer": 0,
            },
            {
                "question": "Quelle est la plus grande planète du système solaire ?",
                "choices": ["Saturne", "Uranus", "Jupiter", "Neptune"],
                "answer": 2,
            },
            {
                "question": "Combien de temps met la lumière du Soleil pour atteindre la Terre ?",
                "choices": ["8 minutes", "1 seconde", "1 heure", "8 secondes"],
                "answer": 0,
            },
        ],
        "Corps humain": [
            {
                "question": "Combien d'os compte le squelette d'un adulte ?",
                "choices": ["186", "206", "226", "246"],
                "answer": 1,
            },
            {
                "question": "Quel est l'organe le plus grand du corps humain ?",
                "choices": ["Le foie", "Le cœur", "La peau", "Le cerveau"],
                "answer": 2,
            },
            {
                "question": "Combien de chambres possède le cœur humain ?",
                "choices": ["2", "3", "4", "5"],
                "answer": 2,
            },
            {
                "question": "Quel organe produit l'insuline ?",
                "choices": ["Le foie", "Le pancréas", "Les reins", "La rate"],
                "answer": 1,
            },
            {
                "question": "Quel est le principal muscle utilisé pour respirer ?",
                "choices": ["Le diaphragme", "Le biceps", "Le trapèze", "Le cœur"],
                "answer": 0,
            },
        ],
        "Chimie": [
            {
                "question": "Quel est le symbole chimique de l'or ?",
                "choices": ["Ag", "Au", "Or", "Go"],
                "answer": 1,
            },
            {
                "question": "Quel gaz les plantes absorbent-elles lors de la photosynthèse ?",
                "choices": ["Oxygène", "Azote", "Dioxyde de carbone", "Hydrogène"],
                "answer": 2,
            },
            {
                "question": "Quel est l'élément chimique le plus abondant dans l'univers ?",
                "choices": ["Oxygène", "Hydrogène", "Hélium", "Carbone"],
                "answer": 1,
            },
            {
                "question": "Quel est le pH de l'eau pure ?",
                "choices": ["5", "7", "9", "0"],
                "answer": 1,
            },
            {
                "question": "Quelle est la formule chimique du sel de table ?",
                "choices": ["NaCl", "KCl", "CaCO3", "H2O"],
                "answer": 0,
            },
        ],
    },
    "Littérature & Arts": {
        "Peinture": [
            {
                "question": "Qui a peint « La Joconde » ?",
                "choices": ["Michel-Ange", "Léonard de Vinci", "Raphaël", "Botticelli"],
                "answer": 1,
            },
            {
                "question": "Quel peintre est célèbre pour ses tournesols ?",
                "choices": ["Claude Monet", "Vincent van Gogh", "Paul Cézanne", "Edgar Degas"],
                "answer": 1,
            },
            {
                "question": "Quel mouvement artistique Pablo Picasso a-t-il co-fondé ?",
                "choices": ["L'impressionnisme", "Le cubisme", "Le surréalisme", "Le fauvisme"],
                "answer": 1,
            },
            {
                "question": "Dans quel musée est exposée « La Joconde » ?",
                "choices": ["Le musée d'Orsay", "Le Louvre", "Le Prado", "Les Offices"],
                "answer": 1,
            },
            {
                "question": "Qui a peint « La Nuit étoilée » ?",
                "choices": ["Salvador Dalí", "Vincent van Gogh", "Edvard Munch", "Gustav Klimt"],
                "answer": 1,
            },
        ],
        "Littérature française": [
            {
                "question": "Qui a écrit « Les Misérables » ?",
                "choices": ["Émile Zola", "Victor Hugo", "Honoré de Balzac", "Gustave Flaubert"],
                "answer": 1,
            },
            {
                "question": "Quel auteur a créé le personnage de d'Artagnan ?",
                "choices": ["Alexandre Dumas", "Jules Verne", "Stendhal", "Molière"],
                "answer": 0,
            },
            {
                "question": "Qui est l'auteur de « Madame Bovary » ?",
                "choices": ["Guy de Maupassant", "Gustave Flaubert", "Émile Zola", "Marcel Proust"],
                "answer": 1,
            },
            {
                "question": "Quel dramaturge français est l'auteur du « Malade imaginaire » ?",
                "choices": ["Racine", "Corneille", "Molière", "Beaumarchais"],
                "answer": 2,
            },
            {
                "question": "Qui a écrit « À la recherche du temps perdu » ?",
                "choices": ["Marcel Proust", "André Gide", "Albert Camus", "Jean-Paul Sartre"],
                "answer": 0,
            },
        ],
    },
    "Sport": {
        "Jeux Olympiques": [
            {
                "question": "Dans quel pays sont nés les Jeux olympiques antiques ?",
                "choices": ["Italie", "Grèce", "Égypte", "Turquie"],
                "answer": 1,
            },
            {
                "question": "Tous les combien d'années les Jeux olympiques d'été ont-ils lieu ?",
                "choices": ["2 ans", "3 ans", "4 ans", "5 ans"],
                "answer": 2,
            },
            {
                "question": "Quelle ville a accueilli les Jeux olympiques d'été de 2024 ?",
                "choices": ["Tokyo", "Londres", "Paris", "Los Angeles"],
                "answer": 2,
            },
            {
                "question": "Combien de couleurs compte le drapeau olympique ?",
                "choices": ["4", "5", "6", "7"],
                "answer": 1,
            },
            {
                "question": "Quel sprinteur jamaïcain a dominé les Jeux de 2008 à 2016 ?",
                "choices": ["Usain Bolt", "Carl Lewis", "Justin Gatlin", "Yohan Blake"],
                "answer": 0,
            },
        ],
        "Football": [
            {
                "question": "Combien de joueurs compte une équipe de football sur le terrain ?",
                "choices": ["9", "10", "11", "12"],
                "answer": 2,
            },
            {
                "question": "Quel pays a remporté la Coupe du monde de football 2018 ?",
                "choices": ["Croatie", "France", "Belgique", "Brésil"],
                "answer": 1,
            },
            {
                "question": "Combien de fois le Brésil a-t-il remporté la Coupe du monde ?",
                "choices": ["3", "4", "5", "6"],
                "answer": 2,
            },
            {
                "question": "Quel joueur détient le record de Ballons d'or ?",
                "choices": ["Cristiano Ronaldo", "Lionel Messi", "Michel Platini", "Ronaldinho"],
                "answer": 1,
            },
            {
                "question": "Quelle est la durée réglementaire d'un match de football (hors prolongations) ?",
                "choices": ["80 minutes", "90 minutes", "100 minutes", "120 minutes"],
                "answer": 1,
            },
        ],
    },
}
