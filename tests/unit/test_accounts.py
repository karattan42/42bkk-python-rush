import unittest
from unittest import mock

import accounts
import db
from tests.support import use_temp_db


class Passwords(unittest.TestCase):
    def test_real_setting_is_slow_enough(self):
        self.assertGreaterEqual(accounts.ITERATIONS, 200000)

    def test_hash_format_and_check(self):
        stored = accounts.hash_password("correct horse")
        self.assertTrue(stored.startswith(f"pbkdf2_sha256${accounts.ITERATIONS}$"))
        self.assertNotIn("correct horse", stored)
        self.assertTrue(accounts.check_password("correct horse", stored))
        self.assertFalse(accounts.check_password("correct horsE", stored))

    def test_same_password_gets_different_salts(self):
        self.assertNotEqual(accounts.hash_password("same"), accounts.hash_password("same"))

    def test_broken_stored_value_never_matches(self):
        self.assertFalse(accounts.check_password("x", ""))
        self.assertFalse(accounts.check_password("x", "md5$abc"))


class SignUp(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)

    def test_username_is_stored_lowercase(self):
        user_id, error = accounts.sign_up("  Alice ", "password-123")
        self.assertEqual(error, "")
        self.assertEqual(db.find_user("alice")["id"], user_id)

    def test_taken_username_any_case(self):
        accounts.sign_up("alice", "password-123")
        self.assertEqual(accounts.sign_up("ALICE", "password-456")[1], "That username is taken.")

    def test_bad_usernames(self):
        for name in ["ab", "a" * 21, "has space", "<b>", "อลิซ", "semi;colon"]:
            user_id, error = accounts.sign_up(name, "password-123")
            self.assertIsNone(user_id, name)
            self.assertNotEqual(error, "", name)

    def test_password_length(self):
        self.assertIn("at least 8", accounts.sign_up("alice", "1234567")[1])
        self.assertIn("at most 128", accounts.sign_up("alice", "x" * 129)[1])
        self.assertEqual(accounts.sign_up("alice", "        ")[1], "")  # spaces are allowed


class LogIn(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)
        self.user_id = accounts.sign_up("bob", "bob-password")[0]

    def test_right_and_wrong_password(self):
        self.assertEqual(accounts.log_in("BOB", "bob-password"), (self.user_id, ""))
        self.assertEqual(accounts.log_in("bob", "nope")[1], "Wrong username or password.")

    def test_unknown_user_gets_the_same_message(self):
        self.assertEqual(accounts.log_in("nobody", "whatever")[1], "Wrong username or password.")

    def test_local_terminal_account_cannot_log_in(self):
        self.assertIsNone(accounts.log_in("local", "")[0])
        self.assertIsNone(accounts.log_in("local", "anything")[0])

    def test_locked_after_five_wrong_tries_then_unlocked(self):
        for i in range(5):
            accounts.log_in("bob", "wrong")
        self.assertIn("Too many", accounts.log_in("bob", "bob-password")[1])
        later = accounts.time.time() + accounts.LOCK_SECONDS + 1
        with mock.patch("accounts.time.time", return_value=later):
            self.assertEqual(accounts.log_in("bob", "bob-password")[0], self.user_id)

    def test_success_resets_the_counter(self):
        for i in range(4):
            accounts.log_in("bob", "wrong")
        accounts.log_in("bob", "bob-password")
        for i in range(4):
            accounts.log_in("bob", "wrong")
        self.assertEqual(accounts.log_in("bob", "bob-password")[0], self.user_id)

    def test_made_up_names_do_not_fill_the_table(self):
        with mock.patch("accounts.MAX_TRACKED", 20):
            for i in range(60):
                accounts.log_in(f"fake{i}", "wrong")
            self.assertLessEqual(len(db.select_all("login_fails")), 21)

    def test_lock_survives_a_new_program(self):
        # Over SSH every connection is a new process: the lock must live in the database.
        for i in range(5):
            accounts.log_in("bob", "wrong")
        rows = db.select_all("login_fails")
        self.assertEqual(rows[0]["username"], "bob")
        self.assertGreater(rows[0]["locked_until"], accounts.time.time())


class Sessions(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)
        self.user_id = accounts.sign_up("carol", "carol-password")[0]

    def test_token_works_until_logout(self):
        token = accounts.start_session(self.user_id)
        self.assertEqual(accounts.user_for_token(token), self.user_id)
        accounts.end_session(token)
        self.assertIsNone(accounts.user_for_token(token))

    def test_only_a_hash_of_the_token_is_stored(self):
        token = accounts.start_session(self.user_id)
        stored = db.select_all("sessions")[0]["token_hash"]
        self.assertNotEqual(stored, token)
        self.assertEqual(stored, accounts.token_hash(token))

    def test_unknown_empty_and_expired_tokens(self):
        self.assertIsNone(accounts.user_for_token(""))
        self.assertIsNone(accounts.user_for_token("made-up"))
        db.save_session(accounts.token_hash("old"), self.user_id, "2000-01-01T00:00:00")
        self.assertIsNone(accounts.user_for_token("old"))
        self.assertIsNone(db.find_session(accounts.token_hash("old")))

    def test_logging_in_clears_expired_sessions(self):
        db.save_session("stale", self.user_id, "2000-01-01T00:00:00")
        accounts.start_session(self.user_id)
        self.assertIsNone(db.find_session("stale"))
        self.assertEqual(len(db.select_all("sessions")), 1)


if __name__ == "__main__":
    unittest.main()
