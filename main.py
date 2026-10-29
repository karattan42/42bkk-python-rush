# Starts the terminal app: python3 main.py (over SSH with STREAKR_LOGIN=1).
# Uses: calendar_view.py, db.py, home.py, login.py, menus.py, onboarding.py, plans.py, ui.py
# Used by: nobody imports it; run it with python3 main.py
import os

import calendar_view
import db
import home
import login
import menus
import onboarding
import plans
import ui


# Returns the goodbye message, which is printed after the app hands the terminal back.
# Used by: run.
def main():
    db.init_db()
    ui.splash()
    # Over SSH (STREAKR_LOGIN=1) everyone logs in to their own account. Run normally,
    # the app uses the built-in local account, exactly as before.
    user_id = db.LOCAL_USER
    if os.environ.get("STREAKR_LOGIN") == "1":
        user_id = login.run_login()
        if user_id is None:
            return "Bye!"
    state = db.load_all(user_id)
    state["user_id"] = user_id
    if state["profile"] is None:
        state["profile"] = onboarding.run_onboarding()
        db.save_profile(state["profile"], user_id)

    # The home screen animates the first time, and again whenever the workouts changed.
    shown_count = -1
    while True:
        home.show(state, len(state["logs"]) != shown_count)
        shown_count = len(state["logs"])
        choice = input("  " + ui.paint(ui.PROMPT, ui.ORANGE, True)).strip()
        if choice == "0":
            return "Everything is saved. Bye! Keep the streak going."
        if choice == "1":
            menus.menu_log(state)
        elif choice == "2":
            plans.menu_plans(state)
        elif choice == "3":
            menus.menu_history(state)
        elif choice == "4":
            menus.menu_manage(state)
        elif choice == "5":
            menus.menu_profile(state)
        elif choice == "6":
            calendar_view.menu_calendar(state)
            continue  # the calendar has its own way back, so no "Press Enter" here
        else:
            ui.error("Please choose 0-6.")
        ui.pause()


# Used by: python3 main.py (the if __name__ block).
def run():
    ui.enter_app_screen()
    try:
        message = main()
    except (KeyboardInterrupt, EOFError):
        message = "Bye!"
    finally:
        ui.leave_app_screen()
    ui.success(message)


if __name__ == "__main__":
    run()
