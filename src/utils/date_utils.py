from datetime import datetime, timedelta

def get_today_date():
    return datetime.now().date()

def format_date(date):
    return date.strftime("%Y-%m-%d")

def calculate_due_date(submission_date, days_until_due):
    return submission_date + timedelta(days=days_until_due)

def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").date()