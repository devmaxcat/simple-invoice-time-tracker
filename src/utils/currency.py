def format_currency(amount, currency_symbol="$"):
    """Format a number as currency."""
    return f"{currency_symbol}{amount:,.2f}"

def convert_currency(amount, conversion_rate):
    """Convert an amount to another currency based on the conversion rate."""
    return amount * conversion_rate

def parse_currency(currency_string):
    """Parse a currency string and return the numeric value."""
    try:
        return float(currency_string.replace("$", "").replace(",", ""))
    except ValueError:
        return 0.0