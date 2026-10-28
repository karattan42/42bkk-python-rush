"""What a visitor does in the browser, start to finish."""
import datetime
import re

from playwright.sync_api import expect

from conftest import unique_name

PASSWORD = "password-123"


def chip(page, text):
    return page.locator("label.chip", has_text=re.compile("^" + re.escape(text) + "$"))


def pick_exercise(page, name):
    """Open the folded group that holds this exercise (like a person would), then tick it."""
    group = page.locator("details.ex-group", has=page.locator(f"input[name=exercise][value=\"{name}\"]"))
    if group.count() > 0 and group.get_attribute("open") is None:
        group.locator("summary").click()
    chip(page, name).click()


def sign_up(page, username, activities=("Gym", "Yoga")):
    page.goto("/signup")
    page.fill("#username", username)
    page.fill("#password", PASSWORD)
    page.click("button:has-text('Create account')")
    expect(page).to_have_url(re.compile("/setup$"))
    page.fill("#name", username.title())
    chip(page, "Female").click()
    page.fill("#age", "30")
    page.fill("#height", "165")
    page.fill("#weight", "60")
    for activity in activities:
        chip(page, activity).click()
    chip(page, "3").click()
    page.click("button:has-text('Save profile')")
    expect(page).to_have_url(re.compile("/$"))


def log_workout(page, activity_focus, exercises, minutes="30", date=None, confirm=False):
    page.goto("/log")
    activity, focus = activity_focus.split("|")
    page.locator(f"input[value='{activity_focus}']").check()
    page.click("button:has-text('Next')")
    expect(page.locator("h1")).to_have_text(focus)
    for name in exercises:
        pick_exercise(page, name)
    chip(page, minutes + " min").click()
    if date is not None:
        page.fill("#date", date)
    if confirm:
        page.check("input[name=confirm_rest]")
    page.click("button:has-text('Save workout')")


def test_sign_up_set_up_and_log_first_workout(page):
    page.goto("/")
    expect(page).to_have_url(re.compile("/login$"))
    sign_up(page, unique_name())
    expect(page.locator(".panel", has_text="No workouts yet")).to_be_visible()
    expect(page.locator(".big")).to_contain_text("0")

    log_workout(page, "Yoga|Relax", ["Cat-Cow", "Child's Pose"])
    expect(page.locator(".notice.ok")).to_contain_text("Saved workout #")
    expect(page.locator(".big")).to_contain_text("1")
    expect(page.locator(".entry")).to_have_count(1)
    expect(page.locator(".entry")).to_contain_text("Child's Pose")
    expect(page.locator(".mood")).to_have_text("Today is done. Rest well.")


def test_form_errors_keep_what_was_typed(page):
    sign_up(page, unique_name())
    page.goto("/log?choice=Gym%7CUpper+Body")
    chip(page, "45 min").click()
    page.click("button:has-text('Save workout')")
    expect(page.locator(".notice.error")).to_contain_text("Pick at least one exercise.")
    expect(page.locator("input[name=duration_pick][value='45']")).to_be_checked()

    pick_exercise(page, "Pull Up")
    page.fill("#duration", "500")
    page.click("button:has-text('Save workout')")
    expect(page.locator(".notice.error")).to_contain_text("1 to 300")


def test_rest_day_warning_then_log_anyway(page):
    sign_up(page, unique_name())
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    log_workout(page, "Gym|Upper Body", ["Pull Up"], date=yesterday)
    expect(page.locator(".notice.ok")).to_be_visible()

    log_workout(page, "Gym|Upper Body", ["Bench Press"])
    expect(page.locator(".notice.warn").first).to_contain_text("Muscles need a rest day")
    expect(chip(page, "Bench Press").locator("input")).to_be_checked()
    page.check("input[name=confirm_rest]")
    page.click("button:has-text('Save workout')")
    expect(page.locator(".notice.ok")).to_be_visible()
    expect(page.locator(".big")).to_contain_text("2")

    log_workout(page, "Gym|Upper Body", ["Pull Up"], confirm=False)
    expect(page.locator(".notice.error")).to_contain_text("already logged")


def test_side_panel_shows_last_session_and_estimates(page):
    sign_up(page, unique_name())
    log_workout(page, "Yoga|Relax", ["Cat-Cow"], minutes="45")
    page.goto("/log?choice=Yoga%7CRelax")
    aside = page.locator("aside")
    expect(aside).to_contain_text("45 min")
    expect(aside).to_contain_text("Cat-Cow")
    expect(aside).to_contain_text("Fine to do every day.")
    expect(aside.locator(".est strong").first).to_have_text("75")  # 2.5 x 60 kg x 0.5 h



def test_click_a_calendar_square_to_see_that_day(page):
    sign_up(page, unique_name())
    yesterday = (datetime.date.today() - datetime.timedelta(days=1))
    log_workout(page, "Yoga|Relax", ["Cat-Cow"], date=yesterday.isoformat())
    page.goto("/")
    page.locator(f"a.cell[href='/day?date={yesterday.isoformat()}']").click()
    expect(page.locator("h1")).to_contain_text(str(yesterday.day))
    expect(page.locator(".entry")).to_contain_text("Cat-Cow")
    page.click("text=Back to dashboard")
    page.locator(f"a.bar[href='/day?date={yesterday.isoformat()}']").click()
    expect(page.locator(".entry")).to_have_count(1)


def test_log_a_forgotten_workout_from_a_rest_day(page):
    sign_up(page, unique_name())
    three_days_ago = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
    page.goto(f"/day?date={three_days_ago}")
    expect(page.locator(".rest-day")).to_contain_text("No workout this day")
    page.click("text=Log a workout for this day")
    page.locator("input[value='Gym|Lower Body']").check()
    page.click("button:has-text('Next')")
    expect(page.locator("#date")).to_have_value(three_days_ago)
    pick_exercise(page, "Squat")
    chip(page, "45 min").click()
    page.click("button:has-text('Save workout')")
    page.goto(f"/day?date={three_days_ago}")
    expect(page.locator(".entry")).to_contain_text("Squat")


def test_folded_groups_and_typed_in_exercise(page):
    sign_up(page, unique_name())
    page.goto("/log?choice=Gym%7CUpper+Body")
    arms = page.locator("details.ex-group", has_text="Arms")
    expect(arms).not_to_have_attribute("open", "")
    arms.locator("summary").click()
    chip(page, "Hammer Curl").click()
    page.fill("#other", "Pec Deck")
    chip(page, "60 min").click()
    page.click("button:has-text('Save workout')")
    expect(page.locator(".entry")).to_contain_text("Pec Deck")

    page.goto("/log?choice=Gym%7CUpper+Body")
    usual = page.locator("details.ex-group.usual")
    expect(usual).to_contain_text("Hammer Curl")
    expect(usual).to_contain_text("Pec Deck")
    expect(page.locator("input[name=exercise][value='Pec Deck']")).to_have_count(1)


def test_theme_choice_is_remembered(page):
    page.goto("/login")
    page.click(".theme >> text=Dark")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    page.reload()
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    page.goto("/signup")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    page.click(".theme >> text=Light")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")


def test_dark_theme_really_changes_colors(page):
    page.goto("/login")
    light = page.evaluate("getComputedStyle(document.body).backgroundColor")
    page.click(".theme >> text=Dark")
    dark = page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert light != dark


def test_two_people_do_not_see_each_other(new_page):
    alice = new_page()
    bob = new_page()
    sign_up(alice, unique_name("alice"))
    sign_up(bob, unique_name("bob"))
    log_workout(alice, "Yoga|Balance", ["Tree Pose"])
    alice_url = alice.url
    bob.goto(alice_url)
    expect(bob.locator(".notice.ok")).to_have_count(0)
    expect(bob.locator("text=Tree Pose")).to_have_count(0)
    expect(alice.locator(".entry", has_text="Tree Pose")).to_be_visible()


def test_log_out(page):
    sign_up(page, unique_name())
    page.click("button:has-text('Log out')")
    expect(page).to_have_url(re.compile("/login$"))
    page.goto("/log")
    expect(page).to_have_url(re.compile("/login$"))


def test_wrong_password_and_log_back_in(page):
    username = unique_name()
    sign_up(page, username)
    page.click("button:has-text('Log out')")
    page.fill("#username", username)
    page.fill("#password", "not-the-password")
    page.click("button:has-text('Log in')")
    expect(page.locator(".notice.error")).to_contain_text("Wrong username or password.")
    page.fill("#password", PASSWORD)
    page.click("button:has-text('Log in')")
    expect(page).to_have_url(re.compile("/$"))


def test_chips_work_with_the_keyboard(page):
    sign_up(page, unique_name())
    page.goto("/log")
    first = page.locator("input[name=choice]").first
    first.focus()
    page.keyboard.press("Space")
    expect(first).to_be_checked()
    page.keyboard.press("Enter")
    expect(page).to_have_url(re.compile("choice="))


def test_no_page_scrolls_sideways_on_a_phone(new_page):
    page = new_page(viewport={"width": 375, "height": 800}, is_mobile=True)
    sign_up(page, unique_name())
    log_workout(page, "Gym|Full Body", ["Burpee", "Kettlebell Swing", "Clean and Press", "Thruster"])
    for path in ["/", "/?all=1", "/log", "/log?choice=Gym%7CFull+Body", "/setup"]:
        page.goto(path)
        too_wide = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        assert not too_wide, path
    page.click("button:has-text('Log out')")
    for path in ["/login", "/signup"]:
        page.goto(path)
        assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth"), path
