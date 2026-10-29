# The calendar screen: one month at a time, each day colored by what was done.
# n / p move between months, a day number opens that day.
# Uses: home.py, menus.py, stats.py, ui.py
# Used by: main.py
import datetime
import time

import home
import menus
import stats
import ui

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FIRST_YEAR = 2000


# One day, 6 columns wide. Today has brackets around the number, so it can be found
# even without color. Without color, a * after the number means a workout was logged.
# Used by: calendar_lines.
def day_cell(day, done, today, shown):
    if not shown:
        return " " * 6
    text = f" {day.day:>2} "
    if day == today:
        text = f"[{day.day:>2}]"
    if not ui.USE_COLOR:
        if len(done) > 0:
            text = text + "*"
        return ui.pad(" " + text, 6)
    if day > today:
        return " " + ui.paint(text, ui.DIM) + " "
    if len(done) > 0:
        # A second activity that day shows as a small dot in its color.
        more = " "
        if len(done) > 1:
            more = ui.paint("•", ui.activity_rgb(done[1]), True)
        return " " + ui.paint(text, (20, 20, 24), True, ui.activity_rgb(done[0])) + more
    if day == today:
        return " " + ui.paint(text, ui.ORANGE, True) + " "
    return " " + ui.paint(text, ui.MUTED) + " "


# reveal = how many days are drawn so far (for the animation); 31 shows them all.
# Used by: show_month.
def calendar_lines(state, year, month, reveal, note):
    logs = state["logs"]
    today = datetime.date.today()
    by_date = stats.activities_by_date(logs)
    month_logs = stats.logs_in_month(logs, year, month)
    first = datetime.date(year, month, 1)

    grid = [""]
    names = ""
    for name in DAY_NAMES:
        names = names + f"  {name} "
    grid.append(ui.paint(names.rstrip(), ui.MUTED))
    for week in stats.month_weeks(year, month):
        row = ""
        for day in week:
            if day is None:
                row = row + " " * 6
            else:
                done = []
                if day.isoformat() in by_date:
                    done = by_date[day.isoformat()]
                row = row + day_cell(day, done, today, day.day <= reveal)
        grid.append(row.rstrip())
        grid.append("")  # a blank row between weeks keeps the days apart

    days_trained = []
    for log in month_logs:
        if log["date"] not in days_trained:
            days_trained.append(log["date"])
    totals = [home.number("workouts", str(len(month_logs))),
              home.number("days", str(len(days_trained))),
              home.number("min", f"{stats.total_of(month_logs, 'duration'):,}"),
              home.number("kcal", f"{stats.total_of(month_logs, 'calories'):,}")]
    grid.append("   ".join(totals))
    legend = ""
    for activity in ui.ACTIVITY_COLORS:
        legend = legend + ui.paint("■ ", ui.activity_rgb(activity)) + ui.paint(activity, ui.MUTED) + "  "
    grid.append(legend + ui.paint("[ ] today", ui.MUTED))

    lines = ["", ui.gradient("STREAKR", ui.ORANGE, ui.PINK) + ui.paint("  ›  ", ui.DIM)
             + ui.paint("Calendar", None, True), ""]
    lines = lines + ui.card(first.strftime("%B %Y"), grid, ui.BLUE)
    lines.append("")
    lines.append(ui.paint("p", ui.ORANGE, True) + " previous   " + ui.paint("n", ui.ORANGE, True)
                 + " next   " + ui.paint("1-31", ui.ORANGE, True) + " open a day   "
                 + ui.paint("b", ui.ORANGE, True) + " back")
    if note != "":
        lines.append(ui.paint(ui.mascot("shocked") + "  " + note, ui.RED))
    lines.append("")
    return lines


# Draw the month. When it changed, the days appear one by one (about a third of a second).
# Used by: menu_calendar.
def show_month(state, year, month, animate, note):
    if not ui.USE_COLOR:
        for line in calendar_lines(state, year, month, 31, note):
            print("  " + line)
        return
    if animate:
        ui.hide_cursor()
        for shown in range(0, 31, 3):
            ui.draw(calendar_lines(state, year, month, shown, note))
            time.sleep(0.025)
        ui.show_cursor()
    else:
        ui.clear()
    ui.draw(calendar_lines(state, year, month, 31, note))


# Everything logged on one day, with the choice to log another workout there.
# Used by: menu_calendar.
def show_day(state, day):
    ui.header("Calendar", menus.nice_date(day.isoformat()))
    found = stats.search_logs(state["logs"], "date", day.isoformat())
    if len(found) == 0:
        ui.say("sleepy", "Rest day. Nothing logged.")
    else:
        menus.print_logs(found)
        print()
        print("  " + home.number("total", f"{stats.total_of(found, 'duration')} min")
              + "   " + home.number("kcal", str(stats.total_of(found, 'calories'))))
    print()
    print(ui.option("L", "Log a workout on this day"))
    print("  " + ui.paint("Enter = back to the calendar", ui.MUTED))
    choice = input("  " + ui.paint(ui.PROMPT, ui.ORANGE, True)).strip().lower()
    if choice == "l":
        menus.menu_log(state, None, day.isoformat())
        ui.pause()


# Used by: main.main.
def menu_calendar(state):
    today = datetime.date.today()
    year = today.year
    month = today.month
    animate = True
    note = ""
    while True:
        show_month(state, year, month, animate, note)
        animate = False
        note = ""
        choice = input("  " + ui.paint(ui.PROMPT, ui.ORANGE, True)).strip().lower()
        if choice == "" or choice == "b" or choice == "0":
            return
        if choice == "n" or choice == "p":
            step = 1
            if choice == "p":
                step = -1
            new_year, new_month = stats.add_months(year, month, step)
            if (new_year, new_month) > (today.year, today.month):
                note = "That month has not happened yet."
            elif new_year < FIRST_YEAR:
                note = f"The calendar starts in {FIRST_YEAR}."
            else:
                year = new_year
                month = new_month
                animate = True
        elif choice.isdigit():
            number = int(choice)
            days_in_month = stats.days_in_month(year, month)
            if number < 1 or number > days_in_month:
                note = f"Pick a day from 1 to {days_in_month}."
            elif datetime.date(year, month, number) > today:
                note = "That day has not happened yet."
            else:
                show_day(state, datetime.date(year, month, number))
                animate = True
        else:
            note = "Type p, n, a day number, or b."
