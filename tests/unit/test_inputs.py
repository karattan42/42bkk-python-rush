import contextlib
import io
import unittest
from unittest import mock

import inputs
from tests.support import day


def answer(function, typed, *args, **kwargs):
    """Call an inputs.ask_* function as if the user typed each item of `typed`.
    Returns (result, everything that was printed)."""
    printed = io.StringIO()
    with mock.patch("builtins.input", side_effect=typed), contextlib.redirect_stdout(printed):
        result = function(*args, **kwargs)
    return result, printed.getvalue()


class AskInt(unittest.TestCase):
    def test_keeps_asking_until_valid(self):
        result, out = answer(inputs.ask_int, ["abc", "", "-5", "301", "4.5", " 42 "], "> ", 1, 300)
        self.assertEqual(result, 42)
        self.assertEqual(out.count("whole number"), 3)
        self.assertEqual(out.count("from 1 to 300"), 2)

    def test_enter_uses_default(self):
        result, out = answer(inputs.ask_int, [""], "> ", 0, 3000, default=262)
        self.assertEqual(result, 262)

    def test_b_goes_back_only_when_allowed(self):
        result, out = answer(inputs.ask_int, ["b"], "> ", 1, 10, True)
        self.assertIsNone(result)
        result, out = answer(inputs.ask_int, ["b", "3"], "> ", 1, 10)
        self.assertEqual(result, 3)


class AskDate(unittest.TestCase):
    def test_enter_is_today(self):
        self.assertEqual(answer(inputs.ask_date, [""], "> ")[0], day(0))

    def test_rejects_bad_format_and_future(self):
        result, out = answer(inputs.ask_date, ["28/10/2026", "2026-13-01", day(1), day(-3)], "> ")
        self.assertEqual(result, day(-3))
        self.assertEqual(out.count("YYYY-MM-DD"), 2)
        self.assertIn("future", out)

    def test_short_date_is_normalised(self):
        self.assertEqual(answer(inputs.ask_date, ["2024-1-5"], "> ")[0], "2024-01-05")


class AskChoices(unittest.TestCase):
    def test_choice(self):
        result, out = answer(inputs.ask_choice, ["0", "4", "2"], "Pick:", ["A", "B", "C"])
        self.assertEqual(result, "B")

    def test_choice_back(self):
        self.assertIsNone(answer(inputs.ask_choice, ["b"], "Pick:", ["A"], True)[0])

    def test_multi_removes_repeats(self):
        result, out = answer(inputs.ask_multi, ["1, 3,1"], "Pick:", ["A", "B", "C"])
        self.assertEqual(result, ["A", "C"])

    def test_multi_rejects_bad_numbers(self):
        result, out = answer(inputs.ask_multi, ["", "1,x", "5", "2"], "Pick:", ["A", "B"])
        self.assertEqual(result, ["B"])
        self.assertEqual(out.count("from 1 to 2"), 3)

    def test_yes_no(self):
        self.assertTrue(answer(inputs.ask_yes_no, ["maybe", "Y"], "Sure?")[0])
        self.assertFalse(answer(inputs.ask_yes_no, ["no"], "Sure?")[0])

    def test_text_cannot_be_empty(self):
        result, out = answer(inputs.ask_text, ["", "   ", " Kan "], "Name: ")
        self.assertEqual(result, "Kan")


if __name__ == "__main__":
    unittest.main()
