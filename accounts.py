# Sign-up, log-in and sessions, for the web view and the terminal login. Standard library only.
import datetime
import hashlib
import hmac
import secrets
import time

import db

ITERATIONS = 200000          # PBKDF2 rounds: slow on purpose, so guessing passwords is slow
SESSION_DAYS = 30
MAX_FAILS = 5                # wrong passwords in a row before the account is locked
LOCK_SECONDS = 300

MAX_TRACKED = 10000          # past this many rows, forget usernames that are not locked

# Wrong tries are kept in the database, not in memory: every SSH connection is a new
# program, so a counter in memory would start from zero each time someone reconnects.


def failed_tries(username):
    for row in db.select_all("login_fails"):
        if row["username"] == username:
            return row
    return None


def record_failed_try(username, now):
    row = failed_tries(username)
    fails = 1
    if row is not None:
        fails = row["fails"] + 1
    locked_until = 0
    if fails >= MAX_FAILS:
        locked_until = now + LOCK_SECONDS
        fails = 0
    rows = db.select_all("login_fails")
    if len(rows) >= MAX_TRACKED:
        # Made-up usernames must not fill the table forever.
        for old in rows:
            if old["locked_until"] < now:
                db.delete_login_fail(old["username"])
    db.save_login_fail(username, fails, locked_until)


# Stored as "pbkdf2_sha256$rounds$salt$hash". A fresh random salt per password means two
# people with the same password still get different hashes.
def hash_password(password, salt=None, rounds=None):
    if salt is None:
        salt = secrets.token_hex(16)
    if rounds is None:
        rounds = ITERATIONS
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), rounds)
    return f"pbkdf2_sha256${rounds}${salt}${digest.hex()}"


def check_password(password, stored):
    parts = stored.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    again = hash_password(password, parts[2], int(parts[1]))
    # compare_digest takes the same time whether the first or last character differs.
    return hmac.compare_digest(again, stored)


def username_error(username):
    if len(username) < 3 or len(username) > 20:
        return "Username must be 3 to 20 characters."
    for ch in username:
        if not (ch.isascii() and (ch.isalnum() or ch in "_-.")):
            return "Username can only use letters, numbers, _ - and ."
    return ""


def password_error(password):
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 128:
        return "Password must be at most 128 characters."
    return ""


# Returns (user_id, error). Usernames are stored in lowercase so "Kan" and "kan" are one account.
def sign_up(username, password):
    username = username.strip().lower()
    error = username_error(username)
    if error == "":
        error = password_error(password)
    if error != "":
        return None, error
    if db.find_user(username) is not None:
        return None, "That username is taken."
    created = datetime.datetime.now().isoformat(timespec="seconds")
    return db.create_user(username, hash_password(password), created), ""


# Returns (user_id, error). The same message for a wrong name or a wrong password,
# so nobody can find out which usernames exist.
def log_in(username, password):
    username = username.strip().lower()
    now = time.time()
    tries = failed_tries(username)
    if tries is not None and tries["locked_until"] > now:
        return None, "Too many wrong tries. Wait 5 minutes and try again."
    user = db.find_user(username)
    if user is None or user["password_hash"] == "":
        hash_password(password)  # same work as a real check, so the timing gives nothing away
        ok = False
    else:
        ok = check_password(password, user["password_hash"])
    if not ok:
        record_failed_try(username, now)
        return None, "Wrong username or password."
    if tries is not None:
        db.delete_login_fail(username)
    return user["id"], ""


# The browser keeps the random token; the database only keeps its SHA-256, so a copy
# of gym.db is not enough to log in as someone.
def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# Old sessions are removed whenever someone logs in, so the table does not keep growing.
def remove_expired_sessions():
    now = datetime.datetime.now().isoformat(timespec="seconds")
    for session in db.select_all("sessions"):
        if session["expires"] < now:
            db.delete_session(session["token_hash"])


def start_session(user_id):
    remove_expired_sessions()
    token = secrets.token_urlsafe(32)
    expires = datetime.datetime.now() + datetime.timedelta(days=SESSION_DAYS)
    db.save_session(token_hash(token), user_id, expires.isoformat(timespec="seconds"))
    return token


# The account id for a session token, or None when it is unknown or expired.
def user_for_token(token):
    if token == "":
        return None
    session = db.find_session(token_hash(token))
    if session is None:
        return None
    if session["expires"] < datetime.datetime.now().isoformat(timespec="seconds"):
        db.delete_session(session["token_hash"])
        return None
    return session["user_id"]


def end_session(token):
    db.delete_session(token_hash(token))
