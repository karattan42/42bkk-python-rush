import unittest

import fitness
import rules
from tests.support import day, make_log


class DuplicateRule(unittest.TestCase):
    def setUp(self):
        self.logs = [make_log(1, day(0), "Gym", "Upper Body")]

    def test_same_day_activity_focus_is_duplicate(self):
        self.assertTrue(rules.is_duplicate(self.logs, day(0), "Gym", "Upper Body"))

    def test_other_focus_or_day_is_not_duplicate(self):
        self.assertFalse(rules.is_duplicate(self.logs, day(0), "Gym", "Lower Body"))
        self.assertFalse(rules.is_duplicate(self.logs, day(-1), "Gym", "Upper Body"))

    def test_edited_log_ignores_itself(self):
        self.assertFalse(rules.is_duplicate(self.logs, day(0), "Gym", "Upper Body", skip_id=1))


class RestDayRule(unittest.TestCase):
    def test_gym_day_before_and_day_after_need_rest(self):
        logs = [make_log(1, day(-1), "Gym", "Upper Body")]
        self.assertTrue(rules.needs_rest(logs, day(0), "Gym", "Upper Body"))
        self.assertTrue(rules.needs_rest(logs, day(-2), "Gym", "Upper Body"))

    def test_two_days_apart_is_fine(self):
        logs = [make_log(1, day(-2), "Gym", "Upper Body")]
        self.assertFalse(rules.needs_rest(logs, day(0), "Gym", "Upper Body"))

    def test_other_muscle_group_is_fine(self):
        logs = [make_log(1, day(-1), "Gym", "Upper Body")]
        self.assertFalse(rules.needs_rest(logs, day(0), "Gym", "Lower Body"))

    def test_yoga_and_pilates_never_need_rest(self):
        logs = [make_log(1, day(-1), "Yoga", "Relax"), make_log(2, day(-1), "Pilates", "Core")]
        self.assertFalse(rules.needs_rest(logs, day(0), "Yoga", "Relax"))
        self.assertFalse(rules.needs_rest(logs, day(0), "Pilates", "Core"))

    def test_only_hiit_counts_for_cardio(self):
        logs = [make_log(1, day(-1), "Cardio", "HIIT"), make_log(2, day(-1), "Cardio", "Run")]
        self.assertTrue(rules.needs_rest(logs, day(0), "Cardio", "HIIT"))
        self.assertFalse(rules.needs_rest(logs, day(0), "Cardio", "Run"))

    def test_moving_a_log_ignores_itself(self):
        logs = [make_log(1, day(-1), "Gym", "Upper Body")]
        self.assertFalse(rules.needs_rest(logs, day(0), "Gym", "Upper Body", skip_id=1))


class ExerciseMustMatch(unittest.TestCase):
    def setUp(self):
        self.library = fitness.default_library()

    def test_all_exercises_in_focus(self):
        ok, bad = rules.valid_exercises(self.library, "Gym", "Upper Body", ["Bench Press", "Pull Up"])
        self.assertTrue(ok)
        self.assertEqual(bad, [])

    def test_wrong_group_is_reported(self):
        ok, bad = rules.valid_exercises(self.library, "Gym", "Upper Body", ["Bench Press", "Squat", "9"])
        self.assertFalse(ok)
        self.assertEqual(bad, ["Squat", "9"])

    def test_names_are_case_sensitive(self):
        ok, bad = rules.valid_exercises(self.library, "Gym", "Upper Body", ["bench press"])
        self.assertFalse(ok)


class PlanRule(unittest.TestCase):
    def test_one_to_ten_unique_exercises(self):
        self.assertTrue(rules.valid_plan(["A"])[0])
        self.assertTrue(rules.valid_plan([str(i) for i in range(10)])[0])

    def test_empty_or_too_long_plan(self):
        self.assertFalse(rules.valid_plan([])[0])
        self.assertFalse(rules.valid_plan([str(i) for i in range(11)])[0])

    def test_repeated_exercise(self):
        ok, message = rules.valid_plan(["Squat", "Lunge", "Squat"])
        self.assertFalse(ok)
        self.assertIn("Squat", message)


if __name__ == "__main__":
    unittest.main()
