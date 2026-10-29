"""The terminal app in SSH mode (STREAKR_LOGIN=1): everyone logs in to their own account."""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from tests.support import ROOT

SIGN_UP_KAN = ["2", "kan", "password-123", "password-123",
               "Kan", "1", "30", "170", "60", "1", "3"]       # account, then onboarding


class TerminalLogin(unittest.TestCase):
    def setUp(self):
        folder = tempfile.mkdtemp(prefix="streakr-login-")
        self.addCleanup(shutil.rmtree, folder, True)
        self.db_file = os.path.join(folder, "gym.db")

    def run_app(self, lines, login=True):
        env = dict(os.environ)
        env["STREAKR_DB"] = self.db_file
        if login:
            env["STREAKR_LOGIN"] = "1"
        else:
            env.pop("STREAKR_LOGIN", None)
        done = subprocess.run([sys.executable, os.path.join(ROOT, "main.py")],
                              input="\n".join(lines) + "\n", capture_output=True, text=True,
                              env=env, cwd=ROOT, timeout=60)
        self.assertEqual(done.stderr, "", done.stderr)
        self.assertEqual(done.returncode, 0)
        return done.stdout

    def rows(self, table):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        rows = []
        for row in conn.execute("SELECT * FROM " + table).fetchall():
            rows.append(dict(row))
        conn.close()
        return rows

    def test_sign_up_with_mistakes_then_onboarding(self):
        out = self.run_app(["2", "b"] +                                 # back to the welcome screen
                           ["2", "x", "Kan!", "kan", "short", "password-123", "typo-123",
                            "password-123", "password-123",
                            "Kan", "1", "30", "170", "60", "1", "3", "0"])
        self.assertIn("3 to 20 characters", out)
        self.assertIn("letters, numbers", out)
        self.assertIn("at least 8 characters", out)
        self.assertIn("two passwords are different", out)
        self.assertIn("Account 'kan' created.", out)
        self.assertIn("Hi Kan!", out)
        users = self.rows("users")
        self.assertEqual(users[-1]["username"], "kan")
        self.assertTrue(users[-1]["password_hash"].startswith("pbkdf2_sha256$"))
        self.assertEqual(self.rows("profile")[0]["id"], users[-1]["id"])

    def test_taken_username(self):
        self.run_app(SIGN_UP_KAN + ["0"])
        out = self.run_app(["2", "KAN", "b", "0"])
        self.assertIn("That username is taken.", out)

    def test_log_in_again_and_see_only_your_own_workouts(self):
        self.run_app(SIGN_UP_KAN + ["1", "", "1", "2", "1", "40", "", "", "0"])  # log Squat
        out = self.run_app(["1", "KAN", "password-123", "3", "", "0"])
        self.assertIn("Hi Kan!", out)
        self.assertIn("Squat", out)
        self.assertIn("TOTAL TIME 40 min", out)

    def test_accounts_and_local_data_are_separate(self):
        self.run_app(["Local", "1", "30", "170", "60", "1", "3", "1", "", "1", "1", "1", "60", "",
                      "", "0"], login=False)                             # local account logs Bench
        self.run_app(SIGN_UP_KAN + ["0"])
        out = self.run_app(["1", "kan", "password-123", "3", "", "0"])
        self.assertIn("No workouts yet", out)
        self.assertNotIn("Bench Press", out)
        out = self.run_app(["3", "", "0"], login=False)
        self.assertIn("Hi Local!", out)
        self.assertIn("Bench Press", out)
        owners = []
        for log in self.rows("logs"):
            owners.append(log["user_id"])
        self.assertEqual(owners, [1])

    def test_local_account_cannot_be_used_over_ssh(self):
        out = self.run_app(["1", "local", "", "", "1", "local", "anything", "",
                            "1", "local", "x"])
        self.assertIn("Too many wrong logins. Bye!", out)

    def test_three_wrong_logins_close_the_program(self):
        self.run_app(SIGN_UP_KAN + ["0"])
        out = self.run_app(["1", "kan", "wrong-1", "", "1", "kan", "wrong-2", "",
                            "1", "kan", "wrong-3"])
        self.assertEqual(out.count("Wrong username or password."), 3)
        self.assertIn("Too many wrong logins. Bye!", out)
        self.assertNotIn("Hi Kan!", out)

    def test_lock_carries_over_to_the_next_connection(self):
        self.run_app(SIGN_UP_KAN + ["0"])
        self.run_app(["1", "kan", "a", "", "1", "kan", "b", "", "1", "kan", "c"])
        self.run_app(["1", "kan", "d", "", "1", "kan", "e", "", "0"])        # fifth wrong try
        out = self.run_app(["1", "kan", "password-123", "", "0"])
        self.assertIn("Too many wrong tries", out)
        self.assertNotIn("Hi Kan!", out)

    def test_exit_and_end_of_input_at_the_welcome_screen(self):
        self.assertIn("Bye!", self.run_app(["0"]))
        self.assertIn("Bye!", self.run_app([]))          # like Ctrl-D

    def test_control_characters_are_refused_in_names(self):
        out = self.run_app(["2", "kan", "password-123", "password-123",
                            "Evil\x1b[2J", "Kan", "1", "30", "170", "60", "1", "3", "0"])
        self.assertIn("normal letters", out)
        self.assertEqual(self.rows("profile")[0]["name"], "Kan")

    def test_without_login_mode_nothing_changes(self):
        out = self.run_app(["Local", "1", "30", "170", "60", "1", "3", "0"], login=False)
        self.assertNotIn("Log in", out)
        self.assertEqual(self.rows("profile")[0]["id"], 1)

    def test_workouts_logged_over_ssh_show_on_the_web(self):
        self.run_app(SIGN_UP_KAN + ["1", "", "1", "2", "1", "40", "", "", "0"])
        conn = sqlite3.connect(self.db_file)
        user_id = conn.execute("SELECT id FROM users WHERE username = 'kan'").fetchone()[0]
        exercises = conn.execute("SELECT exercises FROM logs WHERE user_id = ?", (user_id,)).fetchone()[0]
        conn.close()
        self.assertEqual(json.loads(exercises), ["Squat"])


if __name__ == "__main__":
    unittest.main()
