"""Tests for quiz_game.py.

Run them from this folder with:  python -m unittest

Nobody has to type anything: input() is replaced with scripted answers, the
clock is replaced with one that makes every answer take a fixed time, and the
leaderboard is kept in a temporary folder, never in your own leaderboard.json.
"""

import contextlib
import copy
import io
import itertools
import json
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import quiz_game

SCRIPT = Path(quiz_game.__file__)

# The answer shown for each question, looked up by the question's text.
ANSWER_BOOK = {q["question"]: q["answers"][0] for questions in quiz_game.quiz_data.values() for q in questions}

# Typed in place of an answer, this means "the right answer to the question on screen".
RIGHT = object()


def play(function, *typed, seconds=2.0):
    """Call function() as if these lines were typed at its prompts.

    Returns (what the function returned, everything that was printed).
    Every answer takes exactly 'seconds' on the stand-in clock.
    """
    screen = io.StringIO()
    typed = list(typed)

    def fake_input(prompt=""):
        if not typed:
            raise EOFError("nothing left to type")
        line = typed.pop(0)
        if line is RIGHT:
            question = screen.getvalue().rstrip("\n").split("\n")[-1]
            line = ANSWER_BOOK[question]
        screen.write(f"{prompt}{line}\n")
        return line

    clock = itertools.count(start=0, step=seconds)
    with mock.patch("builtins.input", fake_input), \
            mock.patch("quiz_game.time.perf_counter", lambda: next(clock)), \
            contextlib.redirect_stdout(screen):
        result = function()
    return result, screen.getvalue()


class AnswerTests(unittest.TestCase):
    def test_capital_letters_and_extra_spaces_do_not_matter(self):
        for typed in ("Paris", "paris", "PARIS", "  paris  ", "\tParis\n"):
            with self.subTest(typed=typed):
                self.assertTrue(quiz_game.is_correct(typed, ["Paris"]))
        self.assertTrue(quiz_game.is_correct("george   ORWELL", ["George Orwell"]))

    def test_any_of_the_listed_answers_counts(self):
        answers = ["8", "eight"]
        self.assertTrue(quiz_game.is_correct("8", answers))
        self.assertTrue(quiz_game.is_correct("Eight", answers))

    def test_other_answers_are_wrong(self):
        for typed in ("", " ", "London", "Par", "Paris France", "Paris."):
            with self.subTest(typed=typed):
                self.assertFalse(quiz_game.is_correct(typed, ["Paris"]))


class QuestionDataTests(unittest.TestCase):
    def test_every_category_has_questions(self):
        self.assertTrue(quiz_game.quiz_data)
        for category, questions in quiz_game.quiz_data.items():
            with self.subTest(category=category):
                self.assertTrue(questions)

    def test_every_question_has_text_and_at_least_one_answer(self):
        for category, questions in quiz_game.quiz_data.items():
            for q in questions:
                with self.subTest(category=category, question=q.get("question")):
                    self.assertTrue(q["question"].strip())
                    self.assertTrue(q["answers"])
                    for answer in q["answers"]:
                        self.assertIsInstance(answer, str)
                        self.assertTrue(answer.strip())

    def test_no_question_appears_twice(self):
        every_question = [q["question"] for questions in quiz_game.quiz_data.values() for q in questions]
        self.assertEqual(len(every_question), len(set(every_question)))

    def test_category_names_cannot_be_confused(self):
        names = [quiz_game.tidy(category) for category in quiz_game.quiz_data]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            # A category called "2" could not be told apart from "category number 2".
            self.assertFalse(name.isdigit(), name)


class AskQuestionTests(unittest.TestCase):
    def ask(self, typed, seconds=2.5):
        return play(lambda: quiz_game.ask_question("What is the capital of France?", ["Paris"]), typed, seconds=seconds)

    def test_a_right_answer_earns_a_point(self):
        (points, time_taken), screen = self.ask("paris")
        self.assertEqual(points, 1)
        self.assertEqual(time_taken, 2.5)
        self.assertIn("Correct! You took 2.50 seconds.", screen)

    def test_a_wrong_answer_earns_nothing_and_shows_the_right_one(self):
        (points, time_taken), screen = self.ask("London")
        self.assertEqual(points, 0)
        self.assertEqual(time_taken, 2.5)
        self.assertIn("Wrong! The correct answer was 'Paris'.", screen)

    def test_the_question_is_shown_before_the_answer_is_typed(self):
        _, screen = self.ask("paris")
        self.assertEqual(screen.split("\n")[:2], ["What is the capital of France?", "Your answer: paris"])


class ChooseCategoryTests(unittest.TestCase):
    def test_the_categories_are_listed_with_numbers(self):
        _, screen = play(quiz_game.choose_category, "1")
        for number, category in enumerate(quiz_game.quiz_data, start=1):
            self.assertIn(f"  {number}. {category}\n", screen)

    def test_a_category_can_be_chosen_by_number(self):
        for number, category in enumerate(quiz_game.quiz_data, start=1):
            with self.subTest(number=number):
                self.assertEqual(play(quiz_game.choose_category, str(number))[0], category)

    def test_a_category_can_be_chosen_by_name(self):
        for typed, category in (("Science", "Science"), ("science", "Science"), ("  MATH ", "Math"),
                                ("general knowledge", "General Knowledge"),
                                ("General   Knowledge", "General Knowledge")):
            with self.subTest(typed=typed):
                self.assertEqual(play(quiz_game.choose_category, typed)[0], category)

    def test_anything_else_is_asked_again(self):
        category, screen = play(quiz_game.choose_category, "history", "0", "4", "", "sci", "3")
        self.assertEqual(category, "Math")
        self.assertEqual(screen.count("That is not one of the categories. Please try again."), 5)


class LeaderboardTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.file = Path(folder.name) / "leaderboard.json"

    def load(self):
        """Load the file. Returns (the leaderboard, what was printed)."""
        return play(lambda: quiz_game.load_leaderboard(self.file))

    def test_no_file_yet_means_an_empty_leaderboard(self):
        self.assertEqual(self.load(), ({}, ""))

    def test_what_is_saved_can_be_loaded_again(self):
        leaderboard = {"Walter": {"score": 3, "time": 5.25}, "Zoë": {"score": 2, "time": 7.5},
                       "李雷": {"score": 1, "time": 9.0}}
        quiz_game.save_leaderboard(leaderboard, self.file)
        self.assertEqual(self.load(), (leaderboard, ""))

    def test_a_leaderboard_from_the_first_version_of_the_game_still_loads(self):
        self.file.write_text('{"Walter": {"score": 2, "time": 7.42}, "": {"score": 0, "time": 3.1}}')
        leaderboard, _ = self.load()
        self.assertEqual(leaderboard["Walter"], {"score": 2, "time": 7.42})

    def test_a_damaged_file_gives_an_empty_leaderboard_and_a_message(self):
        damaged = {
            "not JSON": '{"Walter": {"score": 2, ',
            "empty file": "",
            "a list": "[1, 2, 3]",
            "a number for a player": '{"Walter": 3}',
            "no time": '{"Walter": {"score": 2}}',
            "a word for a score": '{"Walter": {"score": "two", "time": 1.5}}',
            "not text": b"\xff\xfe\x00\x01",
        }
        for case, content in damaged.items():
            with self.subTest(case=case):
                if isinstance(content, bytes):
                    self.file.write_bytes(content)
                else:
                    self.file.write_text(content)
                leaderboard, screen = self.load()
                self.assertEqual(leaderboard, {})
                self.assertEqual(screen, "leaderboard.json is damaged, so the leaderboard starts again from empty.\n")

    def test_a_folder_that_cannot_be_written_to_is_reported(self):
        missing_folder = self.file.parent / "no" / "such" / "folder" / "leaderboard.json"
        _, screen = play(lambda: quiz_game.save_leaderboard({"Walter": {"score": 3, "time": 5.0}}, missing_folder))
        self.assertIn("The leaderboard could not be saved:", screen)

    def test_a_first_round_is_recorded(self):
        leaderboard = {}
        self.assertTrue(quiz_game.update_leaderboard(leaderboard, "Walter", 2, 7.5))
        self.assertEqual(leaderboard, {"Walter": {"score": 2, "time": 7.5}})

    def test_only_a_better_round_replaces_the_old_one(self):
        rounds = [
            ("a higher score", 3, 9.0, True),
            ("a higher score, even if slower", 3, 99.0, True),
            ("the same score, faster", 2, 7.0, True),
            ("the same score, slower", 2, 8.0, False),
            ("exactly the same", 2, 7.5, False),
            ("a lower score, even if faster", 1, 1.0, False),
        ]
        for case, score, seconds, recorded in rounds:
            with self.subTest(case=case):
                leaderboard = {"Walter": {"score": 2, "time": 7.5}}
                self.assertEqual(quiz_game.update_leaderboard(leaderboard, "Walter", score, seconds), recorded)
                expected = {"score": score, "time": seconds} if recorded else {"score": 2, "time": 7.5}
                self.assertEqual(leaderboard, {"Walter": expected})

    def test_players_do_not_affect_each_other(self):
        leaderboard = {"Walter": {"score": 2, "time": 7.5}}
        quiz_game.update_leaderboard(leaderboard, "Ada", 1, 3.0)
        self.assertEqual(leaderboard, {"Walter": {"score": 2, "time": 7.5}, "Ada": {"score": 1, "time": 3.0}})

    def test_the_best_score_comes_first_and_time_settles_a_tie(self):
        leaderboard = {
            "Slow and right": {"score": 3, "time": 20.0},
            "Wrong": {"score": 0, "time": 1.0},
            "Fast and right": {"score": 3, "time": 5.0},
            "Middle": {"score": 2, "time": 2.0},
        }
        self.assertEqual([player for player, _ in quiz_game.ranked(leaderboard)],
                         ["Fast and right", "Slow and right", "Middle", "Wrong"])

    def test_the_leaderboard_is_shown_with_places(self):
        leaderboard = {"Ada": {"score": 2, "time": 7.416}, "Walter": {"score": 3, "time": 5.1}}
        _, screen = play(lambda: quiz_game.show_leaderboard(leaderboard))
        self.assertEqual(screen, "\nLeaderboard:\n"
                                 "1. Walter - Score: 3, Time: 5.10 seconds\n"
                                 "2. Ada - Score: 2, Time: 7.42 seconds\n")


class GameTests(unittest.TestCase):
    """Whole games, played through main()."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.file = Path(folder.name) / "leaderboard.json"

    def play(self, *typed, seconds=2.0):
        """Play the game with these lines typed. Returns what was printed."""
        return play(lambda: quiz_game.main(self.file), *typed, seconds=seconds)[1]

    def saved(self):
        return json.loads(self.file.read_text())

    def test_a_perfect_round(self):
        screen = self.play("2", RIGHT, RIGHT, RIGHT, "Walter", "n")
        self.assertTrue(screen.startswith("Welcome to the Quiz Game!\n"))
        self.assertEqual(screen.count("Correct! You took 2.00 seconds."), 3)
        self.assertIn("Quiz Complete! Your score: 3/3\nTotal time: 6.00 seconds.\n", screen)
        self.assertIn("\nLeaderboard:\n1. Walter - Score: 3, Time: 6.00 seconds\n", screen)
        self.assertTrue(screen.endswith("Play again? (y/n): n\nThanks for playing!\n"))
        self.assertEqual(self.saved(), {"Walter": {"score": 3, "time": 6.0}})

    def test_wrong_answers_score_nothing_but_still_take_time(self):
        screen = self.play("math", "no idea", RIGHT, "", "Walter", "n", seconds=1.5)
        self.assertEqual(screen.count("Wrong! The correct answer was"), 2)
        self.assertIn("Quiz Complete! Your score: 1/3\nTotal time: 4.50 seconds.\n", screen)
        self.assertEqual(self.saved(), {"Walter": {"score": 1, "time": 4.5}})

    def test_every_question_in_the_category_is_asked_once(self):
        for category, questions in quiz_game.quiz_data.items():
            for seed in range(5):
                with self.subTest(category=category, seed=seed):
                    random.seed(seed)
                    screen = self.play(category, *[RIGHT] * len(questions), "Walter", "n")
                    for q in questions:
                        self.assertEqual(screen.count(q["question"] + "\n"), 1)
                    self.assertIn(f"Question {len(questions)} of {len(questions)}\n", screen)
                    self.assertIn(f"Your score: {len(questions)}/{len(questions)}", screen)

    def test_the_questions_come_in_a_different_order_from_game_to_game(self):
        orders = set()
        for seed in range(20):
            random.seed(seed)
            screen = self.play("1", RIGHT, RIGHT, RIGHT, "Walter", "n")
            orders.add(tuple(line for line in screen.split("\n") if line in ANSWER_BOOK))
        self.assertGreater(len(orders), 1)

    def test_playing_does_not_reorder_the_question_list_itself(self):
        before = copy.deepcopy(quiz_game.quiz_data)
        for seed in range(5):
            random.seed(seed)
            self.play("1", RIGHT, RIGHT, RIGHT, "Walter", "n")
        self.assertEqual(quiz_game.quiz_data, before)

    def test_playing_again_in_another_category(self):
        screen = self.play("1", RIGHT, RIGHT, RIGHT, "Walter", "y",
                           "3", RIGHT, "wrong", RIGHT, "Ada", "n")
        self.assertEqual(screen.count("Quiz Complete!"), 2)
        self.assertEqual(screen.count("Welcome to the Quiz Game!"), 1)
        self.assertTrue(screen.endswith("\nLeaderboard:\n"
                                        "1. Walter - Score: 3, Time: 6.00 seconds\n"
                                        "2. Ada - Score: 2, Time: 6.00 seconds\n"
                                        "\nPlay again? (y/n): n\nThanks for playing!\n"), screen)
        self.assertEqual(self.saved(), {"Walter": {"score": 3, "time": 6.0}, "Ada": {"score": 2, "time": 6.0}})

    def test_a_worse_round_does_not_replace_a_players_best(self):
        screen = self.play("1", RIGHT, RIGHT, RIGHT, "Walter", "yes",
                           "1", "a", "b", "c", "Walter", "no")
        self.assertIn("Enter your name for the leaderboard: Walter\n"
                      "Your best round is still 3 in 6.00 seconds.\n", screen)
        self.assertEqual(screen.count("Your best round is still"), 1)
        self.assertEqual(self.saved(), {"Walter": {"score": 3, "time": 6.0}})

    def test_the_leaderboard_is_kept_between_games(self):
        self.play("1", RIGHT, RIGHT, RIGHT, "Walter", "n", seconds=3)
        screen = self.play("1", RIGHT, RIGHT, RIGHT, "Ada", "n", seconds=1)
        self.assertIn("\nLeaderboard:\n"
                      "1. Ada - Score: 3, Time: 3.00 seconds\n"
                      "2. Walter - Score: 3, Time: 9.00 seconds\n", screen)

    def test_the_same_score_in_less_time_is_a_new_best(self):
        self.play("1", RIGHT, RIGHT, RIGHT, "Walter", "n", seconds=3)
        screen = self.play("1", RIGHT, RIGHT, RIGHT, "Walter", "n", seconds=1)
        self.assertNotIn("Your best round is still", screen)
        self.assertEqual(self.saved(), {"Walter": {"score": 3, "time": 3.0}})

    def test_a_blank_name_is_asked_for_again(self):
        screen = self.play("1", RIGHT, RIGHT, RIGHT, "", "   ", "  Walter   Aggor ", "n")
        self.assertEqual(screen.count("Please type a name."), 2)
        self.assertEqual(list(self.saved()), ["Walter Aggor"])

    def test_play_again_needs_a_yes_or_a_no(self):
        screen = self.play("1", RIGHT, RIGHT, RIGHT, "Walter", "maybe", "", "N")
        self.assertEqual(screen.count("Please answer y or n."), 2)
        self.assertTrue(screen.endswith("Thanks for playing!\n"))

    def test_a_damaged_leaderboard_does_not_stop_the_game(self):
        self.file.write_text("this is not JSON")
        screen = self.play("1", RIGHT, RIGHT, RIGHT, "Walter", "n")
        self.assertIn("leaderboard.json is damaged", screen)
        self.assertEqual(self.saved(), {"Walter": {"score": 3, "time": 6.0}})

    def test_nothing_is_saved_if_the_game_is_abandoned(self):
        with self.assertRaises(EOFError):
            self.play("1", RIGHT, RIGHT)
        self.assertFalse(self.file.exists())


class ScriptTests(unittest.TestCase):
    """The game started the way a player starts it: python quiz_game.py"""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        # Work on a copy, so that the leaderboard it writes is not your own.
        self.game_folder = Path(folder.name) / "game"
        self.other_folder = Path(folder.name) / "somewhere else"
        self.game_folder.mkdir()
        self.other_folder.mkdir()
        self.script = Path(shutil.copy(SCRIPT, self.game_folder))

    def run_script(self, typed):
        return subprocess.run([sys.executable, str(self.script)], input=typed, cwd=str(self.other_folder),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60)

    def test_a_whole_game(self):
        finished = self.run_script("history\n2\nh2o\nh2o\nh2o\nWalter\nn\n")
        self.assertEqual(finished.returncode, 0, finished.stderr)
        self.assertEqual(finished.stderr, "")
        self.assertIn("Welcome to the Quiz Game!", finished.stdout)
        self.assertIn("Quiz Complete! Your score: 1/3", finished.stdout)
        self.assertIn("1. Walter - Score: 1, Time: ", finished.stdout)
        self.assertTrue(finished.stdout.endswith("Thanks for playing!\n"))

    def test_the_leaderboard_is_saved_next_to_the_game(self):
        self.run_script("1\na\nb\nc\nWalter\nn\n")
        saved = json.loads((self.game_folder / "leaderboard.json").read_text())
        self.assertEqual(list(saved), ["Walter"])
        self.assertEqual(saved["Walter"]["score"], 0)
        self.assertEqual(list(self.other_folder.iterdir()), [])

    def test_input_that_stops_early_ends_the_game_quietly(self):
        finished = self.run_script("1\nparis\n")
        self.assertEqual(finished.returncode, 0)
        self.assertEqual(finished.stderr, "")
        self.assertTrue(finished.stdout.endswith("\nGoodbye!\n"))
        self.assertFalse((self.game_folder / "leaderboard.json").exists())


if __name__ == "__main__":
    unittest.main()
