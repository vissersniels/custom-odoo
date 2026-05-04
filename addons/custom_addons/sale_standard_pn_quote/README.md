# Sale Standard PN Quote

## Purpose

This module adds a dedicated quotation flow for Standard PN pricing that is fully separate from normal product lines.

It solves this business need:

- Sales users must be able to quote cable assemblies by Standard PN without creating product records.
- Pricing must still come from cable pricing master data and quantity-tier logic.
- The quotation PDF must show these Standard PN lines and their totals.

## What This Module Adds

### 1) New Standard PN lines on quotation

Model:

- sale.order.standard.pn.line

Each line captures:

- Standard PN string
- Quantity
- Parsed PN metadata (connector key, AC coding, length)
- Tier, factor, purchase price, unit price, subtotal
- Pricing error (if parsing or master data lookup fails)

These lines are linked to sale.order through standard_pn_line_ids.

### 2) New quotation tab in Sales form

View extension:

- adds a notebook page named Standard PN on sale.order form
- located alongside existing notebook pages (including Customer Signature)

The tab includes:

- editable list/form of Standard PN lines
- automatic computed pricing fields
- summary counters and totals

### 3) Quote-level totals for Standard PN flow

Added on sale.order:

- standard_pn_amount_untaxed
- amount_total_with_standard_pn
- standard_pn_line_count
- standard_pn_has_errors

Important:

- Native amount_total remains unchanged.
- Combined total is exposed separately to avoid side effects in standard Odoo accounting/invoicing flows.

### 4) Quotation PDF integration

Report extension:

- Adds a Standard PN section in sale.report_saleorder_document
- Prints Standard PN, Qty, Tier, Unit Price, and Amount
- Prints Standard PN Total and Combined Quote Total in total summary block

## Pricing Workflow (End-to-End)

1. User opens Sales -> Quotations -> New.
2. User goes to Standard PN tab.
3. User adds Standard PN line(s) and quantity.
4. System parses Standard PN format:
   BASE SUFFIX OPTION AC_CODE LENGTH_MM
5. System resolves master data in cable_pricing:
   - cable.connector.price by connector key
   - cable.cable.price by AC coding
6. System calls cable.connector.price.compute_quote_price(...).
7. System stores computed pricing on Standard PN line:
   - purchase price
   - sales factor
   - sales unit price
   - tier
   - subtotal
8. Order-level Standard PN totals are recomputed.
9. Quotation PDF shows Standard PN lines and totals.

## Why This Is Isolated from Product Lines

This module does not modify sale.order.line pricing behavior.

So:

- Existing product-based quoting works as before.
- Standard PN quoting is available in its own tab and data model.
- No product item creation is required for Standard PN quotes.

## Validation and Error Handling

- Quantity must be greater than zero.
- Invalid Standard PN format is flagged on the line.
- Missing connector or cable master data is flagged on the line.
- Error lines keep subtotal at 0.0 and surface clear diagnostic text.

## Dependency Strategy

Depends on:

- sale_management
- cable_pricing

Reason:

- sale_management provides quotation UI and report context.
- cable_pricing provides master pricing tables and compute_quote_price logic.

## Security

Access to Standard PN lines is granted to:

- Sales User
- Sales Manager

Model access file:

- security/ir.model.access.csv

## Test Coverage

Tests included:

- computes line price without product
- invalid PN raises line-level pricing error
- order combined total includes Standard PN subtotal

Test file:

- tests/test_sale_standard_pn_quote.py

## Operational Notes

- This module is quote-focused. It enriches quotation generation and PDF output.
- If future scope requires invoicing or stock operations from Standard PN lines, add a conversion step from Standard PN lines to real sale.order.line products or dedicated service products.
