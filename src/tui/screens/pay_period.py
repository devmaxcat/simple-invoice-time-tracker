class PayPeriodScreen:
    def __init__(self):
        self.pay_periods = self.get_pay_periods()
        self.current_index = 0

    def get_pay_periods(self):
        # This method should return a list of pay periods
        return ["Weekly", "Bi-Weekly", "Monthly"]

    def display(self):
        # This method should display the current pay period selection
        print("Select Pay Period:")
        for index, period in enumerate(self.pay_periods):
            prefix = "-> " if index == self.current_index else "   "
            print(f"{prefix}{period}")

    def adjust_offset(self, direction):
        # Adjust the current index based on user input
        if direction == "up":
            self.current_index = (self.current_index - 1) % len(self.pay_periods)
        elif direction == "down":
            self.current_index = (self.current_index + 1) % len(self.pay_periods)

    def get_selected_pay_period(self):
        # Return the currently selected pay period
        return self.pay_periods[self.current_index]