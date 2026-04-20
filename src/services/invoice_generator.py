from datetime import datetime
import html
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from playwright.sync_api import sync_playwright

from src.models.invoice import Invoice
from src.services.settings import Settings


class InvoiceGenerationError(Exception):
    pass


class InvoiceGenerator:
    def __init__(self, invoice: Invoice, context=None, settings=None):
        self.invoice = invoice
        self.context = context or {}
        self.settings = settings if settings is not None else Settings()
        self.pdf = FPDF()

    def generate_invoice(self, output_dir: str = "invoices") -> Path:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        invoice_file = output_path / f"invoice_{self.invoice.invoice_number}.pdf"

        template_path = str(self.settings.get("pdf_template_path", "")).strip()
        if template_path:
            resolved_template = self._resolve_template_path(template_path)
            if resolved_template is None:
                raise InvoiceGenerationError(f"Template file not found: {template_path}")
            if resolved_template.suffix.lower() not in {".html", ".htm"}:
                raise InvoiceGenerationError(
                    f"Unsupported template format '{resolved_template.suffix}'. "
                    "Use an HTML template (.html/.htm)."
                )
            return self._generate_from_html_template(resolved_template, invoice_file)

        self.pdf.add_page()
        self.pdf.set_font("Helvetica", size=12)

        work_notes = ""
        if self.invoice.timesheet is not None:
            work_notes = getattr(self.invoice.timesheet, "work_notes", "") or ""

        currency_symbol = self.settings.get("currency_symbol", "$")
        invoice_title = self.settings.get("invoice_title", "Invoice")
        contractor_name = self.settings.get("contractor_name", "")
        client_name = self.settings.get("client_name", "")
        project_name = self.settings.get("project_name", "")

        self.pdf.cell(0, 10, text=invoice_title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if contractor_name:
            self.pdf.cell(0, 10, text=f"Business: {contractor_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if client_name:
            self.pdf.cell(0, 10, text=f"Client: {client_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if project_name:
            self.pdf.cell(0, 10, text=f"Project: {project_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.pdf.cell(0, 10, text=f"Invoice Number: {self.invoice.invoice_number}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.pdf.cell(0, 10, text=f"Date: {datetime.now().strftime('%Y-%m-%d')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.pdf.cell(0, 10, text=f"Total Amount: {currency_symbol}{self.invoice.total_amount:.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.pdf.cell(0, 10, text="Work Notes:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.pdf.multi_cell(0, 10, text=work_notes)
        self.pdf.output(str(invoice_file))

        return invoice_file

    def _resolve_template_path(self, template_path):
        raw_path = Path(template_path)
        candidate = raw_path if raw_path.is_absolute() else Path.cwd() / raw_path
        if candidate.exists():
            return candidate

        parent = candidate.parent
        if not parent.exists():
            return None

        target_name = candidate.name.lower()
        for child in parent.iterdir():
            if child.name.lower() == target_name:
                return child
        return None

    def _format_date(self, date_str: str) -> str:
        """Reformat a YYYY-MM-DD string using the configured pdf_date_format."""
        fmt = str(self.settings.get("pdf_date_format", "%m/%d/%Y"))
        try:
            return datetime.strptime(str(date_str), "%Y-%m-%d").strftime(fmt)
        except (ValueError, TypeError):
            return str(date_str)

    def _build_template_data(self):
        timesheet = self.invoice.timesheet
        submission_date = getattr(timesheet, "submission_date", "") if timesheet else ""
        due_date = getattr(timesheet, "due_date", "") if timesheet else ""
        work_notes = getattr(timesheet, "work_notes", "") if timesheet else ""
        hours_worked = float(getattr(timesheet, "hours_worked", 0.0)) if timesheet else 0.0
        hourly_rate = float(getattr(timesheet, "rate", 0.0)) if timesheet else 0.0
        period_start = self._format_date(str(self.context.get("pay_period_range_start", "")))
        period_end = self._format_date(str(self.context.get("pay_period_range_end", "")))
        period_range = f"{period_start} to {period_end}".strip(" to")
        currency_symbol = str(self.settings.get("currency_symbol", "$"))

        data = {
            "invoice_number": str(self.invoice.invoice_number),
            "invoice_date": datetime.now().strftime(str(self.settings.get("pdf_date_format", "%m/%d/%Y"))),
            "submission_date": self._format_date(str(submission_date)),
            "submitted": self._format_date(str(submission_date)),
            "due_date": self._format_date(str(due_date)),
            "days_until_due": str(self.context.get("days_until_due", "")),
            "pay_period_range_start": period_start,
            "pay_period_range_end": period_end,
            "pay_period_start": period_start,
            "pay_period_end": period_end,
            "pay_period_range": period_range,
            "hours_worked": f"{hours_worked:.2f}",
            "hours": f"{hours_worked:.2f}",
            "hourly_rate": f"{hourly_rate:.2f}",
            "rate": f"{hourly_rate:.2f}",
            "total_amount": f"{self.invoice.total_amount:.2f}",
            "amount": f"{self.invoice.total_amount:.2f}",
            "subtotal": f"{self.invoice.total_amount:.2f}",
            "total": f"{self.invoice.total_amount:.2f}",
            "adjustments": str(self.settings.get("adjustments", "0.00")),
            "total_amount_formatted": f"{currency_symbol}{self.invoice.total_amount:.2f}",
            "work_notes": str(work_notes),
            "description": str(work_notes),
            "contractor_name": str(self.settings.get("contractor_name", "")),
            "contract_address_line1": str(self.settings.get("contract_address_line1", "")),
            "contractor_email": str(self.settings.get("contractor_email", "")),
            "contractor_phone": str(self.settings.get("contractor_phone", "")),
            "client_name": str(self.settings.get("client_name", "")),
            "client_address": str(self.settings.get("client_address", "")),
            "project_name": str(self.settings.get("project_name", "")),
            "invoice_title": str(self.settings.get("invoice_title", "Invoice")),
            "currency_symbol": currency_symbol,
        }

        data["contractor_name"] = str(self.settings.get("contractor_name", data["contractor_name"]))
        data["contractor_address_line1"] = str(self.settings.get("contractor_address_line1", data["contract_address_line1"]))
        data["contractor_city"] = str(self.settings.get("contractor_city", ""))
        data["contractor_state"] = str(self.settings.get("contractor_state", ""))
        data["contractor_zip"] = str(self.settings.get("contractor_zip", ""))
        data["contractor_phone"] = str(self.settings.get("contractor_phone", data["contractor_phone"]))
        data["contractor_payable_to"] = str(self.settings.get("contractor_payable_to", data["contractor_name"]))

        data["client_address_line1"] = str(self.settings.get("client_address_line1", data["client_address"]))
        data["client_city"] = str(self.settings.get("client_city", ""))
        data["client_state"] = str(self.settings.get("client_state", ""))
        data["client_zip"] = str(self.settings.get("client_zip", ""))

        return data

    def _normalize_key(self, value):
        return "".join(character.lower() for character in str(value) if character.isalnum())

    def _template_field_values(self, template_fields):
        data = self._build_template_data()
        explicit_map = self.settings.get("pdf_field_map", {})

        normalized_data = {self._normalize_key(key): str(value) for key, value in data.items()}
        values = {}
        for field_name in template_fields:
            if field_name in explicit_map:
                data_key = explicit_map[field_name]
                if data_key in data:
                    values[field_name] = str(data[data_key])
                continue

            normalized_field = self._normalize_key(field_name)
            if normalized_field in normalized_data:
                values[field_name] = normalized_data[normalized_field]
        return values

    def _replace_triple_brace_placeholders(self, template_html, data):
        pattern = re.compile(r"\{\{\{\s*([a-zA-Z0-9_]+)\s*\}\}\}")

        def replacer(match):
            key = match.group(1)
            value = data.get(key, "")
            return html.escape(str(value), quote=False)

        return pattern.sub(replacer, template_html)

    def _inline_css_links(self, template_html, template_dir: Path):
        link_pattern = re.compile(
            r'<link[^>]*rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\'][^>]*>',
            re.IGNORECASE,
        )

        def link_replacer(match):
            href = match.group(1)
            css_path = (template_dir / href).resolve()
            if not css_path.exists():
                return ""
            css_content = css_path.read_text(encoding="utf-8")
            return f"<style>{css_content}</style>"

        return link_pattern.sub(link_replacer, template_html)

    def _parse_length_to_inches(self, value, default_inches=0.4):
        if value is None:
            return default_inches

        text = str(value).strip().lower()
        if not text:
            return default_inches

        try:
            if text.endswith("in"):
                return float(text[:-2])
            if text.endswith("cm"):
                return float(text[:-2]) / 2.54
            if text.endswith("mm"):
                return float(text[:-2]) / 25.4
            if text.endswith("px"):
                return float(text[:-2]) / 96.0
            return float(text)
        except ValueError:
            return default_inches

    def _page_width_inches(self, page_format):
        widths = {
            "letter": 8.5,
            "legal": 8.5,
            "tabloid": 11.0,
            "ledger": 17.0,
            "a0": 33.11,
            "a1": 23.39,
            "a2": 16.54,
            "a3": 11.69,
            "a4": 8.27,
            "a5": 5.83,
            "a6": 4.13,
        }
        return widths.get(str(page_format).strip().lower(), 8.27)

    def _fit_scale_for_page_width(self, page, page_format, margin_left, margin_right):
        content_width_px = page.evaluate(
            """
            () => {
                const headerCells = Array.from(document.querySelectorAll('thead th.column-headers-background'));
                if (headerCells.length > 0) {
                    const sheetWidth = headerCells.reduce((sum, cell) => {
                        const inline = parseFloat((cell.style && cell.style.width) || '0');
                        const measured = cell.getBoundingClientRect().width || 0;
                        const width = inline > 0 ? inline : measured;
                        return sum + (Number.isFinite(width) ? width : 0);
                    }, 0);
                    if (sheetWidth > 0) {
                        return sheetWidth;
                    }
                }

                const waffleTable = document.querySelector('.waffle') || document.querySelector('table');
                if (waffleTable) {
                    const measured = waffleTable.getBoundingClientRect().width || waffleTable.scrollWidth || 0;
                    if (measured > 0) {
                        return measured;
                    }
                }

                const body = document.body;
                return (body && body.scrollWidth) ? body.scrollWidth : 1;
            }
            """
        )

        page_width_inches = self._page_width_inches(page_format)
        left_inches = self._parse_length_to_inches(margin_left)
        right_inches = self._parse_length_to_inches(margin_right)
        printable_width_inches = max(1.0, page_width_inches - left_inches - right_inches)
        printable_width_px = printable_width_inches * 96.0

        content_width_px = float(content_width_px)
        if content_width_px <= printable_width_px:
            return 1.0

        raw_scale = printable_width_px / content_width_px
        clamped_scale = max(0.85, min(1.0, raw_scale))
        return clamped_scale

    def _generate_from_html_template(self, template_path: Path, output_file: Path) -> Path:
        template_html = template_path.read_text(encoding="utf-8")
        template_html = re.sub(r"<meta[^>]*>", "", template_html, flags=re.IGNORECASE)
        template_html = self._inline_css_links(template_html, template_path.parent)
        data = self._build_template_data()
        rendered_html = self._replace_triple_brace_placeholders(template_html, data)

        page_format = str(self.settings.get("pdf_page_format", "A4"))
        margin_top = str(self.settings.get("pdf_margin_top", "0.4in"))
        margin_right = str(self.settings.get("pdf_margin_right", "0.4in"))
        margin_bottom = str(self.settings.get("pdf_margin_bottom", "0.4in"))
        margin_left = str(self.settings.get("pdf_margin_left", "0.4in"))

        with NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as temp_html:
            temp_html.write(rendered_html)
            temp_html_path = Path(temp_html.name)

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                page.goto(temp_html_path.as_uri(), wait_until="networkidle")
                page.emulate_media(media="print")
                fit_scale = self._fit_scale_for_page_width(page, page_format, margin_left, margin_right)
                page.pdf(
                    path=str(output_file),
                    format=page_format,
                    print_background=True,
                    scale=fit_scale,
                    margin={
                        "top": margin_top,
                        "right": margin_right,
                        "bottom": margin_bottom,
                        "left": margin_left,
                    },
                )
                browser.close()
        finally:
            temp_html_path.unlink(missing_ok=True)

        return output_file


def generate_invoice(invoice: Invoice, context=None, settings=None) -> bool:
    if invoice is None:
        raise InvoiceGenerationError("Invoice data is required.")

    try:
        generator = InvoiceGenerator(invoice, context=context, settings=settings)
        generator.generate_invoice()
        return True
    except Exception as exc:
        raise InvoiceGenerationError(f"Failed to generate invoice: {exc}") from exc
