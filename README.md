# Simple Time Tracker

A command line TUI application for timekeeping that generates invoices based on user input. This application allows users to manage their work hours, rates, and generate invoices efficiently.

## Features

- **Pay Period Selection**: Users can select their pay periods using arrow keys.
- **Timesheet Entry**: Enter total hours worked with input validation.
- **Edit Timesheet**: Enter daily clock-in/clock-out and optional lunch minutes for each day in the pay period; hours are calculated automatically.
- **Optional Live Clocking**: For in-progress pay periods, use clock in/clock out and set lunch break minutes from the main invoice edit menu.
- **Rate Management**: Adjust hourly rates, defaulting to $18.
- **Date Management**: Set submission and due dates, with the submission date defaulting to today.
- **Work Notes**: Enter freeform notes related to work done.
- **Invoice Preview**: View a preview of the generated invoice based on user inputs.
- **Auto-Calculation**: Automatically calculate totals based on hours worked and rates.

## Project Structure

```
simple-time-tracker
├── src
│   ├── main.py
│   ├── tui
│   │   ├── app.py
│   │   ├── screens
│   │   │   ├── pay_period.py
│   │   │   ├── timesheet_entry.py
│   │   │   ├── rates.py
│   │   │   ├── dates.py
│   │   │   ├── work_notes.py
│   │   │   └── invoice_preview.py
│   │   └── widgets
│   │       └── forms.py
│   ├── models
│   │   ├── timesheet.py
│   │   ├── invoice.py
│   │   └── rate.py
│   ├── services
│   │   ├── calculator.py
│   │   ├── invoice_generator.py
│   │   └── storage.py
│   └── utils
│       ├── date_utils.py
│       └── currency.py
├── tests
│   ├── test_calculator.py
│   └── test_invoice_generator.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/devmaxcat/simple-time-tracker.git
   ```
2. Navigate to the project directory:
   ```
   cd simple-time-tracker
   ```
3. Create and activate a virtual environment:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the application, execute the following command:
```
python3 -m src.main
```

Follow the on-screen instructions to navigate through the TUI and manage your timekeeping and invoicing needs.

Main flow:
- From the main menu, choose **Create Next Invoice** or **Open Existing Invoice**.
- In interactive terminals, use **↑ / ↓** to navigate menus and **Enter** to select.
- In **Edit Pay Period**, set the **start date** and **period length (days)** directly.
- When creating the next invoice, the app defaults to the **same period length** as the last saved invoice and starts on the **day after the last period ends**.
- Use **Set Submitted Date** to set the submission date.
- Use **Set Days Until Due** to control due date offset (defaults to **7** for new invoices).
- Due date is always calculated as: **submitted date + days until due**.
- Use **Set Hours** for direct total-hour entry, or **Edit Timesheet** to enter daily in/out/lunch and auto-calculate invoice hours.
- In **Edit Timesheet**, use **↑ / ↓** to choose a day and **Enter** to edit that day quickly.
- Timesheet edits are saved under the invoice `timesheet` key in `storage/invoices.json`, and total hours are recalculated when you finish editing.
- When a pay period is currently in progress, the main invoice menu shows context-aware clock actions:
   - if not clocked in: **Clock In (Now)**
   - if clocked in: **Clock Out (Now)** and **Lunch Break**
- In **Open Existing Invoice**, browse a table of saved invoices with **↑ / ↓**, then press **Enter**.
- In that same invoice list, you can type an invoice number directly and press **Enter** as a shortcut.
- In non-interactive/scripted runs, numeric and letter prompt input still works.
- Use **Save + Generate PDF** to write both the PDF and invoice metadata to disk.

Saved files:
- PDFs: `invoices/invoice_<number>.pdf`
- Metadata: `storage/invoices.json`

## Settings

Application-wide settings are loaded from `storage/settings.json` and are available throughout the app.

Key settings:
- `default_rate`: default hourly rate for new invoices
- `default_days_until_due`: default day offset for due dates


## PDF Template Replacement

If you imported a PDF template, set `pdf_template_path` in `storage/settings.json`.

- `pdf_template_path` should point to an HTML template (`.html`/`.htm`).
- HTML templates are rendered to PDF using **Playwright + Chromium** for high-fidelity CSS/layout output.
- If a setting/invoice field is missing, settings values are used as fallbacks where applicable.
- If no template is configured, the app falls back to built-in PDF generation.

First-time setup for renderer:

```bash
pip install -r requirements.txt
playwright install chromium
```

Template placeholders:
- The template supports triple-brace placeholders such as `{{{invoice_number}}}`.
- Example path in this project: `storage/templates/invoice/Invoice.html`.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.