import datetime


# Rule 2: the same day + activity + focus may only be logged once.
# skip_id lets an edited log ignore itself.
def is_duplicate(logs, date, activity, focus, skip_id=None):
    for log in logs:
        if log["id"] == skip_id:
            continue
        if log["date"] == date and log["activity"] == activity and log["focus"] == focus:
            return True
    return False


# Rest days only matter for Gym and Cardio HIIT. Yoga and Pilates are fine every day.
def rest_rule_applies(activity, focus):
    if activity == "Gym":
        return True
    if activity == "Cardio" and focus == "HIIT":
        return True
    return False


# Rule 1: warn when the same group is trained on the day before or the day after.
def needs_rest(logs, date, activity, focus, skip_id=None):
    if not rest_rule_applies(activity, focus):
        return False
    day = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    day_before = (day - datetime.timedelta(days=1)).isoformat()
    day_after = (day + datetime.timedelta(days=1)).isoformat()
    for log in logs:
        if log["id"] == skip_id:
            continue
        if log["activity"] == activity and log["focus"] == focus:
            if log["date"] == day_before or log["date"] == day_after:
                return True
    return False


# Rule 3: every exercise must belong to the chosen focus.
def valid_exercises(library, activity, focus, names):
    allowed = library[activity][focus]
    bad_names = []
    for name in names:
        if name not in allowed:
            bad_names.append(name)
    ok = len(bad_names) == 0
    return ok, bad_names


# Rule 4: a plan has 1-10 exercises and no exercise twice.
def valid_plan(exercises):
    if len(exercises) < 1 or len(exercises) > 10:
        return False, "A plan needs 1 to 10 exercises."
    seen = []
    for name in exercises:
        if name in seen:
            return False, f"'{name}' is in the plan twice."
        seen.append(name)
    return True, "OK"
