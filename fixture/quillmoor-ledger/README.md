# LedgerLoop

LedgerLoop is the invoicing and payments platform of **Quillmoor Ledger Ltd**,
a FICTIONAL B2B SaaS company created for a code-review demonstration.
No real company, customer, credential or service is represented here.

## Components

- `ledgerloop/` - Flask API (invoices, auth, payments, exports, reports)
- `web/` - dashboard front end (vanilla JS + Jinja templates)

## Running locally

    pip install -r requirements.txt
    flask --app ledgerloop.app run
