import unittest
from src.services.calculator import calculate_total

class TestCalculator(unittest.TestCase):

    def test_calculate_total_with_valid_input(self):
        hours_worked = 10
        hourly_rate = 20
        expected_total = 200
        self.assertEqual(calculate_total(hours_worked, hourly_rate), expected_total)

    def test_calculate_total_with_zero_hours(self):
        hours_worked = 0
        hourly_rate = 20
        expected_total = 0
        self.assertEqual(calculate_total(hours_worked, hourly_rate), expected_total)

    def test_calculate_total_with_negative_hours(self):
        hours_worked = -5
        hourly_rate = 20
        with self.assertRaises(ValueError):
            calculate_total(hours_worked, hourly_rate)

    def test_calculate_total_with_zero_rate(self):
        hours_worked = 10
        hourly_rate = 0
        expected_total = 0
        self.assertEqual(calculate_total(hours_worked, hourly_rate), expected_total)

    def test_calculate_total_with_negative_rate(self):
        hours_worked = 10
        hourly_rate = -20
        with self.assertRaises(ValueError):
            calculate_total(hours_worked, hourly_rate)

if __name__ == '__main__':
    unittest.main()