# Quiz Game

[![Tests](https://github.com/walteraggor/quiz-game/actions/workflows/tests.yml/badge.svg)](https://github.com/walteraggor/quiz-game/actions/workflows/tests.yml)

A command-line quiz written in Python. Pick a category, answer three questions against the clock and try to beat your best result on the leaderboard.

## Features

- Three categories: General Knowledge, Science and Math. Pick one by name or by number
- Questions come in a different order every round
- Every answer is timed
- A question can have several right answers, so `8` and `eight` both count
- Capital letters and extra spaces in an answer do not matter
- A leaderboard, saved to `leaderboard.json`, keeps each player's best round and lists the players from best to worst. A higher score wins; if the score is the same, the faster time wins
- You can play as many rounds as you like without starting the game again

## Run it

You need Python 3.8 or newer. There are no packages to install.

```bash
git clone https://github.com/walteraggor/quiz-game.git
cd quiz-game
python quiz_game.py
```

Press Ctrl+C to leave at any time. A round you have not finished is not saved.

## Example round

```
Welcome to the Quiz Game!

Categories:
  1. General Knowledge
  2. Science
  3. Math
Choose a category (name or number): 2

Question 1 of 3
What is the chemical formula for water?
Your answer: H2O
Correct! You took 2.31 seconds.

Question 2 of 3
What gas do plants absorb from the atmosphere?
Your answer: oxygen
Wrong! The correct answer was 'Carbon dioxide'.

Question 3 of 3
How many planets are in our solar system?
Your answer: eight
Correct! You took 1.87 seconds.

Quiz Complete! Your score: 2/3
Total time: 7.42 seconds.
Enter your name for the leaderboard: Walter

Leaderboard:
1. Walter - Score: 2, Time: 7.42 seconds

Play again? (y/n): n
Thanks for playing!
```

## Add your own questions

Questions live in the `quiz_data` dictionary at the top of `quiz_game.py`:

```python
"Science": [
    {"question": "How many planets are in our solar system?", "answers": ["8", "eight"]},
    ...
],
```

- `answers` lists everything that counts as correct. The first one is shown to the player after a wrong answer.
- Write the answers the way you want them shown. Capital letters and extra spaces are ignored when an answer is checked.
- To add a category, add a new key with its own list of questions. It appears in the menu by itself.

## The leaderboard

`leaderboard.json` is created next to `quiz_game.py` the first time someone finishes a round, wherever you start the game from. Delete the file to reset it.

If the file cannot be read, for example after a mistake while editing it by hand, the game says so and starts a new leaderboard.

## Tests

```bash
python -m unittest
```

The tests play whole games with scripted answers and a stand-in clock, so nobody has to type and every answer takes a known time. They keep their leaderboard in a temporary folder and never touch your own `leaderboard.json`.

GitHub runs the tests on Linux and Windows for every push and pull request.
