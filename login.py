# Login screen for the terminal app when people reach it over SSH (STREAKR_LOGIN=1).
# It uses the same accounts as the web view, so one login works in both places.
# Uses: accounts.py, db.py, inputs.py, ui.py
# Used by: main.py
import getpass
import sys
import time

import accounts
import db
import inputs
import ui

MAX_WRONG = 3        # wrong logins in one visit before the program closes
BACK = "back"


# Used by: log_in, create_account.
def ask_password(prompt):
    # getpass hides what is typed. When the input is not a real terminal (tests), it
    # cannot hide anything, so read the line normally.
    if sys.stdin.isatty():
        return getpass.getpass(prompt)
    return input(prompt)


# One try. Returns the account id, None for a wrong login, or BACK.
# Used by: run_login.
def log_in():
    ui.header("Log in")
    print("  " + ui.paint("(type b to go back)", ui.MUTED))
    username = inputs.ask_text("Username: ", True)
    if username is None:
        return BACK
    password = ask_password("Password: ")
    user_id, error = accounts.log_in(username, password)
    if user_id is None:
        ui.error(error)
        time.sleep(1)  # makes guessing slow
    return user_id


# Returns the new account id, or BACK.
# Used by: run_login.
def create_account():
    ui.header("Create account")
    print("  " + ui.paint("(type b to go back)", ui.MUTED))
    while True:
        username = inputs.ask_text("Choose a username (3-20 letters, numbers, _ - .): ", True)
        if username is None:
            return BACK
        username = username.strip().lower()
        error = accounts.username_error(username)
        if error == "" and db.find_user(username) is not None:
            error = "That username is taken."
        if error == "":
            break
        ui.error(error)
    while True:
        password = ask_password("Choose a password (at least 8 characters): ")
        error = accounts.password_error(password)
        if error != "":
            ui.error(error)
            continue
        if ask_password("Type it again: ") != password:
            ui.error("The two passwords are different. Try again.")
            continue
        break
    user_id, error = accounts.sign_up(username, password)
    if user_id is None:
        # Someone took the name while we were typing the password.
        ui.error(error)
        return BACK
    ui.success(f"Account '{username}' created.")
    return user_id


# Returns the account id of the person who logged in, or None to quit.
# Used by: main.main.
def run_login():
    wrong = 0
    while True:
        ui.clear()
        print("\n")
        for line in ui.logo_lines():
            print("  " + line)
        print()
        ui.say("happy", ui.paint("Welcome! ", None, True) + ui.paint("Track your workouts, keep your streak.", ui.MUTED))
        print()
        print(ui.option(1, "Log in"))
        print(ui.option(2, "Create account"))
        print(ui.option(0, "Exit"))
        print()
        choice = input("  " + ui.paint(ui.PROMPT, ui.ORANGE, True)).strip()
        if choice == "1":
            user_id = log_in()
            if user_id is None:
                wrong = wrong + 1
                if wrong >= MAX_WRONG:
                    ui.error("Too many wrong logins. Bye!")
                    return None
                ui.pause()
            elif user_id != BACK:
                return user_id
        elif choice == "2":
            user_id = create_account()
            if user_id != BACK:
                return user_id
        elif choice == "0":
            return None
        else:
            ui.error("Please choose 0, 1 or 2.")
            ui.pause()
