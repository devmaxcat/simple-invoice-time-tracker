import json
from pathlib import Path

from src.models.invoice import Invoice
from src.models.timesheet import Timesheet
from src.services.invoice_generator import generate_invoice
from src.services.settings import Settings


class Storage:
    def __init__(self, storage_file="storage/invoices.json", legacy_storage_file="invoices/invoices.json"):
        self.storage_path = Path(storage_file)
        self.legacy_storage_path = Path(legacy_storage_file)
        self.settings = Settings()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_storage_if_needed()
        self.invoices = self.load_invoices()

    def _migrate_legacy_storage_if_needed(self):
        if self.storage_path.exists() or not self.legacy_storage_path.exists():
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.legacy_storage_path.replace(self.storage_path)
        except OSError:
            with self.legacy_storage_path.open("r", encoding="utf-8") as source_file:
                contents = source_file.read()
            with self.storage_path.open("w", encoding="utf-8") as destination_file:
                destination_file.write(contents)

    def load_invoices(self):
        try:
            with self.storage_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
                if isinstance(data, list):
                    return data
                return []
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_invoices(self):
        with self.storage_path.open("w", encoding="utf-8") as file:
            json.dump(self.invoices, file, indent=2)

    def get_next_invoice_number(self):
        if not self.invoices:
            return 1
        return max(int(invoice["invoice_number"]) for invoice in self.invoices) + 1

    def _invoice_without_pdf_path(self, invoice_record):
        normalized = dict(invoice_record)
        normalized.pop("pdf_path", None)
        return normalized

    def _build_invoice_from_record(self, invoice_record):
        timesheet = Timesheet(
            hours_worked=float(invoice_record.get("hours_worked", 0.0)),
            rate=float(invoice_record.get("hourly_rate", 0.0)),
            submission_date=invoice_record.get("submission_date"),
            due_date=invoice_record.get("due_date"),
            work_notes=invoice_record.get("work_notes", ""),
        )
        total_amount = float(invoice_record.get("total_amount", timesheet.calculate_total()))
        return Invoice(
            invoice_number=int(invoice_record["invoice_number"]),
            total_amount=total_amount,
            associated_timesheet=timesheet,
        )

    def _regenerate_pdf(self, invoice_record):
        invoice = self._build_invoice_from_record(invoice_record)
        generate_invoice(invoice, context=invoice_record, settings=self.settings)
        invoice_record["pdf_path"] = str(Path("invoices") / f"invoice_{invoice.invoice_number}.pdf")

    def _has_generated_pdf(self, invoice_record):
        pdf_path = invoice_record.get("pdf_path")
        if not pdf_path:
            return False
        return Path(pdf_path).exists()

    def add_or_update_invoice(self, invoice_record):
        invoice_number = int(invoice_record["invoice_number"])
        incoming_record = dict(invoice_record)

        for index, existing in enumerate(self.invoices):
            if int(existing["invoice_number"]) == invoice_number:
                has_changed = self._invoice_without_pdf_path(existing) != self._invoice_without_pdf_path(incoming_record)
                updated_record = dict(incoming_record)

                if has_changed:
                    if not self._has_generated_pdf(updated_record):
                        self._regenerate_pdf(updated_record)
                elif "pdf_path" not in updated_record and "pdf_path" in existing:
                    updated_record["pdf_path"] = existing["pdf_path"]

                self.invoices[index] = updated_record
                self.save_invoices()
                return

        self.invoices.append(incoming_record)
        self.save_invoices()

    def add_invoice(self, invoice):
        self.add_or_update_invoice(invoice)

    def get_invoice_by_number(self, invoice_number):
        target = int(invoice_number)
        for invoice in self.invoices:
            if int(invoice.get("invoice_number", 0)) == target:
                return invoice
        return None