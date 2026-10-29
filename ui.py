# Everything about how the terminal looks: colors, cards, the big pixel font and the
# short animations. All of it is plain print() with ANSI escape codes.
# Used by: calendar_view.py, home.py, inputs.py, login.py, main.py, menus.py, onboarding.py,
#          plans.py, server.py
import datetime
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


# Halloween week (24 October to 1 November) the app dresses up: pumpkin and witch-purple
# colors, bats and ghosts. STREAKR_THEME=halloween or =normal turns it on or off any day.
# Used by: this file, when it is imported.
def halloween_on():
    choice = os.environ.get("STREAKR_THEME", "")
    if choice == "halloween":
        return True
    if choice == "normal":
        return False
    today = datetime.date.today()
    return (today.month == 10 and today.day >= 24) or (today.month == 11 and today.day == 1)


# Only on a color terminal: plain output (files, tests) always looks the same.
HALLOWEEN = USE_COLOR and halloween_on()
if HALLOWEEN:
    ORANGE = (255, 117, 24)    # pumpkin
    PINK = (168, 85, 247)      # witch purple
    GREEN = (132, 225, 60)     # slime
    YELLOW = (255, 200, 40)    # candle

NAMED = {"red": RED, "green": GREEN, "yellow": YELLOW, "blue": BLUE, "magenta": PURPLE,
         "cyan": TEAL, "orange": ORANGE, "pink": PINK, "muted": MUTED, "dim": DIM, "rest": REST}

ACTIVITY_COLORS = {"Gym": "blue", "Yoga": "magenta", "Pilates": "cyan", "Cardio": "yellow"}

MASCOTS = {
    "happy": "(•̀ᴗ•́)و",
    "strong": "ᕦ(ò_óˇ)ᕤ",
    "sleepy": "(￣o￣) zzZ",
    "shocked": "(°ロ°) !",
}
if HALLOWEEN:
    MASCOTS = {
        "happy": "(•̀ᴗ•́)و ᗣ",
        "strong": "ᕦ(ò_óˇ)ᕤ ᗣ",
        "sleepy": "(￣o￣) zzZ ^v^",
        "shocked": "(°ロ°) ! ᗣ",
    }

PROMPT = "› "


# ---------- colors ----------

# The nearest color in the 256-color table (a 6 x 6 x 6 cube starting at 16).
# Used by: color_code.
def to_256(rgb):
    r = round(rgb[0] / 255 * 5)
    g = round(rgb[1] / 255 * 5)
    b = round(rgb[2] / 255 * 5)
    return 16 + 36 * r + 6 * g + b


# Used by: paint.
def color_code(rgb, layer):
    # layer 38 = text color, 48 = background color
    if TRUECOLOR:
        return f"\033[{layer};2;{rgb[0]};{rgb[1]};{rgb[2]}m"
    return f"\033[{layer};5;{to_256(rgb)}m"


# Used by: 46 places in calendar_view, home, inputs, login, main, menus, onboarding, plans, ui.
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


# Used by: activity_rgb.
def activity_color(activity):
    if activity in ACTIVITY_COLORS:
        return ACTIVITY_COLORS[activity]
    return "cyan"


# Used by: 13 places in calendar_view, home, menus, plans.
def activity_rgb(activity):
    return NAMED[activity_color(activity)]


# A color part of the way from a to b (t = 0 is a, t = 1 is b).
# Used by: gradient, progress, big_number, logo_lines.
def mix(a, b, t):
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t),
            round(a[2] + (b[2] - a[2]) * t))


# Used by: calendar_view.calendar_lines, home.screen_lines, header, bats.
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
# Used by: pad, side_by_side, confetti, bats.
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


# Used by: calendar_view.day_cell, home.screen_lines, menus.print_logs, menus.pick_exercises,
# side_by_side.
def pad(text, width):
    return text + " " * (width - display_width(text))


# Usable width: the terminal's width, but never wider than 80 so lines stay readable.
# Used by: home.screen_lines, menus.pick_exercises, display_width, pad, confetti.
def width():
    return min(shutil.get_terminal_size((80, 24)).columns, 80)


# A card: a colored bar down the left and a title. No right border, so characters that
# some fonts draw wider (like the mascot) can never knock it out of line.
# Used by: 8 places in calendar_view, home, menus, plans.
def card(title, lines, rgb=DIM):
    bar = paint("▍", rgb, True)
    out = [bar + " " + paint(title.upper(), rgb, True)]
    for line in lines:
        out.append(bar + " " + line)
    return out


# Used by: home.screen_lines, spooky_logo.
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
# Used by: option.
def pill(text):
    if not USE_COLOR:
        return text
    return paint(f" {text} ", (28, 18, 10), True, ORANGE)


# Used by: calendar_view.show_day, home.screen_lines, inputs.print_options, login.run_login,
# menus.pick_exercises, plans.print_plans.
def option(number, text):
    if not USE_COLOR:
        return f"  {number}. {text}"
    # Numbers are right-aligned to 2 places, so 1 and 10 make buttons of the same width.
    return "  " + pill(f"{number:>2}") + " " + text


# Used by: menus.menu_history, onboarding.run_onboarding.
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
# Used by: menus.menu_history.
def plural(count, word):
    if count == 1:
        return f"{count} {word}"
    return f"{count} {word}s"


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
# Used by: big_number, logo_lines, splash.
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
# Used by: home.streak_card.
def big_number(number):
    rows = big(str(number), "██")
    out = []
    for i in range(5):
        out.append(paint(rows[i], mix(PINK, ORANGE, i / 4), True))
    return out


# Used by: login.run_login, splash, spooky_logo.
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

# Used by: calendar_view.show_month, home.show, login.run_login, header, splash.
def clear():
    if USE_COLOR:
        print("\033[H\033[2J", end="")


# Redraw the whole screen in place (for animation frames): no flicker, no scrolling.
# Used by: calendar_view.show_month, home.show, splash, bats.
def draw(lines):
    text = "\033[H"
    for line in lines:
        text = text + "  " + line + "\033[K\n"
    sys.stdout.write(text + "\033[J")
    sys.stdout.flush()


# The app gets its own screen, like vim or htop, and the terminal comes back
# exactly as it was afterwards.
# Used by: main.run.
def enter_app_screen():
    if USE_COLOR:
        sys.stdout.write("\033[?1049h\033[H\033[2J")
        sys.stdout.flush()


# Used by: main.run.
def leave_app_screen():
    if USE_COLOR:
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()


# Used by: calendar_view.show_month, home.show, confetti, splash.
def hide_cursor():
    if USE_COLOR:
        sys.stdout.write("\033[?25l")


# Used by: calendar_view.show_month, home.show, confetti, splash.
def show_cursor():
    if USE_COLOR:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


# The top of every screen: small logo and where you are, e.g. STREAKR › Log workout.
# Used by: calendar_view.show_day, login.log_in, login.create_account,
# onboarding.run_onboarding, plans.start_plan, title.
def header(*where):
    clear()
    path = ""
    for part in where:
        path = path + paint("  ›  ", DIM) + paint(part, None, True)
    print()
    print("  " + gradient("STREAKR", ORANGE, PINK) + path)
    print()


# Used by: menus.menu_log, menus.menu_history, menus.menu_manage, menus.menu_profile,
# plans.menu_plans, card.
def title(text):
    header(text)


# ---------- messages ----------

# Used by: 10 places in calendar_view, home, server, ui.
def mascot(mood):
    return MASCOTS[mood]


# Used by: calendar_view.show_day, login.run_login, menus.menu_history,
# onboarding.run_onboarding, plans.menu_plans.
def say(mood, message, rgb=ORANGE):
    print("  " + paint(mascot(mood), rgb, True) + "  " + message)


# Used by: 15 places in inputs, login, main, menus, plans.
def error(message):
    line = "  " + paint(mascot("shocked") + "  " + message, RED)
    print(line)
    shake(line)


# Wiggle the line just printed left and right (0.2 s), like a "no" head shake.
# Used by: error.
def shake(line):
    if not USE_COLOR:
        return
    for offset in [2, 0, 2, 0]:
        sys.stdout.write("\033[1A\r\033[K" + " " * offset + line + "\n")
        sys.stdout.flush()
        time.sleep(0.05)


# Used by: menus.rest_day_ok.
def warn(message):
    print("  " + paint("!  " + message, YELLOW))


# Used by: 10 places in login, main, menus, onboarding, plans, ui.
def success(message):
    print("  " + paint(mascot("happy") + "  " + message, GREEN))


# Used by: menus.menu_log.
def strong(message):
    print("  " + paint(mascot("strong") + "  " + message, ORANGE, True))


# Confetti in the activity colors for a moment (0.7 s), then the message.
# Used by: menus.menu_log.
def celebrate(message):
    if USE_COLOR:
        confetti(5)
    success(message)


# Used by: celebrate.
def confetti(rows):
    symbols = "✦✧•·*+"
    colors = [ORANGE, PINK, GREEN, BLUE, PURPLE, YELLOW, TEAL]
    if HALLOWEEN:
        symbols = ["ᗣ", "ᗣ", "^v^", "✦", "·", "*"]   # ghosts, bats and sparks
        colors = [ORANGE, PINK, GREEN, YELLOW]
    columns = width() - 6
    hide_cursor()
    sys.stdout.write("\n" * rows)
    for frame in range(15):
        sys.stdout.write(f"\033[{rows}A")
        for r in range(rows):
            line = ""
            c = 0
            while c < columns - 1:
                symbol = " "
                if random.random() < 0.07 * (1 - frame / 16):
                    symbol = random.choice(symbols)
                # A symbol can be wider than one column (like ^v^), so count its width.
                line = line + paint(symbol, random.choice(colors))
                c = c + display_width(symbol)
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
# Used by: main.main.
def splash():
    if not USE_COLOR:
        return
    hide_cursor()
    clear()
    full = len(big("STREAKR", "█")[0])
    top = ["", "", ""]
    if HALLOWEEN:
        top = ["", "", "", ""]  # the same place as the logo next to the pumpkin
    for shown in range(0, full + 3, 3):
        draw(top + logo_lines(shown))
        time.sleep(0.02)
    tagline = "track the work. keep the streak."
    if HALLOWEEN:
        tagline = "trick or treat. keep the streak."
    for i in range(0, len(tagline) + 1, 2):
        logo = logo_lines()
        if HALLOWEEN:
            logo = spooky_logo(YELLOW)
        draw(["", ""] + logo + ["", paint(tagline[:i], MUTED)])
        time.sleep(0.012)
    if HALLOWEEN:
        bats()
    time.sleep(0.3)
    show_cursor()


# ---------- Halloween pixel art ----------

# A jack-o'-lantern, 22 pixels wide and 18 tall. Each letter is one pixel:
# g = stem, o = pumpkin, d = darker rib, y = candle light inside, space = nothing.
PUMPKIN = [
    "          gg          ",
    "         gggg         ",
    "    ooooodggdooooo    ",
    "  oooooodoooodoooooo  ",
    " ooooooodoooodooooooo ",
    "oooooooodoooodoooooooo",
    "oyyyyyoodoooodooyyyyyo",
    "ooyyyyoodoooodooyyyyoo",
    "oooyyooodoooodoooyyooo",
    "ooooooooooyyoooooooooo",
    "oooooooooyyyyooooooooo",
    "oyooooooooooooooooooyo",
    "ooyyyyyyyyyyyyyyyyyyoo",
    "ooyyoyyyoyyyyoyyyoyyoo",
    "oooyyyyyyyyyyyyyyyyooo",
    " ooooyyyyyyyyyyyyoooo ",
    "  oooooooooooooooooo  ",
    "     oooooooooooo     ",
]


# Used by: spooky_logo.
def pumpkin_colors(glow):
    return {"g": (86, 170, 64), "o": ORANGE, "d": (196, 74, 8), "y": glow}


# Two pixels fit in one character: "▀" colors the top half with the text color and the
# bottom half with the background color. So 18 pixel rows become 9 lines of text.
# Used by: spooky_logo.
def pixel_art(rows, colors):
    lines = []
    for r in range(0, len(rows), 2):
        line = ""
        for c in range(len(rows[r])):
            top = colors.get(rows[r][c])
            bottom = None
            if r + 1 < len(rows) and c < len(rows[r + 1]):
                bottom = colors.get(rows[r + 1][c])
            if top is None and bottom is None:
                line = line + " "
            elif bottom is None:
                line = line + paint("▀", top)
            elif top is None:
                line = line + paint("▄", bottom)
            else:
                line = line + paint("▀", top, False, bottom)
        lines.append(line)
    return lines


# The logo with the pumpkin next to it. glow changes the candle color, so it flickers.
# The logo is 5 lines and the pumpkin 9, so 2 empty lines above the logo center it.
# Used by: splash, bats.
def spooky_logo(glow):
    return side_by_side(["", ""] + logo_lines(), pixel_art(PUMPKIN, pumpkin_colors(glow)), 5)


# The candle flickers while two bats flap across under the logo (about a second),
# then "Happy Halloween!" appears in pumpkin-to-purple.
# Used by: splash.
def bats():
    tagline = paint("trick or treat. keep the streak.", MUTED)
    end = display_width(spooky_logo(YELLOW)[0])
    glows = [(255, 214, 90), (255, 170, 40), (255, 236, 150), (255, 190, 60)]
    frame = 0
    for x in range(0, end - 6, 2):
        wing = "/(ºvº)\\"          # wings down
        if frame % 2 == 0:
            wing = "\\(ºvº)/"      # wings up
        sky = [" " * x + paint(wing, PINK, True),
               " " * max(end - x - 7, 0) + paint(wing, ORANGE, True)]
        draw(["", ""] + spooky_logo(glows[frame % len(glows)]) + ["", tagline, ""] + sky)
        frame = frame + 1
        time.sleep(0.025)
    draw(["", ""] + spooky_logo(glows[0]) + ["", tagline, "",
                                                 gradient("Happy Halloween!", ORANGE, PINK)])
    time.sleep(0.6)


# Used by: calendar_view.show_day, login.run_login, main.main.
def pause():
    input("\n  " + paint("Press Enter to go back", MUTED) + " ")
