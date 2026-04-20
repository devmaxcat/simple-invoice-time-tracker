from datetime import timedelta
from pathlib import Path
import shlex
import subprocess
import sys
import termios
import tty

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from src.models.invoice import Invoice
from src.models.timesheet import Timesheet
from src.services.invoice_generator import generate_invoice
from src.services.settings import Settings
from src.services.storage import Storage
from src.utils.currency import format_currency
from src.utils.date_utils import format_date, get_today_date, is_valid_date, parse_date


class App:
    def __init__(self):
        self.console = Console()
        self.settings = Settings()
        self.storage = Storage()
        self.current_invoice_number = None
        self.pay_period_start_date = get_today_date()
        self.pay_period_length_days = 14
        self.hours_worked = 0.0
        self.hourly_rate = float(self.settings.get("default_rate", 18.0))
        self.submission_date = None
        self.days_until_due = int(self.settings.get("default_days_until_due", 7))
        self.due_date = None
        self.work_notes = ""
        self.is_running = True

    def run(self):
        while self.is_running:
            self.console.clear()
            self.show_start_menu()

    def _supports_arrow_navigation(self):
        return sys.stdin.isatty() and sys.stdout.isatty()

    def _read_key(self):
        file_descriptor = sys.stdin.fileno()
        old_settings = termios.tcgetattr(file_descriptor)
        try:
            tty.setraw(file_descriptor)
            first = sys.stdin.read(1)
            if first in {"\r", "\n"}:
                return "ENTER"
            if first == "\x1b":
                second = sys.stdin.read(1)
                if second == "[":
                    third = sys.stdin.read(1)
                    return {
                        "A": "UP",
                        "B": "DOWN",
                        "C": "RIGHT",
                        "D": "LEFT",
                    }.get(third, "ESC")
                return "ESC"
            return first
        finally:
            termios.tcsetattr(file_descriptor, termios.TCSADRAIN, old_settings)

    def _vertical_padding(self, content_lines: int) -> int:
        """Return number of blank lines to print above content to vertically center it."""
        terminal_height = self.console.size.height
        return max(0, (terminal_height - content_lines) // 2)

    def _arrow_menu_select(self, menu_title, summary_title, options, summary_rows, subtitle, width=76):
        def build_renderable(selected_index):
            menu_table = Table.grid(padding=(0, 2))
            menu_table.add_column(style="bold cyan", justify="right", width=3)
            menu_table.add_column(style="white")
            for index, option in enumerate(options):
                marker = "▶" if index == selected_index else " "
                label_style = "bold black on cyan" if index == selected_index else "white"
                menu_table.add_row(marker, Text(option, style=label_style))

            summary_table = Table.grid(padding=(0, 2))
            summary_table.add_column(style="bold green", justify="right")
            summary_table.add_column(style="white")
            for key, value in summary_rows:
                summary_table.add_row(key, value)

            content = Group(
                Panel(menu_table, title=menu_title, box=box.ROUNDED, border_style="cyan"),
                Panel(summary_table, title=summary_title, box=box.ROUNDED, border_style="green"),
            )

            outer = Panel(
                content,
                title=Text("Simple Time Tracker", style="bold bright_white"),
                subtitle=subtitle,
                box=box.DOUBLE,
                border_style="bright_blue",
                width=width,
            )
            content_height = len(options) + len(summary_rows) + 12
            pad = self._vertical_padding(content_height)
            return Group(Text("\n" * pad), Align.center(outer))

        selected = 0
        with Live(build_renderable(selected), console=self.console, refresh_per_second=20, auto_refresh=False) as live:
            while True:
                key = self._read_key()
                if key == "UP":
                    selected = (selected - 1) % len(options)
                elif key == "DOWN":
                    selected = (selected + 1) % len(options)
                elif key == "ENTER":
                    return selected
                elif key.lower() == "q":
                    return -1
                elif key.isdigit():
                    numeric_index = int(key) - 1
                    if 0 <= numeric_index < len(options):
                        return numeric_index

                live.update(build_renderable(selected), refresh=True)

    def show_start_menu(self):
        if self._supports_arrow_navigation():
            selected = self._arrow_menu_select(
                menu_title="Main Menu",
                summary_title="Invoice Storage",
                options=["Create", "List", "Exit"],
                summary_rows=[
                    ("Saved Invoices", str(len(self.storage.invoices))),
                    ("Next Invoice #", str(self.storage.get_next_invoice_number())),
                ],
                subtitle="↑/↓ navigate • Enter select • 1-3 quick select • q exit",
            )
            if selected == -1:
                selected = 2  # q treated as Exit
            choice = str(selected + 1)
        else:
            choice = Prompt.ask("Selection", choices=["1", "2", "3"])

        if choice == "1":
            self.start_next_invoice()
        elif choice == "2":
            self.open_existing_invoice()
        elif choice == "3":
            self.is_running = False
            self.console.print("Exiting the application. Goodbye!", style="bold green")

    def start_next_invoice(self):
        self.current_invoice_number = self.storage.get_next_invoice_number()
        last_invoice = self._last_invoice_record()

        if last_invoice is not None:
            last_period_end_raw = last_invoice.get("pay_period_range_end")
            if last_period_end_raw and is_valid_date(str(last_period_end_raw)):
                last_period_end = parse_date(str(last_period_end_raw))
            else:
                last_period_end = get_today_date() - timedelta(days=1)
            period_length = self._invoice_period_length_days(last_invoice)
            self.pay_period_start_date = last_period_end + timedelta(days=1)
            self.pay_period_length_days = period_length
        else:
            self.pay_period_start_date = get_today_date()
            self.pay_period_length_days = 14

        period_start, period_end = self._current_period_range()
        self.hours_worked = 0.0
        self.hourly_rate = float(self.settings.get("default_rate", 18.0))
        self.submission_date = None
        self.days_until_due = int(self.settings.get("default_days_until_due", 7))
        self.due_date = None
        self.work_notes = ""
        self.edit_invoice_menu()

    def edit_invoice_menu(self):
        while True:
            period_start, period_end = self._current_period_range()
            if self._supports_arrow_navigation():
                selected = self._arrow_menu_select(
                    menu_title="Invoice Menu",
                    summary_title="Current Draft",
                    options=[
                        "Select Pay Period",
                        "Enter Hours Worked",
                        "Set Hourly Rate",
                        "Set Submitted Date",
                        "Set Days Until Due",
                        "Work Notes",
                        "Preview Invoice",
                        "Save",
                        "Back to Main Menu",
                    ],
                    summary_rows=[
                        ("Invoice #", str(self.current_invoice_number)),
                        ("Period Range", f"{format_date(period_start)} to {format_date(period_end)}"),
                        ("Period Length", f"{self.pay_period_length_days} days"),
                        ("Hours", f"{self.hours_worked:.2f}"),
                        ("Rate", format_currency(self.hourly_rate)),
                        ("Total", format_currency(self.hours_worked * self.hourly_rate)),
                        ("Submission", self._display_date(self.submission_date)),
                        ("Days Until Due", str(self.days_until_due)),
                        ("Due", self._display_date(self.due_date)),
                    ],
                    subtitle="↑/↓ navigate • Enter select • 1-9 quick select",
                )
                if selected == -1:
                    return
                choice = str(selected + 1)
            else:
                choice = Prompt.ask("Selection", choices=[str(i) for i in range(1, 10)])

            if choice == "1":
                self.show_pay_period_screen()
            elif choice == "2":
                self.show_timesheet_entry_screen()
            elif choice == "3":
                self.show_rates_screen()
            elif choice == "4":
                self.show_submission_date_screen()
            elif choice == "5":
                self.show_days_until_due_screen()
            elif choice == "6":
                self.show_work_notes_screen()
            elif choice == "7":
                self.show_invoice_preview_screen()
            elif choice == "8":
                did_save = self.generate_and_save_invoice()
                if did_save:
                    self.open_existing_invoice()
                    return
            elif choice == "9":
                return

    def _pause(self):
        Prompt.ask("Press Enter to continue", default="")

    def _display_date(self, date_value):
        if date_value is None:
            return "-"
        return format_date(date_value)

    def _serialize_date(self, date_value):
        if date_value is None:
            return ""
        return format_date(date_value)

    def _screen_header(self, title, content_lines=10):
        panel = Panel(
            Text(title, style="bold bright_white"),
            border_style="bright_blue",
            box=box.ROUNDED,
            width=76,
        )
        pad = self._vertical_padding(content_lines)
        if pad > 0:
            self.console.print("\n" * pad)
        self.console.print(Align.center(panel))

    def show_pay_period_screen(self):
        self.console.clear()
        self._screen_header("Edit Pay Period", content_lines=12)

        current_start, current_end = self._current_period_range()
        details = Table.grid(padding=(0, 2))
        details.add_column(style="bold cyan", justify="right")
        details.add_column(style="white")
        details.add_row("Current Range", f"{format_date(current_start)} to {format_date(current_end)}")
        details.add_row("Current Length", f"{self.pay_period_length_days} days")
        self.console.print(Align.center(Panel(details, width=76, box=box.ROUNDED, border_style="cyan")))

        while True:
            start_input = Prompt.ask("Start date (YYYY-MM-DD, q to cancel)", default=format_date(self.pay_period_start_date))
            if start_input.strip().lower() == "q":
                return
            if is_valid_date(start_input):
                self.pay_period_start_date = parse_date(start_input)
                break
            self.console.print("Invalid date format. Use YYYY-MM-DD.", style="bold red")

        while True:
            length_input = Prompt.ask("Period length in days (q to cancel)", default=str(self.pay_period_length_days))
            if length_input.strip().lower() == "q":
                return
            try:
                period_length = int(length_input)
                if period_length <= 0:
                    raise ValueError
                self.pay_period_length_days = period_length
                break
            except ValueError:
                self.console.print("Period length must be a positive integer.", style="bold red")

        period_start, period_end = self._current_period_range()
        if self.submission_date is not None and (self.submission_date < period_start or self.submission_date > period_end):
            self.submission_date = period_end
            self.due_date = self.submission_date + timedelta(days=self.days_until_due)

    def show_timesheet_entry_screen(self):
        self.console.clear()
        self._screen_header("Enter Hours Worked")
        while True:
            raw_value = Prompt.ask("Hours worked (q to cancel)", default=f"{self.hours_worked:.2f}")
            if raw_value.strip().lower() == "q":
                return
            try:
                value = float(raw_value)
                if value < 0:
                    raise ValueError
                self.hours_worked = value
                break
            except ValueError:
                self.console.print("Please enter a valid non-negative number.", style="bold red")

    def show_rates_screen(self):
        self.console.clear()
        self._screen_header("Set Hourly Rate")
        while True:
            raw_value = Prompt.ask("Hourly rate (q to cancel)", default=f"{self.hourly_rate:.2f}")
            if raw_value.strip().lower() == "q":
                return
            try:
                value = float(raw_value)
                if value < 0:
                    raise ValueError
                self.hourly_rate = value
                break
            except ValueError:
                self.console.print("Please enter a valid non-negative number.", style="bold red")

    def show_submission_date_screen(self):
        self.console.clear()
        self._screen_header("Set Submitted Date")

        submission_default = self._serialize_date(self.submission_date)

        while True:
            submission_input = Prompt.ask("Submission date (YYYY-MM-DD, blank to clear, q to cancel)", default=submission_default)
            if submission_input.strip().lower() == "q":
                return
            if not submission_input.strip():
                self.submission_date = None
                self.due_date = None
                return
            if is_valid_date(submission_input):
                self.submission_date = parse_date(submission_input)
                self.due_date = self.submission_date + timedelta(days=self.days_until_due)
                break
            self.console.print("Invalid date format. Use YYYY-MM-DD.", style="bold red")

    def show_days_until_due_screen(self):
        self.console.clear()
        self._screen_header("Set Days Until Due")

        while True:
            days_input = Prompt.ask("Days until due (q to cancel)", default=str(self.days_until_due))
            if days_input.strip().lower() == "q":
                return
            try:
                days_until_due = int(days_input)
                if days_until_due <= 0:
                    raise ValueError
                self.days_until_due = days_until_due
                if self.submission_date is not None:
                    self.due_date = self.submission_date + timedelta(days=self.days_until_due)
                break
            except ValueError:
                self.console.print("Days until due must be a positive integer.", style="bold red")

    def show_work_notes_screen(self):
        self.console.clear()
        self._screen_header("Work Notes", content_lines=12)
        default_text = self.work_notes if self.work_notes else "No notes yet"
        self.console.print(Align.center(Panel(default_text, title="Current Notes", width=76, border_style="magenta")))
        notes = Prompt.ask("Enter notes (q to cancel)", default=self.work_notes)
        if notes.strip().lower() == "q":
            return
        self.work_notes = notes.strip()

    def _next_invoice_number(self):
        return self.storage.get_next_invoice_number()

    def _current_period_range(self):
        period_start = self.pay_period_start_date
        period_end = period_start + timedelta(days=self.pay_period_length_days - 1)
        return period_start, period_end

    def _last_invoice_record(self):
        invoices = self._sorted_invoices()
        return invoices[-1] if invoices else None

    def _invoice_period_length_days(self, invoice_record):
        cycle_value = invoice_record.get("pay_period_cycle_days")
        if cycle_value is not None:
            try:
                cycle_days = int(cycle_value)
                if cycle_days > 0:
                    return cycle_days
            except (TypeError, ValueError):
                pass

        range_start = invoice_record.get("pay_period_range_start")
        range_end = invoice_record.get("pay_period_range_end")
        if range_start and range_end and is_valid_date(range_start) and is_valid_date(range_end):
            start_date = parse_date(range_start)
            end_date = parse_date(range_end)
            days = (end_date - start_date).days + 1
            if days > 0:
                return days

        return 14

    def _load_invoice_record_for_edit(self, invoice_record):
        self.current_invoice_number = int(invoice_record.get("invoice_number", self.storage.get_next_invoice_number()))

        period_start_raw = str(invoice_record.get("pay_period_range_start", ""))
        if is_valid_date(period_start_raw):
            self.pay_period_start_date = parse_date(period_start_raw)
        else:
            self.pay_period_start_date = get_today_date()

        self.pay_period_length_days = self._invoice_period_length_days(invoice_record)

        self.hours_worked = float(invoice_record.get("hours_worked", 0.0))
        self.hourly_rate = float(invoice_record.get("hourly_rate", self.settings.get("default_rate", 18.0)))

        submission_raw = str(invoice_record.get("submission_date", ""))
        if is_valid_date(submission_raw):
            self.submission_date = parse_date(submission_raw)
        else:
            self.submission_date = None

        days_until_due = invoice_record.get("days_until_due", self.settings.get("default_days_until_due", 7))
        try:
            parsed_days_until_due = int(days_until_due)
            self.days_until_due = parsed_days_until_due if parsed_days_until_due > 0 else 7
        except (TypeError, ValueError):
            self.days_until_due = int(self.settings.get("default_days_until_due", 7))

        due_raw = str(invoice_record.get("due_date", ""))
        if is_valid_date(due_raw):
            self.due_date = parse_date(due_raw)
        else:
            if self.submission_date is not None:
                self.due_date = self.submission_date + timedelta(days=self.days_until_due)
            else:
                self.due_date = None

        self.work_notes = str(invoice_record.get("work_notes", ""))

    def _build_invoice(self):
        timesheet = Timesheet(
            hours_worked=self.hours_worked,
            rate=self.hourly_rate,
            submission_date=self._serialize_date(self.submission_date),
            due_date=self._serialize_date(self.due_date),
            work_notes=self.work_notes,
        )
        return Invoice(
            invoice_number=self.current_invoice_number,
            total_amount=timesheet.calculate_total(),
            associated_timesheet=timesheet,
        )

    def show_invoice_preview_screen(self):
        self.console.clear()
        self._screen_header("Invoice Preview")

        invoice = self._build_invoice()
        period_start, period_end = self._current_period_range()
        preview = Table.grid(padding=(0, 2))
        preview.add_column(style="bold green", justify="right")
        preview.add_column(style="white")
        preview.add_row("Invoice #", str(invoice.invoice_number))
        preview.add_row("Period Range", f"{format_date(period_start)} to {format_date(period_end)}")
        preview.add_row("Period Length", f"{self.pay_period_length_days} days")
        preview.add_row("Hours", f"{self.hours_worked:.2f}")
        preview.add_row("Rate", format_currency(self.hourly_rate))
        preview.add_row("Total", format_currency(invoice.total_amount))
        preview.add_row("Submission", self._display_date(self.submission_date))
        preview.add_row("Days Until Due", str(self.days_until_due))
        preview.add_row("Due", self._display_date(self.due_date))
        preview.add_row("Notes", self.work_notes or "-")

        self.console.print(Align.center(Panel(preview, width=76, border_style="green", box=box.ROUNDED)))
        self._pause()

    def _build_invoice_record(self, invoice):
        period_start, period_end = self._current_period_range()
        return {
            "invoice_number": invoice.invoice_number,
            "pay_period_cycle_days": self.pay_period_length_days,
            "pay_period_range_start": format_date(period_start),
            "pay_period_range_end": format_date(period_end),
            "hours_worked": self.hours_worked,
            "hourly_rate": self.hourly_rate,
            "total_amount": invoice.total_amount,
            "submission_date": self._serialize_date(self.submission_date),
            "days_until_due": self.days_until_due,
            "due_date": self._serialize_date(self.due_date),
            "work_notes": self.work_notes,
        }

    def _sorted_invoices(self):
        return sorted(self.storage.invoices, key=lambda item: int(item.get("invoice_number", 0)))

    def _invoice_list_table(self, invoices, selected_index=None):
        table = Table(box=box.SIMPLE_HEAVY, expand=False)
        table.add_column("", justify="center", style="bold cyan", no_wrap=True)
        table.add_column("Invoice #", justify="right", style="bold")
        table.add_column("Period Range", style="white")
        table.add_column("Total", justify="right", style="bold green")

        for index, invoice in enumerate(invoices):
            is_selected = selected_index is not None and index == selected_index
            marker = "▶" if is_selected else " "
            number = str(invoice.get("invoice_number", "-"))
            period_range = f"{invoice.get('pay_period_range_start', '-')} to {invoice.get('pay_period_range_end', '-')}"
            total = format_currency(float(invoice.get("total_amount", 0.0)))

            if is_selected:
                number = f"[black on cyan]{number}[/black on cyan]"
                period_range = f"[black on cyan]{period_range}[/black on cyan]"
                total = f"[black on cyan]{total}[/black on cyan]"

            table.add_row(marker, number, period_range, total)

        return table

    def _pick_existing_invoice(self):
        invoices = self._sorted_invoices()
        if not invoices:
            self.console.print(Align.center(Panel("No saved invoices yet.", width=76, border_style="yellow")))
            self._pause()
            return None

        if not self._supports_arrow_navigation():
            self.console.print(Align.center(Panel(self._invoice_list_table(invoices), width=100, border_style="green")))
            number_input = Prompt.ask("Invoice number")
            try:
                target = int(number_input)
            except ValueError:
                self.console.print(Align.center(Panel("Invoice number must be an integer.", width=76, border_style="red")))
                self._pause()
                return None

            for invoice in invoices:
                if int(invoice.get("invoice_number", 0)) == target:
                    return invoice

            self.console.print(Align.center(Panel(f"Invoice #{target} not found.", width=76, border_style="red")))
            self._pause()
            return None

        def build_renderable(selected_index, number_buffer, message):
            controls = "↑/↓ navigate • Enter open • type invoice # then Enter • Backspace edit • q back"
            if number_buffer:
                controls = f"{controls}\nTyped number: {number_buffer}"
            if message:
                controls = f"{controls}\n{message}"

            content = Group(
                Panel(Text("Open Existing Invoice", style="bold bright_white"), border_style="bright_blue", box=box.ROUNDED, width=100),
                Panel(self._invoice_list_table(invoices, selected_index), width=100, border_style="green"),
                Panel(controls, width=100, border_style="cyan", box=box.SIMPLE),
            )
            content_height = len(invoices) + 14
            pad = self._vertical_padding(content_height)
            return Group(Text("\n" * pad), Align.center(content))

        selected_index = 0
        number_buffer = ""
        message = ""

        with Live(build_renderable(selected_index, number_buffer, message), console=self.console, refresh_per_second=20, auto_refresh=False) as live:
            while True:
                key = self._read_key()
                message = ""

                if key == "UP":
                    selected_index = (selected_index - 1) % len(invoices)
                elif key == "DOWN":
                    selected_index = (selected_index + 1) % len(invoices)
                elif key == "ENTER":
                    if number_buffer:
                        target = int(number_buffer)
                        number_buffer = ""
                        for invoice in invoices:
                            if int(invoice.get("invoice_number", 0)) == target:
                                return invoice
                        message = f"Invoice #{target} not found."
                    else:
                        return invoices[selected_index]
                elif key in {"\x7f", "\b"}:
                    number_buffer = number_buffer[:-1]
                elif key.isdigit():
                    number_buffer += key
                elif key.lower() == "q":
                    return None

                live.update(build_renderable(selected_index, number_buffer, message), refresh=True)

    def _open_pdf(self, pdf_path):
        pdf_file = Path(str(pdf_path)).expanduser()
        if not pdf_file.is_absolute():
            pdf_file = Path.cwd() / pdf_file

        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_file}")

        opener_setting = str(self.settings.get("pdf_open_command", "xdg-open")).strip()
        if not opener_setting:
            opener_setting = "xdg-open"

        if "{pdf}" in opener_setting:
            command = shlex.split(opener_setting.replace("{pdf}", str(pdf_file)))
        else:
            command = shlex.split(opener_setting) + [str(pdf_file)]

        if not command:
            raise ValueError("Invalid pdf_open_command setting.")

        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def generate_and_save_invoice(self):
        self.console.clear()
        self._screen_header("Save Invoice")
        invoice = self._build_invoice()

        try:
            invoice_record = self._build_invoice_record(invoice)
            pdf_path = generate_invoice(invoice, context=invoice_record, settings=self.settings)
            invoice_record["pdf_path"] = str(pdf_path)
            self.storage.add_or_update_invoice(invoice_record)
            self.storage.invoices = self.storage.load_invoices()
            self.console.print(
                Align.center(
                    Panel(
                        f"Invoice #{invoice.invoice_number} saved and generated in ./invoices",
                        width=76,
                        border_style="green",
                        box=box.ROUNDED,
                    )
                )
            )
            return True
        except Exception as error:
            self.console.print(
                Align.center(
                    Panel(
                        f"Failed to generate invoice: {error}",
                        width=76,
                        border_style="red",
                        box=box.ROUNDED,
                    )
                )
            )
            self._pause()
            return False

    def open_existing_invoice(self):
        invoice_record = self._pick_existing_invoice()
        if invoice_record is None:
            return

        self.show_saved_invoice(invoice_record)

    def show_saved_invoice(self, invoice_record):
        while True:
            self.console.clear()
            self._screen_header(f"Saved Invoice #{invoice_record['invoice_number']}")

            details = Table.grid(padding=(0, 2))
            details.add_column(style="bold green", justify="right")
            details.add_column(style="white")
            details.add_row(
                "Period Range",
                f"{invoice_record.get('pay_period_range_start', '-')} to {invoice_record.get('pay_period_range_end', '-')}",
            )
            details.add_row("Hours", f"{float(invoice_record.get('hours_worked', 0.0)):.2f}")
            details.add_row("Rate", format_currency(float(invoice_record.get("hourly_rate", 0.0))))
            details.add_row("Total", format_currency(float(invoice_record.get("total_amount", 0.0))))
            details.add_row("Submission", invoice_record.get("submission_date", "-"))
            details.add_row("Due", invoice_record.get("due_date", "-"))
            details.add_row("Notes", invoice_record.get("work_notes") or "-")
            details.add_row("PDF", invoice_record.get("pdf_path", "-"))

            self.console.print(Align.center(Panel(details, width=76, border_style="green", box=box.ROUNDED)))
            if self._supports_arrow_navigation():
                action_index = self._arrow_menu_select(
                    menu_title="Actions",
                    summary_title="Tip",
                    options=["Edit Invoice", "View PDF", "Regenerate PDF", "Back"],
                    summary_rows=[("Navigation", "↑/↓ then Enter")],
                    subtitle="Action menu • q back",
                    width=60,
                )
                if action_index == -1:
                    return
                if action_index == 0:
                    choice = "e"
                elif action_index == 1:
                    choice = "v"
                elif action_index == 2:
                    choice = "r"
                else:
                    choice = "b"
            else:
                self.console.print(Align.center(Panel("[E]dit Invoice  [V]iew PDF  [R]egenerate PDF  [B]ack", width=76, border_style="cyan", box=box.SIMPLE)))
                choice = Prompt.ask("Action", choices=["e", "v", "r", "b", "q"], default="b")

            if choice in {"b", "q"}:
                return

            if choice == "e":
                self._load_invoice_record_for_edit(invoice_record)
                self.edit_invoice_menu()
                latest_record = self.storage.get_invoice_by_number(int(invoice_record["invoice_number"]))
                if latest_record is not None:
                    invoice_record = latest_record
                continue

            if choice == "v":
                try:
                    self._open_pdf(invoice_record.get("pdf_path", ""))
                    self.console.print(Align.center(Panel("Opening PDF...", width=76, border_style="green")))
                except Exception as error:
                    self.console.print(Align.center(Panel(f"Failed to open PDF: {error}", width=76, border_style="red")))
                self._pause()
                continue

            timesheet = Timesheet(
                hours_worked=float(invoice_record.get("hours_worked", 0.0)),
                rate=float(invoice_record.get("hourly_rate", 0.0)),
                submission_date=invoice_record.get("submission_date"),
                due_date=invoice_record.get("due_date"),
                work_notes=invoice_record.get("work_notes", ""),
            )
            invoice = Invoice(
                invoice_number=int(invoice_record["invoice_number"]),
                total_amount=float(invoice_record.get("total_amount", 0.0)),
                associated_timesheet=timesheet,
            )

            try:
                pdf_path = generate_invoice(invoice, context=invoice_record, settings=self.settings)
                invoice_record["pdf_path"] = str(pdf_path)
                self.storage.add_or_update_invoice(invoice_record)
                self.console.print(Align.center(Panel("PDF regenerated successfully.", width=76, border_style="green")))
            except Exception as error:
                self.console.print(Align.center(Panel(f"Failed to regenerate PDF: {error}", width=76, border_style="red")))
            self._pause()


if __name__ == "__main__":
    app = App()
    app.run()