# Order Ingestion Agent

An intelligent pipeline that monitors an email inbox for incoming purchase orders, extracts and interprets the order data from PDF attachments, and automatically creates the corresponding records in Odoo 18.

---

## What it does

Many suppliers send purchase orders as PDF attachments by email. Processing these manually — opening each email, reading the PDF, and entering the data into Odoo — is repetitive, error-prone, and slow.

This agent automates that entire flow:

1. **Monitors a mailbox** for new incoming emails via IMAP
2. **Detects PDF attachments** and extracts their text content
3. **Parses the order data** — order reference, date, partner, line items, totals
4. **Validates and maps** the extracted fields to Odoo's data model
5. **Creates a purchase order** in Odoo 18 via the XML-RPC API
6. **Attaches the original PDF** to the created record for traceability
7. **Logs every step** to an append-only audit log

Emails that have already been processed are tracked and skipped on subsequent runs, preventing duplicate records.

---

## Project structure

```
order_agent/
├── main.py                  # Entry point — runs one polling cycle
├── config.py                # Loads .env and exposes typed config
├── email_listener.py        # IMAP connection, email fetch, mark-as-processed
├── pdf_extractor.py         # Extracts raw text from PDF bytes (pdfplumber)
├── field_parser.py          # Parses order fields from extracted text
├── odoo_client.py           # XML-RPC wrapper for Odoo 18 operations
├── audit_log.py             # Structured append-only JSON lines logger
├── models.py                # Pydantic data models
├── processed_emails.json    # Local record of processed message UIDs
├── audit.log                # Audit trail (generated at runtime)
├── .env                     # Local credentials (not committed)
└── .env.example             # Template for required environment variables
```

---

## Requirements

- Python 3.11+
- A running Odoo 18.0 instance (local or remote)
- An IMAP-accessible email mailbox
- An Odoo API key (generated under Settings → Users → API Keys)

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```
ODOO_URL=http://localhost:8069
ODOO_DB=your_database
ODOO_USERNAME=your@email.com
ODOO_API_KEY=your_api_key

IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USERNAME=your@email.com
IMAP_PASSWORD=your_password
IMAP_INBOX_FOLDER=INBOX
IMAP_PROCESSED_FOLDER=INBOX/Processed
```

> **Before running:** make sure the `IMAP_PROCESSED_FOLDER` folder already exists in your mailbox. The agent will move emails there after processing.

---

## Running the agent

```bash
python main.py
```

Each run fetches all unprocessed emails from the inbox, attempts to process each one, and prints a summary:

```
Processing complete: 3 emails processed — 2 written to Odoo, 1 failed (see audit.log)
```

Schedule it via cron or a task scheduler to run at a regular interval (e.g. every 5 minutes).

---

## Audit log

Every step is recorded in `audit.log` as structured JSON lines. Each entry includes a `processing_id` (UUID per email), a `stage`, and relevant context:

```json
{"timestamp": "2026-09-04T09:12:33Z", "processing_id": "a1b2c3...", "stage": "ODOO_WRITTEN", "odoo_record_id": 42, "partner": "Acme NV", "order_ref": "PO-2026-0091"}
{"timestamp": "2026-09-04T09:12:35Z", "processing_id": "d4e5f6...", "stage": "FAILED", "reason": "Partner not found in Odoo", "email_subject": "Order confirmation #1042"}
```

---

## Current limitations (Phase 1)

This is the foundation release. The following are not yet implemented and are planned for later phases:

- **AI/LLM parsing** — field extraction is currently regex-based and works best with consistent PDF layouts
- **OCR support** — scanned or image-based PDFs are not yet handled
- **Microsoft 365 / Graph API** — only IMAP is supported
- **Human review queue** — orders that fail validation are logged but require manual follow-up in Odoo
- **Task queue / scheduling** — the agent runs as a one-shot script; background scheduling is not yet built in

---

## Tech stack

| Purpose         | Library                     |
| --------------- | --------------------------- |
| Email (IMAP)    | `imaplib`, `email` (stdlib) |
| PDF extraction  | `pdfplumber`                |
| Data validation | `pydantic` v2               |
| Odoo API        | `xmlrpc.client` (stdlib)    |
| Logging         | `structlog`                 |
| Configuration   | `python-dotenv`             |