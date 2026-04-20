class DatesScreen:
    def __init__(self):
        self.submission_date = self.get_today_date()
        self.due_date_offset = 7  # Default due date is 7 days from submission

    def get_today_date(self):
        from datetime import datetime
        return datetime.today().date()

    def set_due_date_offset(self, offset):
        self.due_date_offset = offset

    def get_due_date(self):
        from datetime import timedelta
        return self.submission_date + timedelta(days=self.due_date_offset)

    def display_dates(self):
        print(f"Submission Date: {self.submission_date}")
        print(f"Due Date: {self.get_due_date()}")

    def input_dates(self):
        # Logic for user input to set submission and due dates
        pass

    def save_dates(self):
        # Logic to save the submission and due dates
        pass