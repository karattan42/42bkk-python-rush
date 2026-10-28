import json
import sqlite3
import unittest

import db
from tests.support import PROFILE, day, use_temp_db


def new_log(date, activity="Gym", focus="Upper Body"):
    return {"date": date, "activity": activity, "focus": focus,
            "exercises": ["Bench Press", "Pull Up"], "duration": 60, "calories": 350}


class Setup(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)

    def test_local_account_and_built_in_exercises(self):
        users = db.select_all("users")
        self.assertEqual(users[0]["id"], db.LOCAL_USER)
        self.assertEqual(users[0]["password_hash"], "")
        count = len(db.select_all("exercises"))
        self.assertGreater(count, 40)

    def test_init_twice_does_not_duplicate(self):
        count = len(db.select_all("exercises"))
        db.init_db()
        self.assertEqual(len(db.select_all("exercises")), count)
        self.assertEqual(len(db.select_all("users")), 1)


class Logs(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)

    def test_round_trip_keeps_exercise_list(self):
        log = new_log(day(0))
        db.save_log(log)
        loaded = db.load_all()["logs"]
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["id"], log["id"])
        self.assertEqual(loaded[0]["exercises"], ["Bench Press", "Pull Up"])
        self.assertNotIn("user_id", loaded[0])

    def test_deleted_id_is_never_reused(self):
        first = new_log(day(-1))
        second = new_log(day(0))
        db.save_log(first)
        db.save_log(second)
        db.delete_log(second["id"])
        third = new_log(day(0), "Yoga", "Relax")
        db.save_log(third)
        self.assertEqual(third["id"], second["id"] + 1)

    def test_update(self):
        log = new_log(day(0))
        db.save_log(log)
        log["duration"] = 15
        db.update_log(log)
        self.assertEqual(db.load_all()["logs"][0]["duration"], 15)


class Accounts(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)

    def test_each_account_only_sees_its_own_data(self):
        other = db.create_user("other", "hash", "now")
        db.save_log(new_log(day(0)))
        db.save_log(new_log(day(-1), "Yoga", "Relax"), other)
        db.save_plan({"name": "Mine", "activity": "Gym", "focus": "Upper Body",
                      "exercises": ["Pull Up"]}, other)
        self.assertEqual(len(db.load_all()["logs"]), 1)
        self.assertEqual(db.load_all()["plans"], [])
        self.assertEqual(db.load_all(other)["logs"][0]["activity"], "Yoga")
        self.assertEqual(db.load_all(other)["plans"][0]["name"], "Mine")

    def test_custom_exercise_is_private_built_ins_are_shared(self):
        other = db.create_user("other", "hash", "now")
        db.save_exercise("Gym", "Upper Body", "Secret Move", 1, other)
        self.assertNotIn("Secret Move", db.load_all()["library"]["Gym"]["Upper Body"])
        self.assertIn("Secret Move", db.load_all(other)["library"]["Gym"]["Upper Body"])
        self.assertIn("Bench Press", db.load_all(other)["library"]["Gym"]["Upper Body"])

    def test_profile_per_account(self):
        other = db.create_user("other", "hash", "now")
        self.assertIsNone(db.load_profile(other))
        db.save_profile(PROFILE, other)
        changed = dict(PROFILE)
        changed["name"] = "Changed"
        db.save_profile(changed, other)
        self.assertEqual(db.load_profile(other)["name"], "Changed")
        self.assertIsNone(db.load_profile(db.LOCAL_USER))
        self.assertEqual(len(db.select_all("profile")), 1)

    def test_find_user_and_sessions(self):
        user_id = db.create_user("alice", "hash", "now")
        self.assertEqual(db.find_user("alice")["id"], user_id)
        self.assertIsNone(db.find_user("bob"))
        db.save_session("abc", user_id, "2999-01-01T00:00:00")
        self.assertEqual(db.find_session("abc")["user_id"], user_id)
        db.delete_session("abc")
        self.assertIsNone(db.find_session("abc"))


class Migration(unittest.TestCase):
    def test_old_database_without_accounts_is_upgraded(self):
        use_temp_db(self)
        # Rebuild the file the way it looked before accounts existed.
        conn = sqlite3.connect(db.DB_FILE)
        for table in ["users", "sessions", "profile", "exercises", "plans", "logs"]:
            conn.execute("DROP TABLE " + table)
        conn.execute("CREATE TABLE logs (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT,"
                     " activity TEXT, focus TEXT, exercises TEXT, duration INTEGER, calories INTEGER)")
        conn.execute("CREATE TABLE exercises (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                     " activity TEXT, focus TEXT, name TEXT, is_custom INTEGER)")
        conn.execute("CREATE TABLE plans (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                     " name TEXT, activity TEXT, focus TEXT, exercises TEXT)")
        conn.execute("INSERT INTO logs (date, activity, focus, exercises, duration, calories)"
                     " VALUES (?, 'Gym', 'Upper Body', ?, 60, 350)", (day(0), json.dumps(["Pull Up"])))
        conn.execute("INSERT INTO exercises (activity, focus, name, is_custom)"
                     " VALUES ('Gym', 'Upper Body', 'Pull Up', 0)")
        conn.commit()
        conn.close()

        db.init_db()
        self.assertIn("user_id", db.column_names("logs"))
        self.assertEqual(len(db.load_all(db.LOCAL_USER)["logs"]), 1)
        self.assertEqual(db.select_all("users")[0]["username"], "local")


if __name__ == "__main__":
    unittest.main()
