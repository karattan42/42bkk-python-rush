"""The Halloween pixel art and theme switch in ui.py."""
import os
import unittest
from unittest import mock

import ui


class PixelArt(unittest.TestCase):
    def test_two_pixel_rows_make_one_line(self):
        rows = ["ab ", "a  ", "b b"]
        lines = ui.pixel_art(rows, {"a": ui.ORANGE, "b": ui.PINK})
        self.assertEqual(len(lines), 2)
        # Tests are not a color terminal, so paint() gives back the bare characters.
        self.assertEqual(lines[0], "▀▀ ")
        self.assertEqual(lines[1], "▀ ▀")

    def test_pumpkin_is_symmetric_and_fits_next_to_the_logo(self):
        for row in ui.PUMPKIN:
            self.assertEqual(len(row), 22)
            self.assertEqual(row, row[::-1])
        self.assertEqual(len(ui.pixel_art(ui.PUMPKIN, ui.pumpkin_colors(ui.YELLOW))), 9)
        self.assertLessEqual(ui.display_width(ui.spooky_logo(ui.YELLOW)[0]), 76)


class HalloweenSwitch(unittest.TestCase):
    def test_environment_wins_over_the_date(self):
        with mock.patch.dict(os.environ, {"STREAKR_THEME": "halloween"}):
            self.assertTrue(ui.halloween_on())
        with mock.patch.dict(os.environ, {"STREAKR_THEME": "normal"}):
            self.assertFalse(ui.halloween_on())

    def test_terminal_art_has_no_emoji(self):
        # Emoji are drawn at different widths by different terminals, so the terminal
        # uses colored text art only. (The web page may use emoji.)
        with open(ui.__file__, encoding="utf-8") as f:
            for ch in f.read():
                self.assertLess(ord(ch), 0x1F000, repr(ch))


if __name__ == "__main__":
    unittest.main()
