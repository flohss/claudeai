"""Logique du quiz : sélection aléatoire d'un sujet et déroulement des questions."""

import random


class Quiz:
    def __init__(self, themes):
        self.themes = themes

    def theme_names(self):
        return list(self.themes)

    def pick_subject(self, theme):
        """Choisit aléatoirement un sujet parmi ceux de la thématique donnée."""
        subjects = self.themes[theme]
        subject_name = random.choice(list(subjects))
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
