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
        "Les premières civilisations": [
            {
                "question": "Quelle civilisation est considérée comme l'une des premières civilisations urbaines, en Mésopotamie ?",
                "choices": ["Les Sumériens", "Les Vikings", "Les Celtes", "Les Incas"],
                "answer": 0,
            },
            {
                "question": "Dans quelle région se situe la Mésopotamie, souvent appelée « berceau de la civilisation » ?",
                "choices": ["Entre le Tigre et l'Euphrate", "Entre le Nil et la mer Rouge", "Entre le Gange et l'Indus", "Entre le Rhône et la Loire"],
                "answer": 0,
            },
            {
                "question": "Quelle invention majeure est attribuée aux Sumériens ?",
                "choices": ["L'écriture cunéiforme", "L'imprimerie", "La boussole", "La poudre à canon"],
                "answer": 0,
            },
            {
                "question": "Quelle civilisation a bâti les pyramides de Gizeh ?",
                "choices": ["Les Égyptiens", "Les Babyloniens", "Les Phéniciens", "Les Hittites"],
                "answer": 0,
            },
            {
                "question": "Quel fleuve a permis l'essor de la civilisation égyptienne antique ?",
                "choices": ["Le Nil", "Le Tigre", "L'Euphrate", "L'Indus"],
                "answer": 0,
            },
        ],
        "Antiquité gréco-romaine": [
            {
                "question": "Quelle cité grecque est célèbre pour sa démocratie antique ?",
                "choices": ["Athènes", "Sparte", "Thèbes", "Corinthe"],
                "answer": 0,
            },
            {
                "question": "Qui était le philosophe grec maître de Platon ?",
                "choices": ["Socrate", "Aristote", "Pythagore", "Héraclite"],
                "answer": 0,
            },
            {
                "question": "Quel événement oppose Grecs et Perses en 490 av. J.-C. ?",
                "choices": ["La bataille de Marathon", "La bataille de Salamine", "La guerre du Péloponnèse", "La bataille des Thermopyles"],
                "answer": 0,
            },
            {
                "question": "Quelle langue parlaient les habitants de la Rome antique ?",
                "choices": ["Le latin", "Le grec", "L'étrusque", "Le gaulois"],
                "answer": 0,
            },
            {
                "question": "Quel général carthaginois a traversé les Alpes avec des éléphants pour attaquer Rome ?",
                "choices": ["Hannibal", "Scipion", "Jules César", "Pompée"],
                "answer": 0,
            },
        ],
        "Le Moyen Âge": [
            {
                "question": "Quel système socio-économique caractérise le Moyen Âge en Europe ?",
                "choices": ["Le féodalisme", "Le capitalisme", "Le communisme", "Le mercantilisme"],
                "answer": 0,
            },
            {
                "question": "Quel type d'édifice religieux se multiplie en Europe au Moyen Âge (ex. Notre-Dame de Paris) ?",
                "choices": ["Les cathédrales gothiques", "Les temples romains", "Les pagodes", "Les mosquées andalouses"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on les expéditions militaires chrétiennes vers la Terre sainte ?",
                "choices": ["Les croisades", "Les jacqueries", "Les conquêtes", "Les pèlerinages"],
                "answer": 0,
            },
            {
                "question": "Quelle épidémie dévastatrice frappe l'Europe au XIVe siècle ?",
                "choices": ["La peste noire", "La grippe espagnole", "Le choléra", "La variole"],
                "answer": 0,
            },
            {
                "question": "Qui était Charlemagne ?",
                "choices": ["Un empereur franc sacré en 800", "Un roi d'Angleterre", "Un pape médiéval", "Un explorateur viking"],
                "answer": 0,
            },
        ],
        "Les grandes civilisations anciennes": [
            {
                "question": "Quelle civilisation précolombienne a construit le Machu Picchu ?",
                "choices": ["Les Incas", "Les Aztèques", "Les Mayas", "Les Olmèques"],
                "answer": 0,
            },
            {
                "question": "Quelle civilisation utilisait un calendrier précis et a construit des pyramides à degrés en Amérique centrale ?",
                "choices": ["Les Mayas", "Les Incas", "Les Sumériens", "Les Phéniciens"],
                "answer": 0,
            },
            {
                "question": "Quelle civilisation antique est associée à la vallée de l'Indus ?",
                "choices": ["La civilisation harappéenne", "La civilisation minoenne", "La civilisation olmèque", "La civilisation shang"],
                "answer": 0,
            },
            {
                "question": "Quelle civilisation antique est à l'origine de l'invention de la poudre à canon ?",
                "choices": ["La Chine ancienne", "L'Empire romain", "L'Égypte ancienne", "La Grèce antique"],
                "answer": 0,
            },
            {
                "question": "Quel empire précolombien avait pour capitale Tenochtitlan ?",
                "choices": ["L'empire aztèque", "L'empire inca", "L'empire maya", "L'empire olmèque"],
                "answer": 0,
            },
        ],
        "Les rois de France": [
            {
                "question": "Quel roi est surnommé le « Roi Soleil » ?",
                "choices": ["Louis XIV", "Louis XV", "Louis XIII", "Henri IV"],
                "answer": 0,
            },
            {
                "question": "Quel roi de France a promulgué l'édit de Nantes en 1598 ?",
                "choices": ["Henri IV", "François Ier", "Louis XI", "Charles VII"],
                "answer": 0,
            },
            {
                "question": "Quel roi franc est le premier à être sacré empereur par le pape, fondant la dynastie carolingienne ?",
                "choices": ["Charlemagne", "Clovis", "Pépin le Bref", "Hugues Capet"],
                "answer": 0,
            },
            {
                "question": "Quel roi est à l'origine de la dynastie des Capétiens ?",
                "choices": ["Hugues Capet", "Philippe Auguste", "Saint Louis", "Charles Martel"],
                "answer": 0,
            },
            {
                "question": "Quel roi de France a été sacré grâce à Jeanne d'Arc à Reims en 1429 ?",
                "choices": ["Charles VII", "Charles VI", "Louis XI", "Philippe VI"],
                "answer": 0,
            },
        ],
        "Histoire des religions": [
            {
                "question": "Quelle religion est fondée par le prophète Mahomet au VIIe siècle ?",
                "choices": ["L'islam", "Le christianisme", "Le judaïsme", "Le bouddhisme"],
                "answer": 0,
            },
            {
                "question": "Quelle religion considère Bouddha comme son fondateur ?",
                "choices": ["Le bouddhisme", "L'hindouisme", "Le shintoïsme", "Le taoïsme"],
                "answer": 0,
            },
            {
                "question": "Quel lieu est considéré comme une ville sainte commune aux trois religions monothéistes ?",
                "choices": ["Jérusalem", "La Mecque", "Rome", "Bethléem"],
                "answer": 0,
            },
            {
                "question": "Quelle est la plus ancienne des trois grandes religions monothéistes (judaïsme, christianisme, islam) ?",
                "choices": ["Le judaïsme", "Le christianisme", "L'islam", "Le zoroastrisme"],
                "answer": 0,
            },
            {
                "question": "Vers quelle ville les musulmans se tournent-ils pour prier ?",
                "choices": ["La Mecque", "Médine", "Jérusalem", "Bagdad"],
                "answer": 0,
            },
        ],
        "Les dieux égyptiens": [
            {
                "question": "Quel dieu égyptien est le principal dieu du soleil ?",
                "choices": ["Rê", "Anubis", "Thot", "Seth"],
                "answer": 0,
            },
            {
                "question": "Quel dieu égyptien, à tête de chacal, est associé à l'embaumement et aux morts ?",
                "choices": ["Anubis", "Horus", "Sobek", "Bastet"],
                "answer": 0,
            },
            {
                "question": "Quelle déesse égyptienne est représentée avec une tête de chatte ?",
                "choices": ["Bastet", "Isis", "Hathor", "Nout"],
                "answer": 0,
            },
            {
                "question": "Quel dieu égyptien est le dieu des morts et de la résurrection, époux d'Isis ?",
                "choices": ["Osiris", "Seth", "Horus", "Thot"],
                "answer": 0,
            },
            {
                "question": "Quel dieu égyptien a une tête d'ibis et est le dieu du savoir et de l'écriture ?",
                "choices": ["Thot", "Anubis", "Horus", "Khnoum"],
                "answer": 0,
            },
        ],
        "Les dieux grecs et romains": [
            {
                "question": "Qui est le roi des dieux dans la mythologie grecque ?",
                "choices": ["Zeus", "Poséidon", "Hadès", "Apollon"],
                "answer": 0,
            },
            {
                "question": "Quel est l'équivalent romain de Zeus ?",
                "choices": ["Jupiter", "Mars", "Neptune", "Mercure"],
                "answer": 0,
            },
            {
                "question": "Quelle déesse grecque est associée à la sagesse et à la guerre stratégique ?",
                "choices": ["Athéna", "Aphrodite", "Héra", "Artémis"],
                "answer": 0,
            },
            {
                "question": "Quel dieu romain est le dieu de la guerre ?",
                "choices": ["Mars", "Vulcain", "Bacchus", "Pluton"],
                "answer": 0,
            },
            {
                "question": "Quel dieu grec règne sur les mers ?",
                "choices": ["Poséidon", "Zeus", "Hadès", "Héphaïstos"],
                "answer": 0,
            },
        ],
        "Le monde contemporain (XIXe-XXe siècle)": [
            {
                "question": "Quelle révolution transforme profondément l'Europe au XIXe siècle grâce à la machine à vapeur ?",
                "choices": ["La révolution industrielle", "La révolution numérique", "La révolution verte", "La révolution néolithique"],
                "answer": 0,
            },
            {
                "question": "Quel conflit mondial éclate en 1914 ?",
                "choices": ["La Première Guerre mondiale", "La Seconde Guerre mondiale", "La guerre de Crimée", "La guerre franco-prussienne"],
                "answer": 0,
            },
            {
                "question": "Quel mur symbolise la division de l'Europe pendant la guerre froide, tombé en 1989 ?",
                "choices": ["Le mur de Berlin", "Le mur d'Hadrien", "La muraille de Chine", "Le mur de Chine"],
                "answer": 0,
            },
            {
                "question": "Quelle organisation internationale est fondée en 1945 pour maintenir la paix mondiale ?",
                "choices": ["L'ONU", "L'OTAN", "L'Union européenne", "La Société des Nations"],
                "answer": 0,
            },
            {
                "question": "Quel événement de 1917 change radicalement le régime politique de la Russie ?",
                "choices": ["La révolution russe", "La révolution française", "La révolution industrielle", "La révolution cubaine"],
                "answer": 0,
            },
        ],
        "Renaissance": [
            {
                "question": "Dans quel pays la Renaissance artistique a-t-elle commencé, au XIVe-XVe siècle ?",
                "choices": ["L'Italie", "La France", "L'Espagne", "L'Angleterre"],
                "answer": 0,
            },
            {
                "question": "Quel roi de France a invité Léonard de Vinci à s'installer au Clos Lucé ?",
                "choices": ["François Ier", "Louis XII", "Henri II", "Charles VIII"],
                "answer": 0,
            },
            {
                "question": "Quelle invention de Gutenberg vers 1450 favorise la diffusion des idées de la Renaissance ?",
                "choices": ["L'imprimerie à caractères mobiles", "La boussole", "La poudre à canon", "Le papier"],
                "answer": 0,
            },
            {
                "question": "Quel mouvement intellectuel de la Renaissance remet à l'honneur les textes antiques grecs et latins ?",
                "choices": ["L'humanisme", "Le scolastique", "Le jansénisme", "Le romantisme"],
                "answer": 0,
            },
            {
                "question": "Quel navigateur génois a atteint l'Amérique en 1492 pour le compte de l'Espagne ?",
                "choices": ["Christophe Colomb", "Vasco de Gama", "Fernand de Magellan", "Jacques Cartier"],
                "answer": 0,
            },
        ],
        "Colonisation et décolonisation": [
            {
                "question": "Quelle conférence de 1885 organise le partage de l'Afrique entre puissances européennes ?",
                "choices": ["La conférence de Berlin", "Le congrès de Vienne", "La conférence de Yalta", "Le traité de Versailles"],
                "answer": 0,
            },
            {
                "question": "En quelle décennie la plupart des colonies africaines accèdent-elles à l'indépendance ?",
                "choices": ["Les années 1960", "Les années 1920", "Les années 1980", "Les années 1945"],
                "answer": 0,
            },
            {
                "question": "Quelle guerre oppose la France au mouvement indépendantiste algérien de 1954 à 1962 ?",
                "choices": ["La guerre d'Algérie", "La guerre d'Indochine", "La guerre du Rif", "La guerre des Boers"],
                "answer": 0,
            },
            {
                "question": "Quel dirigeant indien a mené une résistance non-violente contre la colonisation britannique ?",
                "choices": ["Gandhi", "Nehru", "Nelson Mandela", "Hô Chi Minh"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le processus par lequel une colonie devient un État indépendant ?",
                "choices": ["La décolonisation", "L'annexion", "La colonisation", "Le protectorat"],
                "answer": 0,
            },
        ],
        "Première Guerre mondiale": [
            {
                "question": "En quelle année la Première Guerre mondiale a-t-elle commencé ?",
                "choices": ["1914", "1918", "1912", "1916"],
                "answer": 0,
            },
            {
                "question": "Quel assassinat déclenche la Première Guerre mondiale en 1914 ?",
                "choices": ["Celui de l'archiduc François-Ferdinand", "Celui du tsar Nicolas II", "Celui du roi George V", "Celui du Kaiser Guillaume II"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le système de combat qui a caractérisé le front occidental, avec des lignes fortifiées ?",
                "choices": ["La guerre de tranchées", "Le blitzkrieg", "La guerre éclair", "La guerre de mouvement"],
                "answer": 0,
            },
            {
                "question": "Quel traité met officiellement fin à la Première Guerre mondiale en 1919 ?",
                "choices": ["Le traité de Versailles", "Le traité de Yalta", "Le traité de Vienne", "Le traité de Munich"],
                "answer": 0,
            },
            {
                "question": "Quelle bataille de 1916, l'une des plus meurtrières, s'est déroulée dans la Meuse ?",
                "choices": ["La bataille de Verdun", "La bataille de la Somme", "La bataille de la Marne", "La bataille d'Ypres"],
                "answer": 0,
            },
        ],
        "Guerre froide": [
            {
                "question": "Quelles deux superpuissances s'opposent pendant la guerre froide ?",
                "choices": ["Les États-Unis et l'URSS", "La France et l'Allemagne", "Le Royaume-Uni et la Chine", "Le Japon et les États-Unis"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la stratégie qui repose sur la menace des armes nucléaires pour éviter un conflit direct ?",
                "choices": ["La dissuasion nucléaire", "Le désarmement", "La détente", "La non-prolifération"],
                "answer": 0,
            },
            {
                "question": "Quel mur symbolise la division de l'Europe pendant la guerre froide ?",
                "choices": ["Le mur de Berlin", "Le mur d'Hadrien", "La muraille de Chine", "Le mur de Chine"],
                "answer": 0,
            },
            {
                "question": "Quelle crise de 1962 a mis le monde au bord d'une guerre nucléaire ?",
                "choices": ["La crise des missiles de Cuba", "La crise de Suez", "La crise de Berlin", "La crise des otages iraniens"],
                "answer": 0,
            },
            {
                "question": "En quelle année l'URSS s'est-elle dissoute, marquant la fin de la guerre froide ?",
                "choices": ["1991", "1989", "1985", "1993"],
                "answer": 0,
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
        "L'atlas du monde": [
            {
                "question": "Combien de continents compte-t-on généralement dans l'enseignement français ?",
                "choices": ["6", "5", "7", "4"],
                "answer": 0,
            },
            {
                "question": "Quel est le plus grand océan du monde ?",
                "choices": ["L'océan Pacifique", "L'océan Atlantique", "L'océan Indien", "L'océan Arctique"],
                "answer": 0,
            },
            {
                "question": "Quel est le plus grand pays du monde par sa superficie ?",
                "choices": ["La Russie", "Le Canada", "La Chine", "Les États-Unis"],
                "answer": 0,
            },
            {
                "question": "Quelle chaîne de montagnes est la plus haute du monde ?",
                "choices": ["L'Himalaya", "Les Andes", "Les Alpes", "Les Rocheuses"],
                "answer": 0,
            },
            {
                "question": "Quel est le plus petit continent, souvent considéré comme tel ?",
                "choices": ["L'Océanie", "L'Europe", "L'Antarctique", "L'Amérique du Sud"],
                "answer": 0,
            },
        ],
        "Panorama de la France": [
            {
                "question": "Quel est le plus haut sommet de France (et d'Europe occidentale) ?",
                "choices": ["Le Mont Blanc", "Le Puy de Dôme", "Le Mont Ventoux", "Le Pic du Midi"],
                "answer": 0,
            },
            {
                "question": "Quelle mer borde la Côte d'Azur ?",
                "choices": ["La mer Méditerranée", "L'océan Atlantique", "La Manche", "La mer du Nord"],
                "answer": 0,
            },
            {
                "question": "Quel est le plus long fleuve de France ?",
                "choices": ["La Loire", "La Seine", "Le Rhône", "La Garonne"],
                "answer": 0,
            },
            {
                "question": "Quelle région française est surnommée « l'île de Beauté » ?",
                "choices": ["La Corse", "La Bretagne", "La Sardaigne", "La Provence"],
                "answer": 0,
            },
            {
                "question": "Combien de régions compte la France métropolitaine depuis 2016 ?",
                "choices": ["13", "22", "18", "27"],
                "answer": 0,
            },
        ],
        "Le globe terrestre": [
            {
                "question": "Comment appelle-t-on la ligne imaginaire qui divise la Terre en hémisphère nord et sud ?",
                "choices": ["L'équateur", "Le méridien de Greenwich", "Le tropique du Cancer", "Le cercle polaire"],
                "answer": 0,
            },
            {
                "question": "Quelle est la couche la plus interne de la Terre ?",
                "choices": ["Le noyau", "Le manteau", "La croûte", "La lithosphère"],
                "answer": 0,
            },
            {
                "question": "Combien de grandes plaques tectoniques compose-t-on généralement à la surface de la Terre ?",
                "choices": ["Une quinzaine", "Trois", "Cinquante", "Une centaine"],
                "answer": 0,
            },
            {
                "question": "Quel phénomène est provoqué par le mouvement des plaques tectoniques ?",
                "choices": ["Les tremblements de terre", "Les marées", "Les éclipses", "Les aurores boréales"],
                "answer": 0,
            },
            {
                "question": "Quel méridien sert de référence pour les fuseaux horaires (méridien 0°) ?",
                "choices": ["Le méridien de Greenwich", "Le méridien de Paris", "L'équateur", "Le tropique du Capricorne"],
                "answer": 0,
            },
        ],
        "Les pays d'Europe": [
            {
                "question": "Quel est le plus grand pays d'Europe par sa superficie (partie européenne comprise) ?",
                "choices": ["La Russie", "La France", "L'Ukraine", "L'Espagne"],
                "answer": 0,
            },
            {
                "question": "Quelle capitale européenne est traversée par le Danube ?",
                "choices": ["Budapest", "Madrid", "Varsovie", "Lisbonne"],
                "answer": 0,
            },
            {
                "question": "Quel pays scandinave, formé de nombreuses îles et presqu'îles, a Stockholm pour capitale ?",
                "choices": ["La Suède", "La Norvège", "La Finlande", "Le Danemark"],
                "answer": 0,
            },
            {
                "question": "Quel pays d'Europe centrale a Vienne pour capitale ?",
                "choices": ["L'Autriche", "La Hongrie", "La Slovaquie", "La Slovénie"],
                "answer": 0,
            },
            {
                "question": "Quelle monnaie est utilisée par la majorité des pays de l'Union européenne ?",
                "choices": ["L'euro", "Le franc", "Le dollar", "La livre sterling"],
                "answer": 0,
            },
        ],
        "Le continent américain": [
            {
                "question": "Quel est le plus long fleuve d'Amérique du Sud ?",
                "choices": ["L'Amazone", "Le Mississippi", "L'Orénoque", "Le Paraná"],
                "answer": 0,
            },
            {
                "question": "Quelle chaîne de montagnes longe la côte ouest de l'Amérique du Sud ?",
                "choices": ["Les Andes", "Les Rocheuses", "Les Appalaches", "La Sierra Madre"],
                "answer": 0,
            },
            {
                "question": "Quel pays d'Amérique du Sud a le portugais comme langue officielle ?",
                "choices": ["Le Brésil", "L'Argentine", "Le Chili", "La Colombie"],
                "answer": 0,
            },
            {
                "question": "Quelle ville est la capitale des États-Unis ?",
                "choices": ["Washington D.C.", "New York", "Los Angeles", "Chicago"],
                "answer": 0,
            },
            {
                "question": "Quel désert d'Amérique du Sud est l'un des plus arides au monde ?",
                "choices": ["Le désert d'Atacama", "Le désert du Sahara", "Le désert de Gobi", "Le désert du Kalahari"],
                "answer": 0,
            },
        ],
        "Le continent africain": [
            {
                "question": "Quel est le plus grand pays d'Afrique par la superficie ?",
                "choices": ["L'Algérie", "Le Nigeria", "L'Égypte", "L'Afrique du Sud"],
                "answer": 0,
            },
            {
                "question": "Quel désert couvre une grande partie du nord de l'Afrique ?",
                "choices": ["Le Sahara", "Le Kalahari", "Le désert de Namib", "Le désert Arabique"],
                "answer": 0,
            },
            {
                "question": "Quel est le plus haut sommet d'Afrique ?",
                "choices": ["Le Kilimandjaro", "Le mont Kenya", "Les monts Rwenzori", "L'Atlas"],
                "answer": 0,
            },
            {
                "question": "Quel fleuve africain est le plus long du continent ?",
                "choices": ["Le Nil", "Le Congo", "Le Niger", "Le Zambèze"],
                "answer": 0,
            },
            {
                "question": "Environ combien de pays compte le continent africain ?",
                "choices": ["54", "30", "70", "40"],
                "answer": 0,
            },
        ],
        "L'Asie et l'Océanie": [
            {
                "question": "Quel pays d'Asie compte le plus grand nombre d'îles au monde ?",
                "choices": ["L'Indonésie", "Le Japon", "Les Philippines", "La Malaisie"],
                "answer": 0,
            },
            {
                "question": "Quel est le plus haut sommet du monde, situé dans l'Himalaya ?",
                "choices": ["L'Everest", "Le K2", "Le Kangchenjunga", "Le Lhotse"],
                "answer": 0,
            },
            {
                "question": "Quelle île-continent forme l'essentiel de l'Océanie ?",
                "choices": ["L'Australie", "La Nouvelle-Zélande", "La Papouasie-Nouvelle-Guinée", "Fidji"],
                "answer": 0,
            },
            {
                "question": "Quel désert couvre une grande partie du centre de l'Australie ?",
                "choices": ["Le désert du Grand Victoria", "Le Sahara", "Le Gobi", "L'Atacama"],
                "answer": 0,
            },
            {
                "question": "Quelle mer sépare le Japon du continent asiatique ?",
                "choices": ["La mer du Japon", "La mer de Chine", "La mer Jaune", "La mer d'Okhotsk"],
                "answer": 0,
            },
        ],
        "Reliefs et paysages": [
            {
                "question": "Comment appelle-t-on une étendue de terre plate et surélevée ?",
                "choices": ["Un plateau", "Une plaine", "Une vallée", "Un canyon"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on une bande de terre étroite reliant deux masses continentales ?",
                "choices": ["Un isthme", "Un détroit", "Un archipel", "Un delta"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'embouchure d'un fleuve qui se divise en plusieurs bras avant la mer ?",
                "choices": ["Un delta", "Un estuaire", "Un fjord", "Un canyon"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un ensemble d'îles proches les unes des autres ?",
                "choices": ["Un archipel", "Une péninsule", "Un isthme", "Un atoll"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on une avancée de terre entourée d'eau sur trois côtés ?",
                "choices": ["Une péninsule", "Un archipel", "Un isthme", "Un delta"],
                "answer": 0,
            },
        ],
        "Les régions françaises": [
            {
                "question": "Quelle région française a pour capitale Lyon ?",
                "choices": ["Auvergne-Rhône-Alpes", "Occitanie", "Nouvelle-Aquitaine", "Hauts-de-France"],
                "answer": 0,
            },
            {
                "question": "Dans quelle région se trouve Marseille ?",
                "choices": ["Provence-Alpes-Côte d'Azur", "Occitanie", "Corse", "Auvergne-Rhône-Alpes"],
                "answer": 0,
            },
            {
                "question": "Quelle région regroupe l'ancienne Alsace, la Champagne-Ardenne et la Lorraine ?",
                "choices": ["Le Grand Est", "Les Hauts-de-France", "La Bourgogne-Franche-Comté", "L'Île-de-France"],
                "answer": 0,
            },
            {
                "question": "Quelle région a pour capitale Rennes ?",
                "choices": ["La Bretagne", "La Normandie", "Les Pays de la Loire", "Le Centre-Val de Loire"],
                "answer": 0,
            },
            {
                "question": "Dans quelle région se situe Paris ?",
                "choices": ["L'Île-de-France", "Les Hauts-de-France", "Le Centre-Val de Loire", "La Normandie"],
                "answer": 0,
            },
        ],
        "Les capitales du monde": [
            {
                "question": "Quelle est la capitale du Japon ?",
                "choices": ["Tokyo", "Kyoto", "Osaka", "Séoul"],
                "answer": 0,
            },
            {
                "question": "Quelle est la capitale du Canada ?",
                "choices": ["Ottawa", "Toronto", "Montréal", "Vancouver"],
                "answer": 0,
            },
            {
                "question": "Quelle est la capitale de l'Australie ?",
                "choices": ["Canberra", "Sydney", "Melbourne", "Perth"],
                "answer": 0,
            },
            {
                "question": "Quelle est la capitale de l'Égypte ?",
                "choices": ["Le Caire", "Alexandrie", "Louxor", "Gizeh"],
                "answer": 0,
            },
            {
                "question": "Quelle est la capitale du Brésil ?",
                "choices": ["Brasilia", "Rio de Janeiro", "São Paulo", "Salvador"],
                "answer": 0,
            },
        ],
        "Les grands sites naturels de France": [
            {
                "question": "Où se situent les célèbres Gorges du Verdon ?",
                "choices": ["En Provence-Alpes-Côte d'Azur", "En Bretagne", "En Normandie", "En Alsace"],
                "answer": 0,
            },
            {
                "question": "Quel massif montagneux sépare la France de l'Espagne ?",
                "choices": ["Les Pyrénées", "Les Alpes", "Le Massif central", "Le Jura"],
                "answer": 0,
            },
            {
                "question": "Où se situe la célèbre dune du Pilat, la plus haute d'Europe ?",
                "choices": ["En Gironde", "En Bretagne", "En Corse", "Dans les Landes"],
                "answer": 0,
            },
            {
                "question": "Quel parc naturel régional couvre la plus grande partie de la Camargue ?",
                "choices": ["Le Parc naturel régional de Camargue", "Le Parc national des Cévennes", "Le Parc national des Écrins", "Le Parc naturel du Vercors"],
                "answer": 0,
            },
            {
                "question": "Quel volcan endormi domine la chaîne des Puys en Auvergne ?",
                "choices": ["Le Puy de Dôme", "Le Mont Ventoux", "Le Mont Blanc", "Le Piton de la Fournaise"],
                "answer": 0,
            },
        ],
        "Les merveilles du patrimoine mondial": [
            {
                "question": "Quel monument est un mausolée de marbre blanc classé à l'UNESCO en Inde ?",
                "choices": ["Le Taj Mahal", "Le Fort Rouge", "Le palais du Cachemire", "Le temple d'Or"],
                "answer": 0,
            },
            {
                "question": "Quelle cité inca perchée dans les Andes péruviennes est un site classé à l'UNESCO ?",
                "choices": ["Le Machu Picchu", "Cusco", "Nazca", "Lima"],
                "answer": 0,
            },
            {
                "question": "Quelle grande muraille est l'un des monuments les plus longs jamais construits par l'homme ?",
                "choices": ["La Grande Muraille de Chine", "Le mur d'Hadrien", "La muraille de Théodose", "Le mur de Berlin"],
                "answer": 0,
            },
            {
                "question": "Quel site antique jordanien, ville creusée dans la roche rose, est classé au patrimoine mondial ?",
                "choices": ["Pétra", "Palmyre", "Baalbek", "Ebla"],
                "answer": 0,
            },
            {
                "question": "Quelles statues monumentales se dressent sur l'île de Pâques ?",
                "choices": ["Les moaï", "Les sphinx", "Les totems", "Les stèles"],
                "answer": 0,
            },
        ],
        "Les climats du monde": [
            {
                "question": "Quel climat est caractérisé par des étés chauds et secs et des hivers doux et humides, autour de la Méditerranée ?",
                "choices": ["Le climat méditerranéen", "Le climat équatorial", "Le climat polaire", "Le climat continental"],
                "answer": 0,
            },
            {
                "question": "Quel climat se caractérise par des précipitations abondantes toute l'année et une température élevée constante ?",
                "choices": ["Le climat équatorial", "Le climat désertique", "Le climat polaire", "Le climat tempéré"],
                "answer": 0,
            },
            {
                "question": "Quel climat se rencontre aux pôles, avec des températures très basses toute l'année ?",
                "choices": ["Le climat polaire", "Le climat tropical", "Le climat aride", "Le climat océanique"],
                "answer": 0,
            },
            {
                "question": "Quelles lignes imaginaires délimitent la zone intertropicale où le climat est chaud toute l'année ?",
                "choices": ["Les tropiques", "L'équateur seul", "Le cercle polaire", "Le méridien de Greenwich"],
                "answer": 0,
            },
            {
                "question": "Quel climat, présent en France, se caractérise par des saisons bien marquées et des précipitations modérées réparties sur l'année ?",
                "choices": ["Le climat tempéré", "Le climat équatorial", "Le climat désertique", "Le climat polaire"],
                "answer": 0,
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
        "Astronomie": [
            {
                "question": "Comment appelle-t-on notre galaxie ?",
                "choices": ["La Voie lactée", "Andromède", "La galaxie du Tourbillon", "Le Grand Nuage de Magellan"],
                "answer": 0,
            },
            {
                "question": "Qu'est-ce qu'une étoile filante ?",
                "choices": ["Un débris qui brûle en entrant dans l'atmosphère", "Une étoile qui explose", "Une planète qui tombe", "Un satellite artificiel"],
                "answer": 0,
            },
            {
                "question": "Quel astronome italien a perfectionné la lunette astronomique et défendu le modèle héliocentrique ?",
                "choices": ["Galilée", "Copernic", "Kepler", "Newton"],
                "answer": 0,
            },
            {
                "question": "Qu'est-ce qu'un trou noir ?",
                "choices": ["Une région où la gravité est si forte que rien n'en échappe", "Une étoile morte visible", "Un vide total sans matière", "Une comète éteinte"],
                "answer": 0,
            },
            {
                "question": "Qu'est-ce qu'une année-lumière ?",
                "choices": ["Une unité de distance parcourue par la lumière en un an", "Une unité de temps équivalente à un an", "La durée d'une orbite terrestre", "La distance Terre-Lune"],
                "answer": 0,
            },
        ],
        "Les mathématiques": [
            {
                "question": "Quelle est la valeur approximative du nombre pi (π) ?",
                "choices": ["3,14", "2,71", "1,61", "4,13"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un triangle dont un angle mesure 90° ?",
                "choices": ["Un triangle rectangle", "Un triangle isocèle", "Un triangle équilatéral", "Un triangle obtus"],
                "answer": 0,
            },
            {
                "question": "Quel théorème relie les côtés d'un triangle rectangle (a² + b² = c²) ?",
                "choices": ["Le théorème de Pythagore", "Le théorème de Thalès", "Le théorème de Fermat", "Le théorème d'Euclide"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un nombre qui n'est divisible que par 1 et lui-même ?",
                "choices": ["Un nombre premier", "Un nombre pair", "Un nombre entier", "Un nombre rationnel"],
                "answer": 0,
            },
            {
                "question": "Quel mathématicien grec est célèbre pour ses travaux de géométrie compilés dans « Les Éléments » ?",
                "choices": ["Euclide", "Pythagore", "Archimède", "Thalès"],
                "answer": 0,
            },
        ],
        "Énergies et ressources naturelles": [
            {
                "question": "Quelle énergie est produite grâce à la force du vent ?",
                "choices": ["L'énergie éolienne", "L'énergie solaire", "L'énergie hydraulique", "L'énergie géothermique"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on les énergies issues du charbon, du pétrole et du gaz naturel ?",
                "choices": ["Les énergies fossiles", "Les énergies renouvelables", "Les énergies nucléaires", "Les biocarburants"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on une énergie qui se renouvelle naturellement (soleil, vent, eau) ?",
                "choices": ["Une énergie renouvelable", "Une énergie fossile", "Une énergie nucléaire", "Une énergie fissile"],
                "answer": 0,
            },
            {
                "question": "Quel phénomène naturel est exploité par l'énergie géothermique ?",
                "choices": ["La chaleur interne de la Terre", "La force des marées", "La lumière du soleil", "Le vent"],
                "answer": 0,
            },
            {
                "question": "Quel métal est principalement utilisé comme combustible dans les centrales nucléaires ?",
                "choices": ["L'uranium", "Le fer", "Le cuivre", "L'aluminium"],
                "answer": 0,
            },
        ],
        "La médecine": [
            {
                "question": "Qui a découvert la pénicilline, premier antibiotique, en 1928 ?",
                "choices": ["Alexander Fleming", "Louis Pasteur", "Marie Curie", "Robert Koch"],
                "answer": 0,
            },
            {
                "question": "Quel scientifique français a mis au point le vaccin contre la rage ?",
                "choices": ["Louis Pasteur", "Alexander Fleming", "Claude Bernard", "Ambroise Paré"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'inoculation d'une forme atténuée d'un agent infectieux pour prévenir une maladie ?",
                "choices": ["La vaccination", "L'antibiothérapie", "La chimiothérapie", "La transfusion"],
                "answer": 0,
            },
            {
                "question": "Quel organe est directement lié à la production d'insuline et au diabète ?",
                "choices": ["Le pancréas", "Le foie", "Les reins", "Le cœur"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le médecin spécialiste du cœur ?",
                "choices": ["Un cardiologue", "Un neurologue", "Un pneumologue", "Un dermatologue"],
                "answer": 0,
            },
        ],
        "Les origines de la Terre": [
            {
                "question": "Il y a environ combien d'années la Terre s'est-elle formée ?",
                "choices": ["4,5 milliards d'années", "100 millions d'années", "10 000 ans", "1 milliard d'années"],
                "answer": 0,
            },
            {
                "question": "Quelle ère géologique se termine par la disparition des dinosaures ?",
                "choices": ["Le Crétacé", "Le Jurassique", "Le Trias", "Le Cambrien"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la théorie selon laquelle les continents actuels formaient autrefois un seul bloc, la Pangée ?",
                "choices": ["La dérive des continents", "Le Big Bang", "La tectonique des glaces", "L'effet de serre"],
                "answer": 0,
            },
            {
                "question": "Quel événement est considéré comme responsable de l'extinction des dinosaures il y a 66 millions d'années ?",
                "choices": ["La chute d'un astéroïde", "Une guerre entre espèces", "Le réchauffement climatique actuel", "Une éruption volcanique en France"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'étude des fossiles ?",
                "choices": ["La paléontologie", "La géologie", "L'archéologie", "La biologie"],
                "answer": 0,
            },
        ],
        "Une histoire du vivant": [
            {
                "question": "Qui a formulé la théorie de l'évolution par sélection naturelle ?",
                "choices": ["Charles Darwin", "Gregor Mendel", "Louis Pasteur", "Jean-Baptiste Lamarck"],
                "answer": 0,
            },
            {
                "question": "Comment s'appelle le processus par lequel les espèces évoluent au fil des générations ?",
                "choices": ["L'évolution", "La mutation", "La reproduction", "La photosynthèse"],
                "answer": 0,
            },
            {
                "question": "Quel type d'organisme est considéré comme la première forme de vie sur Terre ?",
                "choices": ["Un organisme unicellulaire (bactérie)", "Un dinosaure", "Un poisson", "Un mammifère"],
                "answer": 0,
            },
            {
                "question": "Quel scientifique est le fondateur de la génétique moderne grâce à ses travaux sur les petits pois ?",
                "choices": ["Gregor Mendel", "Charles Darwin", "Louis Pasteur", "James Watson"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'ensemble des espèces ayant totalement disparu ?",
                "choices": ["Les espèces éteintes", "Les espèces invasives", "Les espèces endémiques", "Les espèces protégées"],
                "answer": 0,
            },
        ],
        "Dans le laboratoire des sciences": [
            {
                "question": "Quel instrument permet d'observer des objets trop petits pour être vus à l'œil nu ?",
                "choices": ["Le microscope", "Le télescope", "Le baromètre", "Le sismographe"],
                "answer": 0,
            },
            {
                "question": "Quelle scientifique est célèbre pour ses travaux sur la radioactivité et a reçu deux prix Nobel ?",
                "choices": ["Marie Curie", "Ada Lovelace", "Rosalind Franklin", "Lise Meitner"],
                "answer": 0,
            },
            {
                "question": "Quelle unité mesure la température dans le système international ?",
                "choices": ["Le kelvin", "Le watt", "Le joule", "Le pascal"],
                "answer": 0,
            },
            {
                "question": "Quel appareil sert à mesurer la pression atmosphérique ?",
                "choices": ["Le baromètre", "Le thermomètre", "L'hygromètre", "L'anémomètre"],
                "answer": 0,
            },
            {
                "question": "Quelle réaction chimique se produit lorsqu'une substance se combine avec l'oxygène en dégageant chaleur et lumière ?",
                "choices": ["La combustion", "La fermentation", "L'oxydation lente", "La dissolution"],
                "answer": 0,
            },
        ],
        "Physique": [
            {
                "question": "Quel physicien a formulé les lois de la gravitation universelle ?",
                "choices": ["Isaac Newton", "Albert Einstein", "Galilée", "Niels Bohr"],
                "answer": 0,
            },
            {
                "question": "Quelle est l'unité de mesure de la force dans le système international ?",
                "choices": ["Le newton", "Le joule", "Le watt", "Le pascal"],
                "answer": 0,
            },
            {
                "question": "Quelle théorie d'Einstein relie l'espace, le temps et la gravité ?",
                "choices": ["La relativité générale", "La mécanique quantique", "La thermodynamique", "L'électromagnétisme"],
                "answer": 0,
            },
            {
                "question": "Quelle grandeur physique se mesure en degrés Celsius ou en kelvins ?",
                "choices": ["La température", "La pression", "La masse", "La vitesse"],
                "answer": 0,
            },
            {
                "question": "Quelle est, en ordre de grandeur, la vitesse de la lumière dans le vide ?",
                "choices": ["Environ 300 000 km/s", "Environ 30 000 km/s", "Environ 3 000 km/s", "Environ 3 000 000 km/s"],
                "answer": 0,
            },
        ],
        "Écologie et environnement": [
            {
                "question": "Comment appelle-t-on l'ensemble formé par les êtres vivants et leur milieu naturel en interaction ?",
                "choices": ["Un écosystème", "Une biosphère", "Une biocénose", "Un biotope"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le recyclage naturel de l'eau entre océans, atmosphère et sols ?",
                "choices": ["Le cycle de l'eau", "L'effet de serre", "La photosynthèse", "L'évapotranspiration"],
                "answer": 0,
            },
            {
                "question": "Quel gaz est le principal responsable de l'effet de serre additionnel d'origine humaine ?",
                "choices": ["Le dioxyde de carbone (CO2)", "L'oxygène", "L'azote", "L'hydrogène"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on une espèce animale ou végétale en danger de disparition ?",
                "choices": ["Une espèce menacée", "Une espèce invasive", "Une espèce endémique", "Une espèce domestique"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on les trois gestes pour réduire les déchets : réduire, réutiliser, recycler ?",
                "choices": ["Les 3R", "Le tri sélectif", "Le compostage", "L'économie circulaire"],
                "answer": 0,
            },
        ],
        "Génétique": [
            {
                "question": "Quelle molécule porte l'information génétique dans les cellules ?",
                "choices": ["L'ADN", "L'ARN", "Les protéines", "Les lipides"],
                "answer": 0,
            },
            {
                "question": "Quel moine autrichien est considéré comme le père de la génétique moderne ?",
                "choices": ["Gregor Mendel", "Charles Darwin", "Louis Pasteur", "James Watson"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'unité de base de l'hérédité portée par l'ADN ?",
                "choices": ["Le gène", "Le chromosome", "La cellule", "L'enzyme"],
                "answer": 0,
            },
            {
                "question": "Combien de paires de chromosomes possède une cellule humaine normale ?",
                "choices": ["23", "22", "24", "46"],
                "answer": 0,
            },
            {
                "question": "Quelle structure en double hélice a été décrite par Watson et Crick en 1953 ?",
                "choices": ["L'ADN", "L'ARN messager", "Le ribosome", "La protéine"],
                "answer": 0,
            },
        ],
        "Le cerveau humain": [
            {
                "question": "Combien d'hémisphères possède le cerveau humain ?",
                "choices": ["2", "1", "3", "4"],
                "answer": 0,
            },
            {
                "question": "Quelle partie du cerveau est responsable de la coordination des mouvements et de l'équilibre ?",
                "choices": ["Le cervelet", "Le cortex", "L'hypothalamus", "Le bulbe rachidien"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on les cellules nerveuses qui transmettent l'information dans le cerveau ?",
                "choices": ["Les neurones", "Les globules rouges", "Les hépatocytes", "Les ostéoblastes"],
                "answer": 0,
            },
            {
                "question": "Quelle partie du cerveau gère les fonctions vitales comme la respiration ?",
                "choices": ["Le tronc cérébral", "Le cortex préfrontal", "L'hippocampe", "Le cervelet"],
                "answer": 0,
            },
            {
                "question": "Quelle structure du cerveau joue un rôle central dans la mémoire ?",
                "choices": ["L'hippocampe", "Le cervelet", "Le thalamus", "L'amygdale"],
                "answer": 0,
            },
        ],
        "Informatique": [
            {
                "question": "Quelle unité mesure la quantité d'information numérique de base (0 ou 1) ?",
                "choices": ["Le bit", "L'octet", "Le pixel", "Le hertz"],
                "answer": 0,
            },
            {
                "question": "Combien de bits compose un octet ?",
                "choices": ["8", "4", "16", "2"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le programme qui gère les ressources d'un ordinateur (Windows, macOS, Linux...) ?",
                "choices": ["Le système d'exploitation", "Le navigateur", "Le pilote", "Le compilateur"],
                "answer": 0,
            },
            {
                "question": "Quel langage de programmation est très utilisé pour l'intelligence artificielle et la science des données ?",
                "choices": ["Python", "HTML", "SQL", "CSS"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un programme malveillant qui se propage automatiquement pour infecter des ordinateurs ?",
                "choices": ["Un virus informatique", "Un pare-feu", "Un antivirus", "Un cookie"],
                "answer": 0,
            },
        ],
        "Volcans et séismes": [
            {
                "question": "Comment appelle-t-on le point de la surface terrestre situé à la verticale du foyer d'un séisme ?",
                "choices": ["L'épicentre", "L'hypocentre", "Le magma", "Le cratère"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la roche en fusion qui s'écoule à la surface lors d'une éruption volcanique ?",
                "choices": ["La lave", "Le magma", "Le basalte", "Le granite"],
                "answer": 0,
            },
            {
                "question": "Quelle échelle mesure la magnitude d'un séisme ?",
                "choices": ["L'échelle de Richter", "L'échelle de Beaufort", "L'échelle de Celsius", "L'échelle de Kelvin"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la zone qui concentre la majorité des volcans et séismes autour de l'océan Pacifique ?",
                "choices": ["La ceinture de feu du Pacifique", "La faille de San Andreas", "La dorsale médio-atlantique", "Le point chaud d'Hawaï"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un volcan qui n'est plus entré en éruption depuis très longtemps mais pourrait se réveiller ?",
                "choices": ["Un volcan endormi", "Un volcan éteint", "Un volcan actif", "Un geyser"],
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
        "Littérature mondiale": [
            {
                "question": "Qui a écrit « Don Quichotte » ?",
                "choices": ["Miguel de Cervantès", "Dante Alighieri", "William Shakespeare", "Johann Wolfgang von Goethe"],
                "answer": 0,
            },
            {
                "question": "Qui est l'auteur de « Roméo et Juliette » ?",
                "choices": ["William Shakespeare", "Molière", "Victor Hugo", "Oscar Wilde"],
                "answer": 0,
            },
            {
                "question": "Qui a écrit « Crime et Châtiment » ?",
                "choices": ["Fiodor Dostoïevski", "Léon Tolstoï", "Anton Tchekhov", "Nicolas Gogol"],
                "answer": 0,
            },
            {
                "question": "Quel écrivain britannique a créé le détective Sherlock Holmes ?",
                "choices": ["Arthur Conan Doyle", "Agatha Christie", "Charles Dickens", "Oscar Wilde"],
                "answer": 0,
            },
            {
                "question": "Qui a écrit « Cent ans de solitude » ?",
                "choices": ["Gabriel García Márquez", "Pablo Neruda", "Jorge Luis Borges", "Mario Vargas Llosa"],
                "answer": 0,
            },
        ],
        "Le musée de l'art": [
            {
                "question": "Dans quelle ville se trouve le musée du Louvre ?",
                "choices": ["Paris", "Londres", "Rome", "Madrid"],
                "answer": 0,
            },
            {
                "question": "Quel artiste a peint le plafond de la chapelle Sixtine ?",
                "choices": ["Michel-Ange", "Léonard de Vinci", "Raphaël", "Le Caravage"],
                "answer": 0,
            },
            {
                "question": "Quel mouvement artistique du XXe siècle, initié notamment par Picasso, représente des formes géométriques et une perspective éclatée ?",
                "choices": ["Le cubisme", "L'impressionnisme", "Le romantisme", "Le baroque"],
                "answer": 0,
            },
            {
                "question": "Quelle célèbre statue antique, découverte sans bras, est exposée au Louvre ?",
                "choices": ["La Vénus de Milo", "Le Discobole", "Le Penseur", "La Victoire de Samothrace"],
                "answer": 0,
            },
            {
                "question": "Quel peintre néerlandais est célèbre pour « La Jeune Fille à la perle » ?",
                "choices": ["Johannes Vermeer", "Rembrandt", "Vincent van Gogh", "Pieter Bruegel"],
                "answer": 0,
            },
        ],
        "Théâtre et cinéma": [
            {
                "question": "Quel dramaturge anglais est l'auteur de « Hamlet » ?",
                "choices": ["William Shakespeare", "Christopher Marlowe", "Oscar Wilde", "George Bernard Shaw"],
                "answer": 0,
            },
            {
                "question": "Quel réalisateur est connu pour des films comme « Psychose » et « Les Oiseaux » ?",
                "choices": ["Alfred Hitchcock", "Steven Spielberg", "Stanley Kubrick", "Orson Welles"],
                "answer": 0,
            },
            {
                "question": "Quelle récompense prestigieuse est décernée chaque année au Festival de Cannes ?",
                "choices": ["La Palme d'or", "L'Oscar", "Le César", "Le Lion d'or"],
                "answer": 0,
            },
            {
                "question": "Quel théâtre parisien historique, fondé par la troupe de Molière, est aujourd'hui une institution nationale ?",
                "choices": ["La Comédie-Française", "L'Opéra Garnier", "Le Théâtre du Châtelet", "Le Théâtre de l'Odéon"],
                "answer": 0,
            },
            {
                "question": "Quel réalisateur français a créé « Le Fabuleux Destin d'Amélie Poulain » ?",
                "choices": ["Jean-Pierre Jeunet", "Luc Besson", "François Truffaut", "Jean-Luc Godard"],
                "answer": 0,
            },
        ],
        "Musique": [
            {
                "question": "Quel compositeur allemand, devenu sourd, a composé la « Neuvième Symphonie » ?",
                "choices": ["Ludwig van Beethoven", "Wolfgang Amadeus Mozart", "Johann Sebastian Bach", "Franz Schubert"],
                "answer": 0,
            },
            {
                "question": "Combien de cordes possède une guitare classique standard ?",
                "choices": ["6", "4", "8", "12"],
                "answer": 0,
            },
            {
                "question": "Quel compositeur autrichien, enfant prodige du classicisme, est l'auteur de « La Flûte enchantée » ?",
                "choices": ["Wolfgang Amadeus Mozart", "Ludwig van Beethoven", "Joseph Haydn", "Antonio Vivaldi"],
                "answer": 0,
            },
            {
                "question": "Quel genre musical est né aux États-Unis au début du XXe siècle, mêlant influences africaines et européennes avec l'improvisation ?",
                "choices": ["Le jazz", "Le rock", "Le reggae", "La musique classique"],
                "answer": 0,
            },
            {
                "question": "Quel instrument à clavier fonctionne en pinçant les cordes, ancêtre du piano ?",
                "choices": ["Le clavecin", "Le piano", "L'orgue", "L'accordéon"],
                "answer": 0,
            },
        ],
        "Poésie": [
            {
                "question": "Quel poète français est l'auteur des « Fleurs du mal » ?",
                "choices": ["Charles Baudelaire", "Arthur Rimbaud", "Paul Verlaine", "Victor Hugo"],
                "answer": 0,
            },
            {
                "question": "Quelle forme poétique fixe comporte 14 vers ?",
                "choices": ["Le sonnet", "La ballade", "L'ode", "Le haïku"],
                "answer": 0,
            },
            {
                "question": "Quel poème japonais très court en trois vers évoque souvent la nature ?",
                "choices": ["Le haïku", "Le sonnet", "La ballade", "L'élégie"],
                "answer": 0,
            },
            {
                "question": "Quel poète français a écrit « Le Dormeur du val » ?",
                "choices": ["Arthur Rimbaud", "Charles Baudelaire", "Paul Verlaine", "Stéphane Mallarmé"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la répétition d'un même son à la fin de deux ou plusieurs vers ?",
                "choices": ["La rime", "La strophe", "La césure", "L'allitération"],
                "answer": 0,
            },
        ],
        "Danse": [
            {
                "question": "Quelle danse de couple d'origine argentine est reconnue au patrimoine de l'UNESCO ?",
                "choices": ["Le tango", "La salsa", "Le flamenco", "La valse"],
                "answer": 0,
            },
            {
                "question": "Quelle danse classique se pratique généralement sur pointes ?",
                "choices": ["Le ballet", "Le tango", "Le hip-hop", "Le flamenco"],
                "answer": 0,
            },
            {
                "question": "Quelle danse espagnole s'accompagne souvent de guitare et de castagnettes ?",
                "choices": ["Le flamenco", "Le tango", "La salsa", "La samba"],
                "answer": 0,
            },
            {
                "question": "Quel style de danse est né dans les rues des quartiers afro-américains et latinos de New York dans les années 1970 ?",
                "choices": ["Le hip-hop", "Le ballet", "La valse", "Le flamenco"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un spectacle de danse classique raconté en musique, comme « Le Lac des cygnes » ?",
                "choices": ["Un ballet", "Un opéra", "Une comédie musicale", "Un récital"],
                "answer": 0,
            },
        ],
        "Architecture": [
            {
                "question": "Quel style architectural médiéval est caractérisé par des arcs brisés et de hautes voûtes, comme à Notre-Dame de Paris ?",
                "choices": ["Le gothique", "Le roman", "Le baroque", "Le néoclassique"],
                "answer": 0,
            },
            {
                "question": "Quel architecte est célèbre pour la Sagrada Família à Barcelone ?",
                "choices": ["Antoni Gaudí", "Le Corbusier", "Gustave Eiffel", "Frank Lloyd Wright"],
                "answer": 0,
            },
            {
                "question": "Quel style architectural précède le gothique, avec des arcs en plein cintre et des murs épais ?",
                "choices": ["Le roman", "Le baroque", "Le gothique flamboyant", "L'Art nouveau"],
                "answer": 0,
            },
            {
                "question": "Qui a conçu la tour qui porte son nom, construite pour l'Exposition universelle de 1889 à Paris ?",
                "choices": ["Gustave Eiffel", "Georges-Eugène Haussmann", "Antoni Gaudí", "Le Corbusier"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un édifice religieux musulman ?",
                "choices": ["Une mosquée", "Une synagogue", "Une cathédrale", "Une pagode"],
                "answer": 0,
            },
        ],
        "Bande dessinée": [
            {
                "question": "Quel dessinateur belge a créé Tintin ?",
                "choices": ["Hergé", "René Goscinny", "Albert Uderzo", "Franquin"],
                "answer": 0,
            },
            {
                "question": "Qui a créé le personnage d'Astérix avec Albert Uderzo ?",
                "choices": ["René Goscinny", "Hergé", "Franquin", "Peyo"],
                "answer": 0,
            },
            {
                "question": "Dans quel pays la bande dessinée est-elle appelée « manga » ?",
                "choices": ["Le Japon", "La Corée du Sud", "La Chine", "Les États-Unis"],
                "answer": 0,
            },
            {
                "question": "Quel petit village gaulois résiste encore et toujours à l'envahisseur romain dans la BD d'Uderzo et Goscinny ?",
                "choices": ["Le village d'Astérix", "Moulinsart", "Champignac", "Marcinelle"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le célèbre festival de bande dessinée qui se tient chaque année en Charente ?",
                "choices": ["Le Festival d'Angoulême", "Le Festival de Cannes", "Le Salon du Livre", "Japan Expo"],
                "answer": 0,
            },
        ],
        "Photographie": [
            {
                "question": "Quel procédé photographique du XIXe siècle porte le nom de son inventeur français, Louis Daguerre ?",
                "choices": ["Le daguerréotype", "Le calotype", "La photographie argentique couleur", "Le Polaroid"],
                "answer": 0,
            },
            {
                "question": "Quel photographe français est considéré comme l'auteur de la première photographie permanente connue ?",
                "choices": ["Nicéphore Niépce", "Louis Daguerre", "Man Ray", "Henri Cartier-Bresson"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'ouverture qui règle la quantité de lumière entrant dans un appareil photo ?",
                "choices": ["Le diaphragme", "L'obturateur", "Le viseur", "Le capteur"],
                "answer": 0,
            },
            {
                "question": "Quel photographe français est célèbre pour le concept de « l'instant décisif » ?",
                "choices": ["Henri Cartier-Bresson", "Robert Doisneau", "Man Ray", "Nadar"],
                "answer": 0,
            },
            {
                "question": "Quel type de photographie capture des images en très gros plan de sujets minuscules ?",
                "choices": ["La macrophotographie", "La photographie aérienne", "Le panoramique", "Le sténopé"],
                "answer": 0,
            },
        ],
        "Sculpture": [
            {
                "question": "Qui a sculpté « Le Penseur » ?",
                "choices": ["Auguste Rodin", "Michel-Ange", "Camille Claudel", "Constantin Brâncuși"],
                "answer": 0,
            },
            {
                "question": "Qui a sculpté le « David », statue emblématique de la Renaissance italienne ?",
                "choices": ["Michel-Ange", "Donatello", "Léonard de Vinci", "Bernin"],
                "answer": 0,
            },
            {
                "question": "Quelle technique de sculpture consiste à retirer de la matière (pierre, bois) pour façonner une forme ?",
                "choices": ["La taille directe", "Le moulage", "La fonte", "Le modelage"],
                "answer": 0,
            },
            {
                "question": "Quelle sculptrice française, élève et compagne de Rodin, est célèbre pour « La Valse » ?",
                "choices": ["Camille Claudel", "Niki de Saint Phalle", "Louise Bourgeois", "Germaine Richier"],
                "answer": 0,
            },
            {
                "question": "Quelle statue monumentale, offerte par la France aux États-Unis en 1886, orne le port de New York ?",
                "choices": ["La Statue de la Liberté", "Le Christ Rédempteur", "La Petite Sirène", "Le Colosse de Rhodes"],
                "answer": 0,
            },
        ],
        "Contes et légendes": [
            {
                "question": "Qui a écrit les célèbres contes « Cendrillon » et « Le Petit Chaperon rouge » en France au XVIIe siècle ?",
                "choices": ["Charles Perrault", "Jean de La Fontaine", "Les frères Grimm", "Hans Christian Andersen"],
                "answer": 0,
            },
            {
                "question": "Quels frères allemands ont collecté des contes populaires comme « Blanche-Neige » et « Hansel et Gretel » ?",
                "choices": ["Les frères Grimm", "Les frères Lumière", "Les frères Montgolfier", "Les frères Goncourt"],
                "answer": 0,
            },
            {
                "question": "Quel écrivain danois est l'auteur de « La Petite Sirène » et du « Vilain Petit Canard » ?",
                "choices": ["Hans Christian Andersen", "Charles Perrault", "Lewis Carroll", "Jules Verne"],
                "answer": 0,
            },
            {
                "question": "Quel roi légendaire britannique est associé aux chevaliers de la Table ronde ?",
                "choices": ["Le roi Arthur", "Le roi Richard Cœur de Lion", "Le roi Alfred le Grand", "Le roi Henri VIII"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un récit merveilleux transmis de génération en génération, souvent avec une morale ?",
                "choices": ["Un conte", "Un roman", "Une biographie", "Un essai"],
                "answer": 0,
            },
        ],
        "Opéra": [
            {
                "question": "Quel compositeur allemand est l'auteur de l'opéra « La Flûte enchantée » ?",
                "choices": ["Wolfgang Amadeus Mozart", "Ludwig van Beethoven", "Richard Wagner", "Giuseppe Verdi"],
                "answer": 0,
            },
            {
                "question": "Quel compositeur italien a écrit « La Traviata » et « Aïda » ?",
                "choices": ["Giuseppe Verdi", "Gioachino Rossini", "Giacomo Puccini", "Gaetano Donizetti"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un air chanté en solo par un personnage d'opéra ?",
                "choices": ["Un air (ou aria)", "Un chœur", "Un récitatif", "Un duo"],
                "answer": 0,
            },
            {
                "question": "Quel opéra parisien est célèbre pour son architecture du XIXe siècle et son plafond peint par Chagall ?",
                "choices": ["L'Opéra Garnier", "L'Opéra Bastille", "La Scala", "Le Bolchoï"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la voix masculine la plus aiguë en chant lyrique ?",
                "choices": ["Le ténor", "La basse", "Le baryton", "Le contralto"],
                "answer": 0,
            },
        ],
        "Street art et graffiti": [
            {
                "question": "Quel artiste britannique anonyme est célèbre pour ses œuvres de street art engagées au pochoir ?",
                "choices": ["Banksy", "Keith Haring", "Jean-Michel Basquiat", "Shepard Fairey"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la technique consistant à peindre à travers une forme découpée pour reproduire un motif ?",
                "choices": ["Le pochoir", "Le collage", "La fresque", "La mosaïque"],
                "answer": 0,
            },
            {
                "question": "Quel artiste américain, proche du mouvement hip-hop des années 1980, est connu pour ses figures dansantes au trait simple ?",
                "choices": ["Keith Haring", "Banksy", "Andy Warhol", "Jean-Michel Basquiat"],
                "answer": 0,
            },
            {
                "question": "Dans quelle ville des États-Unis le mouvement du graffiti moderne est-il né dans les années 1970 ?",
                "choices": ["New York", "Los Angeles", "Chicago", "Miami"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on une peinture murale de grande taille réalisée directement sur un mur ?",
                "choices": ["Une fresque", "Une gravure", "Une enluminure", "Une tapisserie"],
                "answer": 0,
            },
        ],
        "Cirque": [
            {
                "question": "Comment appelle-t-on l'artiste qui marche en équilibre sur un fil tendu en hauteur ?",
                "choices": ["Un funambule", "Un trapéziste", "Un jongleur", "Un contorsionniste"],
                "answer": 0,
            },
            {
                "question": "Quelle compagnie québécoise a révolutionné le cirque moderne sans animaux depuis les années 1980 ?",
                "choices": ["Le Cirque du Soleil", "Le Cirque Pinder", "Le Cirque Bouglione", "Le Cirque Medrano"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'artiste qui dirige et présente le spectacle dans un cirque traditionnel ?",
                "choices": ["Le maître de piste (monsieur Loyal)", "Le dompteur", "L'acrobate", "Le clown"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la discipline acrobatique où l'artiste évolue suspendu à deux tissus tendus depuis le plafond ?",
                "choices": ["Le tissu aérien", "Le trapèze fixe", "L'équilibre sur mains", "Le monocycle"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'artiste comique au nez rouge et au costume extravagant, figure emblématique du cirque ?",
                "choices": ["Le clown", "L'acrobate", "Le dompteur", "L'illusionniste"],
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
        "Sports et disciplines": [
            {
                "question": "Combien de joueurs compte une équipe de basketball sur le terrain ?",
                "choices": ["5", "6", "7", "11"],
                "answer": 0,
            },
            {
                "question": "Dans quel sport utilise-t-on un club pour envoyer une balle dans un trou ?",
                "choices": ["Le golf", "Le hockey", "Le cricket", "Le tennis"],
                "answer": 0,
            },
            {
                "question": "Quel sport se pratique sur un ring avec des gants ?",
                "choices": ["La boxe", "Le judo", "L'escrime", "La lutte"],
                "answer": 0,
            },
            {
                "question": "Dans quel sport utilise-t-on une raquette et un volant ?",
                "choices": ["Le badminton", "Le tennis", "Le squash", "Le tennis de table"],
                "answer": 0,
            },
            {
                "question": "Combien de sets faut-il gagner pour remporter un match de tennis en cinq sets gagnants (Grand Chelem masculin) ?",
                "choices": ["3", "2", "4", "5"],
                "answer": 0,
            },
        ],
        "Tennis": [
            {
                "question": "Sur quelle surface se joue le tournoi de Roland-Garros ?",
                "choices": ["La terre battue", "Le gazon", "Le dur", "La moquette"],
                "answer": 0,
            },
            {
                "question": "Combien de Grands Chelems existe-t-il dans le tennis professionnel ?",
                "choices": ["4", "3", "5", "6"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le geste qui consiste à frapper la balle avant qu'elle ne rebondisse ?",
                "choices": ["La volée", "Le service", "Le smash", "Le lob"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un score de 40-40 au tennis ?",
                "choices": ["Égalité (deuce)", "Avantage", "Jeu blanc", "Bris d'égalité"],
                "answer": 0,
            },
            {
                "question": "Sur quelle surface se joue le tournoi de Wimbledon ?",
                "choices": ["Le gazon", "La terre battue", "Le dur", "Le synthétique"],
                "answer": 0,
            },
        ],
        "Cyclisme": [
            {
                "question": "Comment s'appelle la plus célèbre course cycliste française par étapes ?",
                "choices": ["Le Tour de France", "Le Giro", "La Vuelta", "Paris-Roubaix"],
                "answer": 0,
            },
            {
                "question": "Quel maillot porte le leader du classement général au Tour de France ?",
                "choices": ["Le maillot jaune", "Le maillot vert", "Le maillot à pois", "Le maillot blanc"],
                "answer": 0,
            },
            {
                "question": "Quel maillot récompense le meilleur grimpeur au Tour de France ?",
                "choices": ["Le maillot à pois", "Le maillot jaune", "Le maillot vert", "Le maillot blanc"],
                "answer": 0,
            },
            {
                "question": "Quelle célèbre course cycliste italienne par étapes se déroule au printemps ?",
                "choices": ["Le Giro d'Italia", "La Vuelta", "Le Tour de France", "Paris-Nice"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on une course cycliste d'un seul jour, comme Paris-Roubaix ?",
                "choices": ["Une classique", "Une étape", "Un contre-la-montre", "Un critérium"],
                "answer": 0,
            },
        ],
        "Sports d'hiver": [
            {
                "question": "Quel sport d'hiver combine le ski de fond et le tir à la carabine ?",
                "choices": ["Le biathlon", "Le combiné nordique", "Le ski alpin", "Le patinage de vitesse"],
                "answer": 0,
            },
            {
                "question": "Sur quel type de terrain se pratique le ski alpin ?",
                "choices": ["Une piste enneigée en descente", "Une patinoire", "Une piste d'athlétisme", "Un anneau de glace"],
                "answer": 0,
            },
            {
                "question": "Quel sport d'hiver se pratique sur une patinoire avec des pierres et des balais ?",
                "choices": ["Le curling", "Le hockey sur glace", "Le patinage artistique", "Le bobsleigh"],
                "answer": 0,
            },
            {
                "question": "Quel sport d'hiver se joue en équipe avec un palet sur une patinoire ?",
                "choices": ["Le hockey sur glace", "Le curling", "Le patinage de vitesse", "Le ski de fond"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la discipline de ski où l'on saute depuis un tremplin ?",
                "choices": ["Le saut à ski", "Le ski de fond", "Le slalom", "Le combiné nordique"],
                "answer": 0,
            },
        ],
        "Basketball": [
            {
                "question": "Dans quel pays le basketball a-t-il été inventé, en 1891 ?",
                "choices": ["Les États-Unis", "Le Canada", "La France", "Le Royaume-Uni"],
                "answer": 0,
            },
            {
                "question": "Combien de points rapporte un panier marqué derrière la ligne à 3 points ?",
                "choices": ["3", "2", "1", "4"],
                "answer": 0,
            },
            {
                "question": "Quelle est la ligue de basketball professionnelle la plus prestigieuse au monde ?",
                "choices": ["La NBA", "La NFL", "La NHL", "La MLB"],
                "answer": 0,
            },
            {
                "question": "Combien de joueurs une équipe de basketball a-t-elle sur le terrain simultanément ?",
                "choices": ["5", "6", "7", "11"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un panier marqué en sautant pour enfoncer le ballon dans le cercle ?",
                "choices": ["Un dunk", "Un lay-up", "Un airball", "Un alley-oop"],
                "answer": 0,
            },
        ],
        "Rugby": [
            {
                "question": "Combien de joueurs titulaires compte une équipe de rugby à XV sur le terrain ?",
                "choices": ["15", "13", "11", "7"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'action de poser le ballon dans l'en-but adverse au rugby ?",
                "choices": ["Un essai", "Un but", "Une transformation", "Une pénalité"],
                "answer": 0,
            },
            {
                "question": "Combien de points rapporte un essai au rugby à XV ?",
                "choices": ["5", "3", "7", "2"],
                "answer": 0,
            },
            {
                "question": "Quel tournoi annuel oppose la France, l'Angleterre, l'Écosse, le pays de Galles, l'Irlande et l'Italie ?",
                "choices": ["Le Tournoi des Six Nations", "La Coupe du monde", "Le Tri Nations", "Le Challenge européen"],
                "answer": 0,
            },
            {
                "question": "Dans quel pays le rugby est-il né, selon la légende, au collège de Rugby ?",
                "choices": ["Le Royaume-Uni", "La France", "L'Afrique du Sud", "La Nouvelle-Zélande"],
                "answer": 0,
            },
        ],
        "Natation": [
            {
                "question": "Quelle nage est considérée comme la plus rapide en compétition ?",
                "choices": ["Le crawl (nage libre)", "La brasse", "Le dos", "Le papillon"],
                "answer": 0,
            },
            {
                "question": "Sur quelle distance se dispute le 100 mètres nage libre ?",
                "choices": ["100 mètres", "50 mètres", "200 mètres", "400 mètres"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'épreuve où un nageur enchaîne les quatre styles de nage ?",
                "choices": ["Le quatre nages individuel", "Le relais 4x100 m", "Le contre-la-montre", "Le combiné"],
                "answer": 0,
            },
            {
                "question": "Quel nageur américain a remporté 23 médailles d'or olympiques, un record ?",
                "choices": ["Michael Phelps", "Mark Spitz", "Ian Thorpe", "Caeleb Dressel"],
                "answer": 0,
            },
            {
                "question": "Quelle nage se caractérise par un mouvement de bras simultané et un battement de jambes en dauphin ?",
                "choices": ["Le papillon", "Le crawl", "La brasse", "Le dos"],
                "answer": 0,
            },
        ],
        "Athlétisme": [
            {
                "question": "Quelle est l'épreuve reine du sprint sur piste ?",
                "choices": ["Le 100 mètres", "Le 400 mètres", "Le 1 500 mètres", "Le marathon"],
                "answer": 0,
            },
            {
                "question": "Quelle distance parcourt un coureur de marathon ?",
                "choices": ["42,195 km", "21 km", "100 km", "30 km"],
                "answer": 0,
            },
            {
                "question": "Quelle épreuve d'athlétisme consiste à franchir une barre le plus haut possible en sautant en arrière ?",
                "choices": ["Le saut en hauteur", "Le saut en longueur", "Le triple saut", "Le saut à la perche"],
                "answer": 0,
            },
            {
                "question": "Combien d'épreuves comporte le décathlon masculin ?",
                "choices": ["10", "7", "8", "12"],
                "answer": 0,
            },
            {
                "question": "Quel athlète jamaïcain a détenu longtemps le record du monde du 100 mètres ?",
                "choices": ["Usain Bolt", "Carl Lewis", "Justin Gatlin", "Tyson Gay"],
                "answer": 0,
            },
        ],
        "Formule 1": [
            {
                "question": "Combien de roues compte une monoplace de Formule 1 ?",
                "choices": ["4", "6", "3", "8"],
                "answer": 0,
            },
            {
                "question": "Quel circuit mythique accueille le Grand Prix de Monaco de Formule 1 chaque année ?",
                "choices": ["Le circuit de Monaco", "Le circuit de Silverstone", "Le circuit de Spa-Francorchamps", "Le Nürburgring"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'arrêt aux stands pour changer les pneus pendant une course ?",
                "choices": ["Le pit-stop", "Le drapeau à damier", "La grille de départ", "Le safety car"],
                "answer": 0,
            },
            {
                "question": "Quel drapeau signale la fin d'une course de Formule 1 ?",
                "choices": ["Le drapeau à damier", "Le drapeau jaune", "Le drapeau rouge", "Le drapeau vert"],
                "answer": 0,
            },
            {
                "question": "Quel pilote français a été plusieurs fois champion du monde de Formule 1 dans les années 1980-1990 ?",
                "choices": ["Alain Prost", "Michael Schumacher", "Ayrton Senna", "Nelson Piquet"],
                "answer": 0,
            },
        ],
        "Boxe": [
            {
                "question": "Comment appelle-t-on l'espace clos entouré de cordes où se déroule un combat de boxe ?",
                "choices": ["Le ring", "L'octogone", "Le tatami", "L'arène"],
                "answer": 0,
            },
            {
                "question": "Combien de rounds compte généralement un championnat du monde de boxe professionnelle ?",
                "choices": ["12", "10", "15", "8"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la victoire obtenue quand l'adversaire ne peut plus se relever avant la fin du compte ?",
                "choices": ["Le knock-out (KO)", "Le décompte", "L'abandon", "La disqualification"],
                "answer": 0,
            },
            {
                "question": "Quel boxeur américain, surnommé « The Greatest », a marqué l'histoire de la boxe dans les années 1960-1970 ?",
                "choices": ["Mohamed Ali", "Mike Tyson", "Joe Frazier", "George Foreman"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la catégorie de poids la plus lourde en boxe ?",
                "choices": ["Les poids lourds", "Les poids plumes", "Les poids welters", "Les poids coqs"],
                "answer": 0,
            },
        ],
        "Golf": [
            {
                "question": "Comment appelle-t-on un coup réalisé en un coup de moins que le par sur un trou ?",
                "choices": ["Un birdie", "Un bogey", "Un eagle", "Un albatros"],
                "answer": 0,
            },
            {
                "question": "Combien de trous compte un parcours de golf standard ?",
                "choices": ["18", "9", "12", "24"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le petit support sur lequel on pose la balle pour le premier coup d'un trou ?",
                "choices": ["Un tee", "Un green", "Un bunker", "Un fairway"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la zone d'herbe courte autour du trou où l'on putte ?",
                "choices": ["Le green", "Le fairway", "Le rough", "Le bunker"],
                "answer": 0,
            },
            {
                "question": "Quel golfeur américain a dominé le circuit professionnel dans les années 2000, avec de nombreuses victoires en tournois majeurs ?",
                "choices": ["Tiger Woods", "Jack Nicklaus", "Arnold Palmer", "Rory McIlroy"],
                "answer": 0,
            },
        ],
        "Volley-ball": [
            {
                "question": "Combien de joueurs par équipe sont sur le terrain au volley-ball (hors remplaçants) ?",
                "choices": ["6", "5", "7", "4"],
                "answer": 0,
            },
            {
                "question": "Combien de points faut-il pour remporter un set au volley-ball (avec deux points d'écart) ?",
                "choices": ["25", "21", "15", "30"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'action de renvoyer violemment le ballon par-dessus le filet vers le camp adverse ?",
                "choices": ["Le smash (ou attaque)", "Le service", "La passe", "Le contre"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le joueur spécialisé en défense, qui ne peut ni attaquer ni bloquer et porte souvent un maillot différent ?",
                "choices": ["Le libéro", "Le passeur", "Le pointu", "Le central"],
                "answer": 0,
            },
            {
                "question": "Quelle variante du volley-ball se joue à deux contre deux sur sable ?",
                "choices": ["Le beach-volley", "Le volley indoor", "Le foot-volley", "Le mini-volley"],
                "answer": 0,
            },
        ],
        "Handball": [
            {
                "question": "Combien de joueurs de champ (hors gardien) une équipe de handball aligne-t-elle sur le terrain ?",
                "choices": ["6", "7", "5", "8"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la zone semi-circulaire devant chaque but où seul le gardien peut évoluer ?",
                "choices": ["La zone (ou surface) de but", "Le rond central", "Le couloir", "Le carré de service"],
                "answer": 0,
            },
            {
                "question": "Dans quels pays le handball moderne s'est-il particulièrement développé et structuré au XXe siècle ?",
                "choices": ["L'Allemagne et les pays scandinaves", "Le Brésil et l'Argentine", "Le Japon et la Corée", "L'Australie et la Nouvelle-Zélande"],
                "answer": 0,
            },
            {
                "question": "Combien de temps dure un match de handball senior (hors prolongation), en deux mi-temps ?",
                "choices": ["60 minutes (2 x 30)", "90 minutes (2 x 45)", "40 minutes (2 x 20)", "80 minutes (2 x 40)"],
                "answer": 0,
            },
            {
                "question": "Quel pays a remporté de nombreux titres mondiaux et olympiques de handball masculin dans les années 2000-2010 ?",
                "choices": ["La France", "L'Allemagne", "L'Espagne", "La Croatie"],
                "answer": 0,
            },
        ],
        "Escrime": [
            {
                "question": "Combien d'armes différentes sont pratiquées en escrime olympique ?",
                "choices": ["3 (fleuret, épée, sabre)", "2", "4", "5"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la protection métallique portée sur le visage par les escrimeurs ?",
                "choices": ["Le masque", "Le casque", "La visière", "Le heaume"],
                "answer": 0,
            },
            {
                "question": "Sur quelle surface se déroule un assaut d'escrime ?",
                "choices": ["La piste", "Le tatami", "Le ring", "Le tapis"],
                "answer": 0,
            },
            {
                "question": "Quelle arme d'escrime permet de toucher l'adversaire sur tout le corps, y compris les jambes ?",
                "choices": ["L'épée", "Le fleuret", "Le sabre", "La rapière"],
                "answer": 0,
            },
            {
                "question": "Quel pays est traditionnellement l'une des grandes nations de l'escrime, avec de nombreux titres olympiques ?",
                "choices": ["La France", "L'Allemagne", "Le Brésil", "La Suède"],
                "answer": 0,
            },
        ],
    },
    "Nature": {
        "Les animaux marins": [
            {
                "question": "Quel est le plus grand animal ayant jamais existé sur Terre ?",
                "choices": ["La baleine bleue", "Le requin blanc", "L'éléphant d'Afrique", "Le calmar géant"],
                "answer": 0,
            },
            {
                "question": "Comment respirent les dauphins ?",
                "choices": ["Avec des poumons, en remontant à la surface", "Avec des branchies, comme les poissons", "Par la peau", "Ils ne respirent pas"],
                "answer": 0,
            },
            {
                "question": "Quel est l'un des poissons les plus rapides des océans ?",
                "choices": ["L'espadon voilier", "Le thon rouge", "Le requin mako", "Le barracuda"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on les petits de la baleine ?",
                "choices": ["Les baleineaux", "Les poulains", "Les veaux", "Les petons"],
                "answer": 0,
            },
            {
                "question": "Quel animal marin est capable de changer de couleur pour se camoufler ?",
                "choices": ["La pieuvre", "La méduse", "L'étoile de mer", "L'oursin"],
                "answer": 0,
            },
        ],
        "Insectes et arachnides": [
            {
                "question": "Combien de pattes possède un insecte ?",
                "choices": ["6", "8", "4", "10"],
                "answer": 0,
            },
            {
                "question": "Combien de pattes possède une araignée ?",
                "choices": ["8", "6", "10", "4"],
                "answer": 0,
            },
            {
                "question": "Quel insecte produit du miel ?",
                "choices": ["L'abeille", "La guêpe", "La fourmi", "Le papillon"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la métamorphose complète d'un papillon (œuf, chenille, chrysalide, adulte) ?",
                "choices": ["La métamorphose complète", "La mue simple", "La nymphose partielle", "La croissance directe"],
                "answer": 0,
            },
            {
                "question": "Les araignées sont-elles des insectes ?",
                "choices": ["Non, ce sont des arachnides", "Oui, ce sont des insectes", "Ce sont des crustacés", "Ce sont des myriapodes"],
                "answer": 0,
            },
        ],
        "Les mammifères terrestres": [
            {
                "question": "Quel est le plus grand mammifère terrestre actuel ?",
                "choices": ["L'éléphant d'Afrique", "Le rhinocéros blanc", "La girafe", "L'hippopotame"],
                "answer": 0,
            },
            {
                "question": "Quel est le mammifère terrestre le plus rapide sur de courtes distances ?",
                "choices": ["Le guépard", "Le lion", "Le cheval", "L'antilope"],
                "answer": 0,
            },
            {
                "question": "Quel est le plus grand animal terrestre à posséder une trompe ?",
                "choices": ["L'éléphant", "Le tapir", "Le phacochère", "Le rhinocéros"],
                "answer": 0,
            },
            {
                "question": "Quel mammifère marsupial australien est le plus connu pour porter ses petits dans une poche ventrale ?",
                "choices": ["Le kangourou", "Le koala", "L'ornithorynque", "Le wombat"],
                "answer": 0,
            },
            {
                "question": "Quel est le plus grand des félins ?",
                "choices": ["Le tigre", "Le lion", "Le léopard", "Le guépard"],
                "answer": 0,
            },
        ],
        "Les oiseaux": [
            {
                "question": "Quel est le plus grand oiseau vivant du monde, qui ne vole pas ?",
                "choices": ["L'autruche", "Le condor", "L'aigle royal", "Le pélican"],
                "answer": 0,
            },
            {
                "question": "Quel oiseau est connu pour ses très longues migrations entre l'Arctique et l'Antarctique ?",
                "choices": ["La sterne arctique", "Le manchot empereur", "Le pigeon voyageur", "L'hirondelle"],
                "answer": 0,
            },
            {
                "question": "Quel est le plus petit oiseau du monde ?",
                "choices": ["Le colibri", "Le moineau", "Le roitelet", "La mésange"],
                "answer": 0,
            },
            {
                "question": "Quel oiseau incapable de voler vit en Antarctique et couve son œuf sur ses pattes ?",
                "choices": ["Le manchot empereur", "L'autruche", "Le kiwi", "Le pingouin torda"],
                "answer": 0,
            },
            {
                "question": "Quel rapace nocturne possède une ouïe très fine et vole silencieusement ?",
                "choices": ["Le hibou", "L'aigle", "Le faucon", "Le vautour"],
                "answer": 0,
            },
        ],
        "Le règne animal": [
            {
                "question": "Comment appelle-t-on les animaux qui se nourrissent exclusivement de plantes ?",
                "choices": ["Les herbivores", "Les carnivores", "Les omnivores", "Les insectivores"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on les animaux à sang froid, dont la température corporelle dépend du milieu ?",
                "choices": ["Les ectothermes", "Les endothermes", "Les homéothermes", "Les thermorégulateurs"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un animal qui chasse d'autres animaux pour se nourrir ?",
                "choices": ["Un prédateur", "Une proie", "Un charognard", "Un parasite"],
                "answer": 0,
            },
            {
                "question": "Quelle classe d'animaux regroupe les animaux à sang chaud, souvent poilus, qui allaitent leurs petits ?",
                "choices": ["Les mammifères", "Les reptiles", "Les amphibiens", "Les oiseaux"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la danse par laquelle les abeilles indiquent la direction d'une source de nourriture ?",
                "choices": ["La danse des abeilles", "Le chant des abeilles", "Les phéromones seules", "Le vol en cercle aléatoire"],
                "answer": 0,
            },
        ],
        "Reptiles et amphibiens": [
            {
                "question": "Quel est l'un des plus grands reptiles vivant actuellement ?",
                "choices": ["Le crocodile marin", "Le python réticulé", "Le varan de Komodo", "L'anaconda"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le changement de peau chez les serpents ?",
                "choices": ["L'exuviation (la mue)", "La métamorphose", "La régénération", "La nymphose"],
                "answer": 0,
            },
            {
                "question": "Quel amphibien se transforme, au cours de sa vie, de têtard à adulte ?",
                "choices": ["La grenouille", "Le lézard", "La tortue", "Le serpent"],
                "answer": 0,
            },
            {
                "question": "Les tortues sont-elles des reptiles ?",
                "choices": ["Oui", "Non, ce sont des amphibiens", "Non, ce sont des mammifères", "Non, ce sont des poissons"],
                "answer": 0,
            },
            {
                "question": "Comment est produit le venin de certains serpents pour immobiliser leurs proies ?",
                "choices": ["Par des glandes spécialisées", "Par le sang", "Par la salive ordinaire", "Par le mucus"],
                "answer": 0,
            },
        ],
        "Les champignons": [
            {
                "question": "Les champignons appartiennent-ils au règne végétal ?",
                "choices": ["Non, ils forment leur propre règne", "Oui, ce sont des plantes", "Oui, ce sont des algues", "Non, ce sont des animaux"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la partie visible d'un champignon qui sort de terre ?",
                "choices": ["Le carpophore", "La racine", "La tige uniquement", "La feuille"],
                "answer": 0,
            },
            {
                "question": "Quel champignon vénéneux est reconnaissable à son chapeau rouge tacheté de blanc ?",
                "choices": ["L'amanite tue-mouches", "Le cèpe de Bordeaux", "La girolle", "Le champignon de Paris"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le réseau souterrain de filaments d'un champignon ?",
                "choices": ["Le mycélium", "Les spores", "Le carpophore", "Le lichen"],
                "answer": 0,
            },
            {
                "question": "Quelle association symbiotique un champignon peut-il former avec les racines d'un arbre ?",
                "choices": ["Une mycorhize", "Une nodosité", "Une lichénisation", "Une galle"],
                "answer": 0,
            },
        ],
        "Arbres et plantes": [
            {
                "question": "Comment appelle-t-on le processus par lequel les plantes fabriquent leur nourriture grâce à la lumière ?",
                "choices": ["La photosynthèse", "La respiration", "La transpiration", "La pollinisation"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un arbre qui perd ses feuilles chaque automne ?",
                "choices": ["Un arbre à feuilles caduques", "Un conifère", "Un arbre à feuilles persistantes", "Un arbuste"],
                "answer": 0,
            },
            {
                "question": "Quelle partie de la plante absorbe l'eau et les minéraux du sol ?",
                "choices": ["Les racines", "Les feuilles", "Les fleurs", "Les fruits"],
                "answer": 0,
            },
            {
                "question": "Quel est l'un des arbres les plus hauts du monde, une espèce de séquoia ?",
                "choices": ["Le séquoia à feuilles d'if (redwood)", "Le chêne", "Le baobab", "L'eucalyptus"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le transport du pollen d'une fleur à une autre ?",
                "choices": ["La pollinisation", "La germination", "La photosynthèse", "La transpiration"],
                "answer": 0,
            },
        ],
        "Élevage et agriculture": [
            {
                "question": "Comment appelle-t-on la culture d'une seule espèce végétale sur une grande surface ?",
                "choices": ["La monoculture", "La polyculture", "L'agroforesterie", "La permaculture"],
                "answer": 0,
            },
            {
                "question": "Quel animal est principalement élevé pour la production de laine ?",
                "choices": ["Le mouton", "La vache", "La chèvre", "Le porc"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'agriculture qui n'utilise pas de produits chimiques de synthèse ?",
                "choices": ["L'agriculture biologique", "L'agriculture intensive", "L'agro-industrie", "L'hydroponie"],
                "answer": 0,
            },
            {
                "question": "Quelle céréale est la base de l'alimentation dans une grande partie de l'Asie ?",
                "choices": ["Le riz", "Le blé", "Le maïs", "L'orge"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'alternance des cultures pour préserver la fertilité des sols ?",
                "choices": ["L'assolement", "Le labourage", "Le désherbage", "Le drainage"],
                "answer": 0,
            },
        ],
        "Les animaux et leurs milieux": [
            {
                "question": "Quel animal est parfaitement adapté à la vie dans le désert grâce à ses bosses de graisse ?",
                "choices": ["Le dromadaire", "Le zèbre", "L'antilope", "Le lion"],
                "answer": 0,
            },
            {
                "question": "Quel animal polaire possède une épaisse couche de graisse pour résister au froid ?",
                "choices": ["L'ours polaire", "Le lion", "Le tigre", "Le zèbre"],
                "answer": 0,
            },
            {
                "question": "Quel milieu naturel abrite la plus grande biodiversité de la planète ?",
                "choices": ["La forêt tropicale humide", "Le désert", "La banquise", "La steppe"],
                "answer": 0,
            },
            {
                "question": "Quel poisson vit exclusivement en eau douce, contrairement au saumon qui migre vers la mer ?",
                "choices": ["Le brochet", "Le saumon", "L'anguille", "Le thon"],
                "answer": 0,
            },
            {
                "question": "Quel animal est spécifiquement adapté à la vie en haute altitude dans l'Himalaya, avec un pelage épais ?",
                "choices": ["Le yack", "Le zèbre", "Le chameau", "Le bison"],
                "answer": 0,
            },
        ],
        "Les dinosaures": [
            {
                "question": "À quelle ère géologique les dinosaures ont-ils dominé la Terre ?",
                "choices": ["Le Mésozoïque (ère secondaire)", "Le Paléozoïque", "Le Cénozoïque", "Le Précambrien"],
                "answer": 0,
            },
            {
                "question": "Quel dinosaure carnivore géant est célèbre pour ses petits bras et ses grandes dents ?",
                "choices": ["Le Tyrannosaure (T. rex)", "Le Tricératops", "Le Diplodocus", "Le Stégosaure"],
                "answer": 0,
            },
            {
                "question": "Quel dinosaure herbivore possédait trois cornes sur la tête ?",
                "choices": ["Le Tricératops", "Le Tyrannosaure", "Le Vélociraptor", "Le Ptérodactyle"],
                "answer": 0,
            },
            {
                "question": "Les ptérodactyles étaient-ils de véritables dinosaures ?",
                "choices": ["Non, ce sont des reptiles volants apparentés", "Oui, ce sont des dinosaures", "Non, ce sont des oiseaux", "Non, ce sont des poissons"],
                "answer": 0,
            },
            {
                "question": "Quel événement est considéré comme responsable de l'extinction des dinosaures il y a environ 66 millions d'années ?",
                "choices": ["La chute d'un astéroïde", "Une épidémie", "La dérive des continents", "L'apparition des mammifères"],
                "answer": 0,
            },
        ],
        "Les félins": [
            {
                "question": "Quel est le plus grand félin sauvage du monde ?",
                "choices": ["Le tigre", "Le lion", "Le léopard", "Le jaguar"],
                "answer": 0,
            },
            {
                "question": "Quel félin est le plus rapide sur terre, capable de sprints à plus de 100 km/h ?",
                "choices": ["Le guépard", "Le lion", "Le tigre", "Le puma"],
                "answer": 0,
            },
            {
                "question": "Quel félin vit en groupe social appelé une troupe, contrairement aux autres grands félins plutôt solitaires ?",
                "choices": ["Le lion", "Le tigre", "Le léopard", "Le jaguar"],
                "answer": 0,
            },
            {
                "question": "Quel félin d'Amérique du Sud possède l'une des morsures les plus puissantes parmi les grands félins ?",
                "choices": ["Le jaguar", "Le puma", "L'ocelot", "Le lynx"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le petit félin sauvage aux oreilles pointues à pinceaux, présent en Europe ?",
                "choices": ["Le lynx", "Le chat sauvage", "Le caracal", "Le serval"],
                "answer": 0,
            },
        ],
        "Les primates": [
            {
                "question": "Quel est le plus grand primate actuel ?",
                "choices": ["Le gorille", "Le chimpanzé", "L'orang-outan", "Le babouin"],
                "answer": 0,
            },
            {
                "question": "Quel primate partage environ 98 % de son ADN avec l'être humain ?",
                "choices": ["Le chimpanzé", "Le gorille", "Le babouin", "Le lémurien"],
                "answer": 0,
            },
            {
                "question": "Sur quel continent vit l'orang-outan à l'état sauvage ?",
                "choices": ["L'Asie", "L'Afrique", "L'Amérique du Sud", "L'Océanie"],
                "answer": 0,
            },
            {
                "question": "Quel primate, étudié notamment par Jane Goodall, vit en communautés complexes dirigées par un mâle dominant ?",
                "choices": ["Le chimpanzé", "Le gorille", "L'orang-outan", "Le gibbon"],
                "answer": 0,
            },
            {
                "question": "Sur quelle île se trouvent la plupart des espèces de lémuriens à l'état sauvage ?",
                "choices": ["Madagascar", "Bornéo", "Sumatra", "Ceylan"],
                "answer": 0,
            },
        ],
        "La forêt amazonienne": [
            {
                "question": "Sur quel continent se situe la majeure partie de la forêt amazonienne ?",
                "choices": ["L'Amérique du Sud", "L'Afrique", "L'Asie", "L'Océanie"],
                "answer": 0,
            },
            {
                "question": "Quel pays abrite la plus grande partie de la forêt amazonienne ?",
                "choices": ["Le Brésil", "Le Pérou", "La Colombie", "L'Équateur"],
                "answer": 0,
            },
            {
                "question": "Quel grand fleuve traverse la forêt amazonienne ?",
                "choices": ["L'Amazone", "Le Nil", "Le Congo", "Le Mississippi"],
                "answer": 0,
            },
            {
                "question": "Pourquoi la forêt amazonienne est-elle parfois surnommée « le poumon de la planète » ?",
                "choices": ["Elle produit une grande partie de l'oxygène et absorbe du CO2", "Elle abrite le plus grand volcan", "Elle est la plus froide des forêts", "Elle ne contient aucune rivière"],
                "answer": 0,
            },
            {
                "question": "Quelle activité humaine menace le plus la forêt amazonienne aujourd'hui ?",
                "choices": ["La déforestation", "La pollution sonore", "La surpêche", "L'urbanisation côtière"],
                "answer": 0,
            },
        ],
        "Les abeilles": [
            {
                "question": "Quel produit sucré les abeilles fabriquent-elles à partir du nectar des fleurs ?",
                "choices": ["Le miel", "La gelée royale", "La propolis", "Le pollen"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la seule femelle capable de pondre des œufs dans une colonie d'abeilles ?",
                "choices": ["La reine", "L'ouvrière", "Le faux-bourdon", "La nymphe"],
                "answer": 0,
            },
            {
                "question": "Quel rôle essentiel les abeilles jouent-elles pour de nombreuses plantes à fleurs ?",
                "choices": ["La pollinisation", "La photosynthèse", "La décomposition", "La germination"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la communication des abeilles ouvrières pour indiquer la direction d'une source de nourriture ?",
                "choices": ["La danse des abeilles", "Le chant des abeilles", "Les phéromones seules", "Le vol stationnaire"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'habitat construit par les abeilles où elles stockent le miel ?",
                "choices": ["La ruche", "Le nid", "La fourmilière", "Le terrier"],
                "answer": 0,
            },
        ],
        "Les espèces en voie de disparition": [
            {
                "question": "Quel grand félin d'Asie, aux rayures caractéristiques, est aujourd'hui menacé dans la nature ?",
                "choices": ["Le tigre", "Le lion", "Le guépard", "Le lynx"],
                "answer": 0,
            },
            {
                "question": "Quel grand mammifère marin a été chassé au point de devenir menacé, aujourd'hui protégé dans de nombreux pays ?",
                "choices": ["La baleine", "Le dauphin", "Le phoque", "La loutre de mer"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la liste internationale qui recense l'état de conservation des espèces menacées ?",
                "choices": ["La Liste rouge de l'UICN", "Le Livre blanc", "Le Registre vert", "La Charte de la biodiversité"],
                "answer": 0,
            },
            {
                "question": "Quel grand singe d'Afrique, notamment de la région des Virunga, est classé en danger critique d'extinction ?",
                "choices": ["Le gorille des montagnes", "Le chimpanzé", "L'orang-outan", "Le bonobo"],
                "answer": 0,
            },
            {
                "question": "Quelle pratique illégale, consistant à tuer des animaux protégés pour leurs cornes ou défenses, menace rhinocéros et éléphants ?",
                "choices": ["Le braconnage", "La chasse sportive", "L'élevage", "La pêche"],
                "answer": 0,
            },
        ],
    },
    "Société & Monde": {
        "Les grandes inventions": [
            {
                "question": "Qui est crédité de l'invention de l'ampoule électrique à incandescence commercialisable ?",
                "choices": ["Thomas Edison", "Nikola Tesla", "Alexander Graham Bell", "Benjamin Franklin"],
                "answer": 0,
            },
            {
                "question": "Qui a inventé l'imprimerie à caractères mobiles en Europe au XVe siècle ?",
                "choices": ["Johannes Gutenberg", "Léonard de Vinci", "Christophe Colomb", "Galilée"],
                "answer": 0,
            },
            {
                "question": "Qui a inventé le téléphone ?",
                "choices": ["Alexander Graham Bell", "Thomas Edison", "Guglielmo Marconi", "Nikola Tesla"],
                "answer": 0,
            },
            {
                "question": "Quels frères sont considérés comme les inventeurs du cinéma grâce au cinématographe ?",
                "choices": ["Les frères Lumière", "Les frères Wright", "Les frères Montgolfier", "Les frères Grimm"],
                "answer": 0,
            },
            {
                "question": "Quels frères ont inventé la montgolfière ?",
                "choices": ["Les frères Montgolfier", "Les frères Lumière", "Les frères Wright", "Les frères Curie"],
                "answer": 0,
            },
        ],
        "Les transports": [
            {
                "question": "Quel moyen de transport a révolutionné le XIXe siècle grâce à la machine à vapeur ?",
                "choices": ["Le train", "L'avion", "La voiture", "Le vélo"],
                "answer": 0,
            },
            {
                "question": "Qui a réalisé le premier vol motorisé de l'histoire en 1903 ?",
                "choices": ["Les frères Wright", "Les frères Lumière", "Louis Blériot", "Clément Ader"],
                "answer": 0,
            },
            {
                "question": "Comment s'appelle le train français à grande vitesse, mis en service en 1981 ?",
                "choices": ["Le TGV", "L'Eurostar", "Le RER", "Le Thalys"],
                "answer": 0,
            },
            {
                "question": "Quel type de bateau utilise la force du vent pour se déplacer ?",
                "choices": ["Le voilier", "Le paquebot", "Le sous-marin", "Le porte-conteneurs"],
                "answer": 0,
            },
            {
                "question": "Quel tunnel relie la France et l'Angleterre sous la Manche ?",
                "choices": ["Le tunnel sous la Manche", "Le tunnel du Mont-Blanc", "Le tunnel du Gothard", "Le tunnel de Fréjus"],
                "answer": 0,
            },
        ],
        "Industries et technologies": [
            {
                "question": "Comment appelle-t-on la période de profonds changements économiques et technologiques du XVIIIe-XIXe siècle marquée par la machine à vapeur ?",
                "choices": ["La révolution industrielle", "La révolution numérique", "La révolution verte", "La révolution agricole"],
                "answer": 0,
            },
            {
                "question": "Quel matériau léger et résistant est massivement utilisé dans l'aéronautique et l'automobile modernes ?",
                "choices": ["L'aluminium", "Le plomb", "Le fer", "Le cuivre"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la miniaturisation des circuits électroniques sur une puce ?",
                "choices": ["Le circuit intégré", "Le transistor isolé", "La carte perforée", "Le tube à vide"],
                "answer": 0,
            },
            {
                "question": "Quelle énergie, produite par le charbon, a permis l'essor des usines pendant la révolution industrielle ?",
                "choices": ["La vapeur", "L'énergie solaire", "L'énergie éolienne", "L'énergie nucléaire"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un système informatique capable d'apprendre et de s'améliorer grâce aux données ?",
                "choices": ["Une intelligence artificielle", "Un automate simple", "Un algorithme fixe", "Un capteur"],
                "answer": 0,
            },
        ],
        "Communication et médias": [
            {
                "question": "Quel inventeur est à l'origine du télégraphe électrique et du code qui porte son nom ?",
                "choices": ["Samuel Morse", "Alexander Graham Bell", "Guglielmo Marconi", "Thomas Edison"],
                "answer": 0,
            },
            {
                "question": "Qui a inventé la radio (transmission sans fil) ?",
                "choices": ["Guglielmo Marconi", "Thomas Edison", "Alexander Graham Bell", "Nikola Tesla"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un journal publié tous les jours ?",
                "choices": ["Un quotidien", "Un hebdomadaire", "Un mensuel", "Un bimensuel"],
                "answer": 0,
            },
            {
                "question": "Quel réseau mondial d'ordinateurs interconnectés a révolutionné la communication depuis les années 1990 ?",
                "choices": ["Internet", "Le télex", "Le minitel", "Le fax"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la diffusion d'un programme de télévision ou de radio au moment même où il se produit ?",
                "choices": ["Le direct (ou live)", "Le différé", "Le montage", "Le doublage"],
                "answer": 0,
            },
        ],
        "La France et ses institutions": [
            {
                "question": "Comment s'appelle le chef de l'État en France ?",
                "choices": ["Le président de la République", "Le Premier ministre", "Le chancelier", "Le roi"],
                "answer": 0,
            },
            {
                "question": "Combien de chambres compte le Parlement français ?",
                "choices": ["2 (Assemblée nationale et Sénat)", "1", "3", "4"],
                "answer": 0,
            },
            {
                "question": "Quelle devise est inscrite au fronton des bâtiments publics français ?",
                "choices": ["Liberté, Égalité, Fraternité", "Unité, Travail, Patrie", "Ordre et Progrès", "Paix, Justice, Liberté"],
                "answer": 0,
            },
            {
                "question": "Quel texte fondamental encadre l'organisation des pouvoirs de la Ve République depuis 1958 ?",
                "choices": ["La Constitution de 1958", "Le Code civil", "La Déclaration des droits de l'homme", "Le traité de Versailles"],
                "answer": 0,
            },
            {
                "question": "Depuis 2000, combien d'années dure le mandat présidentiel en France ?",
                "choices": ["5 ans", "7 ans", "4 ans", "6 ans"],
                "answer": 0,
            },
        ],
        "Le monde et ses enjeux": [
            {
                "question": "Comment appelle-t-on le réchauffement progressif de la température moyenne de la planète, lié aux activités humaines ?",
                "choices": ["Le réchauffement climatique", "L'effet de serre naturel", "La désertification", "L'érosion"],
                "answer": 0,
            },
            {
                "question": "Quel accord international de 2015 vise à limiter le réchauffement climatique mondial ?",
                "choices": ["L'accord de Paris", "Le protocole de Montréal", "La charte des Nations unies", "Le traité de Versailles"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on la disparition progressive et accélérée de nombreuses espèces animales et végétales ?",
                "choices": ["L'érosion de la biodiversité", "La désertification", "La déforestation", "Le réchauffement climatique"],
                "answer": 0,
            },
            {
                "question": "Quelle organisation regroupe la majorité des pays du monde pour maintenir la paix internationale ?",
                "choices": ["L'Organisation des Nations unies (ONU)", "L'OTAN", "L'Union européenne", "Le G7"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'accroissement des échanges économiques et culturels à l'échelle mondiale ?",
                "choices": ["La mondialisation", "La décentralisation", "Le protectionnisme", "L'autarcie"],
                "answer": 0,
            },
        ],
        "Économie": [
            {
                "question": "Comment appelle-t-on l'augmentation générale et durable des prix ?",
                "choices": ["L'inflation", "La déflation", "La récession", "La croissance"],
                "answer": 0,
            },
            {
                "question": "Quelle institution est chargée de la politique monétaire de la zone euro ?",
                "choices": ["La Banque centrale européenne", "Le FMI", "La Banque mondiale", "L'OMC"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le principe économique selon lequel l'offre et la demande déterminent les prix ?",
                "choices": ["La loi du marché", "La loi de l'offre", "La loi de Say", "La loi de Gresham"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on une période de recul de l'activité économique ?",
                "choices": ["Une récession", "Une inflation", "Une expansion", "Une dévaluation"],
                "answer": 0,
            },
            {
                "question": "Quelle monnaie commune est utilisée par la plupart des pays de l'Union européenne ?",
                "choices": ["L'euro", "Le franc", "Le dollar", "La livre"],
                "answer": 0,
            },
        ],
        "Gastronomie": [
            {
                "question": "Quel pays est réputé pour l'invention de la pizza napolitaine ?",
                "choices": ["L'Italie", "La France", "L'Espagne", "La Grèce"],
                "answer": 0,
            },
            {
                "question": "Quel fromage français à pâte molle est originaire de Normandie ?",
                "choices": ["Le camembert", "Le comté", "Le roquefort", "Le reblochon"],
                "answer": 0,
            },
            {
                "question": "Quelle sauce froide est composée d'huile, de jaune d'œuf et de moutarde ?",
                "choices": ["La mayonnaise", "La vinaigrette", "La béchamel", "Le pesto"],
                "answer": 0,
            },
            {
                "question": "Quel plat japonais se compose de riz vinaigré et de poisson cru ?",
                "choices": ["Les sushis", "Les ramens", "Les tempuras", "Les yakitoris"],
                "answer": 0,
            },
            {
                "question": "Quelle boisson chaude est obtenue par infusion de feuilles séchées, très consommée en Asie ?",
                "choices": ["Le thé", "Le café", "Le chocolat chaud", "La tisane"],
                "answer": 0,
            },
        ],
        "Droit et justice": [
            {
                "question": "Comment appelle-t-on le principe selon lequel toute personne est innocente jusqu'à preuve du contraire ?",
                "choices": ["La présomption d'innocence", "La légitime défense", "La prescription", "L'amnistie"],
                "answer": 0,
            },
            {
                "question": "Quelle juridiction française juge les crimes les plus graves avec un jury populaire ?",
                "choices": ["La cour d'assises", "Le tribunal de police", "Le conseil des prud'hommes", "Le tribunal de commerce"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un texte de loi voté par le Parlement ?",
                "choices": ["Une loi", "Un décret", "Un arrêté", "Une ordonnance"],
                "answer": 0,
            },
            {
                "question": "Quelle institution internationale juge les crimes de guerre et les génocides ?",
                "choices": ["La Cour pénale internationale", "L'ONU", "L'OTAN", "L'UNESCO"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on l'ensemble des règles qui organisent la vie en société et sont sanctionnées par l'État ?",
                "choices": ["Le droit", "La morale", "La coutume", "L'étiquette"],
                "answer": 0,
            },
        ],
        "Mode et vêtements": [
            {
                "question": "Quel couturier français a créé la petite robe noire, révolutionnant la mode féminine au XXe siècle ?",
                "choices": ["Coco Chanel", "Christian Dior", "Yves Saint Laurent", "Pierre Cardin"],
                "answer": 0,
            },
            {
                "question": "Quelle fibre textile naturelle provient du cocon d'une chenille ?",
                "choices": ["La soie", "Le coton", "Le lin", "La laine"],
                "answer": 0,
            },
            {
                "question": "Quelle fibre textile est obtenue à partir de la toison des moutons ?",
                "choices": ["La laine", "La soie", "Le coton", "Le polyester"],
                "answer": 0,
            },
            {
                "question": "Quelle ville est considérée comme une capitale historique de la haute couture ?",
                "choices": ["Paris", "Londres", "Berlin", "Madrid"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le vêtement traditionnel japonais porté avec une large ceinture, l'obi ?",
                "choices": ["Le kimono", "Le sari", "Le boubou", "Le sarong"],
                "answer": 0,
            },
        ],
        "Éducation": [
            {
                "question": "Comment appelle-t-on l'enseignement obligatoire dispensé aux enfants dans la plupart des pays ?",
                "choices": ["La scolarité obligatoire", "L'enseignement supérieur", "La formation continue", "L'apprentissage"],
                "answer": 0,
            },
            {
                "question": "En France, jusqu'à quel âge l'instruction est-elle obligatoire depuis 2019 ?",
                "choices": ["16 ans", "14 ans", "18 ans", "12 ans"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on le diplôme obtenu à la fin des études secondaires en France ?",
                "choices": ["Le baccalauréat", "Le brevet", "La licence", "Le CAP"],
                "answer": 0,
            },
            {
                "question": "Quelle organisation des Nations unies s'occupe de l'éducation, la science et la culture ?",
                "choices": ["L'UNESCO", "L'UNICEF", "L'OMS", "La FAO"],
                "answer": 0,
            },
            {
                "question": "Comment appelle-t-on un établissement d'enseignement supérieur délivrant des diplômes universitaires ?",
                "choices": ["Une université", "Un collège", "Un lycée", "Une école primaire"],
                "answer": 0,
            },
        ],
        "Les organisations internationales": [
            {
                "question": "Quelle organisation regroupe la majorité des pays du monde pour maintenir la paix internationale, fondée en 1945 ?",
                "choices": ["L'Organisation des Nations unies (ONU)", "L'Union européenne", "L'OTAN", "Le G7"],
                "answer": 0,
            },
            {
                "question": "Quelle organisation économique et militaire regroupe des pays d'Amérique du Nord et d'Europe pour leur défense collective ?",
                "choices": ["L'OTAN", "L'ONU", "L'Union européenne", "Le FMI"],
                "answer": 0,
            },
            {
                "question": "Quelle organisation regroupe des pays européens autour d'un marché commun et d'institutions communes ?",
                "choices": ["L'Union européenne", "L'OTAN", "L'ONU", "Le Conseil de l'Europe"],
                "answer": 0,
            },
            {
                "question": "Quelle organisation internationale s'occupe de la santé publique mondiale ?",
                "choices": ["L'Organisation mondiale de la santé (OMS)", "L'UNESCO", "L'UNICEF", "La Croix-Rouge"],
                "answer": 0,
            },
            {
                "question": "Quelle organisation humanitaire, fondée par Henry Dunant, porte une croix rouge comme emblème ?",
                "choices": ["La Croix-Rouge", "Médecins Sans Frontières", "L'UNICEF", "Amnesty International"],
                "answer": 0,
            },
        ],
        "Fêtes et traditions du monde": [
            {
                "question": "Quelle fête chinoise, célébrée selon le calendrier lunaire, est marquée par des dragons et des feux d'artifice ?",
                "choices": ["Le Nouvel An chinois", "Thanksgiving", "Halloween", "Diwali"],
                "answer": 0,
            },
            {
                "question": "Quelle fête indienne des lumières est célébrée par les hindous, sikhs et jaïns ?",
                "choices": ["Diwali", "Holi", "Vaisakhi", "Navratri"],
                "answer": 0,
            },
            {
                "question": "Quelle fête mexicaine, colorée et festive, célèbre la mémoire des défunts fin octobre-début novembre ?",
                "choices": ["Le jour des Morts (Día de los Muertos)", "Le Carnaval", "Le Cinco de Mayo", "La Piñata"],
                "answer": 0,
            },
            {
                "question": "Quelle fête chrétienne célèbre la naissance de Jésus le 25 décembre ?",
                "choices": ["Noël", "Pâques", "L'Épiphanie", "La Pentecôte"],
                "answer": 0,
            },
            {
                "question": "Quel mois de jeûne est observé par les musulmans du lever au coucher du soleil ?",
                "choices": ["Le ramadan", "L'Aïd", "Le Mouharram", "Le Hajj"],
                "answer": 0,
            },
        ],
        "Les langues du monde": [
            {
                "question": "Quelle langue compte le plus grand nombre de locuteurs natifs (langue maternelle) au monde ?",
                "choices": ["Le mandarin", "L'anglais", "L'espagnol", "Le hindi"],
                "answer": 0,
            },
            {
                "question": "Quelle langue est officielle dans la quasi-totalité des pays d'Amérique du Sud, héritée de la colonisation ?",
                "choices": ["L'espagnol", "Le portugais", "Le français", "L'anglais"],
                "answer": 0,
            },
            {
                "question": "Quelle langue est officielle au Brésil, contrairement au reste de l'Amérique du Sud ?",
                "choices": ["Le portugais", "L'espagnol", "Le français", "L'italien"],
                "answer": 0,
            },
            {
                "question": "Combien de langues officielles compte la Suisse ?",
                "choices": ["4", "2", "3", "1"],
                "answer": 0,
            },
            {
                "question": "Quelle famille de langues regroupe le français, l'espagnol, l'italien, le portugais et le roumain ?",
                "choices": ["Les langues romanes", "Les langues germaniques", "Les langues slaves", "Les langues celtiques"],
                "answer": 0,
            },
        ],
        "Monnaies et unités de mesure": [
            {
                "question": "Quelle monnaie est utilisée par la majorité des pays de l'Union européenne ?",
                "choices": ["L'euro", "Le franc", "Le dollar", "La livre"],
                "answer": 0,
            },
            {
                "question": "Quelle monnaie est utilisée aux États-Unis ?",
                "choices": ["Le dollar américain", "L'euro", "La livre sterling", "Le yen"],
                "answer": 0,
            },
            {
                "question": "Quel système d'unités, basé sur le mètre et le kilogramme, est utilisé dans la majorité des pays du monde ?",
                "choices": ["Le système métrique", "Le système impérial", "Le système avoirdupois", "Le système anglo-saxon"],
                "answer": 0,
            },
            {
                "question": "Quel pays utilise encore majoritairement les miles, livres et pouces plutôt que le système métrique ?",
                "choices": ["Les États-Unis", "La France", "Le Japon", "L'Allemagne"],
                "answer": 0,
            },
            {
                "question": "Quelle monnaie officielle est utilisée au Japon ?",
                "choices": ["Le yen", "Le won", "Le yuan", "Le dong"],
                "answer": 0,
            },
        ],
        "Drapeaux et symboles nationaux": [
            {
                "question": "Quelles sont les trois couleurs du drapeau français ?",
                "choices": ["Bleu, blanc, rouge", "Bleu, blanc, vert", "Rouge, blanc, noir", "Vert, blanc, rouge"],
                "answer": 0,
            },
            {
                "question": "Quel oiseau est le symbole emblématique des États-Unis, visible sur leurs armoiries ?",
                "choices": ["Le pygargue à tête blanche", "L'aigle royal", "Le condor", "Le faucon"],
                "answer": 0,
            },
            {
                "question": "Quelle fleur symbolise traditionnellement le printemps au Japon, très célébrée chaque année (hanami) ?",
                "choices": ["La fleur de cerisier (sakura)", "Le chrysanthème", "Le lotus", "L'iris"],
                "answer": 0,
            },
            {
                "question": "Quel symbole figure au centre du drapeau du Canada ?",
                "choices": ["Une feuille d'érable", "Un castor", "Une fleur de lys", "Une étoile"],
                "answer": 0,
            },
            {
                "question": "Quelle couleur ne figure pas sur le drapeau de l'Italie (vert, blanc, rouge) ?",
                "choices": ["Le bleu", "Le vert", "Le blanc", "Le rouge"],
                "answer": 0,
            },
        ],
    },
}
