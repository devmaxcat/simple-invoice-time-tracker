def calculate_total(hours_worked, hourly_rate):
    if hours_worked < 0:
        raise ValueError("Hours worked cannot be negative.")
    if hourly_rate < 0:
        raise ValueError("Hourly rate cannot be negative.")
    return hours_worked * hourly_rate

def format_currency(amount):
    return "${:,.2f}".format(amount)

def calculate_invoice_total(timesheet_entries):
    total_hours = sum(entry['hours'] for entry in timesheet_entries)
    total_rate = sum(entry['rate'] * entry['hours'] for entry in timesheet_entries)
    return total_hours, total_rate

def calculate_due_date(submission_date, days_until_due):
    from datetime import timedelta
    return submission_date + timedelta(days=days_until_due)