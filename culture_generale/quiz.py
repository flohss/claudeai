"""Logique du quiz : sélection aléatoire d'un sujet et déroulement des questions."""

import random


class Quiz:
    def __init__(self, themes):
        self.themes = themes
        self._recently_picked = {}

    def theme_names(self):
        return list(self.themes)

    def pick_subject(self, theme):
        """Choisit aléatoirement un sujet parmi ceux de la thématique donnée.

        Évite de retirer un sujet déjà proposé dans cette thématique durant
        la session (quiz comme Wikipédia partagent ce suivi) tant que
        d'autres sujets restent disponibles ; une fois tous épuisés, le
        tirage recommence sur l'ensemble des sujets.
        """
        subjects = self.themes[theme]
        already_picked = self._recently_picked.setdefault(theme, set())

        available = [name for name in subjects if name not in already_picked]
        if not available:
            already_picked.clear()
            available = list(subjects)

        subject_name = random.choice(available)
        already_picked.add(subject_name)
        return subject_name, subjects[subject_name]

    def run_subject(self, subject_name, questions, ask_question):
        """Pose les questions d'un sujet et renvoie (bonnes réponses, total)."""
        shuffled = questions[:]
        random.shuffle(shuffled)
        score = 0
        for question in shuffled:
            if ask_question(question):
                score += 1
        return score, len(shuffled)
