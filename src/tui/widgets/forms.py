from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text

class TextInput:
    def __init__(self, label: str, default: str = ""):
        self.label = label
        self.default = default

    def get_input(self) -> str:
        text = Text(self.label, style="bold")
        return Prompt.ask(text, default=self.default)

class NumberInput:
    def __init__(self, label: str, default: float = 0.0):
        self.label = label
        self.default = default

    def get_input(self) -> float:
        while True:
            try:
                value = Prompt.ask(self.label, default=str(self.default))
                return float(value)
            except ValueError:
                Console().print("Invalid input. Please enter a number.", style="bold red")

class DateInput:
    def __init__(self, label: str, default: str = ""):
        self.label = label
        self.default = default

    def get_input(self) -> str:
        return Prompt.ask(self.label, default=self.default)

class Form:
    def __init__(self):
        self.fields = []

    def add_field(self, field):
        self.fields.append(field)

    def collect_data(self):
        data = {}
        for field in self.fields:
            data[field.label] = field.get_input()
        return data

def create_invoice_form():
    form = Form()
    form.add_field(TextInput("Client Name"))
    form.add_field(TextInput("Project Description"))
    form.add_field(NumberInput("Hourly Rate", 18))
    form.add_field(NumberInput("Total Hours Worked"))
    form.add_field(DateInput("Submission Date"))
    form.add_field(DateInput("Due Date"))
    form.add_field(TextInput("Work Notes"))
    return form
