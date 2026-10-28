import datetime
import random


def total_of(logs, key):
    total = 0
    for log in logs:
        total = total + log[key]
    return total


def count_by(logs, key):
    counts = {}
    for log in logs:
        value = log[key]
        if value in counts:
            counts[value] = counts[value] + 1
        else:
            counts[value] = 1
    return counts


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


def logged_dates(logs):
    dates = set()
    for log in logs:
        dates.add(log["date"])
    return dates


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
def days_since_last(logs):
    if len(logs) == 0:
        return None
    latest = logs[0]["date"]
    for log in logs:
        if log["date"] > latest:
            latest = log["date"]
    day = datetime.datetime.strptime(latest, "%Y-%m-%d").date()
    return (datetime.date.today() - day).days


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


def comes_before(a, b, key, reverse):
    if reverse:
        return a[key] > b[key]
    return a[key] < b[key]


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


def search_logs(logs, field, value):
    found = []
    for log in logs:
        if str(log[field]).lower() == str(value).lower():
            found.append(log)
    return found


def find_by_id(items, item_id):
    for item in items:
        if item["id"] == item_id:
            return item
    return None


def random_workout(library, activity, focus, n):
    names = library[activity][focus]
    if n > len(names):
        n = len(names)
    return random.sample(names, n)
