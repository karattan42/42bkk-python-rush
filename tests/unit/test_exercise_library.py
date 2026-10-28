"""The bigger exercise library, its groups, and how old databases pick up new exercises."""
import sqlite3
import unittest

import db
import fitness
from tests.support import use_temp_db

# Every exercise that existed before the library grew. Old logs and plans use these
# names, so they must never disappear.
ORIGINAL = {
    ("Gym", "Upper Body"): ["Bench Press", "Pull Up", "Shoulder Press", "Barbell Row", "Bicep Curl"],
    ("Gym", "Lower Body"): ["Squat", "Deadlift", "Lunge", "Leg Press", "Calf Raise"],
    ("Gym", "Full Body"): ["Burpee", "Clean and Press", "Kettlebell Swing", "Thruster"],
    ("Yoga", "Flexibility"): ["Downward Dog", "Forward Fold", "Pigeon Pose", "Cobra Pose"],
    ("Yoga", "Balance"): ["Tree Pose", "Warrior III", "Crow Pose", "Half Moon"],
    ("Yoga", "Relax"): ["Child's Pose", "Corpse Pose", "Cat-Cow", "Legs Up the Wall"],
    ("Pilates", "Core"): ["The Hundred", "Roll Up", "Criss Cross", "Plank"],
    ("Pilates", "Mat"): ["Single Leg Stretch", "Swan", "Saw", "Teaser"],
    ("Pilates", "Posture"): ["Spine Stretch", "Swimming", "Shoulder Bridge", "Side Kick"],
    ("Cardio", "Run"): ["Easy Run", "Tempo Run", "Interval Run", "Long Run"],
    ("Cardio", "Cycle"): ["Road Ride", "Indoor Bike", "Hill Climb"],
    ("Cardio", "HIIT"): ["Jumping Jacks", "Mountain Climbers", "High Knees", "Jump Squat"],
}


class Library(unittest.TestCase):
    def test_old_exercises_are_all_still_there(self):
        library = fitness.default_library()
        for (activity, focus), names in ORIGINAL.items():
            for name in names:
                self.assertIn(name, library[activity][focus], (activity, focus, name))

    def test_every_focus_has_plenty_and_no_repeats(self):
        library = fitness.default_library()
        for activity in library:
            for focus in library[activity]:
                names = library[activity][focus]
                self.assertGreaterEqual(len(names), 6, (activity, focus))
                self.assertEqual(len(names), len(set(names)), (activity, focus))

    def test_names_are_short_and_safe_for_the_terminal_picker(self):
        library = fitness.default_library()
        for activity in library:
            for focus in library[activity]:
                for name in library[activity][focus]:
                    self.assertLessEqual(len(name), 40)
                    self.assertNotIn(",", name)
                    self.assertFalse(name.isdigit())


class Groups(unittest.TestCase):
    def test_groups_hold_each_exercise_exactly_once(self):
        library = fitness.default_library()
        for activity in library:
            for focus in library[activity]:
                seen = []
                for group, names in fitness.grouped_exercises(library, activity, focus):
                    seen.extend(names)
                self.assertEqual(sorted(seen), sorted(library[activity][focus]))

    def test_own_exercises_go_last(self):
        library = fitness.default_library()
        library["Gym"]["Upper Body"].append("Pec Deck")
        groups = fitness.grouped_exercises(library, "Gym", "Upper Body")
        self.assertEqual(groups[0][0], "Chest")
        self.assertEqual(groups[-1], ("Your own", ["Pec Deck"]))

    def test_groups_only_show_exercises_in_the_library(self):
        library = {"Gym": {"Upper Body": ["Pull Up", "My Move"]}}
        groups = fitness.grouped_exercises(library, "Gym", "Upper Body")
        self.assertEqual(groups, [("Back", ["Pull Up"]), ("Your own", ["My Move"])])


class OldDatabase(unittest.TestCase):
    def test_new_built_in_exercises_are_added_once(self):
        use_temp_db(self)
        conn = sqlite3.connect(db.DB_FILE)
        conn.execute("DELETE FROM exercises WHERE name = 'Lat Pulldown' OR name = 'Box Jump'")
        conn.commit()
        conn.close()
        self.assertNotIn("Lat Pulldown", db.load_all()["library"]["Gym"]["Upper Body"])
        db.init_db()
        db.init_db()
        library = db.load_all()["library"]
        self.assertEqual(library["Gym"]["Upper Body"].count("Lat Pulldown"), 1)
        self.assertEqual(library["Cardio"]["HIIT"].count("Box Jump"), 1)

    def test_custom_exercise_with_a_built_in_name_is_listed_once(self):
        use_temp_db(self)
        db.save_exercise("Gym", "Upper Body", "Push Up", 1)
        self.assertEqual(db.load_all()["library"]["Gym"]["Upper Body"].count("Push Up"), 1)


if __name__ == "__main__":
    unittest.main()
