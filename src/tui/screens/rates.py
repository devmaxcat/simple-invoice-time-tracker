class RatesScreen:
    def __init__(self):
        self.rate = 18  # Default hourly rate

    def display(self):
        print("Current Hourly Rate: ${:.2f}".format(self.rate))
        print("Enter new hourly rate (or press Enter to keep current):")

    def input_rate(self):
        user_input = input()
        if user_input.strip():
            try:
                new_rate = float(user_input)
                self.rate = new_rate
                print("Hourly rate updated to: ${:.2f}".format(self.rate))
            except ValueError:
                print("Invalid input. Please enter a valid number.")

    def get_rate(self):
        return self.rate

    def run(self):
        self.display()
        self.input_rate()