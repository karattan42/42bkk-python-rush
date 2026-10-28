"""The web view's form checks and HTML, called directly (no network)."""
import unittest

import db
import server
from tests.support import day, new_user_with_profile, use_temp_db

EVIL = "<script>alert(1)</script>"


def form(**fields):
    """Build a form the way urllib.parse.parse_qs returns it: every value is a list."""
    result = {}
    for key in fields:
        value = fields[key]
        if isinstance(value, list):
            result[key] = value
        else:
            result[key] = [value]
    return result


class LogForm(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)
        self.user_id = new_user_with_profile()

    def state(self):
        state = db.load_all(self.user_id)
        state["user_id"] = self.user_id
        return state

    def save(self, **fields):
        return server.save_from_form(self.state(), form(**fields))

    def test_valid_log_uses_estimated_kcal(self):
        log, error, confirm = self.save(choice="Gym|Upper Body", date=day(0),
                                        exercise=["Pull Up"], duration_pick="60")
        self.assertEqual(error, "")
        self.assertEqual(log["calories"], 350)
        self.assertEqual(db.load_all(self.user_id)["logs"][0]["id"], log["id"])

    def test_typed_duration_beats_quick_pick(self):
        log = self.save(choice="Yoga|Relax", date=day(0), exercise="Cat-Cow",
                        duration="25", duration_pick="90")[0]
        self.assertEqual(log["duration"], 25)

    def test_typed_calories_are_kept(self):
        log = self.save(choice="Yoga|Relax", date=day(0), exercise="Cat-Cow",
                        duration="25", calories="111")[0]
        self.assertEqual(log["calories"], 111)

    def test_each_bad_field_is_rejected(self):
        base = {"choice": "Gym|Upper Body", "date": day(0), "exercise": "Pull Up", "duration": "30"}
        cases = [("choice", "Gym|Nope", "Pick an activity"),
                 ("choice", "Pilates|Core", "Pick an activity"),   # not in this profile
                 ("date", day(1), "not in the future"),
                 ("date", "29-10-2026", "YYYY-MM-DD"),
                 ("exercise", [], "at least one exercise"),
                 ("exercise", "Squat", "Not in Upper Body"),
                 ("exercise", EVIL, "Not in Upper Body"),
                 ("duration", "0", "1 to 300"),
                 ("duration", "301", "1 to 300"),
                 ("duration", "abc", "1 to 300"),
                 ("calories", "3001", "0 to 3000"),
                 ("calories", "-1", "0 to 3000")]
        for field, value, message in cases:
            fields = dict(base)
            fields[field] = value
            log, error, confirm = self.save(**fields)
            self.assertIsNone(log, (field, value))
            self.assertIn(message, error, (field, value))
        self.assertEqual(db.load_all(self.user_id)["logs"], [])

    def test_repeated_exercise_is_saved_once(self):
        log = self.save(choice="Gym|Upper Body", date=day(0),
                        exercise=["Pull Up", "Pull Up", "Bicep Curl"], duration="30")[0]
        self.assertEqual(log["exercises"], ["Pull Up", "Bicep Curl"])

    def test_duplicate_day_is_rejected(self):
        self.save(choice="Yoga|Relax", date=day(0), exercise="Cat-Cow", duration="20")
        log, error, confirm = self.save(choice="Yoga|Relax", date=day(0), exercise="Cat-Cow",
                                        duration="20")
        self.assertIsNone(log)
        self.assertIn("already logged", error)

    def test_rest_day_needs_confirmation(self):
        self.save(choice="Gym|Upper Body", date=day(-1), exercise="Pull Up", duration="30")
        log, error, confirm = self.save(choice="Gym|Upper Body", date=day(0),
                                        exercise="Pull Up", duration="30")
        self.assertIsNone(log)
        self.assertTrue(confirm)
        log = self.save(choice="Gym|Upper Body", date=day(0), exercise="Pull Up",
                        duration="30", confirm_rest="yes")[0]
        self.assertIsNotNone(log)


class ProfileForm(unittest.TestCase):
    good = {"name": "Alice", "gender": "female", "age": "30", "height": "165", "weight": "58",
            "activities": ["Yoga", "Pilates"], "weekly_goal": "3"}

    def test_valid_profile(self):
        profile, error = server.profile_from_form(form(**self.good))
        self.assertEqual(error, "")
        self.assertEqual(profile["age"], 30)
        self.assertEqual(profile["activities"], ["Yoga", "Pilates"])

    def test_unknown_and_repeated_activities_are_dropped(self):
        fields = dict(self.good)
        fields["activities"] = ["Yoga", "Hacking", "Yoga"]
        self.assertEqual(server.profile_from_form(form(**fields))[0]["activities"], ["Yoga"])

    def test_bad_fields(self):
        cases = [("name", ""), ("name", "x" * 31), ("name", "Evil\x1b[2J"), ("gender", "robot"), ("age", "9"),
                 ("age", "101"), ("height", "99"), ("weight", "251"), ("weight", "70.5"),
                 ("activities", []), ("activities", ["Hacking"]), ("weekly_goal", "0"),
                 ("weekly_goal", "8")]
        for field, value in cases:
            fields = dict(self.good)
            fields[field] = value
            profile, error = server.profile_from_form(form(**fields))
            self.assertIsNone(profile, (field, value))
            self.assertNotEqual(error, "")

    def test_profile_as_form_round_trip(self):
        profile = server.profile_from_form(form(**self.good))[0]
        again = server.profile_from_form(server.profile_as_form(profile))[0]
        self.assertEqual(again, profile)


class Escaping(unittest.TestCase):
    """Text typed by users (even in the terminal app) must never become HTML."""

    def setUp(self):
        use_temp_db(self)
        profile = {"name": EVIL, "gender": "male", "age": 24, "height": 175, "weight": 70,
                   "weekly_goal": 4, "activities": ["Gym"]}
        self.user_id = new_user_with_profile(profile=profile)
        db.save_exercise("Gym", "Upper Body", EVIL, 1, self.user_id)
        db.save_log({"date": day(0), "activity": "Gym", "focus": "Upper Body",
                     "exercises": [EVIL], "duration": 30, "calories": 175}, self.user_id)

    def test_no_page_contains_raw_html_from_data(self):
        state = db.load_all(self.user_id)
        state["user_id"] = self.user_id
        pages = [server.dashboard_html(state, EVIL, True),
                 server.choose_html(state, EVIL),
                 server.log_form_html(state, "Gym", "Upper Body", form(duration="'><b>", exercise=EVIL),
                                      EVIL, True),
                 server.setup_html(server.profile_as_form(state["profile"]), EVIL, True),
                 server.auth_html("login", EVIL, EVIL)]
        for html_text in pages:
            self.assertNotIn("<script>", html_text)
            self.assertNotIn("'><b>", html_text)
            self.assertIn("&lt;script&gt;", html_text)


class Dashboard(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)
        self.user_id = new_user_with_profile()

    def state(self):
        state = db.load_all(self.user_id)
        state["user_id"] = self.user_id
        return state

    def test_empty_dashboard(self):
        html_text = server.dashboard_html(self.state(), "", False)
        self.assertIn("No workouts yet", html_text)
        self.assertIn("Log a workout to start a streak.", html_text)

    def test_history_shows_seven_days_then_a_link(self):
        for offset in range(10):
            db.save_log({"date": day(-offset * 2), "activity": "Yoga", "focus": "Relax",
                         "exercises": ["Cat-Cow"], "duration": 20, "calories": 58}, self.user_id)
        short = server.dashboard_html(self.state(), "", False)
        full = server.dashboard_html(self.state(), "", True)
        self.assertEqual(short.count("class='day'"), 7)
        self.assertIn("Show all 10 days", short)
        self.assertEqual(full.count("class='day'"), 10)

    def test_no_dashes_that_look_machine_written(self):
        db.save_log({"date": day(0), "activity": "Gym", "focus": "Upper Body",
                     "exercises": ["Pull Up"], "duration": 20, "calories": 117}, self.user_id)
        state = self.state()
        for html_text in [server.dashboard_html(state, "", True), server.choose_html(state, ""),
                          server.log_form_html(state, "Gym", "Upper Body", {}, "", False)]:
            self.assertNotIn("—", html_text)
            self.assertNotIn("–", html_text)



class DayPage(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)
        self.user_id = new_user_with_profile()
        for offset, focus in [(-1, "Upper Body"), (-1, "Lower Body"), (-3, "Full Body")]:
            db.save_log({"date": day(offset), "activity": "Gym", "focus": focus,
                         "exercises": ["Burpee"], "duration": 30, "calories": 175}, self.user_id)

    def state(self):
        state = db.load_all(self.user_id)
        state["user_id"] = self.user_id
        return state

    def test_day_with_workouts(self):
        html_text = server.day_html(self.state(), day(-1))
        self.assertEqual(html_text.count("class='entry'"), 2)
        self.assertIn("<div class='num'>60</div>", html_text)      # minutes
        self.assertIn("<div class='num'>350</div>", html_text)     # kcal
        self.assertIn(f"/log?date={day(-1)}", html_text)
        self.assertIn(f"/day?date={day(-2)}", html_text)
        self.assertIn(f"/day?date={day(0)}", html_text)

    def test_rest_day_offers_logging_that_day(self):
        html_text = server.day_html(self.state(), day(-2))
        self.assertIn("No workout this day", html_text)
        self.assertIn(f"href='/log?date={day(-2)}'", html_text)

    def test_today_has_no_link_to_tomorrow(self):
        self.assertNotIn(f"/day?date={day(1)}", server.day_html(self.state(), day(0)))

    def test_calendar_chart_and_history_link_to_days(self):
        html_text = server.dashboard_html(self.state(), "", False)
        self.assertIn(f"<a class='cell' href='/day?date={day(-1)}'", html_text)
        self.assertIn(f"<a class='bar' href='/day?date={day(-3)}'", html_text)
        self.assertIn(f"<a class='day-date' href='/day?date={day(-1)}'", html_text)
        self.assertNotIn(f"/day?date={day(1)}", html_text)

    def test_choose_page_carries_the_date(self):
        html_text = server.choose_html(self.state(), "", day(-5))
        self.assertIn(f"name='date' value='{day(-5)}'", html_text)


class ExercisePicker(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)
        self.user_id = new_user_with_profile()

    def state(self):
        state = db.load_all(self.user_id)
        state["user_id"] = self.user_id
        return state

    def log(self, exercises, offset):
        db.save_log({"date": day(offset), "activity": "Gym", "focus": "Upper Body",
                     "exercises": exercises, "duration": 30, "calories": 175}, self.user_id)

    def test_usual_is_most_used_first(self):
        self.log(["Lat Pulldown", "Dips"], -6)
        self.log(["Dips", "Face Pull"], -4)
        self.log(["Dips", "Lat Pulldown"], -2)
        state = self.state()
        usual = server.usual_exercises(state["logs"], "Gym", "Upper Body", state["library"])
        self.assertEqual(usual[:2], ["Dips", "Lat Pulldown"])
        self.assertEqual(len(usual), 3)

    def test_every_exercise_is_offered_exactly_once(self):
        self.log(["Lat Pulldown", "Dips"], -2)
        state = self.state()
        html_text = server.exercise_picker(state, "Gym", "Upper Body", [])
        for name in state["library"]["Gym"]["Upper Body"]:
            self.assertEqual(html_text.count(f"value='{server.esc(name)}'"), 1, name)
        self.assertIn("Your usual", html_text)
        self.assertLess(html_text.index("Your usual"), html_text.index("Chest"))

    def test_only_first_group_and_groups_with_picks_are_open(self):
        html_text = server.exercise_picker(self.state(), "Gym", "Upper Body", ["Face Pull"])
        self.assertEqual(html_text.count("<details class='ex-group' open>"), 2)  # Chest + Back
        self.assertIn("1 picked of 7", html_text)

    def test_one_group_focus_has_no_folding(self):
        html_text = server.exercise_picker(self.state(), "Cardio", "Run", [])
        self.assertNotIn("<details", html_text)


class TypedInExercises(unittest.TestCase):
    def setUp(self):
        use_temp_db(self)
        self.user_id = new_user_with_profile()

    def save(self, user_id=None, **fields):
        if user_id is None:
            user_id = self.user_id
        state = db.load_all(user_id)
        state["user_id"] = user_id
        base = {"choice": "Gym|Upper Body", "date": day(0), "duration": "30"}
        base.update(fields)
        return server.save_from_form(state, form(**base))

    def test_typed_exercise_is_logged_and_saved_for_next_time(self):
        log, error, confirm = self.save(exercise="Pull Up", other=" Pec  Deck , cable curl,")
        self.assertEqual(error, "")
        self.assertEqual(log["exercises"], ["Pull Up", "Pec Deck", "cable curl"])
        library = db.load_all(self.user_id)["library"]["Gym"]["Upper Body"]
        self.assertIn("Pec Deck", library)
        self.assertIn("cable curl", library)

    def test_typed_only_is_enough(self):
        self.assertIsNotNone(self.save(other="Pec Deck")[0])

    def test_typing_a_built_in_name_does_not_duplicate_it(self):
        before = len(db.select_all("exercises"))
        self.save(other="Bench Press")
        self.assertEqual(len(db.select_all("exercises")), before)

    def test_other_people_do_not_get_my_exercises(self):
        self.save(other="Secret Move")
        other_user = new_user_with_profile("other")
        self.assertNotIn("Secret Move", db.load_all(other_user)["library"]["Gym"]["Upper Body"])

    def test_limits(self):
        self.assertIn("at most 40", self.save(other="x" * 41)[1])
        self.assertIn("normal letters", self.save(other="Bad\x1b[31mName")[1])
        names = ", ".join(["Move " + str(i) for i in range(11)])
        self.assertIn("at most 10", self.save(other=names)[1])

    def test_nothing_is_saved_when_the_log_is_rejected(self):
        before = len(db.select_all("exercises"))
        log, error, confirm = self.save(other="Pec Deck", duration="0")
        self.assertIsNone(log)
        self.assertEqual(len(db.select_all("exercises")), before)


if __name__ == "__main__":
    unittest.main()
