# Asks the user for text, numbers, dates and choices, again and again until valid.
# Uses: ui.py
# Used by: login.py, menus.py, onboarding.py, plans.py, seed.py
import datetime

import ui


# Line prompts up with the rest of the screen (2 spaces in from the left).
# Used by: ask_text, ask_int, ask_date, ask_yes_no, menus.pick_exercises, plans.start_plan.
def indent(prompt):
    if prompt.startswith(" "):
        return prompt
    return "  " + prompt


# allow_back=True lets the user type b to go back; the function then returns None.
# Used by: ask_text, ask_int, ask_multi.
def wants_back(text, allow_back):
    return allow_back and text.lower() == "b"


# Ask until the user types something non-empty and printable. None means back.
# Used by: 8 places in login, menus, onboarding, plans.
def ask_text(prompt, allow_back=False):
    while True:
        text = input(indent(prompt)).strip()
        if wants_back(text, allow_back):
            return None
        if text == "":
            ui.error("Please type at least one character.")
        elif not text.isprintable():
            ui.error("Please use only normal letters, numbers and symbols.")
        else:
            return text


# default: the value returned when the user just presses Enter.
# Used by: 10 places in inputs, menus, onboarding, plans.
def ask_int(prompt, lo, hi, allow_back=False, default=None):
    while True:
        text = input(indent(prompt)).strip()
        if wants_back(text, allow_back):
            return None
        if text == "" and default is not None:
            return default
        try:
            number = int(text)
        except ValueError:
            ui.error("Please enter a whole number.")
            continue
        if number < lo or number > hi:
            ui.error(f"Please enter a number from {lo} to {hi}.")
            continue
        return number


# Ask for a YYYY-MM-DD date that is real and not in the future. Enter = today.
# Used by: menus.menu_log, menus.menu_manage, menus.edit_log.
def ask_date(prompt):
    while True:
        text = input(indent(prompt)).strip()
        if text == "":
            return datetime.date.today().isoformat()
        try:
            day = datetime.datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            ui.error("Please use the format YYYY-MM-DD, e.g. 2026-10-28.")
            continue
        if day > datetime.date.today():
            ui.error("The date cannot be in the future.")
            continue
        return day.isoformat()


# Print a numbered list, starting at 1.
# Used by: ask_choice, ask_multi.
def print_options(options):
    for i in range(len(options)):
        print(ui.option(i + 1, options[i]))


# The orange arrow shown before the user types.
# Used by: ask_choice, ask_multi.
def prompt_mark():
    return "  " + ui.paint(ui.PROMPT, ui.ORANGE, True)


# Show numbered options and return the one picked (the text, not the number).
# Used by: 10 places in menus, onboarding, plans.
def ask_choice(prompt, options, allow_back=False):
    print()
    print("  " + ui.paint(prompt, None, True))
    print_options(options)
    number = ask_int(prompt_mark(), 1, len(options), allow_back)
    if number is None:
        return None
    return options[number - 1]


# Like ask_choice, but several numbers separated by commas.
# Used by: menus.menu_profile, onboarding.step_activities.
def ask_multi(prompt, options, allow_back=False):
    print()
    print("  " + ui.paint(prompt, None, True))
    print_options(options)
    while True:
        text = input(prompt_mark() + "Numbers separated by commas (e.g. 1,3): ").strip()
        if wants_back(text, allow_back):
            return None
        chosen = []
        ok = True
        for part in text.split(","):
            try:
                number = int(part.strip())
            except ValueError:
                ok = False
                break
            if number < 1 or number > len(options):
                ok = False
                break
            if options[number - 1] not in chosen:
                chosen.append(options[number - 1])
        if ok:
            return chosen
        ui.error(f"Please enter numbers from 1 to {len(options)}, separated by commas.")


# Ask until the answer is y/yes or n/no. Returns True or False.
# Used by: menus.rest_day_ok, menus.confirm_delete_log, plans.confirm_delete_plan, seed.main.
def ask_yes_no(prompt):
    while True:
        text = input(indent(prompt) + " (y/n): ").strip().lower()
        if text == "y" or text == "yes":
            return True
        if text == "n" or text == "no":
            return False
        ui.error("Please answer y or n.")
