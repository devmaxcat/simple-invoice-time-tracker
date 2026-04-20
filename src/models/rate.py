class Rate:
    def __init__(self, hourly_rate=18):
        self.hourly_rate = hourly_rate

    def set_rate(self, new_rate):
        if new_rate < 0:
            raise ValueError("Rate cannot be negative.")
        self.hourly_rate = new_rate

    def calculate_total(self, hours_worked):
        if hours_worked < 0:
            raise ValueError("Hours worked cannot be negative.")
        return self.hourly_rate * hours_worked

    def __str__(self):
        return f"Hourly Rate: ${self.hourly_rate:.2f}"