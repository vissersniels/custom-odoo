# Order Ingestion Agent

A Python pipeline that reads purchase order emails, extracts data from PDF attachments, and automatically creates purchase order records in Odoo 18.

---

## What it does

Many suppliers send purchase orders as PDF attachments by email. Processing these manually — opening each email, reading the PDF, and keying the data into Odoo — is repetitive, error-prone, and slow.

This agent automates that entire flow:

1. **Reads saved emails** from a local folder of `.eml` files
2. **Detects PDF attachments** and extracts their text content
3. **Parses the order data** — order reference, date, partner, line items, totals
4. **Validates and maps** the extracted fields to Odoo's data model
5. **Creates a purchase order** in Odoo 18 via the XML-RPC API
6. **Attaches the original PDF** to the created record for traceability
7. **Logs every step** to an append-only audit log

Emails that have already been processed are tracked by their `message-id` header and skipped on subsequent runs, preventing duplicate records.

---

## Current stage

This is **Phase 1** — a working foundation built around local `.eml` files rather than a live inbox. The pipeline is intentionally structured so that the email source can be swapped out for a live IMAP or Microsoft 365 connection later without changing anything else.

```
Phase 1 (now)   →   read from sample_emails/ folder
Phase 2         →   connect to live IMAP or M365 inbox
Phase 3         →   add AI/LLM parsing for variable PDF layouts
```

---

## Project structure

```
order_agent/
├── sample_emails/           # place your .eml files here
├── main.py                  # entry point — processes all unprocessed .eml files
├── config.py                # loads .env, exposes typed config object
├── eml_reader.py            # parses .eml files and extracts PDF attachments
├── pdf_extractor.py         # extracts raw text from PDF bytes (pdfplumber)
├── field_parser.py          # regex-based field extraction from raw text
├── odoo_client.py           # XML-RPC wrapper for Odoo 18 operations
├── audit_log.py             # structured append-only JSON lines logger
├── models.py                # pydantic data models
├── processed_emails.json    # tracks which emails have already been processed
├── audit.log                # audit trail (generated at runtime)
├── .env                     # local credentials (not committed to git)
└── .env.example             # template for required environment variables
```

---

## Requirements

- Python 3.11+
- A running Odoo 18.0 instance (local or remote)
- An Odoo API key (Settings → Users → your user → API Keys)
- One or more `.eml` files to test with

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your Odoo credentials:

```
ODOO_URL=http://localhost:8069
ODOO_DB=your_database
ODOO_USERNAME=your@email.com
ODOO_API_KEY=your_api_key

SAMPLE_EMAILS_DIR=sample_emails
LOG_FILE=audit.log
PROCESSED_EMAILS_FILE=processed_emails.json
```

No email server credentials are needed for Phase 1.

---

## Running the agent

Drop your `.eml` files into the `sample_emails/` folder, then run:

```bash
python main.py
```

The agent scans the folder, skips any files it has already processed, and prints a summary when done:

```
Processing complete: 3 emails read — 2 orders written to Odoo, 1 failed (see audit.log)
```

Run it again at any time — already-processed files are safely skipped.

---

## Audit log

Every step is recorded in `audit.log` as structured JSON lines. Each entry includes a `processing_id` (UUID per email), a `stage`, and relevant context:

```json
{"timestamp": "2026-09-04T09:12:33Z", "processing_id": "a1b2c3...", "stage": "ODOO_WRITTEN", "odoo_record_id": 42, "partner": "Acme NV", "order_ref": "PO-2026-0091"}
{"timestamp": "2026-09-04T09:12:35Z", "processing_id": "d4e5f6...", "stage": "FAILED", "reason": "Partner not found in Odoo", "source_file": "order_002.eml"}
```

Possible stages:

| Stage               | Meaning                                         |
| ------------------- | ----------------------------------------------- |
| `EML_READ`          | .eml file parsed, attachments identified        |
| `PDF_EXTRACTED`     | text extracted from PDF                         |
| `FIELDS_PARSED`     | order fields extracted from text                |
| `ODOO_WRITTEN`      | purchase order created in Odoo                  |
| `SKIPPED_DUPLICATE` | email already processed in a previous run       |
| `FAILED`            | processing stopped at this stage — see `reason` |

---

## Current limitations (Phase 1)

- **Local files only** — no live email inbox connection yet (IMAP / M365 comes next)
- **Text-native PDFs only** — scanned or image-based PDFs are not yet handled (no OCR)
- **Regex-based parsing** — field extraction works best with consistent PDF layouts; AI/LLM parsing is planned for Phase 3
- **No human review UI** — orders that fail validation are logged but require manual follow-up
- **No task queue** — the agent runs as a one-shot script; background scheduling is not yet built in

---

## Tech stack

| Purpose         | Library                  |
| --------------- | ------------------------ |
| Email parsing   | `email` (stdlib)         |
| File system     | `pathlib` (stdlib)       |
| PDF extraction  | `pdfplumber`             |
| Data validation | `pydantic` v2            |
| Odoo API        | `xmlrpc.client` (stdlib) |
| Logging         | `structlog`              |
| Configuration   | `python-dotenv`          |