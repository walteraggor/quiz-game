# Quiz Game

A command-line quiz written in Python. Pick a category, answer three questions against the clock and try to beat your best result on the leaderboard.

## Features

- Three categories: General Knowledge, Science and Math
- Questions are shuffled every round
- Every answer is timed
- A leaderboard, saved to `leaderboard.json`, keeps each player's best round. A higher score wins; if the score is the same, the faster time wins
- Capital letters, and spaces before or after an answer, do not matter

## Run it

You need Python 3.6 or newer. There are no packages to install.

```bash
git clone https://github.com/walteraggor/quiz-game.git
cd quiz-game
python quiz_game.py
```

## Example round

```
Welcome to the Quiz Game!
Categories: General Knowledge, Science, Math
Choose a category: science
What is the chemical symbol for water?: H2O
Correct! You took 2.31 seconds.
What gas do plants absorb from the atmosphere?: oxygen
Wrong! The correct answer was 'carbon dioxide'.
How many planets are in our solar system?: 8
Correct! You took 1.87 seconds.

Quiz Complete! Your score: 2/3
Total time: 7.42 seconds.
Enter your name for the leaderboard: Walter

Leaderboard:
Walter - Score: 2, Time: 7.42 seconds
```

## Add your own questions

Questions live in the `quiz_data` dictionary at the top of `quiz_game.py`:

```python
"Science": [
    {"question": "What is the chemical symbol for water?", "answer": "h2o"},
    ...
],
```

- Write answers in lowercase, because what the player types is lowercased before it is compared.
- To add a category, add a new key in Title Case (for example `"World History"`) and add its name to the `Categories:` line printed in `run_quiz()`.

The leaderboard file is created the first time someone finishes a round. Delete `leaderboard.json` to reset it.
