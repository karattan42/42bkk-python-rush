import datetime
import unittest

import fitness
import stats
from tests.support import day, make_log


class Totals(unittest.TestCase):
    def test_total_and_count(self):
        logs = [make_log(1, day(0), "Gym", duration=60, calories=350),
                make_log(2, day(-1), "Yoga", "Relax", duration=30, calories=90),
                make_log(3, day(-2), "Gym", duration=45, calories=260)]
        self.assertEqual(stats.total_of(logs, "duration"), 135)
        self.assertEqual(stats.total_of(logs, "calories"), 700)
        self.assertEqual(stats.count_by(logs, "activity"), {"Gym": 2, "Yoga": 1})

    def test_empty(self):
        self.assertEqual(stats.total_of([], "duration"), 0)
        self.assertEqual(stats.count_by([], "activity"), {})
        self.assertIsNone(stats.most_frequent_exercise([]))
        self.assertIsNone(stats.days_since_last([]))

    def test_most_frequent_exercise(self):
        logs = [make_log(1, day(0), exercises=["Squat", "Lunge"]),
                make_log(2, day(-1), exercises=["Lunge"]),
                make_log(3, day(-2), exercises=["Squat", "Lunge"])]
        self.assertEqual(stats.most_frequent_exercise(logs), ("Lunge", 3))


class Streaks(unittest.TestCase):
    def logs_on(self, offsets):
        logs = []
        for i in range(len(offsets)):
            logs.append(make_log(i + 1, day(offsets[i])))
        return logs

    def test_streak_including_today(self):
        self.assertEqual(stats.current_streak(self.logs_on([0, -1, -2])), 3)

    def test_streak_still_alive_when_today_not_logged(self):
        self.assertEqual(stats.current_streak(self.logs_on([-1, -2])), 2)

    def test_streak_broken(self):
        self.assertEqual(stats.current_streak(self.logs_on([-2, -3])), 0)
        self.assertEqual(stats.current_streak([]), 0)

    def test_two_logs_on_one_day_count_once(self):
        self.assertEqual(stats.current_streak(self.logs_on([0, 0, -1])), 2)

    def test_longest_streak_finds_best_run(self):
        logs = self.logs_on([-1, -2, -10, -11, -12, -13, -20])
        self.assertEqual(stats.longest_streak(logs), 4)
        self.assertEqual(stats.longest_streak([]), 0)

    def test_days_since_last(self):
        self.assertEqual(stats.days_since_last(self.logs_on([-5, -3])), 3)
        self.assertEqual(stats.days_since_last(self.logs_on([0])), 0)

    def test_days_this_week_counts_distinct_days_since_monday(self):
        today = datetime.date.today()
        monday_offset = -today.weekday()
        logs = self.logs_on([0, 0, monday_offset, monday_offset - 1, -8])
        expected = 1
        if monday_offset != 0:
            expected = 2
        self.assertEqual(stats.days_this_week(logs), expected)


class SortSearchFind(unittest.TestCase):
    def setUp(self):
        self.logs = [make_log(1, day(-2)), make_log(2, day(0), "Yoga", "Relax"),
                     make_log(3, day(-1)), make_log(4, day(0))]

    def test_sort_newest_first_keeps_order_of_ties(self):
        result = stats.sort_logs(self.logs, "date", True)
        ids = []
        for log in result:
            ids.append(log["id"])
        self.assertEqual(ids, [2, 4, 3, 1])

    def test_sort_oldest_first(self):
        result = stats.sort_logs(self.logs, "date", False)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[-1]["date"], day(0))

    def test_sort_does_not_change_original(self):
        stats.sort_logs(self.logs, "date", True)
        self.assertEqual(self.logs[0]["id"], 1)

    def test_search_is_case_insensitive(self):
        self.assertEqual(len(stats.search_logs(self.logs, "activity", "yoga")), 1)
        self.assertEqual(len(stats.search_logs(self.logs, "date", day(0))), 2)
        self.assertEqual(stats.search_logs(self.logs, "activity", "Pilates"), [])

    def test_find_by_id(self):
        self.assertEqual(stats.find_by_id(self.logs, 3)["id"], 3)
        self.assertIsNone(stats.find_by_id(self.logs, 99))


class RandomWorkout(unittest.TestCase):
    def test_random_exercises_come_from_focus_without_repeats(self):
        library = fitness.default_library()
        for i in range(20):
            names = stats.random_workout(library, "Gym", "Upper Body", 3)
            self.assertEqual(len(names), 3)
            self.assertEqual(len(set(names)), 3)
            for name in names:
                self.assertIn(name, library["Gym"]["Upper Body"])

    def test_asking_for_too_many_gives_all(self):
        library = fitness.default_library()
        names = stats.random_workout(library, "Cardio", "Cycle", 50)
        self.assertEqual(sorted(names), sorted(library["Cardio"]["Cycle"]))


if __name__ == "__main__":
    unittest.main()
