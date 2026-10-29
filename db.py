# Every SQL statement of the program is in this file (the SQLite file gym.db).
# Uses: fitness.py
# Used by: accounts.py, login.py, main.py, menus.py, plans.py, seed.py, server.py
import json
import os
import sqlite3

import fitness

# gym.db sits next to this file, so the app finds it from any folder.
# STREAKR_DB moves it somewhere else (Docker keeps it in a volume at /data).
DB_FILE = os.environ.get("STREAKR_DB",
                         os.path.join(os.path.dirname(os.path.abspath(__file__)), "gym.db"))

# Every row belongs to an account. The terminal app always uses account 1 ("local"),
# which has no password, so nobody can log in to it from the web.
LOCAL_USER = 1


# Run one INSERT / UPDATE / DELETE and return the id of the new row (for INSERT).
# Used by: 15 places in db.
def run(sql, values=()):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    cursor = conn.execute(sql, values)
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


# SELECT * from one table, as a list of dict. Filtering and sorting happen in Python.
# Used by: 9 places in accounts, db.
def select_all(table):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM " + table).fetchall()
    conn.close()
    result = []
    for row in rows:
        result.append(dict(row))
    return result


# Used by: add_user_column.
def column_names(table):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    rows = conn.execute("PRAGMA table_info(" + table + ")").fetchall()
    conn.close()
    names = []
    for row in rows:
        names.append(row[1])
    return names


# A gym.db made before accounts existed has no user_id column: add it, and give
# all the old rows to the local account.
# Used by: init_db.
def add_user_column(table):
    if "user_id" not in column_names(table):
        run("ALTER TABLE " + table + " ADD COLUMN user_id INTEGER DEFAULT " + str(LOCAL_USER))


# AUTOINCREMENT makes sure an id is never used again, even after a delete.
# profile.id is the account id, so each account has at most one profile.
# Used by: main.main, seed.main, server.run_server.
def init_db():
    run("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " username TEXT, password_hash TEXT, created TEXT)")
    run("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER,"
        " expires TEXT)")
    run("CREATE TABLE IF NOT EXISTS login_fails (username TEXT PRIMARY KEY, fails INTEGER,"
        " locked_until REAL)")
    run("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, name TEXT, gender TEXT,"
        " age INTEGER, height INTEGER, weight INTEGER, weekly_goal INTEGER, activities TEXT)")
    run("CREATE TABLE IF NOT EXISTS exercises (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " activity TEXT, focus TEXT, name TEXT, is_custom INTEGER, user_id INTEGER)")
    run("CREATE TABLE IF NOT EXISTS plans (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " name TEXT, activity TEXT, focus TEXT, exercises TEXT, user_id INTEGER)")
    run("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT,"
        " activity TEXT, focus TEXT, exercises TEXT, duration INTEGER, calories INTEGER,"
        " user_id INTEGER)")
    add_user_column("exercises")
    add_user_column("plans")
    add_user_column("logs")
    if len(select_all("users")) == 0:
        run("INSERT INTO users (id, username, password_hash, created) VALUES (?, 'local', '', '')",
            (LOCAL_USER,))
    # Add every built-in exercise (shared by everyone) that the table does not have yet:
    # all of them on the first run, only the new ones when the library has grown.
    have = set()
    for row in select_all("exercises"):
        if row["is_custom"] == 0:
            have.add(row["activity"] + "|" + row["focus"] + "|" + row["name"])
    library = fitness.default_library()
    for activity in library:
        for focus in library[activity]:
            for name in library[activity][focus]:
                if activity + "|" + focus + "|" + name not in have:
                    save_exercise(activity, focus, name, 0, 0)


# Used by: load_all.
def load_profile(user_id):
    for row in select_all("profile"):
        if row["id"] == user_id:
            del row["id"]
            row["activities"] = json.loads(row["activities"])
            return row
    return None


# Rebuild the dict -> dict -> list library: the built-in exercises plus this
# account's own custom ones.
# Used by: load_all.
def load_library(user_id):
    library = {}
    for row in select_all("exercises"):
        if row["is_custom"] == 1 and row["user_id"] != user_id:
            continue
        activity = row["activity"]
        focus = row["focus"]
        if activity not in library:
            library[activity] = {}
        if focus not in library[activity]:
            library[activity][focus] = []
        if row["name"] not in library[activity][focus]:
            library[activity][focus].append(row["name"])
    return library


# This account's logs or plans. Their exercise list is stored as JSON text.
# Used by: load_all.
def load_with_exercises(table, user_id):
    items = []
    for item in select_all(table):
        if item["user_id"] != user_id:
            continue
        del item["user_id"]
        item["exercises"] = json.loads(item["exercises"])
        items.append(item)
    return items


# Used by: main.main, server.save_from_form, server.Handler.do_GET, server.Handler.do_POST.
def load_all(user_id=LOCAL_USER):
    return {"profile": load_profile(user_id), "library": load_library(user_id),
            "logs": load_with_exercises("logs", user_id),
            "plans": load_with_exercises("plans", user_id)}


# One profile per account, so replace that account's row.
# Used by: main.main, menus.menu_profile, seed.main, server.Handler.do_POST.
def save_profile(profile, user_id=LOCAL_USER):
    run("DELETE FROM profile WHERE id = ?", (user_id,))
    run("INSERT INTO profile (id, name, gender, age, height, weight, weekly_goal, activities)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, profile["name"], profile["gender"], profile["age"], profile["height"],
         profile["weight"], profile["weekly_goal"], json.dumps(profile["activities"])))


# Used by: init_db, menus.add_exercise, seed.main, server.save_from_form.
def save_exercise(activity, focus, name, is_custom, user_id=LOCAL_USER):
    run("INSERT INTO exercises (activity, focus, name, is_custom, user_id) VALUES (?, ?, ?, ?, ?)",
        (activity, focus, name, is_custom, user_id))


# Inserts the log and writes the id SQLite gave it back into the dict.
# Used by: menus.menu_log, seed.main, server.save_from_form.
def save_log(log, user_id=LOCAL_USER):
    log["id"] = run("INSERT INTO logs (date, activity, focus, exercises, duration, calories,"
                    " user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (log["date"], log["activity"], log["focus"], json.dumps(log["exercises"]),
                     log["duration"], log["calories"], user_id))


# Used by: menus.edit_log.
def update_log(log):
    run("UPDATE logs SET date = ?, activity = ?, focus = ?, exercises = ?, duration = ?,"
        " calories = ? WHERE id = ?",
        (log["date"], log["activity"], log["focus"], json.dumps(log["exercises"]),
         log["duration"], log["calories"], log["id"]))


# Used by: plans.save_new_plan, seed.main.
def save_plan(plan, user_id=LOCAL_USER):
    plan["id"] = run("INSERT INTO plans (name, activity, focus, exercises, user_id)"
                     " VALUES (?, ?, ?, ?, ?)",
                     (plan["name"], plan["activity"], plan["focus"],
                      json.dumps(plan["exercises"]), user_id))


# Used by: plans.edit_plan.
def update_plan(plan):
    run("UPDATE plans SET name = ?, activity = ?, focus = ?, exercises = ? WHERE id = ?",
        (plan["name"], plan["activity"], plan["focus"], json.dumps(plan["exercises"]),
         plan["id"]))


# Used by: plans.delete_plan.
def delete_plan(plan_id):
    run("DELETE FROM plans WHERE id = ?", (plan_id,))


# Used by: menus.delete_log.
def delete_log(log_id):
    run("DELETE FROM logs WHERE id = ?", (log_id,))


# Accounts and logins (used by the web view only).
# Used by: accounts.sign_up.
def create_user(username, password_hash, created):
    return run("INSERT INTO users (username, password_hash, created) VALUES (?, ?, ?)",
               (username, password_hash, created))


# Used by: accounts.sign_up, accounts.log_in, login.create_account.
def find_user(username):
    for row in select_all("users"):
        if row["username"] == username:
            return row
    return None


# Used by: accounts.start_session.
def save_session(token_hash, user_id, expires):
    run("INSERT INTO sessions (token_hash, user_id, expires) VALUES (?, ?, ?)",
        (token_hash, user_id, expires))


# Used by: accounts.user_for_token.
def find_session(token_hash):
    for row in select_all("sessions"):
        if row["token_hash"] == token_hash:
            return row
    return None


# Used by: accounts.remove_expired_sessions, accounts.user_for_token, accounts.end_session.
def delete_session(token_hash):
    run("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


# Used by: accounts.record_failed_try.
def save_login_fail(username, fails, locked_until):
    run("DELETE FROM login_fails WHERE username = ?", (username,))
    run("INSERT INTO login_fails (username, fails, locked_until) VALUES (?, ?, ?)",
        (username, fails, locked_until))


# Used by: accounts.record_failed_try, accounts.log_in.
def delete_login_fail(username):
    run("DELETE FROM login_fails WHERE username = ?", (username,))
