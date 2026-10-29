"""Run main.py as a real program and type into it, like a person at the defense."""
import datetime
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from tests.support import ROOT


class Terminal(unittest.TestCase):
    def setUp(self):
        folder = tempfile.mkdtemp(prefix="streakr-cli-")
        self.addCleanup(shutil.rmtree, folder, True)
        self.db_file = os.path.join(folder, "gym.db")

    def run_program(self, script, lines):
        env = dict(os.environ)
        env["STREAKR_DB"] = self.db_file
        env.pop("NO_COLOR", None)
        typed = "\n".join(lines) + "\n"
        done = subprocess.run([sys.executable, os.path.join(ROOT, script)], input=typed,
                              capture_output=True, text=True, env=env, cwd=ROOT, timeout=60)
        self.assertEqual(done.stderr, "", done.stderr)
        return done

    def app(self, *lines):
        return self.run_program("main.py", list(lines)).stdout

    def seed(self):
        self.run_program("seed.py", [])

    def rows(self, table):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        rows = []
        for row in conn.execute("SELECT * FROM " + table).fetchall():
            rows.append(dict(row))
        conn.close()
        return rows

    def test_onboarding_with_wrong_input_and_going_back(self):
        out = self.app("", "Kan",                 # empty name is refused
                       "1",                       # gender: male
                       "b",                       # back to gender
                       "2",                       # female
                       "9", "30", "170", "60",    # age 9 is refused
                       "1,9", "1,2",              # 9 is not an option
                       "8", "3",                  # 8 days is refused
                       "0")
        self.assertIn("at least one character", out)
        self.assertIn("from 10 to 100", out)
        self.assertIn("from 1 to 4", out)
        self.assertIn("from 1 to 7", out)
        profile = self.rows("profile")[0]
        self.assertEqual(profile["name"], "Kan")
        self.assertEqual(profile["gender"], "female")
        self.assertEqual((profile["age"], profile["height"], profile["weight"]), (30, 170, 60))
        self.assertEqual(json.loads(profile["activities"]), ["Gym", "Yoga"])
        self.assertEqual(profile["weekly_goal"], 3)

    def test_rest_day_warning_can_cancel(self):
        self.seed()  # the demo data has Gym / Upper Body yesterday
        out = self.app("1", "", "1", "1", "n", "", "0")
        self.assertIn("Muscles need a rest day", out)
        self.assertIn("Cancelled", out)
        self.assertEqual(len(self.rows("logs")), 18)

    def test_log_with_wrong_exercise_then_duplicate(self):
        self.seed()
        out = self.app("1", "", "1", "2", "Squat, Bench Press", "1,8", "45", "", "",
                       "1", "", "1", "2", "",
                       "0")
        self.assertIn("Not in Lower Body: Bench Press", out)
        self.assertIn("Enter = 262", out)
        self.assertIn("New record: 6 days in a row!", out)
        self.assertIn("You already logged Gym / Lower Body", out)
        logs = self.rows("logs")
        self.assertEqual(len(logs), 19)
        self.assertEqual(json.loads(logs[-1]["exercises"]), ["Squat", "Deadlift"])
        self.assertEqual(logs[-1]["calories"], 262)

    def test_search_missing_id_and_delete_with_confirmation(self):
        self.seed()
        out = self.app("4", "1", "999", "",
                       "4", "1", "18", "2", "n", "",
                       "4", "1", "18", "2", "y", "",
                       "0")
        self.assertIn("No workout with ID 999", out)
        self.assertIn("Kept", out)
        self.assertIn("Deleted", out)
        ids = []
        for log in self.rows("logs"):
            ids.append(log["id"])
        self.assertNotIn(18, ids)
        self.assertEqual(len(ids), 17)

    def test_plan_with_repeated_exercise_is_refused(self):
        self.seed()
        out = self.app("2", "1", "Arms", "1", "1", "1,1", "1,2", "6", "", "0")
        self.assertIn("is in the plan twice", out)
        self.assertIn("Saved plan 'Arms'", out)
        names = []
        for plan in self.rows("plans"):
            names.append(plan["name"])
        self.assertIn("Arms", names)

    def test_start_plan_goes_to_log(self):
        self.seed()
        out = self.app("2", "4", "3", "", "", "30", "", "", "0")  # Morning stretch
        self.assertIn("Plan: Morning stretch (Yoga / Flexibility)", out)
        last = self.rows("logs")[-1]
        self.assertEqual((last["activity"], last["focus"]), ("Yoga", "Flexibility"))

    def test_bad_menu_choice_and_end_of_input(self):
        self.seed()
        done = self.run_program("main.py", ["x", ""])  # input then ends, like Ctrl-D
        self.assertEqual(done.returncode, 0)
        self.assertIn("Please choose 0-6", done.stdout)
        self.assertIn("Bye!", done.stdout)

    def test_exercise_list_is_grouped_and_numbers_match(self):
        self.seed()
        # Gym / Lower Body: Quads first, so number 8 is the first Hamstrings and glutes exercise.
        out = self.app("1", "", "1", "2", "8", "40", "", "", "0")
        self.assertIn("QUADS", out)
        self.assertIn("HAMSTRINGS AND GLUTES", out)
        self.assertIn("8. Deadlift", out)
        self.assertEqual(json.loads(self.rows("logs")[-1]["exercises"]), ["Deadlift"])

    def test_terminal_data_stays_in_the_local_account(self):
        self.seed()
        for log in self.rows("logs"):
            self.assertEqual(log["user_id"], 1)

    def test_calendar_moves_between_months_and_opens_days(self):
        self.seed()
        today = datetime.date.today()
        out = self.app("6", "n", "p", "40", "x", "b", "0")
        self.assertIn(today.strftime("%B %Y").upper(), out)
        self.assertIn("That month has not happened yet.", out)
        self.assertIn("Pick a day from 1 to", out)
        self.assertIn("Type p, n, a day number, or b.", out)
        self.assertIn("WORKOUTS", out)
        self.assertNotIn("Press Enter to go back", out.split("Calendar")[-1])

    def test_open_a_day_and_log_a_forgotten_workout(self):
        self.seed()
        today = datetime.date.today()
        if today.day == 1:
            self.skipTest("needs an earlier day in this month")
        missing = None
        logged = set(log["date"] for log in self.rows("logs"))
        for number in range(today.day - 1, 0, -1):
            if datetime.date(today.year, today.month, number).isoformat() not in logged:
                missing = number
                break
        if missing is None:
            self.skipTest("every day this month already has a workout")
        date = datetime.date(today.year, today.month, missing).isoformat()
        # Yoga (choice 2) has no rest-day question, so the answers always line up.
        out = self.app("6", str(missing), "l", "2", "1", "1", "45", "", "", "b", "0")
        self.assertIn("Rest day. Nothing logged.", out)
        self.assertIn("Saved workout", out)
        self.assertIn(date, [log["date"] for log in self.rows("logs")])


if __name__ == "__main__":
    unittest.main()
