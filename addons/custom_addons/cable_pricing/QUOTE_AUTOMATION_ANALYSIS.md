# Cable Quote Automation - Deep Analysis

## Scope and Intent

This document explains, in depth, the changes made to automate quotation line pricing in the cable_pricing module, with special focus on the test evolution and the end-to-end workflow used when creating a quotation.

Branch context:
- Branch: automatic-quotes-for-standard-items
- Relevant module: addons/custom_addons/cable_pricing
- Relevant commits:
  - 342d10d15221 - Implement three pricing models and tier lookup methods
  - 38c28c4e2e9c - Implement test data plus UI in Sales -> New Quotation for testing

## What Changed, Exactly

### Commit 1 (342d10d15221): Pricing Engine Foundation

The first commit introduced the pricing domain models and core calculation logic:

- Model 1: cable.connector.price
  - Holds connector unit prices per quantity range (1-49, 50-299, etc.).
  - Implements tier selection by quantity via _get_price_at_qty.

- Model 2: cable.cable.price
  - Holds cable meter price per AC coding (for example A0).

- Model 3: cable.price.break
  - Holds MOQ breakpoints and category-specific multipliers (signal, pur, power, ea).
  - Provides _get_break_for_qty and _get_factor helpers.

- Pricing service method:
  - cable.connector.price.compute_quote_price(connector_combined, ac_coding, qty, length_m, category)
  - Computes:
    - connector component
    - cable component
    - purchase price
    - sales factor
    - final sales price
    - tier label

- Initial tests (3 tests):
  - Connector price range boundaries
  - Price break and factor selection
  - Formula correctness for a known fixture

At this point, calculation correctness existed, but there was no automatic wiring into sale.order.line quotation entry flow.

### Commit 2 (38c28c4e2e9c): Quote-Line Automation Layer

The second commit added the full integration into Sales quotation lines and expanded tests from pure pricing math to user workflow behavior.

Main additions:

- New model extension: sale.order.line
  - File: addons/custom_addons/cable_pricing/models/sale_order_line.py
  - Adds cable metadata and computed pricing fields.
  - Parses product code and computes cable pricing details.
  - Automatically writes price_unit for applicable lines.
  - Detects and preserves manual price overrides.
  - Avoids disturbing non-cable standard products.

- New quotation UI extension:
  - File: addons/custom_addons/cable_pricing/views/sale_order_views.xml
  - Adds read-only cable pricing context fields in quotation line form and list views.

- New data files loaded by manifest:
  - data/cable_connector_price_data.xml
  - data/cable_cable_price_data.xml
  - plus sale order view inclusion

- Existing price break data changed:
  - Removed noupdate="1" wrapper in cable_price_break_data.xml
  - Replaced default multipliers (1.0) with tiered realistic multipliers by category

- Test suite expanded from 3 to 8 tests
  - Added parser, create-time auto-pricing, quantity recomputation, standard product fallback, and manual override behavior tests.

## Deep Analysis of Test Changes

Primary test file:
- addons/custom_addons/cable_pricing/tests/test_cable_pricing.py

### 1) Test Data Setup Became End-to-End Ready

New setup behavior in setUpClass:

- Before:
  - Only cable.price.break records were wiped and recreated.
- After:
  - cable.connector.price and cable.cable.price are also wiped and recreated.
  - A partner and a saleable product are created for realistic sale.order and sale.order.line flow.
  - Product default_code is set to cable pattern: Z209BG P 00 A0 0150.

Why this matters:
- The second commit starts loading seeded connector/cable records from XML data files.
- Without explicit cleanup in test setup, fixture collisions could occur.
- Full cleanup guarantees deterministic, isolated tests independent of module data files.

### 2) Existing Pricing Tests Still Anchor Core Math

The original 3 tests remain and still validate:

- Connector boundary mapping:
  - Confirms exact quantity buckets.
- Tier and factor retrieval:
  - Confirms MOQ break selection and category factor lookup.
- Formula integrity:
  - Confirms purchase and sales calculations for known inputs.

This preserved baseline confidence while adding integration behavior.

### 3) New Test: test_parse_cable_pn

What it validates:
- sale.order.line._parse_cable_pn correctly transforms
  - Input: Z209BG P 00 A0 0150
  - Output:
    - connector_combined = Z209BGP
    - option_code = 00
    - ac_coding = A0
    - length_m = 0.150

Why this is important:
- Parsing is now the gate into quote automation.
- If parsing fails, pricing is skipped or flagged, so parser correctness is critical.

### 4) New Test: test_sale_order_line_applies_cable_price_on_create

What it validates:
- Creating a sale.order.line with product and quantity is enough to auto-compute cable pricing details and apply sales price to price_unit.

Key assertions:
- No cable_pricing_error
- Tier set to A
- Connector and AC coding extracted correctly
- Purchase price computed as expected
- price_unit set to computed cable sales price

Why this is the automation core:
- It proves "create quotation line -> price auto-filled" works without manual calculation.

### 5) New Test: test_sale_order_line_recomputes_cable_price_when_qty_changes

What it validates:
- Writing product_uom_qty from 10 to 60 causes:
  - tier transition A -> B
  - recomputed purchase price
  - updated sales factor
  - updated price_unit (rounded per currency precision)

Numerical path in test:
- qty 60
  - connector component = 1.95
  - cable component = 0.8 * 0.150 = 0.12
  - purchase = 2.07
  - B/signal factor = 0.95
  - sales = 2.07 * 0.95 = 1.9665 -> asserted as 1.97 (2 decimals)

Why this matters:
- Confirms dynamic quote maintenance, not just one-time pricing.

### 6) New Test: test_non_cable_product_code_keeps_standard_pricing_without_error

What it validates:
- For standard products (default_code not matching cable pattern):
  - No pricing error is raised.
  - Cable fields remain empty/zero.
  - price_unit stays at normal product list price behavior.

Why this is key for branch intent:
- Protects standard items from cable logic side effects.
- Enables mixed quotation usage where only cable-coded items auto-price.

### 7) New Test: test_manual_price_override_is_preserved_after_qty_change

What it validates:
- If user manually edits price_unit, the system marks line as manual override.
- Later quantity updates do not overwrite user-entered price.

Why this is essential:
- Automation should assist, not force.
- This test verifies user control has priority once they intentionally override.

### 8) Test Runtime Evidence

Execution logs in module tests indicate:
- 8 tests executed
- 0 failed
- 0 errors

Log files:
- addons/custom_addons/cable_pricing/tests/latest_run_utf8.log
- addons/custom_addons/cable_pricing/tests/latest_upgrade_run_utf8.log

## General Workflow (End-to-End)

The automated quotation workflow now follows this path:

1. User creates a quotation line in Sales.
   - product_id and product_uom_qty are set.

2. sale.order.line computes cable pricing details.
   - _compute_cable_pricing_details is triggered by dependencies.

3. System determines candidate P/N source.
   - _get_cable_pn_candidate checks product default_code, then product name.
   - If no parseable product value, it may use manually entered cable_pn.

4. Parser extracts structured components.
   - _parse_cable_pn expects exactly 5 whitespace-separated parts:
     BASE SUFFIX OPTION AC_CODE LENGTH_MM

5. Connector and cable master data lookup.
   - connector via connector_combined
   - cable via ac_coding
   - only active records considered

6. Pricing engine computes values.
   - compute_quote_price:
     - picks connector tier by qty
     - computes cable component as price_per_meter * length_m
     - computes purchase subtotal
     - picks MOQ price break and category factor
     - computes sales price

7. sale.order.line stores computed pricing context.
   - cable_purchase_price
   - cable_sales_factor
   - cable_sales_price
   - cable_tier
   - parsed metadata fields

8. Price unit is auto-applied if allowed.
   - _compute_price_unit writes price_unit = cable_sales_price unless blocked by:
     - display line
     - missing order
     - pricing error
     - invoiced quantity > 0
     - manual override flag

9. Onchange behavior keeps UI responsive.
   - _onchange_cable_pricing updates line price in form interaction.
   - Warnings shown for invalid manual cable_pn format.
   - Non-cable product lines remain silent (no noisy warning).

10. Manual override tracking controls future auto-updates.
    - write method compares price_unit vs cable_sales_price.
    - If different beyond currency precision, cable_manual_price = True.
    - Product or cable_pn changes reset manual flag to re-enable automation on new item definition.

## Why This Is "Automating Quote Creation" in Practice

Before integration:
- You could compute quote prices only by calling pricing methods directly.
- Sales quotation creation still required manual translation from model output to line unit price.

After integration:
- Selecting a cable-coded product in a quotation line triggers parse + lookup + formula + tier logic automatically.
- The final computed quote price is written directly to quotation line unit price.
- Quantity edits reflow pricing automatically.
- Standard products are not broken by cable-specific logic.
- Manual user overrides are respected.

In other words, pricing moved from isolated business calculation to operational quotation workflow automation.

## Design Strengths

- Strong separation of concerns:
  - Pricing models contain rules and data.
  - sale.order.line integration orchestrates UI and pricing application.

- Deterministic tests:
  - Test setup wipes seeded master data and recreates fixtures.

- Backward-safe behavior:
  - Non-cable products keep default Odoo pricing path.

- Human override compatibility:
  - Manual price changes are not clobbered by later qty recomputes.

## Current Constraints and Considerations

- Parser strictness:
  - Requires exactly 5 tokens and numeric length in mm.
  - Any variant formatting fails parsing.

- Category source:
  - Factor category comes from connector.application.
  - Divergence from cable.application is not currently reconciled.

- No dedicated test yet for explicit error payload paths:
  - Missing connector master record
  - Missing cable master record
  - Invalid manual cable_pn warning content

- Currency rounding behavior is implicit through Odoo monetary precision.

## File Map for Fast Navigation

- Module manifest and loaded assets:
  - addons/custom_addons/cable_pricing/__manifest__.py

- Core pricing models:
  - addons/custom_addons/cable_pricing/models/cable_connector_price.py
  - addons/custom_addons/cable_pricing/models/cable_cable_price.py
  - addons/custom_addons/cable_pricing/models/cable_price_break.py
  - addons/custom_addons/cable_pricing/models/constants.py

- Quotation line automation:
  - addons/custom_addons/cable_pricing/models/sale_order_line.py

- Quotation UI exposure:
  - addons/custom_addons/cable_pricing/views/sale_order_views.xml

- Test suite:
  - addons/custom_addons/cable_pricing/tests/test_cable_pricing.py
  - addons/custom_addons/cable_pricing/tests/latest_run_utf8.log
  - addons/custom_addons/cable_pricing/tests/latest_upgrade_run_utf8.log

## Short Conclusion

The key evolution is from a standalone pricing engine to a full sales quotation automation pipeline. The second commit is where automation actually lands: it injects cable pricing into sale.order.line lifecycle, makes it visible in quotation UI, preserves manual edits, avoids affecting standard products, and verifies all of this with end-to-end tests.

## Stakeholder Summary (Short Version)

What changed:
- Quotation line pricing for cable-coded products is now automated in Sales.
- The system now parses the product code, looks up connector and cable master data, applies quantity-tier logic, and fills the line unit price automatically.
- The test suite was expanded from 3 to 8 tests to validate end-to-end behavior, not only pricing math.

Why this matters:
- Sales users can create quotes faster with less manual calculation.
- Pricing consistency improves because every line follows the same tier and factor rules.
- Standard non-cable products are not impacted and keep normal Odoo pricing behavior.

How the workflow works:
1. User adds a product and quantity to a quotation line.
2. The module parses the cable part number format.
3. It retrieves connector and cable prices from master data.
4. It calculates purchase and sales prices using quantity breaks.
5. It writes the computed sales price to the quotation line automatically.

Controls and safeguards:
- Manual price overrides are respected and preserved on later quantity changes.
- Invalid manual cable P/N input triggers a clear warning.
- Missing pricing master data is surfaced through pricing error details.

Business outcome:
- The branch moves pricing from a manual or semi-manual process to a reliable automated quotation flow, while preserving user control where needed.
