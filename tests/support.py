"""Helpers shared by the tests. Every test gets its own empty database, so the real
gym.db is never touched."""
import datetime
import os
import shutil
import tempfile

import accounts
import db

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def use_temp_db(test):
    """Point db.py at a fresh database for this test and undo it afterwards."""
    folder = tempfile.mkdtemp(prefix="streakr-test-")
    old_file = db.DB_FILE
    db.DB_FILE = os.path.join(folder, "test.db")
    db.init_db()
    old_rounds = accounts.ITERATIONS
    accounts.ITERATIONS = 1000  # real hashing is slow on purpose; tests do not need that

    def restore():
        db.DB_FILE = old_file
        accounts.ITERATIONS = old_rounds
        shutil.rmtree(folder, ignore_errors=True)

    test.addCleanup(restore)
    return db.DB_FILE


def day(offset):
    """The date `offset` days from today as YYYY-MM-DD (negative = in the past)."""
    return (datetime.date.today() + datetime.timedelta(days=offset)).isoformat()


def make_log(log_id, date, activity="Gym", focus="Upper Body", exercises=None,
             duration=60, calories=350):
    if exercises is None:
        exercises = ["Bench Press"]
    return {"id": log_id, "date": date, "activity": activity, "focus": focus,
            "exercises": exercises, "duration": duration, "calories": calories}


PROFILE = {"name": "Tester", "gender": "male", "age": 24, "height": 175, "weight": 70,
           "weekly_goal": 4, "activities": ["Gym", "Yoga", "Cardio"]}


def new_user_with_profile(username="tester", password="password-123", profile=None):
    """Create a web account with a saved profile and return its id."""
    user_id, error = accounts.sign_up(username, password)
    assert error == "", error
    if profile is None:
        profile = dict(PROFILE)
    db.save_profile(profile, user_id)
    return user_id
