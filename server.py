# Optional web view: python3 server.py, then open http://localhost:8042
# The HTML lives in this file as strings (only *.py files can be turned in).
# The data, rules and stats are the same modules the terminal app uses.
# Uses: accounts.py, db.py, fitness.py, home.py, rules.py, stats.py, ui.py
# Used by: nobody imports it; run it with python3 server.py
import datetime
import html
import http.cookies
import http.server
import os
import threading
import urllib.parse

import accounts
import db
import fitness
import home
import rules
import stats
import ui

# Settings come from environment variables so the same file runs locally and in Docker.
PORT = int(os.environ.get("PORT", "8042"))
# 127.0.0.1 = only this computer can connect. Docker sets HOST=0.0.0.0.
HOST = os.environ.get("HOST", "127.0.0.1")
# Host names the browser may use to reach us, separated by commas. Requests for any other
# host are refused (blocks DNS rebinding), and form posts must come from one of these.
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", f"localhost:{PORT},127.0.0.1:{PORT}").split(",")
MAX_BODY = 10000  # bytes; a log form is far smaller
THEMES = ["auto", "light", "dark", "halloween"]

# No page uses JavaScript, so the browser is told to run none at all: even if some text
# slipped past html.escape, it could not execute.
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; "
                               "form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
}

# Each activity's color, as a CSS variable defined in STYLE.
ACTIVITY_COLORS = {"Gym": "var(--gym)", "Yoga": "var(--yoga)",
                   "Pilates": "var(--pilates)", "Cardio": "var(--cardio)"}

DURATION_PICKS = ["15", "30", "45", "60", "90"]

# The server answers several requests at once. Checking "already logged?" and then saving
# must happen as one step, or two quick identical posts could both pass the check.
SAVE_LOCK = threading.Lock()

# Shape rule: panels 20px, tiles and badges 12px, inputs 10px, buttons and chips fully round.
DARK_COLORS = """
  --bg: #111113; --surface: #1a1a1d; --text: #ededef; --muted: #a1a1aa; --line: #2c2c31;
  --accent: #fb923c; --on-accent: #1c0d03; --rest: #26262b; --error: #ff8a80; --warn: #f5c451;
  color-scheme: dark;
"""

# Pumpkin orange, witch purple and slime green on a night-sky background.
HALLOWEEN_COLORS = """
  --bg: #0c0912; --surface: #17121f; --text: #f4eeff; --muted: #a99bbd; --line: #2e2440;
  --accent: #ff7518; --on-accent: #1a0b00; --rest: #241c33; --error: #ff7a7a; --warn: #ffc94d;
  --gym: #6f9bff; --yoga: #b57bff; --pilates: #84e04a; --cardio: #ffb02e;
  color-scheme: dark;
"""

# data-theme on <html> is "auto" (follow the system), "light", "dark" or "halloween".
STYLE = """
:root {
  --bg: #f3f3f0; --surface: #ffffff; --text: #18181b; --muted: #5f5f66; --line: #e2e2de;
  --accent: #c2410c; --on-accent: #ffffff; --rest: #e8e8e3; --error: #b42318; --warn: #8a5a00;
  --gym: #3b63e0; --yoga: #8b5cf6; --pilates: #0f9f86; --cardio: #d99a00;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) { :root[data-theme=auto] { """ + DARK_COLORS + """ } }
:root[data-theme=dark] { """ + DARK_COLORS + """ }
:root[data-theme=halloween] { """ + HALLOWEEN_COLORS + """ }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
       font: 16px/1.5 ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif; }
.wrap { max-width: 1080px; margin: 0 auto; padding: 0 16px 64px; }
a { color: inherit; }
h1, h2, h3 { margin: 0; letter-spacing: -0.02em; }
h1 { font-size: 30px; }
h2 { font-size: 17px; }
h3 { font-size: 18px; }
.muted { color: var(--muted); }
.small { font-size: 14px; }
.mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }

.top { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;
        gap: 10px 16px; min-height: 72px; padding: 12px 0; }
.top-right { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.inline-form { margin: 0; }
.link-btn { font: inherit; background: none; border: 0; padding: 0; color: var(--muted);
            cursor: pointer; }
.link-btn:hover { color: var(--text); }
.auth { max-width: 420px; margin: 40px auto 0; }
.auth h1 { margin-bottom: 6px; }
.auth form { margin-top: 22px; }
.auth input[type=text], .auth input[type=password] { max-width: none; }
.auth-other { margin-top: 18px; text-align: center; }
.auth-other a { color: var(--accent); font-weight: 650; }
.three { display: grid; gap: 16px; margin-bottom: 26px; }
.setup input[type=text] { max-width: 360px; }
.theme { display: flex; border: 1px solid var(--line); border-radius: 999px; padding: 3px;
         font-size: 13px; }
.theme a { padding: 4px 11px; border-radius: 999px; text-decoration: none; color: var(--muted); }
.theme a:hover { color: var(--text); }
:root[data-theme=auto] .t-auto, :root[data-theme=light] .t-light,
:root[data-theme=dark] .t-dark { background: var(--text); color: var(--bg); }
:root[data-theme=halloween] .t-halloween { background: var(--accent); color: var(--on-accent); }
.brand { font-weight: 800; font-size: 21px; letter-spacing: -0.03em; text-decoration: none; }
.btn { display: inline-block; background: var(--accent); color: var(--on-accent); border: 0;
       border-radius: 999px; padding: 11px 22px; font: inherit; font-weight: 650;
       text-decoration: none; cursor: pointer; white-space: nowrap; transition: transform 0.15s; }
.btn:hover { transform: translateY(-1px); }
.btn:active { transform: scale(0.98); }
.link { color: var(--muted); text-decoration: none; }
.link:hover { color: var(--text); }

.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 20px;
         padding: 24px; }
.panel-head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px;
              margin-bottom: 18px; flex-wrap: wrap; }
.notice { border-radius: 14px; padding: 14px 18px; margin-bottom: 20px; }
.ok { background: color-mix(in srgb, var(--pilates) 15%, transparent); }
.error { background: color-mix(in srgb, var(--error) 12%, transparent); color: var(--error); }
.warn { background: color-mix(in srgb, var(--cardio) 16%, transparent); color: var(--warn); }

/* Dashboard */
.hero { display: grid; gap: 16px; margin: 8px 0 16px; }
.hero > *, .lower > *, .log-layout > * { min-width: 0; }
.streak-card { display: flex; flex-direction: column; border-radius: 20px; padding: 28px;
               color: #fff; background: linear-gradient(140deg, #9a3412, #c2410c 70%); }
.streak-card .label { font-weight: 600; opacity: 0.85; }
.streak-row { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; }
.big { font-family: var(--mono); font-size: 120px; line-height: 0.95; font-weight: 700;
       letter-spacing: -0.06em; }
.big small { font-size: 22px; letter-spacing: 0; font-weight: 600; margin-left: 6px; }
.face { font-size: 30px; white-space: nowrap; padding-bottom: 12px; }
.mood { margin: 18px 0 22px; font-size: 17px; }
.streak-foot { margin-top: auto; }
.pips { display: flex; gap: 6px; margin-bottom: 8px; }
.pips span { flex: 0 0 34px; height: 8px; border-radius: 999px; background: rgb(255 255 255 / 0.28); }
.pips .on { background: #fff; }
.streak-card .goal { opacity: 0.9; font-size: 15px; }

.month-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
.day-name { font-size: 12px; color: var(--muted); text-align: center; }
.cell { aspect-ratio: 1; border-radius: 6px; background: var(--rest); }
.cell.future { background: transparent; border: 1px dashed var(--line); }
a.cell { display: block; transition: transform 0.15s; }
a.cell:hover { transform: scale(1.1); }
a.cell:focus-visible, a.bar:focus-visible, a.day-date:focus-visible {
  outline: 2px solid var(--accent); outline-offset: 2px; }
.hint { margin: 12px 0 0; font-size: 13px; color: var(--muted); }
.cell.today { outline: 2px solid var(--text); outline-offset: 2px; }
.legend { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 16px; font-size: 13px;
          color: var(--muted); }
.legend span::before { content: ""; display: inline-block; width: 10px; height: 10px;
                       border-radius: 3px; background: var(--c); margin-right: 6px; }

.tiles { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 16px; }
.tile { border-radius: 12px; padding: 18px 20px; border: 1px solid var(--line);
        background: color-mix(in srgb, var(--c) 12%, var(--surface)); }
.tile .num { font-family: var(--mono); font-size: 32px; font-weight: 700; letter-spacing: -0.03em;
             line-height: 1.2; }
.tile .sub { font-size: 13px; color: var(--muted); margin-top: 2px; }

.chart-panel { margin-bottom: 16px; }
.chart { display: grid; grid-template-columns: repeat(14, 1fr); gap: 8px; height: 170px;
         align-items: end; }
.bar { display: flex; flex-direction: column; justify-content: flex-end; height: 100%; gap: 2px;
       border-radius: 5px; }
a.bar:hover span { filter: brightness(1.12); }
.bar span { background: var(--c); border-radius: 5px; min-height: 4px; }
.bar .none { background: var(--rest); height: 4px; }
.chart-days { display: grid; grid-template-columns: repeat(14, 1fr); gap: 8px; margin-top: 8px;
              font-size: 12px; color: var(--muted); text-align: center; }
.chart-days .now { color: var(--text); font-weight: 700; }

.lower { display: grid; gap: 16px; align-items: start; }
.mix { display: flex; height: 14px; border-radius: 999px; overflow: hidden; gap: 3px; }
.mix span { background: var(--c); }
.mix-rows { margin: 18px 0 0; padding: 0; list-style: none; }
.mix-rows li { display: flex; justify-content: space-between; padding: 6px 0; }
.mix-rows li span::before { content: ""; display: inline-block; width: 10px; height: 10px;
                            border-radius: 3px; background: var(--c); margin-right: 10px; }
.top-move { margin: 18px 0 0; padding-top: 16px; border-top: 1px solid var(--line); }

.day { padding: 16px 0; border-top: 1px solid var(--line); }
.day:first-of-type { border-top: 0; padding-top: 0; }
.day-date { display: inline-block; font-weight: 650; margin-bottom: 10px; text-decoration: none; }
a.day-date:hover { color: var(--accent); }
.day-nav { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.tiles.day-tiles { grid-template-columns: repeat(3, 1fr); }
.day-more { margin: 14px 0 0; }
.rest-day { text-align: center; padding: 40px 24px; }
.rest-day .face { font-size: 34px; padding: 0; margin-bottom: 10px; }
.rest-day h2 { margin-bottom: 6px; }
.rest-day .btn { margin-top: 10px; }
.ex-group { border: 1px solid var(--line); border-radius: 12px; margin-bottom: 8px;
            background: var(--surface); }
.ex-group.usual { border-color: color-mix(in srgb, var(--c) 50%, var(--line));
                  background: color-mix(in srgb, var(--c) 6%, var(--surface)); }
.ex-group summary { display: flex; justify-content: space-between; align-items: center; gap: 12px;
                    padding: 12px 16px; cursor: pointer; font-weight: 650; list-style: none; }
.ex-group summary::-webkit-details-marker { display: none; }
.ex-group summary::after { content: "+"; color: var(--muted); font-size: 18px; line-height: 1; }
.ex-group[open] summary::after { content: "\\2212"; }
.ex-group summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px;
                                  border-radius: 12px; }
.ex-group .count { margin-left: auto; color: var(--muted); font-weight: 400; font-size: 14px; }
.ex-group .chips { padding: 0 16px 16px; }
.other { margin-top: 14px; }
.other label { display: block; margin-bottom: 6px; }
.other input { max-width: 420px; }
.entry { display: grid; grid-template-columns: 40px 1fr auto; gap: 14px; align-items: start;
         padding: 8px 0; }
.badge { width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center;
         font-weight: 800; background: color-mix(in srgb, var(--c) 22%, var(--surface));
         border: 1px solid color-mix(in srgb, var(--c) 45%, transparent); }
.entry-title { font-weight: 650; }
.pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.pills span { font-size: 13px; padding: 2px 10px; border-radius: 999px; background: var(--bg);
              border: 1px solid var(--line); }
.entry-meta { text-align: right; white-space: nowrap; }
.entry-meta strong { font-family: var(--mono); font-size: 22px; }

/* Log pages */
.form-head { margin: 8px 0 22px; }
.crumbs { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; font-size: 14px; }
.crumbs .here { color: var(--text); font-weight: 650; }
.act-grid { display: grid; gap: 16px; margin-bottom: 20px; }
.act-card { border-radius: 20px; padding: 22px; border: 1px solid var(--line);
            background: linear-gradient(160deg, color-mix(in srgb, var(--c) 16%, var(--surface)),
                                        var(--surface) 65%); }
.act-head { display: flex; gap: 14px; align-items: center; margin-bottom: 16px; }
.act-card .last { margin-top: 14px; font-size: 13px; color: var(--muted); }

fieldset { border: 0; padding: 0; margin: 0 0 26px; min-width: 0; }
legend, label.field { display: block; font-weight: 650; margin-bottom: 10px; padding: 0; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { position: relative; display: inline-flex; }
.chip input { position: absolute; inset: 0; opacity: 0; margin: 0; cursor: pointer; }
.chip span { padding: 9px 16px; border: 1px solid var(--line); border-radius: 999px;
             background: var(--surface); transition: background 0.15s, border-color 0.15s; }
.chip:hover span { border-color: var(--c, var(--accent)); }
.chip input:checked + span { background: color-mix(in srgb, var(--c, var(--accent)) 20%, var(--surface));
                             border-color: var(--c, var(--accent)); font-weight: 650; }
.chip input:checked + span::before { content: "\\2713  "; }
.chip input:focus-visible + span { outline: 2px solid var(--accent); outline-offset: 2px; }
input[type=date], input[type=number], input[type=text], input[type=password] {
  font: inherit; color: var(--text); background: var(--surface); width: 100%; max-width: 260px;
  border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; }
input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.help { color: var(--muted); font-size: 13px; margin-top: 6px; }
.inline { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.inline input { max-width: 140px; }
.confirm { display: flex; gap: 10px; align-items: center; font-weight: 650; }
.log-layout { display: grid; gap: 16px; align-items: start; }
.aside h3 { margin-bottom: 14px; }
.aside-block { padding: 14px 0; border-top: 1px solid var(--line); }
.aside-block:first-of-type { border-top: 0; padding-top: 0; }
.est { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 8px; }
.est div { border-radius: 12px; padding: 10px; text-align: center;
           background: color-mix(in srgb, var(--c) 12%, var(--surface)); }
.est strong { display: block; font-family: var(--mono); font-size: 20px; }

/* Calendar page */
.cal-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px;
            flex-wrap: wrap; margin: 8px 0 20px; }
.cal-nav { display: flex; gap: 8px; }
.cal-nav a, .cal-nav span { padding: 8px 14px; border: 1px solid var(--line); border-radius: 999px;
                            text-decoration: none; font-size: 14px; background: var(--surface); }
.cal-nav a:hover { border-color: var(--accent); }
.cal-nav span { color: var(--muted); opacity: 0.5; }
.cal { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; }
.cal .day-name { padding-bottom: 4px; }
.cal-day { display: flex; flex-direction: column; gap: 4px; min-height: 64px; padding: 7px;
           border-radius: 12px; border: 1px solid var(--line); background: var(--bg);
           text-decoration: none; min-width: 0; }
a.cal-day { transition: transform 0.15s, border-color 0.15s; }
a.cal-day:hover { transform: translateY(-2px); border-color: var(--accent); }
a.cal-day:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.cal-day.done { background: color-mix(in srgb, var(--c) 16%, var(--surface));
                border-color: color-mix(in srgb, var(--c) 45%, var(--line)); }
.cal-day.future { background: transparent; border-style: dashed; color: var(--muted); opacity: 0.6; }
.cal-day.today { outline: 2px solid var(--text); outline-offset: 1px; }
.cal-day .d { font-family: var(--mono); font-weight: 700; font-size: 14px; }
.cal-day .acts { display: flex; flex-wrap: wrap; gap: 3px; }
.cal-day .acts span { width: 8px; height: 8px; border-radius: 3px; background: var(--c); }
.cal-day .acts b { display: none; }
.cal-day .mins { margin-top: auto; font-size: 11px; color: var(--muted); font-family: var(--mono); }
.cal-day .unit { display: none; }
.cal-blank { min-height: 64px; }
.tiles.cal-tiles { margin-bottom: 16px; }

/* Halloween: a glowing night sky, a pumpkin-to-purple streak card and two bats.
   The bats are only decoration (pointer-events: none), so they never block a click. */
:root[data-theme=halloween] body {
  background: radial-gradient(900px 420px at 88% -8%, rgb(255 117 24 / 0.16), transparent 62%),
              radial-gradient(800px 480px at -5% 0%, rgb(168 85 247 / 0.18), transparent 58%),
              var(--bg) fixed; }
:root[data-theme=halloween] .brand::after { content: " 🎃"; }
:root[data-theme=halloween] .streak-card {
  background: linear-gradient(140deg, #3b0f6b, #7c2d12 58%, #ea580c);
  box-shadow: 0 20px 50px rgb(234 88 12 / 0.18); }
:root[data-theme=halloween] .panel, :root[data-theme=halloween] .tile {
  box-shadow: 0 0 0 1px rgb(168 85 247 / 0.06), 0 14px 40px rgb(0 0 0 / 0.35); }
:root[data-theme=halloween] .cell.today, :root[data-theme=halloween] .cal-day.today {
  outline-color: var(--accent); }
:root[data-theme=halloween] .btn { box-shadow: 0 6px 22px rgb(255 117 24 / 0.35); }
:root[data-theme=halloween] body::before, :root[data-theme=halloween] body::after {
  content: "🦇"; position: fixed; top: 90px; left: -60px; font-size: 26px;
  pointer-events: none; z-index: 5; opacity: 0.85; }
:root[data-theme=halloween] body::after { top: 210px; font-size: 18px; }

@media (min-width: 760px) {
  .wrap { padding: 0 32px 80px; }
  .hero { grid-template-columns: 1fr 1fr; }
  .tiles { grid-template-columns: repeat(4, 1fr); }
  .lower { grid-template-columns: 1fr 1.7fr; }
  .act-grid { grid-template-columns: 1fr 1fr; }
  .log-layout { grid-template-columns: 1.6fr 1fr; }
  .three { grid-template-columns: repeat(3, 1fr); max-width: 640px; }
  .big { font-size: 150px; }
  .cal { gap: 10px; }
  .cal-day, .cal-blank { min-height: 104px; padding: 10px; }
  .cal-day .acts { flex-direction: column; }
  .cal-day .acts span { width: auto; height: auto; background: none; font-size: 12px;
                        line-height: 1.3; padding-left: 7px; border-left: 3px solid var(--c);
                        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .cal-day .acts b { display: inline; font-weight: 600; }
  .cal-day .unit { display: inline; }
}
@media (prefers-reduced-motion: no-preference) {
  .rise { animation: rise 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
          animation-delay: calc(var(--i, 0) * 70ms); }
  :root[data-theme=halloween] body::before { animation: fly 14s linear infinite; }
  :root[data-theme=halloween] body::after { animation: fly 19s linear 4s infinite; }
  .cal-day { animation: pop 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
             animation-delay: calc(var(--n) * 12ms + 150ms); }
  .cell { animation: pop 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
          animation-delay: calc(var(--n) * 14ms + 200ms); }
  .bar { transform-origin: bottom; animation: grow 0.7s cubic-bezier(0.16, 1, 0.3, 1) both;
         animation-delay: calc(var(--n) * 30ms + 250ms); }
}
@keyframes rise { from { opacity: 0; transform: translateY(14px); } }
@keyframes pop { from { opacity: 0; transform: scale(0.6); } }
@keyframes grow { from { transform: scaleY(0); } }
@keyframes fly {
  0% { transform: translate(0, 0) rotate(-8deg); }
  25% { transform: translate(30vw, 40px) rotate(6deg); }
  50% { transform: translate(60vw, -10px) rotate(-6deg); }
  75% { transform: translate(90vw, 50px) rotate(8deg); }
  100% { transform: translate(120vw, 0) rotate(-8deg); } }
"""


# Used by: 19 places in server.
def esc(text):
    return html.escape(str(text))


# Used by: 8 places in server.
def color_of(activity):
    if activity in ACTIVITY_COLORS:
        return ACTIVITY_COLORS[activity]
    return "var(--muted)"


# Used by: entry_html, choose_html, log_form_html.
def badge(activity):
    return f"<div class='badge' style='--c:{color_of(activity)}'>{esc(activity[0])}</div>"


THEME_SWITCH = ("<nav class='theme' aria-label='Theme'>"
                "<a class='t-auto' href='/theme?set=auto'>Auto</a>"
                "<a class='t-light' href='/theme?set=light'>Light</a>"
                "<a class='t-dark' href='/theme?set=dark'>Dark</a>"
                "<a class='t-halloween' href='/theme?set=halloween'>🎃 Halloween</a></nav>")


# Pages are built with data-theme='auto'; Handler.send_html swaps in the visitor's choice.
# Used by: 7 places in server.
def page(title, right, body):
    return ("<!doctype html><html lang='en' data-theme='auto'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>{esc(title)}</title><style>{STYLE}</style></head><body><div class='wrap'>"
            f"<header class='top'><a class='brand' href='/'>Streakr</a>"
            f"<div class='top-right'>{THEME_SWITCH}{right}</div></header>"
            f"{body}</div></body></html>")


LOG_BUTTON = "<a class='btn' href='/log'>Log workout</a>"
# Log out is a form (POST), so another site cannot log you out with a simple link.
LOGOUT_FORM = ("<form class='inline-form' method='post' action='/logout'>"
               "<button class='link-btn'>Log out</button></form>")
ACCOUNT_LINKS = ("<a class='link' href='/calendar'>Calendar</a>"
                 "<a class='link' href='/setup'>Profile</a>" + LOGOUT_FORM)
BACK_LINK = "<a class='link' href='/'>Back to dashboard</a>"


# parse_qs gives a list for every key; this returns the first value or "".
# Used by: 8 places in server.
def first(form, key):
    if key in form:
        return form[key][0].strip()
    return ""


# Used by: save_from_form, profile_from_form, Handler.do_GET, Handler.do_POST.
def to_int(text, lo, hi):
    try:
        number = int(text)
    except ValueError:
        return None
    if number < lo or number > hi:
        return None
    return number


# Same checks as inputs.ask_date: real date, not in the future.
# Used by: save_from_form, Handler.do_GET.
def check_date(text):
    try:
        day = datetime.datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None
    if day > datetime.date.today():
        return None
    return day.isoformat()


# "Gym|Upper Body" -> ("Gym", "Upper Body"), or None if it is not in the library.
# Used by: save_from_form, Handler.do_GET, Handler.do_POST.
def split_choice(state, value):
    parts = value.split("|")
    if len(parts) != 2:
        return None
    activity = parts[0]
    focus = parts[1]
    if activity not in state["library"] or focus not in state["library"][activity]:
        return None
    if activity not in state["profile"]["activities"]:
        return None
    return activity, focus


# Used by: 7 places in server.
def nice_date(iso):
    day = datetime.datetime.strptime(iso, "%Y-%m-%d").date()
    return f"{day.strftime('%a')} {day.day} {day.strftime('%b')}"


# The most recent log that matches activity (and focus, unless focus is None).
# Used by: choose_html, aside_html.
def last_log(logs, activity, focus):
    latest = None
    for log in logs:
        if log["activity"] != activity:
            continue
        if focus is not None and log["focus"] != focus:
            continue
        if latest is None or log["date"] > latest["date"]:
            latest = log
    return latest


# Used by: tiles_html.
def this_week_logs(logs):
    today = datetime.date.today()
    monday = (today - datetime.timedelta(days=today.weekday())).isoformat()
    found = []
    for log in logs:
        if log["date"] >= monday:
            found.append(log)
    return found


# Used by: streak_html.
def mood_sentence(logs, mood):
    days_off = stats.days_since_last(logs)
    if mood == "sleepy":
        return f"No workout in {days_off} days. Time to move."
    if days_off == 0:
        return "Today is done. Rest well."
    if stats.current_streak(logs) > 0:
        return "Log today to keep the streak alive."
    return "Log a workout to start a streak."


# Used by: dashboard_html.
def streak_html(state):
    logs = state["logs"]
    goal = state["profile"]["weekly_goal"]
    done = stats.days_this_week(logs)
    mood = home.pick_mood(logs)
    streak = stats.current_streak(logs)
    unit = "days"
    if streak == 1:
        unit = "day"
    pips = ""
    for i in range(goal):
        if i < done:
            pips += "<span class='on'></span>"
        else:
            pips += "<span></span>"
    return ("<div class='streak-card rise'>"
            f"<div class='label'>Hi {esc(state['profile']['name'])}, your streak</div>"
            f"<div class='streak-row'><div class='big'>{streak}<small>{unit}</small></div>"
            f"<div class='face'>{esc(ui.mascot(mood))}</div></div>"
            f"<div class='streak-foot'><p class='mood'>{esc(mood_sentence(logs, mood))}</p>"
            f"<div class='pips'>{pips}</div>"
            f"<div class='goal'>{done} of {goal} training days this week</div></div></div>")


# The last 4 weeks, Monday first. Each square takes the color of what was done that day.
# Used by: dashboard_html.
def month_html(logs):
    by_date = {}
    for log in logs:
        if log["date"] not in by_date:
            by_date[log["date"]] = []
        if log["activity"] not in by_date[log["date"]]:
            by_date[log["date"]].append(log["activity"])

    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday() + 21)
    cells = ""
    for name in ["M", "T", "W", "T", "F", "S", "S"]:
        cells += f"<div class='day-name'>{name}</div>"
    for i in range(28):
        day = start + datetime.timedelta(days=i)
        iso = day.isoformat()
        extra = ""
        if day == today:
            extra = " today"
        if day > today:
            cells += f"<div class='cell future' style='--n:{i}'></div>"
        elif iso not in by_date:
            label = f"{nice_date(iso)}: rest"
            cells += (f"<a class='cell{extra}' href='/day?date={iso}' style='--n:{i}' "
                      f"title='{label}' aria-label='{label}'></a>")
        else:
            done = by_date[iso]
            if len(done) == 1:
                fill = color_of(done[0])
            else:
                # Two activities on one day: split the square diagonally.
                fill = f"linear-gradient(135deg, {color_of(done[0])} 50%, {color_of(done[1])} 50%)"
            label = esc(f"{nice_date(iso)}: {', '.join(done)}")
            cells += (f"<a class='cell{extra}' href='/day?date={iso}' "
                      f"style='--n:{i}; background:{fill}' title='{label}' aria-label='{label}'></a>")

    legend = ""
    for activity in ACTIVITY_COLORS:
        legend += f"<span style='--c:{color_of(activity)}'>{activity}</span>"
    return ("<div class='panel rise' style='--i:1'><div class='panel-head'><h2>Last 4 weeks</h2>"
            "<a class='link small' href='/calendar'>Full calendar &rarr;</a></div>"
            f"<div class='month-grid'>{cells}</div><div class='legend'>{legend}</div>"
            "<p class='hint'>Tap a day to see what you did.</p></div>")


# Used by: calendar_html, dashboard_html.
def tiles_html(logs):
    week = this_week_logs(logs)
    tiles = [("var(--accent)", "Best streak", f"{stats.longest_streak(logs)} days",
              f"current {stats.current_streak(logs)}"),
             ("var(--gym)", "Minutes trained", f"{stats.total_of(logs, 'duration'):,}",
              f"{stats.total_of(week, 'duration')} this week"),
             ("var(--cardio)", "Kcal burned", f"{stats.total_of(logs, 'calories'):,}",
              f"{stats.total_of(week, 'calories')} this week"),
             ("var(--yoga)", "Workouts", f"{len(logs)}", f"{len(week)} this week")]
    html_text = ""
    for i in range(len(tiles)):
        c, label, value, sub = tiles[i]
        html_text += (f"<div class='tile rise' style='--c:{c}; --i:{i + 2}'>"
                      f"<div class='small muted'>{label}</div><div class='num'>{value}</div>"
                      f"<div class='sub'>{sub}</div></div>")
    return f"<section class='tiles'>{html_text}</section>"


# Minutes per day for the last 14 days, stacked by activity.
# Used by: dashboard_html.
def chart_html(logs):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=13)
    minutes = {}
    for log in logs:
        if log["date"] < start.isoformat():
            continue
        if log["date"] not in minutes:
            minutes[log["date"]] = {}
        day = minutes[log["date"]]
        if log["activity"] not in day:
            day[log["activity"]] = 0
        day[log["activity"]] = day[log["activity"]] + log["duration"]

    most = 1
    total = 0
    for date in minutes:
        day_total = 0
        for activity in minutes[date]:
            day_total = day_total + minutes[date][activity]
        total = total + day_total
        if day_total > most:
            most = day_total

    bars = ""
    labels = ""
    for i in range(14):
        day = start + datetime.timedelta(days=i)
        iso = day.isoformat()
        segments = ""
        tip = nice_date(iso) + ": rest"
        if iso in minutes:
            parts = []
            for activity in ACTIVITY_COLORS:
                if activity in minutes[iso]:
                    mins = minutes[iso][activity]
                    height = mins * 100 / most
                    segments += f"<span style='--c:{color_of(activity)}; height:{height:.1f}%'></span>"
                    parts.append(f"{activity} {mins} min")
            tip = nice_date(iso) + ": " + ", ".join(parts)
        else:
            segments = "<span class='none'></span>"
        bars += (f"<a class='bar' href='/day?date={iso}' style='--n:{i}' title='{esc(tip)}' "
                 f"aria-label='{esc(tip)}'>{segments}</a>")
        now = ""
        if day == today:
            now = " class='now'"
        labels += f"<div{now}>{day.strftime('%a')[0]}</div>"
    return ("<div class='panel chart-panel rise' style='--i:6'><div class='panel-head'>"
            f"<h2>Minutes, last 14 days</h2><span class='muted small mono'>{total} min</span></div>"
            f"<div class='chart'>{bars}</div><div class='chart-days'>{labels}</div></div>")


# Used by: dashboard_html.
def mix_html(logs):
    counts = stats.count_by(logs, "activity")
    total = len(logs)
    bar = ""
    rows = ""
    for activity in counts:
        percent = counts[activity] * 100 / total
        bar += f"<span style='--c:{color_of(activity)}; width:{percent:.1f}%'></span>"
        rows += (f"<li><span style='--c:{color_of(activity)}'>{esc(activity)}</span>"
                 f"<span class='mono muted'>{counts[activity]} ({round(percent)}%)</span></li>")
    top = stats.most_frequent_exercise(logs)
    top_text = ""
    if top is not None:
        top_text = (f"<p class='top-move'><span class='muted small'>Most used exercise</span><br>"
                    f"<strong>{esc(top[0])}</strong>, {top[1]} times</p>")
    return ("<div class='panel'><div class='panel-head'><h2>Activity mix</h2></div>"
            f"<div class='mix'>{bar}</div><ul class='mix-rows'>{rows}</ul>{top_text}</div>")


# Used by: day_html, history_html.
def entry_html(log):
    pills = ""
    for name in log["exercises"]:
        pills += f"<span>{esc(name)}</span>"
    return (f"<div class='entry'>{badge(log['activity'])}<div>"
            f"<div class='entry-title'>{esc(log['focus'])} "
            f"<span class='muted small'>{esc(log['activity'])}  #{log['id']}</span></div>"
            f"<div class='pills'>{pills}</div></div>"
            f"<div class='entry-meta'><strong>{log['duration']}</strong> min<br>"
            f"<span class='muted small mono'>{log['calories']} kcal</span></div></div>")


# One day: what was done, or a rest day, with links to the days around it.
# Used by: Handler.do_GET.
def day_html(state, date):
    day = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    day_logs = []
    for log in state["logs"]:
        if log["date"] == date:
            day_logs.append(log)
    before = (day - datetime.timedelta(days=1)).isoformat()
    after = day + datetime.timedelta(days=1)
    nav = f"<a class='link' href='/day?date={before}'>&larr; {nice_date(before)}</a>"
    if after <= datetime.date.today():
        nav += f"<a class='link' href='/day?date={after.isoformat()}'>{nice_date(after.isoformat())} &rarr;</a>"
    log_here = f"<a class='btn' href='/log?date={date}'>Log a workout for this day</a>"

    if len(day_logs) == 0:
        content = ("<div class='panel rest-day rise' style='--i:1'>"
                   f"<div class='face'>{esc(ui.mascot('sleepy'))}</div>"
                   "<h2>No workout this day</h2>"
                   "<p class='muted'>Rest days help your muscles recover. Forgot to log one?</p>"
                   f"{log_here}</div>")
    else:
        entries = ""
        for log in day_logs:
            entries += entry_html(log)
        workouts = "workout"
        if len(day_logs) > 1:
            workouts = "workouts"
        content = ("<section class='tiles day-tiles'>"
                   f"<div class='tile rise' style='--c:var(--accent); --i:1'><div class='small muted'>Workouts</div>"
                   f"<div class='num'>{len(day_logs)}</div><div class='sub'>{workouts} this day</div></div>"
                   f"<div class='tile rise' style='--c:var(--gym); --i:2'><div class='small muted'>Minutes</div>"
                   f"<div class='num'>{stats.total_of(day_logs, 'duration')}</div><div class='sub'>trained</div></div>"
                   f"<div class='tile rise' style='--c:var(--cardio); --i:3'><div class='small muted'>Kcal</div>"
                   f"<div class='num'>{stats.total_of(day_logs, 'calories')}</div><div class='sub'>burned</div></div>"
                   "</section>"
                   f"<div class='panel rise' style='--i:4'>{entries}"
                   f"<p class='day-more'><a class='link' href='/log?date={date}'>+ Log another workout on this day</a></p></div>")
    body = (f"<div class='form-head rise'><div class='day-nav small'>{nav}</div>"
            f"<h1>{day.strftime('%A')} {day.day} {day.strftime('%B %Y')}</h1></div>{content}")
    month = f"<a class='link small' href='{month_link(day.year, day.month)}'>{day.strftime('%B %Y')} calendar</a>"
    body = body.replace("<h1>", month + "<h1>", 1)
    return page(nice_date(date), ACCOUNT_LINKS + BACK_LINK, body)


# "YYYY-MM" from the address, as (year, month). Anything else, or a month that has not
# started yet, gives None.
# Used by: Handler.do_GET.
def check_month(text):
    try:
        first = datetime.datetime.strptime(text + "-01", "%Y-%m-%d").date()
    except ValueError:
        return None
    today = datetime.date.today()
    if first.year < 2000 or (first.year, first.month) > (today.year, today.month):
        return None
    return first.year, first.month


# Used by: day_html, calendar_html.
def month_link(year, month):
    return f"/calendar?month={year:04d}-{month:02d}"


# One month, Monday first. Each day links to its day page and shows what was done.
# Used by: Handler.do_GET.
def calendar_html(state, year, month):
    logs = state["logs"]
    today = datetime.date.today()
    first = datetime.date(year, month, 1)
    month_logs = stats.logs_in_month(logs, year, month)
    by_date = stats.activities_by_date(month_logs)
    minutes = {}
    for log in month_logs:
        minutes[log["date"]] = minutes.get(log["date"], 0) + log["duration"]

    before = stats.add_months(year, month, -1)
    after = stats.add_months(year, month, 1)
    nav = f"<a href='{month_link(before[0], before[1])}'>&larr; {datetime.date(before[0], before[1], 1).strftime('%b')}</a>"
    if after <= (today.year, today.month):
        nav += f"<a href='{month_link(after[0], after[1])}'>{datetime.date(after[0], after[1], 1).strftime('%b')} &rarr;</a>"
        nav += "<a href='/calendar'>Today</a>"
    else:
        nav += "<span aria-hidden='true'>Next &rarr;</span>"

    cells = ""
    for name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        cells += f"<div class='day-name'>{name}</div>"
    n = 0
    for week in stats.month_weeks(year, month):
        for day in week:
            if day is None:
                cells += "<div class='cal-blank'></div>"
                continue
            n = n + 1
            iso = day.isoformat()
            extra = ""
            if day == today:
                extra = " today"
            if day > today:
                cells += f"<div class='cal-day future' style='--n:{n}'><span class='d'>{day.day}</span></div>"
                continue
            if iso not in by_date:
                label = f"{nice_date(iso)}: rest"
                cells += (f"<a class='cal-day{extra}' href='/day?date={iso}' style='--n:{n}' "
                          f"aria-label='{label}'><span class='d'>{day.day}</span></a>")
                continue
            done = by_date[iso]
            acts = ""
            for activity in done:
                acts += f"<span style='--c:{color_of(activity)}'><b>{esc(activity)}</b></span>"
            label = esc(f"{nice_date(iso)}: {', '.join(done)}")
            cells += (f"<a class='cal-day done{extra}' href='/day?date={iso}' "
                      f"style='--n:{n}; --c:{color_of(done[0])}' aria-label='{label}'>"
                      f"<span class='d'>{day.day}</span><span class='acts'>{acts}</span>"
                      f"<span class='mins'>{minutes[iso]}<span class='unit'> min</span></span></a>")

    legend = ""
    for activity in ACTIVITY_COLORS:
        legend += f"<span style='--c:{color_of(activity)}'>{activity}</span>"
    tiles = [("var(--accent)", "Workouts", len(month_logs)), ("var(--gym)", "Training days", len(by_date)),
             ("var(--pilates)", "Minutes", f"{stats.total_of(month_logs, 'duration'):,}"),
             ("var(--cardio)", "Kcal", f"{stats.total_of(month_logs, 'calories'):,}")]
    tiles_html = ""
    for i in range(len(tiles)):
        color, name, value = tiles[i]
        tiles_html += (f"<div class='tile rise' style='--c:{color}; --i:{i + 1}'>"
                       f"<div class='small muted'>{name}</div><div class='num'>{value}</div></div>")
    body = (f"<div class='cal-head rise'><div><div class='muted small'>Calendar</div>"
            f"<h1>{first.strftime('%B %Y')}</h1></div><nav class='cal-nav' aria-label='Months'>{nav}</nav></div>"
            f"<section class='tiles cal-tiles'>{tiles_html}</section>"
            f"<div class='panel rise' style='--i:5'><div class='cal'>{cells}</div>"
            f"<div class='legend'>{legend}</div>"
            "<p class='hint'>Tap a day to see it, or to log a workout you forgot.</p></div>")
    return page(first.strftime("%B %Y"), ACCOUNT_LINKS + LOG_BUTTON, body)


# Workouts grouped by day, newest first. Shows the last 7 days unless show_all.
# Used by: dashboard_html.
def history_html(logs, show_all):
    groups = []
    for log in stats.sort_logs(logs, "date", True):
        if len(groups) == 0 or groups[-1][0] != log["date"]:
            groups.append([log["date"], []])
        groups[-1][1].append(log)
    shown = groups
    if not show_all and len(groups) > 7:
        shown = groups[:7]

    body = ""
    for date, day_logs in shown:
        entries = ""
        for log in day_logs:
            entries += entry_html(log)
        body += (f"<div class='day'><a class='day-date' href='/day?date={date}'>{nice_date(date)}</a>"
                 f"{entries}</div>")

    more = ""
    if len(shown) < len(groups):
        more = f"<p><a class='link' href='/?all=1'>Show all {len(groups)} days</a></p>"
    return ("<div class='panel'><div class='panel-head'><h2>Recent workouts</h2>"
            f"<span class='muted small'>{len(logs)} total</span></div>{body}{more}</div>")


# Used by: Handler.do_GET.
def dashboard_html(state, message, show_all):
    logs = state["logs"]
    body = ""
    if message != "":
        body += f"<div class='notice ok' role='status'>{esc(ui.mascot('happy'))}  {esc(message)}</div>"
    body += f"<section class='hero'>{streak_html(state)}{month_html(logs)}</section>"
    if len(logs) == 0:
        body += ("<div class='panel'><h2>No workouts yet</h2>"
                 "<p class='muted'>Your chart, stats and history show up here after the first one.</p>"
                 f"{LOG_BUTTON}</div>")
    else:
        body += tiles_html(logs)
        body += chart_html(logs)
        body += (f"<section class='lower rise' style='--i:7'>{mix_html(logs)}"
                 f"{history_html(logs, show_all)}</section>")
    return page("Streakr", ACCOUNT_LINKS + LOG_BUTTON, body)


# Used by: choose_html, log_form_html, auth_html, setup_html.
def error_html(error, confirm_needed):
    if error == "":
        return ""
    if confirm_needed:
        return f"<div class='notice warn' role='alert'>{esc(error)}</div>"
    return f"<div class='notice error' role='alert'>{esc(ui.mascot('shocked'))}  {esc(error)}</div>"


# Used by: choose_html, log_form_html.
def crumbs(on_details):
    if on_details:
        return ("<div class='crumbs muted'><a class='link' href='/log'>Choose activity</a>"
                "<span>/</span><span class='here'>Details</span></div>")
    return ("<div class='crumbs muted'><span class='here'>Choose activity</span>"
            "<span>/</span><span>Details</span></div>")


# Step 1: one card per activity, with its focus options as chips.
# Used by: Handler.do_GET, Handler.do_POST.
def choose_html(state, error, date=""):
    weight = state["profile"]["weight"]
    date_field = ""
    date_note = ""
    if date != "":
        date_field = f"<input type='hidden' name='date' value='{esc(date)}'>"
        date_note = f"<p class='muted'>For {nice_date(date)}</p>"
    cards = ""
    for activity in state["profile"]["activities"]:
        chips = ""
        for focus in state["library"][activity]:
            value = activity + "|" + focus
            chips += (f"<label class='chip'>"
                      f"<input type='radio' name='choice' value='{esc(value)}' required>"
                      f"<span>{esc(focus)}</span></label>")
        latest = last_log(state["logs"], activity, None)
        last_text = "Not logged yet"
        if latest is not None:
            last_text = f"Last time: {nice_date(latest['date'])}, {latest['focus']}"
        per_hour = fitness.estimate_kcal(activity, weight, 60)
        cards += (f"<div class='act-card' role='group' aria-label='{esc(activity)}' "
                  f"style='--c:{color_of(activity)}'>"
                  f"<div class='act-head'>{badge(activity)}<div><h3>{esc(activity)}</h3>"
                  f"<div class='small muted'>About {per_hour} kcal per hour for you</div></div></div>"
                  f"<div class='chips'>{chips}</div><div class='last'>{esc(last_text)}</div></div>")
    body = (f"<div class='form-head rise'>{crumbs(False)}<h1>What did you train?</h1>{date_note}</div>"
            f"{error_html(error, False)}"
            f"<form class='rise' style='--i:1' method='get' action='/log'>{date_field}"
            f"<div class='act-grid'>{cards}</div><button class='btn'>Next</button></form>")
    return page("Log workout", ACCOUNT_LINKS + BACK_LINK, body)


# Right-hand panel on step 2: what helps you fill in the form.
# Used by: log_form_html.
def aside_html(state, activity, focus):
    latest = last_log(state["logs"], activity, focus)
    if latest is None:
        last_text = "<p class='muted'>First time logging this one.</p>"
    else:
        pills = ""
        for name in latest["exercises"]:
            pills += f"<span>{esc(name)}</span>"
        last_text = (f"<div>{nice_date(latest['date'])}, {latest['duration']} min</div>"
                     f"<div class='pills'>{pills}</div>")
    if rules.rest_rule_applies(activity, focus):
        rest_text = "Needs a rest day in between. You get a warning on back-to-back days."
    else:
        rest_text = "Fine to do every day."
    estimates = ""
    for minutes in [30, 45, 60]:
        kcal = fitness.estimate_kcal(activity, state["profile"]["weight"], minutes)
        estimates += f"<div><strong>{kcal}</strong><span class='small muted'>{minutes} min</span></div>"
    return (f"<aside class='panel aside rise' style='--i:2; --c:{color_of(activity)}'>"
            "<h3>About this session</h3>"
            f"<div class='aside-block'><div class='small muted'>Last time</div>{last_text}</div>"
            f"<div class='aside-block'><div class='small muted'>Rest days</div><div>{rest_text}</div></div>"
            "<div class='aside-block'><div class='small muted'>Estimated kcal</div>"
            f"<div class='est'>{estimates}</div></div></aside>")


# Step 2: the rest of the form. form holds what was typed before, so an error keeps it.
# The exercises this person did most often for this focus, most used first (up to 6).
# Used by: exercise_picker.
def usual_exercises(logs, activity, focus, library):
    counts = {}
    for log in logs:
        if log["activity"] == activity and log["focus"] == focus:
            for name in log["exercises"]:
                if name in library[activity][focus]:
                    if name not in counts:
                        counts[name] = 0
                    counts[name] = counts[name] + 1
    usual = []
    while len(usual) < 6 and len(counts) > 0:
        best = None
        for name in counts:
            if best is None or counts[name] > counts[best]:
                best = name
        usual.append(best)
        del counts[best]
    return usual


# Used by: exercise_picker.
def exercise_chips(names, chosen):
    chips = ""
    for name in names:
        checked = ""
        if name in chosen:
            checked = " checked"
        chips += (f"<label class='chip'><input type='checkbox' name='exercise' "
                  f"value='{esc(name)}'{checked}><span>{esc(name)}</span></label>")
    return f"<div class='chips'>{chips}</div>"


# A long list is split into groups that fold open (<details>, no JavaScript needed).
# "Your usual" comes first; every exercise appears only once.
# Used by: log_form_html.
def exercise_picker(state, activity, focus, chosen):
    usual = usual_exercises(state["logs"], activity, focus, state["library"])
    groups = []
    if len(usual) > 0:
        groups.append(("Your usual", usual))
    for group, names in fitness.grouped_exercises(state["library"], activity, focus):
        rest = []
        for name in names:
            if name not in usual:
                rest.append(name)
        if len(rest) > 0:
            groups.append((group, rest))
    if len(groups) == 1 and groups[0][0] == "":
        return exercise_chips(groups[0][1], chosen)

    html_text = ""
    for i in range(len(groups)):
        group, names = groups[i]
        if group == "":
            group = "More"
        picked = 0
        for name in names:
            if name in chosen:
                picked = picked + 1
        is_open = ""
        if i == 0 or picked > 0:
            is_open = " open"
        note = f"{len(names)}"
        if picked > 0:
            note = f"{picked} picked of {len(names)}"
        extra = ""
        if group == "Your usual":
            extra = " usual"
        html_text += (f"<details class='ex-group{extra}'{is_open}><summary><span>{esc(group)}</span>"
                      f"<span class='count'>{note}</span></summary>{exercise_chips(names, chosen)}</details>")
    return html_text


# Used by: Handler.do_GET, Handler.do_POST.
def log_form_html(state, activity, focus, form, error, confirm_needed):
    chosen = []
    if "exercise" in form:
        chosen = form["exercise"]
    picker = exercise_picker(state, activity, focus, chosen)
    duration_chips = ""
    for minutes in DURATION_PICKS:
        checked = ""
        if first(form, "duration_pick") == minutes:
            checked = " checked"
        duration_chips += (f"<label class='chip'><input type='radio' name='duration_pick' "
                           f"value='{minutes}'{checked}><span>{minutes} min</span></label>")
    date = first(form, "date")
    if date == "":
        date = datetime.date.today().isoformat()
    today = datetime.date.today().isoformat()

    confirm = ""
    if confirm_needed:
        confirm = ("<fieldset><label class='confirm notice warn'><input type='checkbox' "
                   "name='confirm_rest' value='yes'>Log it anyway</label></fieldset>")
    form_html = (f"<form class='panel rise' style='--i:1; --c:{color_of(activity)}' method='post' action='/log'>"
                 f"<input type='hidden' name='choice' value='{esc(activity + '|' + focus)}'>"
                 f"<fieldset><legend>Exercises</legend>{picker}"
                 "<div class='other'><label class='small muted' for='other'>Not in the list?</label>"
                 f"<input id='other' type='text' name='other' maxlength='200' value='{esc(first(form, 'other'))}' "
                 "placeholder='e.g. Cable Curl, Pec Deck'>"
                 "<div class='help'>Separate with commas. They are saved to your list for next time.</div>"
                 "</div></fieldset>"
                 f"<fieldset><legend>How long?</legend><div class='chips'>{duration_chips}</div>"
                 "<div class='inline' style='margin-top:12px'><label class='small muted' for='duration'>"
                 "Other</label><input id='duration' type='number' inputmode='numeric' name='duration' "
                 f"value='{esc(first(form, 'duration'))}'><span class='small muted'>minutes, 1 to 300</span>"
                 "</div></fieldset>"
                 "<fieldset><label class='field' for='calories'>Calories (kcal)</label>"
                 f"<input id='calories' type='number' inputmode='numeric' name='calories' "
                 f"value='{esc(first(form, 'calories'))}'>"
                 "<div class='help'>Leave empty to use the estimate</div></fieldset>"
                 "<fieldset><label class='field' for='date'>Date</label>"
                 f"<input id='date' type='date' name='date' value='{esc(date)}' max='{today}'></fieldset>"
                 f"{confirm}<button class='btn'>Save workout</button></form>")
    body = (f"<div class='form-head rise'>{crumbs(True)}<div class='act-head'>{badge(activity)}"
            f"<div><h1>{esc(focus)}</h1><div class='muted'>{esc(activity)}</div></div></div></div>"
            f"{error_html(error, confirm_needed)}"
            f"<div class='log-layout'>{form_html}{aside_html(state, activity, focus)}</div>")
    return page("Log workout", ACCOUNT_LINKS + BACK_LINK, body)


# Same rules as the terminal app. Returns (log, error, confirm_needed);
# log is None when nothing was saved.
# Used by: Handler.do_POST.
def save_from_form(state, form):
    choice = split_choice(state, first(form, "choice"))
    if choice is None:
        return None, "Pick an activity and focus.", False
    activity = choice[0]
    focus = choice[1]
    date = check_date(first(form, "date"))
    if date is None:
        return None, "The date must be YYYY-MM-DD and not in the future.", False
    exercises = []
    if "exercise" in form:
        for name in form["exercise"]:
            if name not in exercises:
                exercises.append(name)
    # Typed-in exercises: new ones become part of this person's library for this focus.
    new_names = []
    for name in first(form, "other").split(","):
        name = " ".join(name.split())  # trim and squeeze spaces
        if name == "":
            continue
        if len(name) > 40:
            return None, "Each exercise name can be at most 40 characters.", False
        if not name.isprintable():
            return None, "Exercise names can only use normal letters, numbers and symbols.", False
        if name not in exercises:
            exercises.append(name)
        if name not in state["library"][activity][focus] and name not in new_names:
            new_names.append(name)
    if len(new_names) > 10:
        return None, "Add at most 10 new exercises at a time.", False
    if len(exercises) == 0:
        return None, "Pick at least one exercise.", False
    for name in new_names:
        state["library"][activity][focus].append(name)
    ok, bad_names = rules.valid_exercises(state["library"], activity, focus, exercises)
    if not ok:
        return None, f"Not in {focus}: {', '.join(bad_names)}.", False
    # A typed duration wins over the quick-pick buttons.
    duration_text = first(form, "duration")
    if duration_text == "":
        duration_text = first(form, "duration_pick")
    duration = to_int(duration_text, 1, 300)
    if duration is None:
        return None, "Pick a duration, or type one from 1 to 300 minutes.", False
    if first(form, "calories") == "":
        calories = fitness.estimate_kcal(activity, state["profile"]["weight"], duration)
    else:
        calories = to_int(first(form, "calories"), 0, 3000)
        if calories is None:
            return None, "Calories must be a whole number from 0 to 3000.", False
    with SAVE_LOCK:
        # Reload inside the lock, so a workout saved a moment ago is seen.
        logs = db.load_all(state["user_id"])["logs"]
        if rules.is_duplicate(logs, date, activity, focus):
            return None, f"You already logged {activity} / {focus} on {date}.", False
        if rules.needs_rest(logs, date, activity, focus):
            if first(form, "confirm_rest") != "yes":
                return None, (f"You trained {activity} / {focus} the day before or after {date}. "
                              "Muscles need a rest day to recover."), True
        log = {"date": date, "activity": activity, "focus": focus,
               "exercises": exercises, "duration": duration, "calories": calories}
        for name in new_names:
            db.save_exercise(activity, focus, name, 1, state["user_id"])
        db.save_log(log, state["user_id"])
    return log, "", False


# Pages for people who are not logged in, and the first-time profile form.
# Used by: Handler.do_GET, Handler.do_POST.
def auth_html(mode, username, error):
    if mode == "signup":
        title = "Create account"
        lead = "Track your workouts and keep your streak going."
        password_hint = "<div class='help'>At least 8 characters</div>"
        autocomplete = "new-password"
        other = "Already have an account? <a href='/login'>Log in</a>"
    else:
        title = "Log in"
        lead = "Welcome back. Your streak is waiting."
        password_hint = ""
        autocomplete = "current-password"
        other = "New here? <a href='/signup'>Create an account</a>"
    body = (f"<div class='auth rise'><h1>{title}</h1><p class='muted'>{lead}</p>"
            f"{error_html(error, False)}"
            f"<form class='panel' method='post' action='/{mode}'>"
            "<fieldset><label class='field' for='username'>Username</label>"
            f"<input id='username' type='text' name='username' value='{esc(username)}' "
            "autocomplete='username' maxlength='20' required></fieldset>"
            "<fieldset><label class='field' for='password'>Password</label>"
            f"<input id='password' type='password' name='password' autocomplete='{autocomplete}' "
            f"maxlength='128' required>{password_hint}</fieldset>"
            f"<button class='btn'>{title}</button></form>"
            f"<p class='muted small auth-other'>{other}</p></div>")
    return page(title, "", body)


# Used by: setup_html.
def chip_group(kind, name, options, chosen):
    chips = ""
    for value, label in options:
        checked = ""
        if value in chosen:
            checked = " checked"
        chips += (f"<label class='chip'><input type='{kind}' name='{name}' value='{esc(value)}'"
                  f"{checked}><span>{esc(label)}</span></label>")
    return f"<div class='chips'>{chips}</div>"


# The same questions as onboarding.py in the terminal app. form holds what was typed.
# Used by: Handler.do_GET, Handler.do_POST.
def setup_html(form, error, editing):
    genders = [("male", "Male"), ("female", "Female"), ("none", "Not specified")]
    activities = []
    for activity in fitness.MET:
        activities.append((activity, activity))
    goals = []
    for days in range(1, 8):
        goals.append((str(days), str(days)))
    chosen_activities = []
    if "activities" in form:
        chosen_activities = form["activities"]
    title = "Set up your profile"
    if editing:
        title = "Your profile"
    body = (f"<div class='form-head rise'><h1>{title}</h1>"
            "<p class='muted'>Used for your calorie estimates and weekly goal.</p></div>"
            f"{error_html(error, False)}"
            "<form class='panel rise setup' style='--i:1' method='post' action='/setup'>"
            "<fieldset><label class='field' for='name'>What should we call you?</label>"
            f"<input id='name' type='text' name='name' maxlength='30' value='{esc(first(form, 'name'))}'>"
            "</fieldset>"
            f"<fieldset><legend>Gender</legend>{chip_group('radio', 'gender', genders, [first(form, 'gender')])}"
            "<div class='help'>Only used for the daily calorie (BMR) formula</div></fieldset>"
            "<div class='three'>"
            "<div><label class='field' for='age'>Age</label>"
            f"<input id='age' type='number' name='age' value='{esc(first(form, 'age'))}'>"
            "<div class='help'>10 to 100</div></div>"
            "<div><label class='field' for='height'>Height (cm)</label>"
            f"<input id='height' type='number' name='height' value='{esc(first(form, 'height'))}'>"
            "<div class='help'>100 to 250</div></div>"
            "<div><label class='field' for='weight'>Weight (kg)</label>"
            f"<input id='weight' type='number' name='weight' value='{esc(first(form, 'weight'))}'>"
            "<div class='help'>30 to 250</div></div></div>"
            f"<fieldset><legend>What do you do?</legend>"
            f"{chip_group('checkbox', 'activities', activities, chosen_activities)}</fieldset>"
            f"<fieldset><legend>Training days per week</legend>"
            f"{chip_group('radio', 'weekly_goal', goals, [first(form, 'weekly_goal')])}</fieldset>"
            "<button class='btn'>Save profile</button></form>")
    right = LOGOUT_FORM
    if editing:
        right = ACCOUNT_LINKS + BACK_LINK
    return page(title, right, body)


# Same ranges as the terminal onboarding. Returns (profile, error).
# Used by: Handler.do_POST.
def profile_from_form(form):
    name = first(form, "name")
    if len(name) < 1 or len(name) > 30:
        return None, "Name must be 1 to 30 characters."
    if not name.isprintable():
        return None, "Name can only use normal letters, numbers and symbols."
    gender = first(form, "gender")
    if gender not in ["male", "female", "none"]:
        return None, "Pick a gender option."
    age = to_int(first(form, "age"), 10, 100)
    height = to_int(first(form, "height"), 100, 250)
    weight = to_int(first(form, "weight"), 30, 250)
    if age is None or height is None or weight is None:
        return None, "Age 10 to 100, height 100 to 250 cm, weight 30 to 250 kg, as whole numbers."
    activities = []
    if "activities" in form:
        for activity in form["activities"]:
            if activity in fitness.MET and activity not in activities:
                activities.append(activity)
    if len(activities) == 0:
        return None, "Pick at least one activity."
    goal = to_int(first(form, "weekly_goal"), 1, 7)
    if goal is None:
        return None, "Pick how many days a week you want to train."
    return {"name": name, "gender": gender, "age": age, "height": height, "weight": weight,
            "weekly_goal": goal, "activities": activities}, ""


# A saved profile shown in the form, so editing starts from what is there.
# Used by: Handler.do_GET.
def profile_as_form(profile):
    return {"name": [profile["name"]], "gender": [profile["gender"]],
            "age": [str(profile["age"])], "height": [str(profile["height"])],
            "weight": [str(profile["weight"])], "activities": profile["activities"],
            "weekly_goal": [str(profile["weekly_goal"])]}


# http.server needs a class with do_GET / do_POST. This is the only class in the
# project: each method just reads the request and calls the plain functions above.
class Handler(http.server.BaseHTTPRequestHandler):
    # Called by: http.server, for every GET request (opening a page).
    def do_GET(self):
        if not self.host_ok():
            self.send_error(400, "Unknown host")
            return
        url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(url.query)
        if url.path == "/theme":
            self.set_theme(first(query, "set"))
            return
        user_id = self.current_user()
        if url.path == "/login" or url.path == "/signup":
            if user_id is not None:
                self.redirect("/")
            else:
                self.send_html(auth_html(url.path[1:], "", ""))
            return
        if user_id is None:
            self.redirect("/login")
            return
        state = db.load_all(user_id)
        state["user_id"] = user_id
        if url.path == "/setup":
            if state["profile"] is None:
                self.send_html(setup_html({}, "", False))
            else:
                self.send_html(setup_html(profile_as_form(state["profile"]), "", True))
        elif state["profile"] is None:
            self.redirect("/setup")
        elif url.path == "/":
            # Only show the message for a workout that really exists, so a link
            # cannot put made-up text on the page.
            message = ""
            saved_id = to_int(first(query, "saved"), 1, 1000000000)
            if saved_id is not None and stats.find_by_id(state["logs"], saved_id) is not None:
                message = f"Saved workout #{saved_id}."
            self.send_html(dashboard_html(state, message, first(query, "all") == "1"))
        elif url.path == "/calendar":
            today = datetime.date.today()
            chosen = (today.year, today.month)
            if first(query, "month") != "":
                chosen = check_month(first(query, "month"))
            if chosen is None:
                self.redirect("/calendar")
            else:
                self.send_html(calendar_html(state, chosen[0], chosen[1]))
        elif url.path == "/day":
            date = check_date(first(query, "date"))
            if date is None:
                self.redirect("/")
            else:
                self.send_html(day_html(state, date))
        elif url.path == "/log":
            # A date can come from the day page; ignore it if it is not a valid past date.
            date = check_date(first(query, "date"))
            if date is None:
                date = ""
            choice = split_choice(state, first(query, "choice"))
            if first(query, "choice") == "":
                self.send_html(choose_html(state, "", date))
            elif choice is None:
                self.send_html(choose_html(state, "Pick an activity and focus.", date))
            else:
                self.send_html(log_form_html(state, choice[0], choice[1], {"date": [date]}, "", False))
        else:
            self.send_error(404)

    # Called by: http.server, for every POST request (sending a form).
    def do_POST(self):
        if not self.host_ok() or not self.same_origin():
            self.send_error(403, "Form must be sent from this site")
            return
        length = to_int(self.headers.get("Content-Length", "0"), 0, MAX_BODY)
        if length is None:
            self.send_error(413, "Request too large")
            return
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        form = urllib.parse.parse_qs(body)

        if self.path == "/signup" or self.path == "/login":
            username = first(form, "username")
            password = ""
            if "password" in form:
                password = form["password"][0]  # not stripped: spaces may be part of it
            if self.path == "/signup":
                user_id, error = accounts.sign_up(username, password)
            else:
                user_id, error = accounts.log_in(username, password)
            if user_id is None:
                self.send_html(auth_html(self.path[1:], username, error))
            else:
                self.redirect("/", self.session_cookie(accounts.start_session(user_id)))
            return
        if self.path == "/logout":
            accounts.end_session(self.cookie("session"))
            self.redirect("/login", "session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")
            return

        user_id = self.current_user()
        if user_id is None:
            self.redirect("/login")
            return
        state = db.load_all(user_id)
        state["user_id"] = user_id
        if self.path == "/setup":
            profile, error = profile_from_form(form)
            if profile is None:
                self.send_html(setup_html(form, error, state["profile"] is not None))
            else:
                db.save_profile(profile, user_id)
                self.redirect("/")
            return
        if self.path != "/log":
            self.send_error(404)
            return
        if state["profile"] is None:
            self.redirect("/setup")
            return
        log, error, confirm_needed = save_from_form(state, form)
        if log is not None:
            # Redirect after saving, so refreshing the page does not save twice.
            self.redirect(f"/?saved={log['id']}")
            return
        choice = split_choice(state, first(form, "choice"))
        if choice is None:
            self.send_html(choose_html(state, error))
        else:
            self.send_html(log_form_html(state, choice[0], choice[1], form, error,
                                         confirm_needed))

    # Used by: Handler.do_GET, Handler.do_POST.
    def send_html(self, text):
        text = text.replace("data-theme='auto'", f"data-theme='{self.theme()}'", 1)
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for name in SECURITY_HEADERS:
            self.send_header(name, SECURITY_HEADERS[name])
        self.end_headers()
        self.wfile.write(data)

    # Used by: Handler.do_GET, Handler.do_POST, Handler.set_theme.
    def redirect(self, location, cookie=""):
        self.send_response(303)
        if cookie != "":
            self.send_header("Set-Cookie", cookie)
        self.send_header("Location", location)
        self.end_headers()

    # Used by: Handler.do_GET, Handler.do_POST.
    def host_ok(self):
        return self.headers.get("Host", "") in ALLOWED_HOSTS

    # Browsers send Origin with every form post. A post from another website would carry
    # that site's address, so it is refused (this blocks cross-site request forgery).
    # Used by: Handler.do_POST.
    def same_origin(self):
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return urllib.parse.urlparse(origin).netloc in ALLOWED_HOSTS

    # Used by: Handler.do_POST, Handler.current_user, Handler.theme.
    def cookie(self, name):
        try:
            cookie = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
        except http.cookies.CookieError:
            return ""
        if name in cookie:
            return cookie[name].value
        return ""

    # Used by: Handler.do_GET, Handler.do_POST.
    def current_user(self):
        return accounts.user_for_token(self.cookie("session"))

    # HttpOnly: page code cannot read it. SameSite=Lax: other sites cannot send it with
    # their forms. Secure (only over HTTPS) when we sit behind an HTTPS proxy like Dokploy's.
    # Used by: Handler.do_POST.
    def session_cookie(self, token):
        cookie = f"session={token}; Path=/; Max-Age={accounts.SESSION_DAYS * 86400}; HttpOnly; SameSite=Lax"
        if self.headers.get("X-Forwarded-Proto") == "https":
            cookie = cookie + "; Secure"
        return cookie

    # The theme lives in a cookie, so the choice is remembered on the next visit.
    # Used by: Handler.send_html.
    def theme(self):
        theme = self.cookie("theme")
        if theme in THEMES:
            return theme
        return "auto"

    # Used by: Handler.do_GET.
    def set_theme(self, theme):
        if theme not in THEMES:
            theme = "auto"
        # Go back to the page the user was on, but only if it is one of our own pages.
        back = "/"
        referer = urllib.parse.urlparse(self.headers.get("Referer", ""))
        pages = ["/", "/log", "/day", "/calendar", "/setup", "/login", "/signup"]
        if referer.netloc in ALLOWED_HOSTS and referer.path in pages:
            back = referer.path
            if referer.query != "":
                back = back + "?" + referer.query
        self.redirect(back, f"theme={theme}; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly")

    # Keep the terminal quiet instead of printing every request.
    # Called by: http.server after each request (we replace its printing).
    def log_message(self, format, *args):
        pass


# Used by: python3 server.py (the if __name__ block).
def run_server():
    db.init_db()
    try:
        # Threading: one slow visitor does not make everyone else wait.
        server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError:
        print(f"Port {PORT} is already in use. Is server.py already running in another terminal?")
        return
    print(f"Streakr web view on {HOST}:{PORT}, open http://localhost:{PORT}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    server.server_close()


if __name__ == "__main__":
    run_server()
