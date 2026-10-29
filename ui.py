# Everything about how the terminal looks: colors, cards, the big pixel font and the
# short animations. All of it is plain print() with ANSI escape codes.
import os
import random
import shutil
import sys
import time
import unicodedata

# Colors and animation only on a real terminal, and never when the user set NO_COLOR.
USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ
# Terminals that support 24-bit color say so in COLORTERM. Others get the nearest of 256 colors.
TRUECOLOR = os.environ.get("COLORTERM", "") in ("truecolor", "24bit")

# Colors as (red, green, blue). Normal text has no color at all, so it stays readable
# on both dark and light terminal backgrounds.
ORANGE = (255, 138, 61)
PINK = (255, 84, 112)
MUTED = (140, 140, 152)
DIM = (96, 96, 108)
REST = (70, 70, 80)
GREEN = (46, 196, 140)
RED = (240, 82, 82)
YELLOW = (240, 180, 20)
BLUE = (96, 128, 255)
PURPLE = (160, 112, 255)
TEAL = (32, 190, 150)

NAMED = {"red": RED, "green": GREEN, "yellow": YELLOW, "blue": BLUE, "magenta": PURPLE,
         "cyan": TEAL, "orange": ORANGE, "pink": PINK, "muted": MUTED, "dim": DIM, "rest": REST}

ACTIVITY_COLORS = {"Gym": "blue", "Yoga": "magenta", "Pilates": "cyan", "Cardio": "yellow"}

MASCOTS = {
    "happy": "(•̀ᴗ•́)و",
    "strong": "ᕦ(ò_óˇ)ᕤ",
    "sleepy": "(￣o￣) zzZ",
    "shocked": "(°ロ°) !",
}

PROMPT = "› "


# ---------- colors ----------

# The nearest color in the 256-color table (a 6 x 6 x 6 cube starting at 16).
def to_256(rgb):
    r = round(rgb[0] / 255 * 5)
    g = round(rgb[1] / 255 * 5)
    b = round(rgb[2] / 255 * 5)
    return 16 + 36 * r + 6 * g + b


def color_code(rgb, layer):
    # layer 38 = text color, 48 = background color
    if TRUECOLOR:
        return f"\033[{layer};2;{rgb[0]};{rgb[1]};{rgb[2]}m"
    return f"\033[{layer};5;{to_256(rgb)}m"


def paint(text, rgb=None, bold=False, background=None):
    if not USE_COLOR:
        return text
    start = ""
    if bold:
        start = start + "\033[1m"
    if rgb is not None:
        start = start + color_code(rgb, 38)
    if background is not None:
        start = start + color_code(background, 48)
    return start + text + "\033[0m"


def color(text, c):
    if c == "bold":
        return paint(text, None, True)
    return paint(text, NAMED[c])


def activity_color(activity):
    if activity in ACTIVITY_COLORS:
        return ACTIVITY_COLORS[activity]
    return "cyan"


def activity_rgb(activity):
    return NAMED[activity_color(activity)]


# A color part of the way from a to b (t = 0 is a, t = 1 is b).
def mix(a, b, t):
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t),
            round(a[2] + (b[2] - a[2]) * t))


def gradient(text, a, b, bold=True):
    if not USE_COLOR:
        return text
    out = ""
    last = max(len(text) - 1, 1)
    for i in range(len(text)):
        if text[i] == " ":
            out = out + " "
        else:
            out = out + paint(text[i], mix(a, b, i / last), bold)
    return out


# ---------- measuring and laying out ----------

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


# Usable width: the terminal's width, but never wider than 80 so lines stay readable.
def width():
    return min(shutil.get_terminal_size((80, 24)).columns, 80)


# A card: a colored bar down the left and a title. No right border, so characters that
# some fonts draw wider (like the mascot) can never knock it out of line.
def card(title, lines, rgb=DIM):
    bar = paint("▍", rgb, True)
    out = [bar + " " + paint(title.upper(), rgb, True)]
    for line in lines:
        out.append(bar + " " + line)
    return out


def side_by_side(left, right, gap):
    left_width = 0
    for line in left:
        if display_width(line) > left_width:
            left_width = display_width(line)
    out = []
    for i in range(max(len(left), len(right))):
        a = ""
        b = ""
        if i < len(left):
            a = left[i]
        if i < len(right):
            b = right[i]
        out.append(pad(a, left_width) + " " * gap + b)
    return out


# A small number button like [ 1 ] in front of a menu choice.
def pill(text):
    if not USE_COLOR:
        return text
    return paint(f" {text} ", (28, 18, 10), True, ORANGE)


def option(number, text):
    if not USE_COLOR:
        return f"  {number}. {text}"
    # Numbers are right-aligned to 2 places, so 1 and 10 make buttons of the same width.
    return "  " + pill(f"{number:>2}") + " " + text


def progress(current, total, size=10):
    filled = current * size // total
    if filled > size:
        filled = size
    if not USE_COLOR:
        return "█" * filled + "░" * (size - filled)
    bar = ""
    for i in range(filled):
        bar = bar + paint("█", mix(PINK, ORANGE, i / max(size - 1, 1)))
    return bar + paint("░" * (size - filled), DIM)


# "1 day", "2 days": the word changes when there is more than one.
def plural(count, word):
    if count == 1:
        return f"{count} {word}"
    return f"{count} {word}s"


def rule():
    return paint("─" * (width() - 4), DIM)


# ---------- the big pixel font (5 rows tall) ----------

FONT = {
    "0": ["###", "# #", "# #", "# #", "###"], "1": [" # ", "## ", " # ", " # ", "###"],
    "2": ["###", "  #", "###", "#  ", "###"], "3": ["###", "  #", "###", "  #", "###"],
    "4": ["# #", "# #", "###", "  #", "  #"], "5": ["###", "#  ", "###", "  #", "###"],
    "6": ["###", "#  ", "###", "# #", "###"], "7": ["###", "  #", "  #", "  #", "  #"],
    "8": ["###", "# #", "###", "# #", "###"], "9": ["###", "# #", "###", "  #", "###"],
    "S": ["###", "#  ", "###", "  #", "###"], "T": ["###", " # ", " # ", " # ", " # "],
    "R": ["## ", "# #", "## ", "# #", "# #"], "E": ["###", "#  ", "## ", "#  ", "###"],
    "A": [" # ", "# #", "###", "# #", "# #"], "K": ["# #", "# #", "## ", "# #", "# #"],
}


# Text drawn with blocks: each "#" in FONT becomes `pixel`. Returns 5 lines.
def big(text, pixel):
    rows = []
    for r in range(5):
        row = ""
        for ch in text:
            for p in FONT[ch][r]:
                if p == "#":
                    row = row + pixel
                else:
                    row = row + " " * len(pixel)
            row = row + " "
        rows.append(row.rstrip())
    return rows


# A big number, colored top to bottom from pink to orange.
def big_number(number):
    rows = big(str(number), "██")
    out = []
    for i in range(5):
        out.append(paint(rows[i], mix(PINK, ORANGE, i / 4), True))
    return out


def logo_lines(shown_columns=999):
    rows = big("STREAKR", "█")
    full = len(rows[0])
    out = []
    for row in rows:
        line = ""
        for i in range(min(len(row), shown_columns)):
            if row[i] == " ":
                line = line + " "
            else:
                line = line + paint(row[i], mix(ORANGE, PINK, i / full), True)
        out.append(line)
    return out


# ---------- the screen ----------

def clear():
    if USE_COLOR:
        print("\033[H\033[2J", end="")


# Redraw the whole screen in place (for animation frames): no flicker, no scrolling.
def draw(lines):
    text = "\033[H"
    for line in lines:
        text = text + "  " + line + "\033[K\n"
    sys.stdout.write(text + "\033[J")
    sys.stdout.flush()


# The app gets its own screen, like vim or htop, and the terminal comes back
# exactly as it was afterwards.
def enter_app_screen():
    if USE_COLOR:
        sys.stdout.write("\033[?1049h\033[H\033[2J")
        sys.stdout.flush()


def leave_app_screen():
    if USE_COLOR:
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()


def hide_cursor():
    if USE_COLOR:
        sys.stdout.write("\033[?25l")


def show_cursor():
    if USE_COLOR:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


# The top of every screen: small logo and where you are, e.g. STREAKR › Log workout.
def header(*where):
    clear()
    path = ""
    for part in where:
        path = path + paint("  ›  ", DIM) + paint(part, None, True)
    print()
    print("  " + gradient("STREAKR", ORANGE, PINK) + path)
    print()


def title(text):
    header(text)


# ---------- messages ----------

def mascot(mood):
    return MASCOTS[mood]


def say(mood, message, rgb=ORANGE):
    print("  " + paint(mascot(mood), rgb, True) + "  " + message)


def error(message):
    line = "  " + paint(mascot("shocked") + "  " + message, RED)
    print(line)
    shake(line)


# Wiggle the line just printed left and right (0.2 s), like a "no" head shake.
def shake(line):
    if not USE_COLOR:
        return
    for offset in [2, 0, 2, 0]:
        sys.stdout.write("\033[1A\r\033[K" + " " * offset + line + "\n")
        sys.stdout.flush()
        time.sleep(0.05)


def warn(message):
    print("  " + paint("!  " + message, YELLOW))


def success(message):
    print("  " + paint(mascot("happy") + "  " + message, GREEN))


def strong(message):
    print("  " + paint(mascot("strong") + "  " + message, ORANGE, True))


# Confetti in the activity colors for a moment (0.7 s), then the message.
def celebrate(message):
    if USE_COLOR:
        confetti(5)
    success(message)


def confetti(rows):
    symbols = "✦✧•·*+"
    colors = [ORANGE, PINK, GREEN, BLUE, PURPLE, YELLOW, TEAL]
    columns = width() - 6
    hide_cursor()
    sys.stdout.write("\n" * rows)
    for frame in range(15):
        sys.stdout.write(f"\033[{rows}A")
        for r in range(rows):
            line = ""
            for c in range(columns):
                if random.random() < 0.07 * (1 - frame / 16):
                    line = line + paint(random.choice(symbols), random.choice(colors))
                else:
                    line = line + " "
            sys.stdout.write("\r\033[K  " + line + "\n")
        sys.stdout.flush()
        time.sleep(0.045)
    # Wipe the confetti rows and put the cursor back where they started.
    sys.stdout.write(f"\033[{rows}A")
    for r in range(rows):
        sys.stdout.write("\r\033[K\n")
    sys.stdout.write(f"\033[{rows}A")
    show_cursor()


# The logo wipes in from the left, then the tagline types itself (about 1 second).
def splash():
    if not USE_COLOR:
        return
    hide_cursor()
    clear()
    full = len(big("STREAKR", "█")[0])
    for shown in range(0, full + 3, 3):
        draw(["", "", ""] + logo_lines(shown))
        time.sleep(0.02)
    tagline = "track the work. keep the streak."
    for i in range(0, len(tagline) + 1, 2):
        draw(["", "", ""] + logo_lines() + ["", paint(tagline[:i], MUTED)])
        time.sleep(0.012)
    time.sleep(0.3)
    show_cursor()


def pause():
    input("\n  " + paint("Press Enter to go back", MUTED) + " ")
