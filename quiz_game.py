import time
import random
import json

# Question categories and questions
quiz_data = {
    "General Knowledge": [
        {"question": "What is the capital of France?", "answer": "paris"},
        {"question": "What is the largest ocean?", "answer": "pacific"},
        {"question": "Who wrote '1984'?", "answer": "george orwell"}
    ],
    "Science": [
        {"question": "What is the chemical symbol for water?", "answer": "h2o"},
        {"question": "How many planets are in our solar system?", "answer": "8"},
        {"question": "What gas do plants absorb from the atmosphere?", "answer": "carbon dioxide"}
    ],
    "Math": [
        {"question": "What is 12 * 12?", "answer": "144"},
        {"question": "What is the square root of 81?", "answer": "9"},
        {"question": "What is 50% of 200?", "answer": "100"}
    ]
}

# Load leaderboard
try:
    with open("leaderboard.json", "r") as file:
        leaderboard = json.load(file)
except FileNotFoundError:
    leaderboard = {}

# Function to ask a question and track correct answers
def ask_question(question, correct_answer):
    start_time = time.time()  # Start the timer
    user_answer = input(f"{question}: ").strip().lower()  # Ignore stray spaces and capitals
    elapsed_time = time.time() - start_time  # Measure elapsed time

    if user_answer == correct_answer:
        print(f"Correct! You took {elapsed_time:.2f} seconds.")
        return 1, elapsed_time
    else:
        print(f"Wrong! The correct answer was '{correct_answer}'.")
        return 0, elapsed_time

# Function to run the quiz
def run_quiz():
    total_score = 0
    total_time = 0

    # Choose a category
    print("Categories: General Knowledge, Science, Math")
    category = input("Choose a category: ").strip().title()
    
    if category not in quiz_data:
        print("Invalid category. Exiting.")
        return
    
    questions = quiz_data[category]
    random.shuffle(questions)  # Shuffle questions for randomness

    # Ask questions
    for q in questions:
        score, time_taken = ask_question(q["question"], q["answer"])
        total_score += score
        total_time += time_taken

    print(f"\nQuiz Complete! Your score: {total_score}/{len(questions)}")
    print(f"Total time: {total_time:.2f} seconds.")

    # Ask for player name and update leaderboard
    player_name = input("Enter your name for the leaderboard: ").strip()
    if player_name not in leaderboard:
        leaderboard[player_name] = {"score": total_score, "time": total_time}
    else:
        # Compare score and update if the current score is better
        previous = leaderboard[player_name]
        if total_score > previous["score"] or (total_score == previous["score"] and total_time < previous["time"]):
            leaderboard[player_name] = {"score": total_score, "time": total_time}

    # Save leaderboard
    with open("leaderboard.json", "w") as file:
        json.dump(leaderboard, file)

    print("\nLeaderboard:")
    for player, stats in leaderboard.items():
        print(f"{player} - Score: {stats['score']}, Time: {stats['time']:.2f} seconds")

# Start the game
if __name__ == "__main__":
    print("Welcome to the Quiz Game!")
    run_quiz()
