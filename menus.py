# Terminal menus 1, 3, 4 and 5: log a workout, history & stats, search & edit, profile.
# Uses: db.py, fitness.py, home.py, inputs.py, onboarding.py, rules.py, stats.py, ui.py
# Used by: calendar_view.py, main.py, plans.py
import datetime

import db
import fitness
import home
import inputs
import onboarding
import rules
import stats
import ui


# 2026-10-29 -> "Thu 29 Oct 2026".
# Used by: calendar_view.show_day, print_logs, menu_log.
def nice_date(iso):
    day = datetime.datetime.strptime(iso, "%Y-%m-%d").date()
    return f"{day.strftime('%a')} {day.day} {day.strftime('%b %Y')}"


# Workouts grouped under their date. Each one: a bar in the activity's color, what was
# trained, its ID, the minutes and kcal on the right, and the exercises underneath.
# Used by: calendar_view.show_day, menu_history, menu_manage, confirm_delete_log.
def print_logs(logs):
    last_date = None
    for log in logs:
        if log["date"] != last_date:
            print()
            print("  " + ui.paint(nice_date(log["date"]), None, True))
            last_date = log["date"]
        bar = ui.paint("▍", ui.activity_rgb(log["activity"]), True)
        left = (ui.paint(log["focus"], None, True) + "  "
                + ui.paint(log["activity"], ui.activity_rgb(log["activity"]))
                + ui.paint(f"  #{log['id']}", ui.MUTED))
        right = (ui.paint(f"{log['duration']:>3} min", None, True)
                 + ui.paint(f"  {log['calories']:>4} kcal", ui.MUTED))
        print("  " + bar + " " + ui.pad(left, 42) + right)
        print("  " + bar + "   " + ui.paint(", ".join(log["exercises"]), ui.MUTED))


# Rule 2 check with the message. Returns True when it is OK to continue.
# Used by: menu_log, edit_log.
def not_duplicate(logs, date, activity, focus, skip_id=None):
    if rules.is_duplicate(logs, date, activity, focus, skip_id):
        ui.error(f"You already logged {activity} / {focus} on {date}.")
        print("  " + ui.paint("Edit that workout from menu 4 instead.", ui.MUTED))
        return False
    return True


# Rule 1 check with the warning. Returns True when it is OK to continue.
# Used by: menu_log, edit_log.
def rest_day_ok(logs, date, activity, focus, skip_id=None):
    if rules.needs_rest(logs, date, activity, focus, skip_id):
        ui.warn(f"You trained {activity} / {focus} the day before or after {date}.")
        ui.warn("Muscles need a rest day to recover.")
        if not inputs.ask_yes_no("Log it anyway?"):
            print("  " + ui.paint("Cancelled.", ui.MUTED))
            return False
    return True


# for_plan=True also checks rule 4 (1-10 exercises, no repeats).
# For a log, repeats are simply dropped.
# Used by: menu_log, edit_log, plans.create_plan.
def pick_exercises(library, activity, focus, for_plan=False):
    # Print the exercises under their group names, numbered straight through.
    names = []
    print()
    print("  " + ui.paint(f"Exercises for {activity} / {focus}", None, True))
    columns = 1
    if ui.USE_COLOR:
        columns = max(1, (ui.width() - 4) // 26)
    for group, group_names in fitness.grouped_exercises(library, activity, focus):
        if group != "":
            print("  " + ui.paint(group.upper(), ui.activity_rgb(activity), True))
        row = ""
        for i in range(len(group_names)):
            names.append(group_names[i])
            row = row + ui.pad(ui.option(len(names), group_names[i]), 26)
            if (i + 1) % columns == 0 or i == len(group_names) - 1:
                print(row.rstrip())
                row = ""
    while True:
        text = input(inputs.indent("Exercises (numbers or names, separated by commas): "))
        chosen = []
        for part in text.split(","):
            part = part.strip()
            if part == "":
                continue
            if part.isdigit() and int(part) >= 1 and int(part) <= len(names):
                part = names[int(part) - 1]
            if for_plan or part not in chosen:
                chosen.append(part)
        if len(chosen) == 0:
            ui.error("Pick at least one exercise.")
            continue
        ok, bad_names = rules.valid_exercises(library, activity, focus, chosen)
        if not ok:
            ui.error(f"Not in {focus}: {', '.join(bad_names)}. Try again.")
            continue
        if for_plan:
            ok, message = rules.valid_plan(chosen)
            if not ok:
                ui.error(f"{message} Try again.")
                continue
        return chosen


# Suggest kcal from MET; Enter accepts it, or the user types their own number.
# Used by: menu_log, edit_log.
def ask_calories(state, activity, duration):
    estimate = fitness.estimate_kcal(activity, state["profile"]["weight"], duration)
    return inputs.ask_int(f"Calories burned (Enter = {estimate}, 0-3000): ", 0, 3000,
                          default=estimate)


# preset: a plan to log. date: a day chosen on the calendar (otherwise we ask).
# Used by: calendar_view.show_day, main.main, plans.start_plan.
def menu_log(state, preset=None, date=None):
    ui.title("Log workout")
    library = state["library"]
    logs = state["logs"]
    if date is None:
        date = inputs.ask_date("Date YYYY-MM-DD (Enter = today): ")
    else:
        print("  " + ui.paint("Date: " + nice_date(date), None, True))
    if preset is None:
        activity = inputs.ask_choice("Activity:", state["profile"]["activities"])
        focus = inputs.ask_choice("Focus:", list(library[activity].keys()))
    else:
        activity = preset["activity"]
        focus = preset["focus"]
        print("  " + ui.paint(f"Plan: {preset['name']} ({activity} / {focus})", ui.activity_rgb(activity), True))

    if not not_duplicate(logs, date, activity, focus):
        return
    if not rest_day_ok(logs, date, activity, focus):
        return

    if preset is None:
        exercises = pick_exercises(library, activity, focus)
    else:
        exercises = list(preset["exercises"])
    duration = inputs.ask_int("Duration in minutes (1-300): ", 1, 300)
    calories = ask_calories(state, activity, duration)

    log = {"date": date, "activity": activity, "focus": focus,
           "exercises": exercises, "duration": duration, "calories": calories}
    record_before = stats.longest_streak(logs)
    db.save_log(log, state["user_id"])
    logs.append(log)
    ui.celebrate(f"Saved workout #{log['id']}.")
    record_after = stats.longest_streak(logs)
    if record_after > record_before and record_after >= 2:
        ui.strong(f"New record: {record_after} days in a row!")


# One bar split into each activity's share of all workouts, with a legend.
# Used by: menu_history.
def mix_lines(logs):
    counts = stats.count_by(logs, "activity")
    size = 36
    bar = ""
    used = 0
    names = list(counts.keys())
    for i in range(len(names)):
        part = counts[names[i]] * size // len(logs)
        if i == len(names) - 1:
            part = size - used
        used = used + part
        bar = bar + ui.paint("█" * part, ui.activity_rgb(names[i]))
    legend = ""
    for name in names:
        percent = round(counts[name] * 100 / len(logs))
        legend = legend + ui.paint("■ ", ui.activity_rgb(name)) + f"{name} {counts[name]} " + ui.paint(f"({percent}%)", ui.MUTED) + "   "
    if not ui.USE_COLOR:
        bar = ""
    return [bar, legend.rstrip()]


# Menu 3: totals, weekly goal, activity mix, last 4 weeks, 14-day bars, all workouts.
# Used by: main.main.
def menu_history(state):
    logs = state["logs"]
    ui.title("History & stats")
    if len(logs) == 0:
        ui.say("sleepy", "No workouts yet. Log one from menu 1.")
        return
    goal = state["profile"]["weekly_goal"]
    done = stats.days_this_week(logs)
    totals = [home.label_value("total time", f"{stats.total_of(logs, 'duration'):,} min"),
              home.label_value("kcal", f"{stats.total_of(logs, 'calories'):,}"),
              home.label_value("streak", ui.plural(stats.current_streak(logs), "day"))
              + ui.paint(f" (best {stats.longest_streak(logs)})", ui.MUTED)]
    summary = ["   ".join(totals),
               ui.paint("THIS WEEK ", ui.MUTED) + ui.progress(done, goal) + f" {done} of {goal} days", ""]
    summary = summary + mix_lines(logs)
    top = stats.most_frequent_exercise(logs)
    if top is not None:
        summary.append("")
        summary.append(ui.paint("MOST USED ", ui.MUTED) + ui.paint(top[0], None, True)
                       + ui.paint("  " + ui.plural(top[1], "time"), ui.MUTED))
    for line in ui.card("Summary", summary, ui.ORANGE):
        print("  " + line)
    print()
    for line in home.month_card(logs, 28):
        print("  " + line)
    print("  " + ui.paint("▍", ui.BLUE, True) + " " + ui.paint("LAST 14 DAYS ", ui.MUTED) + home.spark_line(logs, 1))
    print()
    print("  " + ui.paint("WORKOUTS", ui.MUTED, True) + ui.paint(f"  {len(logs)} total, newest first", ui.MUTED))
    print_logs(stats.sort_logs(logs, "date", True))


# Menu 4: find workouts by ID, date or activity, then edit or delete one.
# Used by: main.main.
def menu_manage(state):
    logs = state["logs"]
    ui.title("Search & edit")
    how = inputs.ask_choice("Search by:", ["ID", "Date", "Activity"])
    if how == "ID":
        log_id = inputs.ask_int("Workout ID: ", 1, 1000000)
        found = stats.find_by_id(logs, log_id)
        if found is None:
            ui.error(f"No workout with ID {log_id}.")
            return
        results = [found]
    elif how == "Date":
        date = inputs.ask_date("Date YYYY-MM-DD (Enter = today): ")
        results = stats.search_logs(logs, "date", date)
    else:
        activity = inputs.ask_choice("Activity:", list(state["library"].keys()))
        results = stats.search_logs(logs, "activity", activity)

    if len(results) == 0:
        ui.error("Nothing found.")
        return
    print_logs(stats.sort_logs(results, "date", True))
    action = inputs.ask_choice("What next?", ["Edit", "Delete", "Back"])
    if action == "Back":
        return
    if len(results) == 1:
        log = results[0]
    else:
        log_id = inputs.ask_int("Which ID? ", 1, 1000000)
        log = stats.find_by_id(results, log_id)
        if log is None:
            ui.error(f"ID {log_id} is not in the results.")
            return
    if action == "Edit":
        edit_log(state, log)
    else:
        confirm_delete_log(state, log)


# Change one field of a workout. A new date is checked by the same rules as logging.
# Used by: menu_manage.
def edit_log(state, log):
    logs = state["logs"]
    field = inputs.ask_choice("Edit which field?", ["Date", "Duration", "Calories", "Exercises"])
    if field == "Date":
        new_date = inputs.ask_date("New date YYYY-MM-DD (Enter = today): ")
        if not not_duplicate(logs, new_date, log["activity"], log["focus"], log["id"]):
            return
        if not rest_day_ok(logs, new_date, log["activity"], log["focus"], log["id"]):
            return
        log["date"] = new_date
    elif field == "Duration":
        log["duration"] = inputs.ask_int("Duration in minutes (1-300): ", 1, 300)
    elif field == "Calories":
        log["calories"] = ask_calories(state, log["activity"], log["duration"])
    else:
        log["exercises"] = pick_exercises(state["library"], log["activity"], log["focus"])
    db.update_log(log)
    ui.success(f"Workout #{log['id']} updated.")


# Delete a workout after asking y/n.
# Used by: menu_manage.
def confirm_delete_log(state, log):
    print_logs([log])
    if inputs.ask_yes_no(f"Delete workout #{log['id']}?"):
        db.delete_log(log["id"])
        state["logs"].remove(log)
        ui.success("Deleted.")
    else:
        print("  " + ui.paint("Kept.", ui.MUTED))


# Add a custom exercise to the library (saved for this account only).
# Used by: menu_profile.
def add_exercise(state):
    library = state["library"]
    activity = inputs.ask_choice("Activity:", state["profile"]["activities"])
    focus = inputs.ask_choice("Focus:", list(library[activity].keys()))
    name = inputs.ask_text("Exercise name: ")
    if "," in name:
        ui.error("Names cannot contain commas.")
        return
    if name in library[activity][focus]:
        ui.error(f"{name} is already in {activity} / {focus}.")
        return
    db.save_exercise(activity, focus, name, 1, state["user_id"])
    library[activity][focus].append(name)
    ui.success(f"Added {name} to {activity} / {focus}.")


# Menu 5: show the profile, edit it, or add a custom exercise.
# Used by: main.main.
def menu_profile(state):
    profile = state["profile"]
    while True:
        ui.title("Profile")
        activities = ""
        for activity in profile["activities"]:
            activities = activities + ui.paint("■ ", ui.activity_rgb(activity)) + activity + "  "
        lines = ["",
                 ui.paint(profile["gender"].capitalize(), None, True) + ui.paint("  ·  ", ui.DIM)
                 + f"{profile['age']} years" + ui.paint("  ·  ", ui.DIM)
                 + f"{profile['height']} cm" + ui.paint("  ·  ", ui.DIM) + f"{profile['weight']} kg",
                 ui.paint("GOAL ", ui.MUTED) + f"{profile['weekly_goal']} days a week",
                 ui.paint("DOES ", ui.MUTED) + activities.rstrip(),
                 ui.paint("BMR  ", ui.MUTED) + ui.paint(f"{round(fitness.bmr(profile)):,}", None, True)
                 + ui.paint(" kcal a day at rest", ui.MUTED), ""]
        for line in ui.card(profile["name"], lines, ui.PURPLE):
            print("  " + line)
        choice = inputs.ask_choice("Choose:", ["Edit name", "Edit gender", "Edit age", "Edit height",
                                               "Edit weight", "Edit weekly goal",
                                               "Edit activities",
                                               "Add my own exercise", "Back"])
        if choice == "Edit name":
            profile["name"] = inputs.ask_text("Name: ")
        elif choice == "Edit gender":
            label = inputs.ask_choice("Gender:", ["Male", "Female", "Not specified"])
            profile["gender"] = onboarding.GENDERS[label]
        elif choice == "Edit age":
            profile["age"] = inputs.ask_int("Age (10-100): ", 10, 100)
        elif choice == "Edit height":
            profile["height"] = inputs.ask_int("Height in cm (100-250): ", 100, 250)
        elif choice == "Edit weight":
            profile["weight"] = inputs.ask_int("Weight in kg (30-250): ", 30, 250)
        elif choice == "Edit weekly goal":
            profile["weekly_goal"] = inputs.ask_int("Days per week (1-7): ", 1, 7)
        elif choice == "Edit activities":
            profile["activities"] = inputs.ask_multi("Which activities do you do?",
                                                     list(state["library"].keys()))
        elif choice == "Add my own exercise":
            add_exercise(state)
        else:
            return
        db.save_profile(profile, state["user_id"])
