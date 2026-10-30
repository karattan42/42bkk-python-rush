# Totals, streaks, sorting, searching and months, all with plain loops.
# Used by: calendar_view.py, home.py, menus.py, plans.py, server.py
import datetime
import random


# Add up one number field (duration or calories) over all logs.
# Used by: 7 places in calendar_view, home, menus, server.
def total_of(logs, key):
    total = 0
    for log in logs:
        total = total + log[key]
    return total


# How many logs have each value of a field, e.g. {"Gym": 5, "Yoga": 2}.
# Used by: menus.mix_lines, server.mix_html.
def count_by(logs, key):
    counts = {}
    for log in logs:
        value = log[key]
        if value in counts:
            counts[value] = counts[value] + 1
        else:
            counts[value] = 1
    return counts


# The exercise name that appears in the most logs.
# Used by: menus.menu_history, server.mix_html.
def most_frequent_exercise(logs):
    counts = {}
    for log in logs:
        for name in log["exercises"]:
            if name in counts:
                counts[name] = counts[name] + 1
            else:
                counts[name] = 1
    best_name = None
    best_count = 0
    for name in counts:
        if counts[name] > best_count:
            best_name = name
            best_count = counts[name]
    if best_name is None:
        return None
    return best_name, best_count


# Every date with at least one workout (a set, so each date once).
# Used by: current_streak, longest_streak, days_this_week.
def logged_dates(logs):
    dates = set()
    for log in logs:
        dates.add(log["date"])
    return dates


# Used by: home.pick_mood, home.show, menus.menu_history, server.mood_sentence,
# server.streak_html, server.tiles_html.
def current_streak(logs):
    dates = logged_dates(logs)
    day = datetime.date.today()
    # Not trained yet today? The streak is still alive, so start counting from yesterday.
    if day.isoformat() not in dates:
        day = day - datetime.timedelta(days=1)
    streak = 0
    while day.isoformat() in dates:
        streak = streak + 1
        day = day - datetime.timedelta(days=1)
    return streak


# No sorting needed: a streak starts on a day whose day before was not logged,
# then we count forward while the next day is logged.
# Used by: home.streak_card, menus.menu_log, menus.menu_history, server.tiles_html.
def longest_streak(logs):
    dates = logged_dates(logs)
    best = 0
    for date in dates:
        day = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        if (day - datetime.timedelta(days=1)).isoformat() in dates:
            continue
        length = 0
        while day.isoformat() in dates:
            length = length + 1
            day = day + datetime.timedelta(days=1)
        if length > best:
            best = length
    return best


# Days since the most recent workout, or None when there are no workouts.
# Used by: home.pick_mood, server.mood_sentence.
def days_since_last(logs):
    if len(logs) == 0:
        return None
    latest = logs[0]["date"]
    for log in logs:
        if log["date"] > latest:
            latest = log["date"]
    day = datetime.datetime.strptime(latest, "%Y-%m-%d").date()
    return (datetime.date.today() - day).days


# How many different days have a workout since Monday.
# Used by: home.streak_card, menus.menu_history, server.streak_html.
def days_this_week(logs):
    dates = logged_dates(logs)
    today = datetime.date.today()
    day = today - datetime.timedelta(days=today.weekday())  # Monday
    count = 0
    while day <= today:
        if day.isoformat() in dates:
            count = count + 1
        day = day + datetime.timedelta(days=1)
    return count


# True when a should be placed before b (sort_logs uses this).
# Used by: sort_logs.
def comes_before(a, b, key, reverse):
    if reverse:
        return a[key] > b[key]
    return a[key] < b[key]


# Return a sorted copy of logs by one key (our own insertion sort).
# Used by: menus.menu_history, menus.menu_manage, server.history_html.
def sort_logs(logs, key, reverse):
    result = []
    for log in logs:
        result.append(log)
    # Insertion sort: take each item and slide it left until it is in the right place.
    for i in range(1, len(result)):
        current = result[i]
        j = i - 1
        while j >= 0 and comes_before(current, result[j], key, reverse):
            result[j + 1] = result[j]
            j = j - 1
        result[j + 1] = current
    return result


# Logs whose field equals value, ignoring upper/lower case.
# Used by: calendar_view.show_day, menus.menu_manage.
def search_logs(logs, field, value):
    found = []
    for log in logs:
        if str(log[field]).lower() == str(value).lower():
            found.append(log)
    return found


# The item with this id, or None.
# Used by: menus.menu_manage, server.Handler.do_GET.
def find_by_id(items, item_id):
    for item in items:
        if item["id"] == item_id:
            return item
    return None


# n different random exercises from one focus.
# Used by: plans.random_plan.
def random_workout(library, activity, focus, n):
    names = library[activity][focus]
    if n > len(names):
        n = len(names)
    return random.sample(names, n)


# The month `step` months away from year/month (step can be negative).
# Used by: calendar_view.menu_calendar, server.calendar_html, days_in_month.
def add_months(year, month, step):
    index = year * 12 + (month - 1) + step
    return index // 12, index % 12 + 1


# 28 to 31: the first of next month minus the first of this month.
# Used by: calendar_view.menu_calendar.
def days_in_month(year, month):
    next_year, next_month = add_months(year, month, 1)
    return (datetime.date(next_year, next_month, 1) - datetime.date(year, month, 1)).days


# The days of a month as weeks, Monday first. Days outside the month are None,
# e.g. a month starting on Wednesday begins [None, None, date(..., 1), ...].
# Used by: calendar_view.calendar_lines, server.calendar_html.
def month_weeks(year, month):
    day = datetime.date(year, month, 1)
    week = []
    for i in range(day.weekday()):
        week.append(None)
    weeks = []
    while day.month == month:
        week.append(day)
        if len(week) == 7:
            weeks.append(week)
            week = []
        day = day + datetime.timedelta(days=1)
    if len(week) > 0:
        while len(week) < 7:
            week.append(None)
        weeks.append(week)
    return weeks


# Dates are "YYYY-MM-DD", so a month's logs all start with "YYYY-MM-".
# Used by: calendar_view.calendar_lines, server.calendar_html.
def logs_in_month(logs, year, month):
    prefix = f"{year:04d}-{month:02d}-"
    found = []
    for log in logs:
        if log["date"].startswith(prefix):
            found.append(log)
    return found


# date -> list of the activities done that day (each one once, in the order logged).
# Used by: calendar_view.calendar_lines, server.calendar_html.
def activities_by_date(logs):
    by_date = {}
    for log in logs:
        if log["date"] not in by_date:
            by_date[log["date"]] = []
        if log["activity"] not in by_date[log["date"]]:
            by_date[log["date"]].append(log["activity"])
    return by_date
