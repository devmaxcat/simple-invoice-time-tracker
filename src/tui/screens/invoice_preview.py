class InvoicePreviewScreen:
    def __init__(self, invoice):
        self.invoice = invoice

    def render(self):
        print("Invoice Preview")
        print("----------------")
        print(f"Invoice Number: {self.invoice.invoice_number}")
        print(f"Total Amount: {self.format_currency(self.invoice.total_amount)}")
        print("Timesheet Details:")
        for entry in self.invoice.timesheet.entries:
            print(f" - Hours Worked: {entry.hours_worked}, Rate: {self.format_currency(entry.rate)}, Total: {self.format_currency(entry.total)}")
        print("----------------")
        print("Thank you for your business!")

    def format_currency(self, amount):
        return f"${amount:,.2f}"