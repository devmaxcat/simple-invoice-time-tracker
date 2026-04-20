class Timesheet:
    def __init__(self, hours_worked=0, rate=18.0, submission_date=None, due_date=None, work_notes=""):
        self.hours_worked = hours_worked
        self.rate = rate
        self.submission_date = submission_date
        self.due_date = due_date
        self.work_notes = work_notes

    def calculate_total(self):
        return self.hours_worked * self.rate

    def __str__(self):
        return (f"Timesheet Entry:\n"
                f"Hours Worked: {self.hours_worked}\n"
                f"Rate: {self.rate}\n"
                f"Total: {self.calculate_total()}\n"
                f"Submission Date: {self.submission_date}\n"
                f"Due Date: {self.due_date}\n"
                f"Work Notes: {self.work_notes}")