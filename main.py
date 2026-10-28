import os

import db
import login
import menus
import onboarding
import plans
import stats
import ui

MENU_ITEMS = ["1. Log workout", "2. My plans", "3. History & stats",
              "4. Search / edit / delete", "5. Profile & library", "0. Exit"]


# Sleepy after 3+ days off, flexing on a 3+ day streak, happy otherwise.
def pick_mood(logs):
    days_off = stats.days_since_last(logs)
    if days_off is not None and days_off >= 3:
        return "sleepy"
    if stats.current_streak(logs) >= 3:
        return "strong"
    return "happy"


def print_main_menu(state):
    profile = state["profile"]
    logs = state["logs"]
    streak = stats.current_streak(logs)
    done = stats.days_this_week(logs)
    goal = profile["weekly_goal"]
    lines = [f"Hi {profile['name']}!  {ui.mascot(pick_mood(logs))}",
             f"Streak: {ui.color(str(streak) + ' days', 'yellow')}   "
             f"Week: {ui.progress(done, goal)} {done}/{goal}",
             ""]
    for item in MENU_ITEMS:
        lines.append(item)
    ui.clear()
    print(ui.box("Streakr", lines))


def main():
    db.init_db()
    # Over SSH (STREAKR_LOGIN=1) everyone logs in to their own account. Run normally,
    # the app uses the built-in local account, exactly as before.
    user_id = db.LOCAL_USER
    if os.environ.get("STREAKR_LOGIN") == "1":
        user_id = login.run_login()
        if user_id is None:
            print("Bye!")
            return
    state = db.load_all(user_id)
    state["user_id"] = user_id
    if state["profile"] is None:
        state["profile"] = onboarding.run_onboarding()
        db.save_profile(state["profile"], user_id)
    while True:
        print_main_menu(state)
        choice = input("> ").strip()
        if choice == "0":
            ui.success("Everything is saved. Bye! Keep the streak going.")
            break
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
        else:
            ui.error("Please choose 0-5.")
        ui.pause()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nBye!")
