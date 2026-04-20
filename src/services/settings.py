import json
from pathlib import Path


class Settings:
    def __init__(self, settings_file="storage/settings.json"):
        self.settings_path = Path(settings_file)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.defaults = {
            "default_days_until_due": 7,
            "default_rate": 18.0,
            "pdf_template_path": "storage/templates/invoice/Invoice.html",
            "pdf_date_format": "%m/%d/%Y",
            "client_name": "",
            "client_address_line1": "",
            "client_city": "",
            "client_state": "",
            "client_zip": "",
            "contractor_name": "",
            "contractor_address_line1": "",
            "contractor_city": "",
            "contractor_state": "",
            "contractor_zip": "",
            "contractor_phone": "",
            "contractor_email": "",
            "contractor_payable_to": "",
            "project_name": "",
            "invoice_title": "Invoice",
            "currency_symbol": "$",
            "pdf_page_format": "Letter",
            "pdf_margin_top": "0.5in",
            "pdf_margin_right": "0.5in",
            "pdf_margin_bottom": "0.5in",
            "pdf_margin_left": "0.5in",
            "adjustments": "0.00"
        }
        self._settings = self.load_settings()

    def load_settings(self):
        data = {}
        if self.settings_path.exists():
            try:
                with self.settings_path.open("r", encoding="utf-8") as settings_file:
                    loaded = json.load(settings_file)
                    if isinstance(loaded, dict):
                        data = loaded
            except json.JSONDecodeError:
                data = {}

        unknown_keys = set(data.keys()) - set(self.defaults.keys())
        if unknown_keys:
            raise ValueError(f"Unknown keys in settings.json: {', '.join(sorted(unknown_keys))}")

        merged = dict(self.defaults)
        merged.update(data)

        self._settings = merged
        self.save_settings()
        return self._settings

    def save_settings(self):
        with self.settings_path.open("w", encoding="utf-8") as settings_file:
            json.dump(self._settings, settings_file, indent=2)

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def all(self):
        return dict(self._settings)
