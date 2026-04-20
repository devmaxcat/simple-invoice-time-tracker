class Invoice:
    def __init__(self, invoice_number, total_amount, timesheet=None, associated_timesheet=None):
        self.invoice_number = invoice_number
        self.total_amount = total_amount
        self.timesheet = timesheet if timesheet is not None else associated_timesheet

    def __str__(self):
        return f"Invoice #{self.invoice_number}: Total Amount: {self.total_amount}, Timesheet: {self.timesheet}"

    def calculate_total(self):
        return self.total_amount

    def get_invoice_details(self):
        return {
            "invoice_number": self.invoice_number,
            "total_amount": self.total_amount,
            "timesheet": self.timesheet
        }