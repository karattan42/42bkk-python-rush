import unittest

import fitness


class Calories(unittest.TestCase):
    def test_kcal_is_met_times_weight_times_hours(self):
        self.assertEqual(fitness.estimate_kcal("Gym", 70, 60), 350)
        self.assertEqual(fitness.estimate_kcal("Yoga", 70, 30), 88)      # 87.5 rounds to 88
        self.assertEqual(fitness.estimate_kcal("Cardio", 80, 45), 420)
        self.assertEqual(fitness.estimate_kcal("Pilates", 60, 1), 3)

    def test_every_activity_has_a_met(self):
        for activity in fitness.default_library():
            self.assertIn(activity, fitness.MET)


class Bmr(unittest.TestCase):
    def profile(self, gender):
        return {"gender": gender, "weight": 70, "height": 175, "age": 24}

    def test_mifflin_st_jeor(self):
        self.assertAlmostEqual(fitness.bmr(self.profile("male")), 1678.75)
        self.assertAlmostEqual(fitness.bmr(self.profile("female")), 1512.75)

    def test_not_specified_is_the_average(self):
        self.assertAlmostEqual(fitness.bmr(self.profile("none")), (1678.75 + 1512.75) / 2)


class Library(unittest.TestCase):
    def test_each_call_returns_a_fresh_copy(self):
        first = fitness.default_library()
        first["Gym"]["Upper Body"].append("Changed")
        self.assertNotIn("Changed", fitness.default_library()["Gym"]["Upper Body"])

    def test_no_exercise_name_contains_a_comma(self):
        # The terminal picker splits on commas.
        library = fitness.default_library()
        for activity in library:
            for focus in library[activity]:
                for name in library[activity][focus]:
                    self.assertNotIn(",", name)


if __name__ == "__main__":
    unittest.main()
