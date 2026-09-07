"""Interface en ligne de commande de l'application de culture générale."""

from .data import THEMES
from .quiz import Quiz

LETTERS = "ABCD"


def choose_theme(quiz):
    themes = quiz.theme_names()
    print("\nChoisissez une thématique :")
    for i, theme in enumerate(themes, start=1):
        print(f"  {i}. {theme}")
    print("  0. Quitter")

    while True:
        choice = input("> ").strip()
        if choice == "0":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(themes):
            return themes[int(choice) - 1]
        print("Choix invalide, réessayez.")


def ask_question(question):
    print(f"\n{question['question']}")
    for letter, choice in zip(LETTERS, question["choices"]):
        print(f"  {letter}. {choice}")

    valid = LETTERS[: len(question["choices"])]
    while True:
        answer = input("Votre réponse : ").strip().upper()
        if answer in valid:
            break
        print(f"Répondez avec une lettre parmi {', '.join(valid)}.")

    correct_letter = LETTERS[question["answer"]]
    if answer == correct_letter:
        print("✅ Bonne réponse !")
        return True
    print(f"❌ Mauvaise réponse. La bonne réponse était {correct_letter}. {question['choices'][question['answer']]}")
    return False


def main():
    quiz = Quiz(THEMES)
    print("=== Culture Générale ===")
    print("Choisissez une thématique, un sujet sera ouvert au hasard pour vous.")

    total_score = 0
    total_questions = 0

    try:
        while True:
            theme = choose_theme(quiz)
            if theme is None:
                break

            subject_name, questions = quiz.pick_subject(theme)
            print(f"\n>>> Sujet tiré au sort : {subject_name} ({theme})")

            score, count = quiz.run_subject(subject_name, questions, ask_question)
            total_score += score
            total_questions += count
            print(f"\nScore pour ce sujet : {score}/{count}")

            again = input("\nRejouer avec une autre thématique ? (o/n) ").strip().lower()
            if again != "o":
                break
    except (KeyboardInterrupt, EOFError):
        print()

    if total_questions:
        print(f"\nScore total : {total_score}/{total_questions}")
    print("Merci d'avoir joué, à bientôt !")


if __name__ == "__main__":
    main()
