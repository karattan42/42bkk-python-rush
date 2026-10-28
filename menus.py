import db
import fitness
import inputs
import onboarding
import rules
import stats
import ui


def print_logs(logs):
    print(ui.color(f"{'ID':>4}  {'Date':<10}  {'Activity':<18}  {'Min':>4}  {'kcal':>5}  Exercises", "bold"))
    for log in logs:
        what = ui.color(f"{log['activity'] + ' / ' + log['focus']:<18}", ui.activity_color(log["activity"]))
        names = ", ".join(log["exercises"])
        print(f"{log['id']:>4}  {log['date']:<10}  {what}  {log['duration']:>4}  {log['calories']:>5}  {names}")


# Rule 2 check with the message. Returns True when it is OK to continue.
def not_duplicate(logs, date, activity, focus, skip_id=None):
    if rules.is_duplicate(logs, date, activity, focus, skip_id):
        ui.error(f"You already logged {activity} / {focus} on {date}.")
        print("  Edit that workout from menu 4 instead.")
        return False
    return True


# Rule 1 check with the warning. Returns True when it is OK to continue.
def rest_day_ok(logs, date, activity, focus, skip_id=None):
    if rules.needs_rest(logs, date, activity, focus, skip_id):
        ui.warn(f"You trained {activity} / {focus} the day before or after {date}.")
        ui.warn("Muscles need a rest day to recover.")
        if not inputs.ask_yes_no("Log it anyway?"):
            print("  Cancelled.")
            return False
    return True


# for_plan=True also checks rule 4 (1-10 exercises, no repeats).
# For a log, repeats are simply dropped.
def pick_exercises(library, activity, focus, for_plan=False):
    # Print the exercises under their group names, numbered straight through.
    names = []
    print(f"Exercises for {activity} / {focus}:")
    for group, group_names in fitness.grouped_exercises(library, activity, focus):
        if group != "":
            print(ui.color("  " + group, "dim"))
        for name in group_names:
            names.append(name)
            print(f"  {len(names)}. {name}")
    while True:
        text = input("Exercises (numbers or names, separated by commas): ")
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
def ask_calories(state, activity, duration):
    estimate = fitness.estimate_kcal(activity, state["profile"]["weight"], duration)
    return inputs.ask_int(f"Calories burned (Enter = {estimate}, 0-3000): ", 0, 3000,
                          default=estimate)


def menu_log(state, preset=None):
    ui.title("Log workout")
    library = state["library"]
    logs = state["logs"]
    date = inputs.ask_date("Date YYYY-MM-DD (Enter = today): ")
    if preset is None:
        activity = inputs.ask_choice("Activity:", state["profile"]["activities"])
        focus = inputs.ask_choice("Focus:", list(library[activity].keys()))
    else:
        activity = preset["activity"]
        focus = preset["focus"]
        print(f"Plan: {preset['name']} ({activity} / {focus})")

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


def menu_history(state):
    logs = state["logs"]
    ui.title("History & stats")
    if len(logs) == 0:
        print("  No workouts yet. Log one from menu 1.")
        return
    print_logs(stats.sort_logs(logs, "date", True))
    print()
    goal = state["profile"]["weekly_goal"]
    done = stats.days_this_week(logs)
    lines = [f"Total time     : {stats.total_of(logs, 'duration')} min",
             f"Total calories : {stats.total_of(logs, 'calories')} kcal",
             f"Current streak : {stats.current_streak(logs)} days",
             f"Best streak    : {stats.longest_streak(logs)} days",
             f"This week      : {ui.progress(done, goal)} {done}/{goal} days"]
    top = stats.most_frequent_exercise(logs)
    if top is not None:
        lines.append(f"Most frequent  : {top[0]} ({top[1]} times)")
    lines.append("")
    counts = stats.count_by(logs, "activity")
    for activity in counts:
        bar = ui.color("■" * counts[activity], ui.activity_color(activity))
        lines.append(f"{activity:<8} {counts[activity]:>3} {bar}")
    print(ui.box("Summary", lines))


def menu_manage(state):
    logs = state["logs"]
    ui.title("Search / edit / delete")
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
        delete_log(state, log)


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


def delete_log(state, log):
    print_logs([log])
    if inputs.ask_yes_no(f"Delete workout #{log['id']}?"):
        db.delete_log(log["id"])
        state["logs"].remove(log)
        ui.success("Deleted.")
    else:
        print("  Kept.")


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


def menu_profile(state):
    profile = state["profile"]
    while True:
        ui.title("Profile & library")
        print(ui.box(profile["name"], [
            f"Gender: {profile['gender']}   Age: {profile['age']}",
            f"Height: {profile['height']} cm   Weight: {profile['weight']} kg",
            f"Weekly goal: {profile['weekly_goal']} days",
            f"Activities: {', '.join(profile['activities'])}",
            f"BMR: {round(fitness.bmr(profile))} kcal/day at rest"]))
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
