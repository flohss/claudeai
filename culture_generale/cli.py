"""Interface en ligne de commande de l'application de culture générale."""

from .data import THEMES
from .quiz import Quiz
from .wikipedia import WikipediaError, random_article

LETTERS = "ABCD"


def choose_mode():
    print("\nQue voulez-vous faire ?")
    print("  1. Quiz de culture générale")
    print("  2. Article surprise (Wikipédia)")
    print("  0. Quitter")

    while True:
        choice = input("> ").strip()
        if choice == "0":
            return None
        if choice == "1":
            return "quiz"
        if choice == "2":
            return "wikipedia"
        print("Choix invalide, réessayez.")


def choose_theme(quiz, exit_label="Retour au menu principal"):
    themes = quiz.theme_names()
    print("\nChoisissez une thématique :")
    for i, theme in enumerate(themes, start=1):
        print(f"  {i}. {theme}")
    print(f"  0. {exit_label}")

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


def display_article(article):
    print(f"\n📖 {article['title']}")
    print(article["extract"])
    if article["url"]:
        print(f"\n🔗 {article['url']}")


def run_quiz_mode(quiz):
    print("\n--- Quiz de culture générale ---")
    print("Choisissez une thématique, un sujet sera ouvert au hasard pour vous.")

    total_score = 0
    total_questions = 0

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

    if total_questions:
        print(f"\nScore total : {total_score}/{total_questions}")


def run_wikipedia_mode(quiz):
    print("\n--- Article surprise (Wikipédia) ---")
    print("Choisissez une thématique, un article Wikipédia sera ouvert au hasard.")

    while True:
        theme = choose_theme(quiz)
        if theme is None:
            break

        print(f"\nRecherche d'un article sur la thématique « {theme} »...")
        try:
            article = random_article(theme)
        except WikipediaError as exc:
            print(f"⚠️  {exc}")
        else:
            display_article(article)

        again = input("\nVoir un autre article ? (o/n) ").strip().lower()
        if again != "o":
            break


def main():
    quiz = Quiz(THEMES)
    print("=== Culture Générale ===")

    try:
        while True:
            mode = choose_mode()
            if mode is None:
                break
            if mode == "quiz":
                run_quiz_mode(quiz)
            elif mode == "wikipedia":
                run_wikipedia_mode(quiz)
    except (KeyboardInterrupt, EOFError):
        print()

    print("\nMerci d'avoir joué, à bientôt !")


if __name__ == "__main__":
    main()
