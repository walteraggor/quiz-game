"""A command-line quiz: pick a category, answer against the clock, climb the leaderboard."""

import json
import random
import time
from pathlib import Path

# Question categories and questions.
# "answers" lists every answer that counts as correct. The first one is shown
# to the player after a wrong answer. Capital letters and extra spaces are ignored.
quiz_data = {
    "General Knowledge": [
        {"question": "What is the capital of France?", "answers": ["Paris"]},
        {"question": "What is the largest ocean?",
         "answers": ["Pacific", "Pacific Ocean", "The Pacific", "The Pacific Ocean"]},
        {"question": "Who wrote '1984'?", "answers": ["George Orwell", "Orwell"]},
    ],
    "Science": [
        {"question": "What is the chemical formula for water?", "answers": ["H2O"]},
        {"question": "How many planets are in our solar system?", "answers": ["8", "eight"]},
        {"question": "What gas do plants absorb from the atmosphere?", "answers": ["Carbon dioxide", "CO2"]},
    ],
    "Math": [
        {"question": "What is 12 * 12?", "answers": ["144"]},
        {"question": "What is the square root of 81?", "answers": ["9", "nine"]},
        {"question": "What is 50% of 200?", "answers": ["100", "one hundred"]},
    ],
}

# The leaderboard is saved next to this file, whichever folder the game is started from.
LEADERBOARD_FILE = Path(__file__).with_name("leaderboard.json")


def tidy(text):
    """Lowercase the text and remove extra spaces, so that ' PARIS' and 'paris' match."""
    return " ".join(text.lower().split())


def is_correct(user_answer, answers):
    """Check what the player typed against every accepted answer."""
    return tidy(user_answer) in [tidy(answer) for answer in answers]


# Function to ask a question and track correct answers
def ask_question(question, answers):
    """Ask one question. Returns the points earned (1 or 0) and the seconds taken."""
    print(question)
    start_time = time.perf_counter()  # Start the timer
    user_answer = input("Your answer: ")
    elapsed_time = time.perf_counter() - start_time  # Measure elapsed time

    if is_correct(user_answer, answers):
        print(f"Correct! You took {elapsed_time:.2f} seconds.")
        return 1, elapsed_time
    else:
        print(f"Wrong! The correct answer was '{answers[0]}'.")
        return 0, elapsed_time


def choose_category():
    """Show the categories and keep asking until the player picks one of them."""
    categories = list(quiz_data)
    print("\nCategories:")
    for number, category in enumerate(categories, start=1):
        print(f"  {number}. {category}")

    while True:
        choice = tidy(input("Choose a category (name or number): "))
        for number, category in enumerate(categories, start=1):
            if choice == str(number) or choice == tidy(category):
                return category
        print("That is not one of the categories. Please try again.")


# Function to run the quiz
def run_quiz(category):
    """Ask every question in the category. Returns the score and the total seconds taken."""
    questions = quiz_data[category]
    questions = random.sample(questions, len(questions))  # A shuffled copy, for randomness
    total_score = 0
    total_time = 0

    # Ask questions
    for number, q in enumerate(questions, start=1):
        print(f"\nQuestion {number} of {len(questions)}")
        score, time_taken = ask_question(q["question"], q["answers"])
        total_score += score
        total_time += time_taken

    print(f"\nQuiz Complete! Your score: {total_score}/{len(questions)}")
    print(f"Total time: {total_time:.2f} seconds.")
    return total_score, total_time


def load_leaderboard(path=LEADERBOARD_FILE):
    """Read the saved leaderboard. Returns an empty one if nothing has been saved yet."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            saved = json.load(file)
        # Rebuild every entry, so that a file with the wrong shape is noticed here
        # and not in the middle of a game.
        return {str(player): {"score": int(stats["score"]), "time": float(stats["time"])}
                for player, stats in saved.items()}
    except FileNotFoundError:
        return {}
    except (ValueError, TypeError, KeyError, AttributeError):
        print(f"{Path(path).name} is damaged, so the leaderboard starts again from empty.")
        return {}


def save_leaderboard(leaderboard, path=LEADERBOARD_FILE):
    """Write the leaderboard to its file."""
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(leaderboard, file, indent=2)
    except OSError as error:
        print(f"The leaderboard could not be saved: {error}")


def update_leaderboard(leaderboard, player_name, score, seconds):
    """Record a round if it is the player's first or their best. Returns True if it was recorded."""
    previous = leaderboard.get(player_name)
    # A higher score is better. With the same score, the faster time is better.
    if previous is None or score > previous["score"] or (score == previous["score"] and seconds < previous["time"]):
        leaderboard[player_name] = {"score": score, "time": seconds}
        return True
    return False


def ranked(leaderboard):
    """Return the leaderboard as a list of (player, stats), best first."""
    return sorted(leaderboard.items(), key=lambda entry: (-entry[1]["score"], entry[1]["time"]))


def show_leaderboard(leaderboard):
    print("\nLeaderboard:")
    for place, (player, stats) in enumerate(ranked(leaderboard), start=1):
        print(f"{place}. {player} - Score: {stats['score']}, Time: {stats['time']:.2f} seconds")


def ask_name():
    """Keep asking until the player types a name."""
    while True:
        player_name = " ".join(input("Enter your name for the leaderboard: ").split())
        if player_name:
            return player_name
        print("Please type a name.")


def play_again():
    """Ask whether to play another round, until the answer is yes or no."""
    print()
    while True:
        answer = tidy(input("Play again? (y/n): "))
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer y or n.")


def main(leaderboard_file=LEADERBOARD_FILE):
    print("Welcome to the Quiz Game!")
    leaderboard = load_leaderboard(leaderboard_file)

    while True:
        category = choose_category()
        total_score, total_time = run_quiz(category)

        # Ask for player name and update leaderboard
        player_name = ask_name()
        if update_leaderboard(leaderboard, player_name, total_score, total_time):
            save_leaderboard(leaderboard, leaderboard_file)
        else:
            best = leaderboard[player_name]
            print(f"Your best round is still {best['score']} in {best['time']:.2f} seconds.")
        show_leaderboard(leaderboard)

        if not play_again():
            break

    print("Thanks for playing!")


# Start the game
if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C, or no more input: leave quietly instead of with an error.
        print("\nGoodbye!")
