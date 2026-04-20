import unittest
from src.services.invoice_generator import generate_invoice, InvoiceGenerationError
from src.models.invoice import Invoice
from src.models.timesheet import Timesheet

class TestInvoiceGenerator(unittest.TestCase):

    def setUp(self):
        self.timesheet = Timesheet(
            hours_worked=40,
            rate=20,
            submission_date='2023-10-01',
            due_date='2023-10-15',
            work_notes='Worked on project X'
        )
        self.invoice = Invoice(
            invoice_number=1,
            total_amount=800,  # 40 hours * $20/hour
            associated_timesheet=self.timesheet
        )

    def test_generate_invoice_success(self):
        result = generate_invoice(self.invoice)
        self.assertTrue(result)
        # Additional checks can be added here to verify the PDF file creation

    def test_generate_invoice_failure(self):
        with self.assertRaises(InvoiceGenerationError):
            # Simulate a failure in invoice generation
            generate_invoice(None)

    def test_invoice_total_calculation(self):
        self.assertEqual(self.invoice.total_amount, self.timesheet.hours_worked * self.timesheet.rate)

if __name__ == '__main__':
    unittest.main()