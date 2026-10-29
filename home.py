# The home screen (main menu): streak, last 4 weeks, today, totals and the menu.
import datetime
import time

import stats
import ui

MENU = [("1", "Log workout"), ("2", "My plans"), ("3", "History & stats"),
        ("4", "Search & edit"), ("5", "Profile"), ("0", "Exit")]

SPARK = "▁▂▃▄▅▆▇█"


# Sleepy after 3+ days off, flexing on a 3+ day streak, happy otherwise.
def pick_mood(logs):
    days_off = stats.days_since_last(logs)
    if days_off is not None and days_off >= 3:
        return "sleepy"
    if stats.current_streak(logs) >= 3:
        return "strong"
    return "happy"


def logged_today(logs):
    today = datetime.date.today().isoformat()
    for log in logs:
        if log["date"] == today:
            return True
    return False


def minutes_this_week(logs):
    today = datetime.date.today()
    monday = (today - datetime.timedelta(days=today.weekday())).isoformat()
    total = 0
    for log in logs:
        if log["date"] >= monday:
            total = total + log["duration"]
    return total


def streak_card(state, shown_streak):
    logs = state["logs"]
    goal = state["profile"]["weekly_goal"]
    done = stats.days_this_week(logs)
    digits = ui.big_number(shown_streak)
    lines = [""]
    for i in range(5):
        extra = ""
        if i == 3:
            extra = "  " + ui.paint("day streak", None, True)
        if i == 4:
            extra = "  " + ui.paint(f"best {stats.longest_streak(logs)}", ui.MUTED)
        lines.append(digits[i] + extra)
    lines.append("")
    dots = ""
    for i in range(goal):
        if i < done:
            dots = dots + ui.paint("●", ui.ORANGE) + " "
        else:
            dots = dots + ui.paint("○", ui.DIM) + " "
    lines.append(dots + ui.paint(f"{done} of {goal} days this week", ui.MUTED))
    return ui.card("Streak", lines, ui.ORANGE)


# The last 4 weeks, Monday first, one colored square per day. Squares appear one by
# one while `reveal` grows from 0 to 28.
def month_card(logs, reveal):
    first_activity = {}
    for log in logs:
        if log["date"] not in first_activity:
            first_activity[log["date"]] = log["activity"]
    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday() + 21)
    lines = ["", ui.paint(" M  T  W  T  F  S  S", ui.MUTED)]
    row = ""
    for i in range(28):
        day = start + datetime.timedelta(days=i)
        iso = day.isoformat()
        # One small square per day, so days never merge into stripes, whatever the
        # terminal's line spacing.
        if day > today:
            cell = ui.paint("·", ui.DIM)
        elif i >= reveal:
            cell = " "
        elif iso in first_activity:
            cell = ui.paint("■", ui.activity_rgb(first_activity[iso]))
        elif ui.USE_COLOR:
            cell = ui.paint("■", ui.REST)
        else:
            cell = "□"  # without color, rest days need a different shape
        row = row + " " + cell + " "
        if i % 7 == 6:
            lines.append(row)
            row = ""
    lines.append("")
    legend = ""
    for activity in ui.ACTIVITY_COLORS:
        legend = legend + ui.paint("■ ", ui.activity_rgb(activity)) + ui.paint(activity, ui.MUTED) + "  "
    lines.append(legend.rstrip())
    return ui.card("Last 4 weeks", lines, ui.BLUE)


# One bar per day for the last 14 days; `grow` (0 to 1) animates the bars upwards.
def spark_line(logs, grow):
    today = datetime.date.today()
    days = []
    most = 1
    for back in range(13, -1, -1):
        iso = (today - datetime.timedelta(days=back)).isoformat()
        total = 0
        activity = None
        for log in logs:
            if log["date"] == iso:
                total = total + log["duration"]
                if activity is None:
                    activity = log["activity"]
        days.append((total, activity))
        if total > most:
            most = total
    line = ""
    for total, activity in days:
        if total == 0:
            line = line + ui.paint("▁ ", ui.REST)
        else:
            level = round(total / most * 7 * grow)
            if level > 7:
                level = 7
            line = line + ui.paint(SPARK[level] + " ", ui.activity_rgb(activity))
    return line


def number(label, value):
    return ui.paint(label.upper(), ui.MUTED) + " " + ui.paint(value, None, True)


def screen_lines(state, shown_streak, reveal, grow):
    logs = state["logs"]
    wide = ui.width() >= 66
    today = datetime.date.today()
    lines = ["", ui.gradient("STREAKR", ui.ORANGE, ui.PINK) + "   "
             + ui.paint(f"Hi {state['profile']['name']}!", None, True)
             + ui.paint("  ·  " + f"{today.strftime('%A')} {today.day} {today.strftime('%B')}", ui.MUTED), ""]
    if wide:
        lines = lines + ui.side_by_side(streak_card(state, shown_streak), month_card(logs, reveal), 6)
    else:
        lines = lines + streak_card(state, shown_streak) + [""] + month_card(logs, reveal)
    lines.append("")

    if logged_today(logs):
        message = "Today is done. Rest well."
    elif wide:
        message = "Nothing logged today yet. Press 1 to keep the streak alive."
    else:
        message = "Not logged today. Press 1."
    lines.append(ui.paint(ui.mascot(pick_mood(logs)), ui.ORANGE, True) + "  " + message)
    lines.append("")

    totals = [number("minutes", f"{stats.total_of(logs, 'duration'):,}"),
              number("kcal", f"{stats.total_of(logs, 'calories'):,}"),
              number("workouts", str(len(logs))),
              ui.paint("THIS WEEK", ui.MUTED) + " " + ui.paint(f"{minutes_this_week(logs)} min", None, True)]
    if wide:
        lines.append("    ".join(totals))
    else:
        lines.append("    ".join(totals[:2]))
        lines.append("    ".join(totals[2:]))
    lines.append(ui.paint("LAST 14 DAYS ", ui.MUTED) + spark_line(logs, grow))
    lines.append("")
    lines.append(ui.paint("─" * (ui.width() - 6), ui.DIM))

    per_row = 2
    if wide:
        per_row = 3
    for i in range(0, len(MENU), per_row):
        row = ""
        for key, name in MENU[i:i + per_row]:
            row = row + ui.pad(ui.option(key, name), 22)
        lines.append(row.rstrip())
    lines.append("")
    return lines


# Show the home screen. With animate=True the streak counts up, the calendar fills in
# and the bars grow (about half a second); without a real terminal it just prints.
def show(state, animate):
    streak = stats.current_streak(state["logs"])
    if not ui.USE_COLOR:
        for line in screen_lines(state, streak, 28, 1):
            print("  " + line)
        return
    if animate:
        ui.hide_cursor()
        frames = 14
        for frame in range(frames + 1):
            part = frame / frames
            ui.draw(screen_lines(state, round(streak * part), round(28 * part), part))
            time.sleep(0.03)
        ui.show_cursor()
    else:
        ui.clear()
        ui.draw(screen_lines(state, streak, 28, 1))
