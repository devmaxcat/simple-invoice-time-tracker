class TimesheetEntryScreen:
    def __init__(self):
        self.hours_worked = 0
        self.rate = 18  # Default hourly rate
        self.work_notes = ""
    
    def display(self):
        print("=== Timesheet Entry ===")
        print(f"Hours Worked: {self.hours_worked}")
        print(f"Hourly Rate: {self.rate}")
        print(f"Work Notes: {self.work_notes}")
        print("========================")
    
    def enter_hours(self, hours):
        if self.validate_hours(hours):
            self.hours_worked = hours
        else:
            print("Invalid hours. Please enter a positive number.")
    
    def validate_hours(self, hours):
        return isinstance(hours, (int, float)) and hours >= 0
    
    def enter_rate(self, rate):
        if self.validate_rate(rate):
            self.rate = rate
        else:
            print("Invalid rate. Please enter a positive number.")
    
    def validate_rate(self, rate):
        return isinstance(rate, (int, float)) and rate > 0
    
    def enter_work_notes(self, notes):
        self.work_notes = notes
    
    def calculate_total(self):
        return self.hours_worked * self.rate
    
    def submit_entry(self):
        total = self.calculate_total()
        print(f"Entry submitted. Total amount: {total}")