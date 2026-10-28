import datetime

import ui


# allow_back=True lets the user type b to go back; the function then returns None.
def wants_back(text, allow_back):
    return allow_back and text.lower() == "b"


def ask_text(prompt, allow_back=False):
    while True:
        text = input(prompt).strip()
        if wants_back(text, allow_back):
            return None
        if text == "":
            ui.error("Please type at least one character.")
        elif not text.isprintable():
            ui.error("Please use only normal letters, numbers and symbols.")
        else:
            return text


# default: the value returned when the user just presses Enter.
def ask_int(prompt, lo, hi, allow_back=False, default=None):
    while True:
        text = input(prompt).strip()
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


def ask_date(prompt):
    while True:
        text = input(prompt).strip()
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


def print_options(options):
    for i in range(len(options)):
        print(f"  {i + 1}. {options[i]}")


def ask_choice(prompt, options, allow_back=False):
    print(prompt)
    print_options(options)
    number = ask_int("> ", 1, len(options), allow_back)
    if number is None:
        return None
    return options[number - 1]


def ask_multi(prompt, options, allow_back=False):
    print(prompt)
    print_options(options)
    while True:
        text = input("Numbers separated by commas (e.g. 1,3): ").strip()
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


def ask_yes_no(prompt):
    while True:
        text = input(prompt + " (y/n): ").strip().lower()
        if text == "y" or text == "yes":
            return True
        if text == "n" or text == "no":
            return False
        ui.error("Please answer y or n.")
