import os
import sys
import time
import unicodedata

# Colors only when printing to a real terminal and the user did not set NO_COLOR.
USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ

COLORS = {"red": "31", "green": "32", "yellow": "33", "blue": "34",
          "magenta": "35", "cyan": "36", "bold": "1", "dim": "2"}

ACTIVITY_COLORS = {"Gym": "red", "Yoga": "magenta", "Pilates": "blue", "Cardio": "yellow"}

MASCOTS = {
    "happy": "(•̀ᴗ•́)و",
    "strong": "ᕦ(ò_óˇ)ᕤ",
    "sleepy": "(￣o￣) zzZ",
    "shocked": "(°ロ°) !",
}


def color(text, c):
    if not USE_COLOR:
        return text
    return "\033[" + COLORS[c] + "m" + text + "\033[0m"


def activity_color(activity):
    if activity in ACTIVITY_COLORS:
        return ACTIVITY_COLORS[activity]
    return "cyan"


# How many columns text takes on screen: color codes take 0, wide characters
# (like ロ) take 2, and accent marks that sit on the letter before take 0.
def display_width(text):
    width = 0
    in_code = False
    for ch in text:
        if ch == "\033":
            in_code = True
        elif in_code:
            if ch == "m":
                in_code = False
        elif unicodedata.combining(ch):
            continue
        elif unicodedata.east_asian_width(ch) == "W" or unicodedata.east_asian_width(ch) == "F":
            width = width + 2
        else:
            width = width + 1
    return width


def pad(text, width):
    return text + " " * (width - display_width(text))


def box(title, lines):
    inner = display_width(title) + 2
    for line in lines:
        if display_width(line) > inner:
            inner = display_width(line)
    top = "╭─ " + color(title, "bold") + " " + "─" * (inner - display_width(title) - 1) + "╮"
    result = [top]
    for line in lines:
        result.append("│ " + pad(line, inner) + " │")
    result.append("╰" + "─" * (inner + 2) + "╯")
    return "\n".join(result)


def mascot(mood):
    return MASCOTS[mood]


def progress(current, total):
    width = 10
    filled = current * width // total
    if filled > width:
        filled = width
    return color("█" * filled, "green") + color("░" * (width - filled), "dim")


def clear():
    if USE_COLOR:
        print("\033[2J\033[H", end="")


def title(text):
    print()
    print(color("▌ " + text, "cyan"))


def error(message):
    print("  " + color(mascot("shocked") + " " + message, "red"))


def warn(message):
    print("  " + color("! " + message, "yellow"))


def success(message):
    print("  " + color(mascot("happy") + " " + message, "green"))


def strong(message):
    print("  " + color(mascot("strong") + " " + message, "magenta"))


# A short jump animation (0.6 s) before the success message. Skipped without a terminal.
def celebrate(message):
    if USE_COLOR:
        frames = ["  (•̀ᴗ•́)  ", "  \\(•̀ᴗ•́)/", "  (•̀ᴗ•́)و "]
        for i in range(4):
            print("\r" + color(frames[i % 3], "green"), end="", flush=True)
            time.sleep(0.15)
        print("\r", end="")
    success(message)


def pause():
    input(color("\n  Press Enter to go back to the menu...", "dim"))
